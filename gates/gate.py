#!/usr/bin/env python3
"""keyturn's gate: run a project's stack-profile checks and the guardrail checks on a Git range. See ADR 0028.

Usage (from inside the project's repository; the base and the head are checked out in temporary worktrees, so only committed files count):
  gate.sh --base REV [--head REV] [--others ROLE:COMMIT ...] [--log FILE] [--profiles DIR] [--timeout-minutes N]
  gate.sh --task TASK --default-branch REV [--head REV] [--log FILE] [--profiles DIR] [--timeout-minutes N]
    (a task run by deliver, as in CI: the base and the other roles' commits are found from the branch and its state
    file, ADR 0043)

Checks, in this order, each reported as one PASS or FAIL line:
  protected-paths  no change in the range to a protected path ("Guardrails" 1)
  suppressions     no new suppression comment, unless the same line names an accepted ADR that existed at the base
                   (or at the newest spec, design, or conventions commit named with --others)
  pinned-tools     the profile's tools in a part's lock file are at the versions of the newest conventions commit named with
                   --others, or of the base (profiles with "pinned" only)
  install-scripts  no package with an install script in a part's lock file at the head that is not at the base, unless
                   an ADR accepted at the newest spec or design commit named with --others, or at the base, allows it
                   ("- Allows install scripts: <package>@<version>", ADR 0056; profiles with "install_scripts" only)
  test-count       no part has fewer tests at the head than at the base
  <profile check>  each check its profile names (build, test, lint, ...), run in the part's folder at the head,
                   after the profile's setup commands (for example, installing dependencies)

Then one VERSIONS line per part: the versions of the tools its checks ran, as its profile reads them (recorded, never judged).

Exit codes: 0 every check passed; 1 at least one check failed; 2 the gate could not run (setup error).
Needs Python 3.9 or later and Git. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PROJECT_CONFIG = PLUGIN_ROOT / "skills" / "project-config" / "scripts" / "project_config.py"
CONFIG_PATH = "keyturn/config.json"
DESIGN_PATH = "keyturn/internal/design.md"
ADR_DIR = "keyturn/internal/adr"

# Paths no developer change may touch, whatever the profiles say ("Guardrails" 1): the configuration, every other role's
# documents, the CI jobs, and the Git files that change what the checks see. QA's folders come from the design,
# and each profile adds its linter configs, wherever in the repository they are.
FIXED_PROTECTED = (
    CONFIG_PATH,
    "keyturn/client/**",
    "keyturn/internal/**",
    ".github/workflows/**",
    "**/.gitattributes",
    "**/.gitignore",
)
# The developer's own document, under a protected folder.
NOT_PROTECTED = ("keyturn/internal/handoff.md",)

# What a commit named as another role's may change (ADR 0029, ADR 0032, ADR 0033 for "deliver": the state file, and,
# in its last step, the gate's log, the acceptance guide, and the delivery report, and ADR 0039 for the `.gitignore` files
# "conventions" writes, and ADR 0046 for "merge": the client's acceptance), by the step names of the task state file. QA's
# folders from the design are added for "qa", each profile's linter configs for "conventions", and a "security-review"
# commit may change only the "Status" lines of the threat model.
THREAT_MODEL = "keyturn/internal/threat-model.md"
ROLE_PATHS = {
    "spec": ["keyturn/client/requirements.md", "keyturn/client/approvals.md", ".gitattributes", CONFIG_PATH],
    "design": [DESIGN_PATH, THREAT_MODEL, f"{ADR_DIR}/**", "keyturn/client/design-summary.md",
               "keyturn/client/decision-card-*.md"],
    "conventions": ["keyturn/internal/conventions.md", f"{ADR_DIR}/**", CONFIG_PATH, "**/.gitignore"],
    "qa": ["keyturn/internal/test-report.md"],
    "security-review": ["keyturn/internal/security-review.md", THREAT_MODEL],
    "review": ["keyturn/internal/review.md"],
    "deliver": ["keyturn/internal/state/**", "keyturn/internal/gate/**", "keyturn/client/acceptance-guide.md",
                "keyturn/client/delivery-report.md"],
    # The client's acceptance, recorded by the PM in the merge step (ADR 0042, ADR 0046), and the card that asks the
    # client what to do after they did not accept (ADR 0047).
    "merge": ["keyturn/client/approvals.md", "keyturn/client/decision-card-*.md"],
}

PROFILE_FIELDS = {"name", "tools", "setup", "checks", "count_tests", "versions", "pinned", "install_scripts", "source_files",
                  "suppressions", "protected"}
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")
EXIT_PASS, EXIT_FAIL, EXIT_SETUP = 0, 1, 2
# The roles that write the documents the developer is judged against. Their commits all come before the developer's
# (ADR 0031), and the gate reads the design and the ADRs at the newest of them (ADR 0032).
DOCUMENT_ROLES = ("spec", "design", "conventions")

# Every command the gate runs gets the caller's environment without Git's variables: GIT_DIR, GIT_WORK_TREE, and the like
# would point git, and the profile commands, at another repository than the worktree they run in.
ENV = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}


class SetupError(Exception):
    """The gate cannot run. Holds every problem found."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class Result:
    check: str
    part: str | None
    passed: bool
    details: list[str] = field(default_factory=list)

    def line(self) -> str:
        where = f" [{self.part}]" if self.part is not None else ""
        summary = "; ".join(self.details) if self.details else "ok"
        return f"{'PASS' if self.passed else 'FAIL'} {self.check}{where}: {summary}"


@dataclass
class Part:
    path: str  # relative to the repository root, POSIX, "." for the whole repository
    profile: dict

    def contains(self, path: str) -> bool:
        return self.path == "." or path == self.path or path.startswith(self.path + "/")


# --- Git -----------------------------------------------------------------------------------------

def git(root: Path, *args: str, input_text: str | None = None) -> str:
    """Run git in the repository and return stdout. A failure is a setup error, never an empty result."""
    # Bytes, decoded without newline translation: text mode would turn a lone "\r" in a source line into a line break,
    # and a line after it could then read as a patch header.
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=ENV,
                            input=input_text.encode("utf-8") if input_text is not None else None)
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise SetupError([f"git {' '.join(args)}: {error or f'exit {result.returncode}'}"])
    return result.stdout.decode("utf-8", errors="surrogateescape")


def repo_root() -> Path:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, env=ENV)
    if result.returncode != 0:
        raise SetupError(["not inside a Git repository: run the gate from the project's repository"])
    return Path(result.stdout.strip())


def commit_of(root: Path, rev: str) -> str:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
                            capture_output=True, text=True, env=ENV)
    if result.returncode != 0:
        raise SetupError([f"{rev}: not a commit in this repository"])
    return result.stdout.strip()


def file_at(root: Path, commit: str, path: str) -> str | None:
    """A file's text at a commit, or None if it is not there."""
    result = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, env=ENV)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def name_status(root: Path, old: str, new: str) -> list[str]:
    """Every path one diff adds, changes, deletes, or renames (a rename gives both its old and new path)."""
    fields = git(root, "diff", "--name-status", "-z", "-M", "--no-ext-diff", old, new).split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        count = 2 if status[:1] in ("R", "C") else 1
        paths.extend(fields[index + 1:index + 1 + count])
        index += 1 + count
    return paths


def range_commits(root: Path, base: str, head: str) -> list[tuple[str, list[str]]]:
    """Each commit in the range, oldest first, with its parents."""
    commits = []
    for line in git(root, "rev-list", "--reverse", "--parents", f"{base}..{head}").splitlines():
        commit, *parents = line.split()
        commits.append((commit, parents))
    return commits


def changed_paths(root: Path, base: str, head: str, skip: set[str]) -> list[str]:
    """Every path a commit in the range changes, so that a change a later commit undoes is still found.

    A merge is compared with each of its parents. Without commits to skip, the range's total diff counts too;
    with them, it does not, since it holds the skipped commits' changes as well.
    """
    paths = set() if skip else set(name_status(root, base, head))
    for commit, parents in range_commits(root, base, head):
        if commit not in skip:
            for parent in parents:
                paths.update(name_status(root, parent, commit))
    return sorted(paths)


def unquote_git_path(text: str) -> str:
    """Undo Git's C-style quoting of a path in a patch header (octal bytes and backslash escapes)."""
    if not (len(text) >= 2 and text.startswith('"') and text.endswith('"')):
        return text
    escapes = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
    raw = bytearray()
    body = text[1:-1]
    index = 0
    while index < len(body):
        char = body[index]
        if char == "\\" and re.match(r"[0-7]{3}", body[index + 1:index + 4]):
            raw.append(int(body[index + 1:index + 4], 8))
            index += 4
        elif char == "\\" and body[index + 1:index + 2] in escapes:
            raw.append(escapes[body[index + 1]])
            index += 2
        else:
            raw.extend(char.encode("utf-8"))
            index += 1
    return raw.decode("utf-8", errors="replace")


def added_lines(root: Path, base: str, head: str) -> list[tuple[str, int, str]]:
    """Every line the range adds, as (path at the head, line number, text)."""
    # --text and --no-textconv: a .gitattributes entry (`-diff`, `binary`, a textconv driver) or a NUL byte must not hide lines.
    patch = git(root, "-c", "core.quotePath=false", "diff", "--no-color", "--no-ext-diff", "--text", "--no-textconv", "-M", "--unified=0",
                "--src-prefix=a/", "--dst-prefix=b/", base, head)
    lines: list[tuple[str, int, str]] = []
    path: str | None = None
    number = 0
    in_header = False  # between "diff --git" and the file's first "@@": only there is "+++ " a header, not an added "++ " line
    for row in patch.split("\n"):
        if row.startswith("diff --git "):
            in_header, path = True, None
        elif in_header and row.startswith("+++ "):
            # Git ends the name with a tab when it contains a space.
            target = unquote_git_path(row[4:].removesuffix("\t"))
            path = target[2:] if target.startswith("b/") else None  # "/dev/null" for a deleted file
        elif row.startswith("@@"):
            in_header = False
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
            number = int(match.group(1)) if match else 0
        elif not in_header and row.startswith("+") and path is not None:
            lines.append((path, number, row[1:]))
            number += 1
    return lines


# --- Inputs --------------------------------------------------------------------------------------

def pattern_regex(pattern: str) -> re.Pattern:
    """A path pattern as a regular expression: `**` matches across folders, `*` and `?` within one name."""
    out = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out += r"(?:.*/)?"
            index += 3
        elif pattern.startswith("**", index):
            out += r".*"
            index += 2
        elif pattern[index] == "*":
            out += r"[^/]*"
            index += 1
        elif pattern[index] == "?":
            out += r"[^/]"
            index += 1
        else:
            out += re.escape(pattern[index])
            index += 1
    return re.compile(out, re.DOTALL)  # a path may hold a newline, and `.*` must match it too


def matches(path: str, pattern: str) -> bool:
    return pattern_regex(pattern).fullmatch(path) is not None


def load_config(root: Path) -> list[dict]:
    """Check the project configuration with project-config (ADR 0014), then return its parts."""
    result = subprocess.run([sys.executable, str(PROJECT_CONFIG), "check"], cwd=root, capture_output=True, text=True, env=ENV)
    if result.returncode != 0:
        problems = [line.removeprefix("error: ") for line in result.stderr.splitlines() if line.strip()]
        raise SetupError(problems or [f"{CONFIG_PATH}: the check failed"])
    parts = json.loads((root / CONFIG_PATH).read_text(encoding="utf-8")).get("parts")
    if not parts:
        raise SetupError([f"{CONFIG_PATH}: no \"parts\": name each part's folder and stack profile (see the project-config skill)"])
    return parts


def profile_problems(name: str, profile: object) -> list[str]:
    where = f"profile {name}"
    if not isinstance(profile, dict):
        return [f"{where}: must be a JSON object"]
    problems = [f"{where}: {key}: unknown field" for key in sorted(set(profile) - PROFILE_FIELDS)]
    problems += [f"{where}: {key}: missing" for key in sorted(PROFILE_FIELDS - set(profile))]
    if problems:
        return problems
    if profile["name"] != name:
        problems.append(f"{where}: name: {json.dumps(profile['name'])} does not match its folder")
    tools = profile["tools"]
    if not isinstance(tools, list) or not all(
            isinstance(tool, dict) and set(tool) == {"command", "install"} and all(isinstance(v, str) and v for v in tool.values())
            for tool in tools):
        problems.append(f"{where}: tools: must be a list of {{\"command\", \"install\"}} with text values")
    checks = profile["checks"]
    if not isinstance(checks, list) or not checks or not all(
            isinstance(check, dict) and set(check) == {"name", "run"} and isinstance(check["name"], str)
            and NAME_RE.fullmatch(check["name"]) and is_command(check["run"]) for check in checks):
        problems.append(f"{where}: checks: must be a non-empty list of {{\"name\", \"run\"}}, run as a list of words")
    elif len({check["name"] for check in checks}) != len(checks):
        problems.append(f"{where}: checks: names must be unique")
    if not isinstance(profile["setup"], list) or not all(is_command(command) for command in profile["setup"]):
        problems.append(f"{where}: setup: must be a list of commands, each a non-empty list of words (it may be empty)")
    for key in ("count_tests", "versions"):
        if not is_command(profile[key]):
            problems.append(f"{where}: {key}: must be a command, as a non-empty list of words")
    pinned = profile["pinned"]
    if pinned is not None and not (
            isinstance(pinned, dict) and set(pinned) == {"files", "lock", "read"} and is_command(pinned["read"])
            and isinstance(pinned["lock"], str) and is_plain_name(pinned["lock"]) and isinstance(pinned["files"], list)
            and pinned["lock"] in pinned["files"] and all(isinstance(name, str) and is_plain_name(name) for name in pinned["files"])):
        problems.append(f"{where}: pinned: must be null, or {{\"files\", \"lock\", \"read\"}}: file names in the part's folder, "
                        "the lock file among them, and a command")
    scripts = profile["install_scripts"]
    if scripts is not None and not (
            isinstance(scripts, dict) and set(scripts) == {"lock", "read"} and is_command(scripts["read"])
            and isinstance(scripts["lock"], str) and is_plain_name(scripts["lock"])):
        problems.append(f"{where}: install_scripts: must be null, or {{\"lock\", \"read\"}}: a file name in the part's folder, "
                        "and a command")
    for key in ("source_files", "suppressions", "protected"):
        value = profile[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            problems.append(f"{where}: {key}: must be a list of text values")
    if not problems:
        for pattern in profile["suppressions"]:
            try:
                re.compile(pattern)
            except re.error as error:
                problems.append(f"{where}: suppressions: {json.dumps(pattern)}: {error}")
    return problems


def is_plain_name(value: str) -> bool:
    """A file name in the part's folder itself, with no folder in it."""
    return bool(value) and "/" not in value and value not in (".", "..")


def is_command(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(word, str) and word for word in value)


def load_parts(root: Path, profiles_dir: Path) -> list[Part]:
    parts: list[Part] = []
    problems: list[str] = []
    for entry in load_config(root):
        name = entry["profile"]
        path = profiles_dir / name / "profile.json"
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            problems.append(f"profile {name}: no {path}")
            continue
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            problems.append(f"profile {name}: cannot read {path}: {error}")
            continue
        found = profile_problems(name, profile)
        problems += found
        if not found:
            parts.append(Part(entry["path"], profile))
    if problems:
        raise SetupError(problems)
    return parts


def qa_folders(root: Path, base: str) -> list[str]:
    """The path patterns under "QA's tests" in the design at the base (ADR 0017), so that a change in the range cannot narrow them."""
    text = file_at(root, base, DESIGN_PATH)
    if text is None:
        raise SetupError([f"{DESIGN_PATH}: missing at the base (or at the newest design commit named with --others); "
                          "the gate needs its \"QA's tests\" section"])
    section = re.search(r"^## QA's tests\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if section is None:
        raise SetupError([f"{DESIGN_PATH}: no \"QA's tests\" section"])
    folders = [match.group(1) for match in re.finditer(r"^\|\s*`([^`]+)`", section.group(1), re.M)]
    if not folders:
        raise SetupError([f"{DESIGN_PATH}: \"QA's tests\" names no folder (a table row starting with a `path`)"])
    placeholders = [folder for folder in folders if "<" in folder or ">" in folder]
    if placeholders:
        raise SetupError([f"{DESIGN_PATH}: \"QA's tests\" still has a template placeholder: {folder}" for folder in placeholders])
    patterns = []
    for folder in folders:
        folder = folder.rstrip("/")
        # A folder written without a wildcard (`app/qa` or `app/qa/`) protects everything under it.
        patterns += [folder] if any(char in folder for char in "*?") else [folder, f"{folder}/**"]
    return patterns


def check_tools(parts: list[Part]) -> None:
    missing = []
    for part in parts:
        for tool in part.profile["tools"]:
            if shutil.which(tool["command"]) is None:
                missing.append(f"{tool['command']} (profile {part.profile['name']}) is not installed: {tool['install']}")
    if missing:
        raise SetupError(sorted(set(missing)))


# --- Checks --------------------------------------------------------------------------------------

def protected_patterns(parts: list[Part], qa: list[str]) -> list[str]:
    patterns = list(FIXED_PROTECTED) + qa
    for part in parts:
        # Anywhere in the repository: `conventions` puts a config above the part when the part's folder is one the developer may change.
        patterns += [f"**/{pattern}" for pattern in part.profile["protected"]]
    return sorted(set(patterns), key=patterns.index)


def check_protected(paths: list[str], patterns: list[str]) -> Result:
    hits = sorted({f"{path} (matches {pattern})" for path in paths if path not in NOT_PROTECTED
                   for pattern in patterns if matches(path, pattern)})
    return Result("protected-paths", None, not hits, hits)


@dataclass
class Allowed:
    """What the project's accepted ADRs allow: by number, the text a line that names the ADR may contain ("- Allows: <text>"),
    and, for every line in a file matching a path pattern, the text it may contain without naming the ADR
    ("- Allows in <pattern>: <text>", ADR 0038), as (pattern, text, ADR number)."""
    named: dict[str, list[str]] = field(default_factory=dict)
    placed: list[tuple[str, str, str]] = field(default_factory=list)
    # "- Allows install scripts: <package>@<version>" (ADR 0055, ADR 0056): by "<package>@<version>", the ADR number.
    scripts: dict[str, str] = field(default_factory=dict)


def accepted_adrs(root: Path, base: str) -> Allowed:
    """What the project's ADRs accepted at a commit allow: the base, or the newest commit named as a document role's
    (ADR 0032), so that no ADR the developer's commits add can approve anything.

    Only the lines before the first "## " heading count: "- Status: accepted", one "- Allows: <text>" or
    "- Allows in <path pattern>: <text>" line per suppression it allows, and one "- Allows install scripts:
    <package>@<version>" line per package whose install script it allows.
    """
    listing = git(root, "ls-tree", "-z", "--name-only", f"{base}:{ADR_DIR}") if file_at(root, base, ADR_DIR) is not None else ""
    allowed = Allowed()
    for name in filter(None, listing.split("\0")):
        match = re.fullmatch(r"(\d{4})-.*\.md", name)
        text = file_at(root, base, f"{ADR_DIR}/{name}") if match else None
        if not text:
            continue
        header = re.split(r"^## ", text, maxsplit=1, flags=re.M)[0]
        if re.search(r"^- Status: accepted\s*$", header, re.M):
            number = match.group(1)
            allowed.named[number] = [value for value in map(allowed_text, re.findall(r"^- Allows: (.+)$", header, re.M)) if value]
            for pattern, value in re.findall(r"^- Allows in `?([^`:\s]+)`?: (.+)$", header, re.M):
                if allowed_text(value):
                    allowed.placed.append((pattern, allowed_text(value), number))
            for value in re.findall(r"^- Allows install scripts: (.+)$", header, re.M):
                if allowed_text(value):
                    allowed.scripts.setdefault(allowed_text(value), number)
    return allowed


def allowed_text(value: str) -> str:
    """An allowed suppression as the ADR writes it, without the backticks around it (`//nolint:gosec`)."""
    value = value.strip()
    return value[1:-1].strip() if len(value) > 2 and value.startswith("`") and value.endswith("`") else value


def check_suppressions(root: Path, base: str, head: str, parts: list[Part], others: dict[str, str],
                       documents: str) -> list[Result]:
    # QA's commits are checked too: a suppression in QA's tests needs an ADR as the developer's does (ADR 0029).
    skip = {commit for commit, role in others.items() if role != "qa"}
    if others:  # commit by commit, leaving out the other roles' commits
        added = [line for commit, parents in range_commits(root, base, head) if commit not in skip
                 for line in added_lines(root, parents[0], commit)]
    else:
        added = added_lines(root, base, head)
    approved = accepted_adrs(root, documents)
    results = []
    for part in parts:
        patterns = [re.compile(pattern) for pattern in part.profile["suppressions"]]
        hits = []
        for path, number, text in added:
            name = PurePosixPath(path).name
            # A file outside every part is checked by every profile: nothing else builds or lints it.
            inside = part.contains(path) or not any(other.contains(path) for other in parts)
            if not inside or not any(matches(name, glob) for glob in part.profile["source_files"]):
                continue
            if any(pattern.search(text) for pattern in patterns):
                named = ADR_REF_RE.findall(text)
                # Approved only by an ADR that was accepted at the base and allows what this line writes: one the line
                # names, or one that allows it in this file's folder.
                if not any(allowed in text for adr in named for allowed in approved.named.get(adr, [])) and not any(
                        allowed in text and matches(path, where) for where, allowed, _ in approved.placed):
                    if not named:
                        reason = "names no accepted ADR"
                    elif not any(adr in approved.named for adr in named):
                        reason = f"names ADR-{', ADR-'.join(named)}, not accepted at the base"
                    else:
                        reason = f"ADR-{', ADR-'.join(named)} has no \"- Allows:\" line that this line contains"
                    hits.append(f"{path}:{number}: {text.strip()} ({reason})")
        results.append(Result("suppressions", part.path, not hits, hits))
    return results


def run(command: list[str], cwd: Path, timeout: float) -> tuple[int, str]:
    """Run a profile's command; return its exit code and the end of its output."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=ENV)
    except FileNotFoundError:
        return 127, f"{command[0]}: command not found"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout / 60:g} minutes"
    output = (result.stdout + result.stderr).strip().splitlines()
    return result.returncode, "\n".join(output[-20:])


def count_tests(part: Part, tree: Path, timeout: float) -> tuple[int | None, str]:
    """The number of tests in the part's folder of a checkout, or None and why it could not be counted."""
    folder = tree / part.path
    if not folder.is_dir():
        return 0, "the folder is not there"
    code, output = run(part.profile["count_tests"], folder, timeout)
    last = output.splitlines()[-1].strip() if output else ""
    if code != 0 or not re.fullmatch(r"[0-9]+", last):
        return None, f"count_tests failed (exit {code}): {output or 'no output'}"
    return int(last), ""


class Trees:
    """Fresh worktrees of the base and the head, so that only committed files are checked, and each part set up once in each."""

    def __init__(self, root: Path, base: str, head: str, temp: Path, timeout: float):
        self.root, self.timeout = root, timeout
        self.paths = {"base": temp / "base", "head": temp / "head"}
        for name, commit in (("base", base), ("head", head)):
            git(root, "worktree", "add", "--detach", "--quiet", str(self.paths[name]), commit)
        self.prepared: dict[tuple[str, str], str] = {}

    def remove(self) -> None:
        for path in self.paths.values():
            subprocess.run(["git", "-C", str(self.root), "worktree", "remove", "--force", str(path)], capture_output=True, env=ENV)

    def prepare(self, name: str, part: Part) -> str:
        """Run the profile's setup in the part's folder once; return "" when it worked, or why it did not."""
        key = (name, part.path)
        if key not in self.prepared:
            folder = self.paths[name] / part.path
            problem = ""
            tree = self.paths[name].resolve()
            if folder.exists() and tree != folder.resolve() and tree not in folder.resolve().parents:
                problem = f"{part.path} leads outside the repository (a symbolic link?); only the committed folder is checked"
            elif folder.is_dir():
                for command in part.profile["setup"]:
                    code, output = run(command, folder, self.timeout)
                    if code != 0:
                        problem = f"setup failed (exit {code}): {output or 'no output'}"
                        break
            self.prepared[key] = problem
        return self.prepared[key]


def count_in(trees: Trees, name: str, part: Part) -> tuple[int | None, str]:
    problem = trees.prepare(name, part)
    if problem:
        return None, problem
    return count_tests(part, trees.paths[name], trees.timeout)


def check_test_count(trees: Trees, parts: list[Part]) -> list[Result]:
    results = []
    for part in parts:
        before, why_before = count_in(trees, "base", part)
        after, why_after = count_in(trees, "head", part)
        if before is None or after is None:
            details = [f"at the base: {why_before}" if before is None else "", f"at the head: {why_after}" if after is None else ""]
            results.append(Result("test-count", part.path, False, [d for d in details if d]))
        else:
            results.append(Result("test-count", part.path, after >= before, [f"{before} tests at the base, {after} at the head"]))
    return results


def check_profile(trees: Trees, parts: list[Part]) -> list[Result]:
    results = []
    for part in parts:
        problem = trees.prepare("head", part)
        for check in part.profile["checks"]:
            if problem:
                results.append(Result(check["name"], part.path, False, [f"not run: {problem}"]))
                continue
            code, output = run(check["run"], trees.paths["head"] / part.path, trees.timeout)
            details = [] if code == 0 else [f"exit {code}: {output or 'no output'}"]
            results.append(Result(check["name"], part.path, code == 0, details))
    return results


def in_part(part: Part, name: str) -> str:
    return name if part.path == "." else f"{part.path}/{name}"


def read_lock(command: list[str], text: str, timeout: float) -> tuple[str | None, str]:
    """What a profile's command prints for a lock file's text ("" when there is none), run in an empty folder, or None
    and why it failed."""
    with tempfile.TemporaryDirectory(prefix="keyturn-lock-") as folder:
        try:
            result = subprocess.run(command, cwd=folder, input=text, capture_output=True, text=True, timeout=timeout, env=ENV)
        except (OSError, subprocess.TimeoutExpired) as error:
            return None, str(error)
    if result.returncode != 0:
        return None, (result.stdout + result.stderr).strip() or f"exit {result.returncode}"
    return result.stdout, ""


def pinned_versions(part: Part, text: str, timeout: float) -> tuple[dict[str, str] | None, str]:
    """The versions the profile's `pinned.read` reads from a lock file's text ("" when there is none), by tool name."""
    output, why = read_lock(part.profile["pinned"]["read"], text, timeout)
    if output is None:
        return None, why
    versions = {}
    for line in output.splitlines():
        name, _, version = line.strip().partition(" ")
        if name:
            versions[name] = version.strip()
    return versions, ""


def check_pinned(root: Path, reference: str, where: str, head: str, parts: list[Part], timeout: float) -> list[Result]:
    """The profile's tools at the head are at the versions in the lock file at the reference: the newest commit named as
    conventions', or else the base (ADR 0040). A tool missing at one and present at the other is a change too."""
    results = []
    for part in parts:
        if part.profile["pinned"] is None:
            continue
        lock = in_part(part, part.profile["pinned"]["lock"])
        before, why_before = pinned_versions(part, file_at(root, reference, lock) or "", timeout)
        after, why_after = pinned_versions(part, file_at(root, head, lock) or "", timeout)
        if before is None or after is None:
            details = [f"{lock} at {where}: {why_before}" if before is None else "", f"{lock} at the head: {why_after}" if after is None else ""]
            results.append(Result("pinned-tools", part.path, False, [d for d in details if d]))
            continue
        changed = [f"{name}: {before.get(name) or 'not installed'} at {where}, {after.get(name) or 'not installed'} at the head"
                   for name in sorted(set(before) | set(after)) if (before.get(name) or "") != (after.get(name) or "")]
        results.append(Result("pinned-tools", part.path, not changed, changed))
    return results


def architect_commit(root: Path, base: str, head: str, others: dict[str, str]) -> tuple[str, str]:
    """The newest commit in the range named as spec's or design's, or else the base, and how to name it in a result. Only
    the architect writes "- Allows install scripts:" (ADR 0055), so a conventions commit, which may write ADRs too, is
    not where those lines are read (ADR 0056)."""
    reference, where = base, "the base"
    for commit, _ in range_commits(root, base, head):
        if others.get(commit) in ("spec", "design"):
            reference, where = commit, f"the {others[commit]} commit {commit[:12]}"
    return reference, where


def check_install_scripts(root: Path, base: str, head: str, parts: list[Part], others: dict[str, str],
                          timeout: float) -> list[Result]:
    """Every package with an install script in the lock file at the head that was not there, at that version, at the base
    is allowed by an ADR accepted at the newest spec or design commit, or else at the base (ADR 0056)."""
    reference, where = architect_commit(root, base, head, others)
    allowed = accepted_adrs(root, reference).scripts
    results = []
    for part in parts:
        if part.profile["install_scripts"] is None:
            continue
        lock = in_part(part, part.profile["install_scripts"]["lock"])
        found = {}
        for name, commit in (("the base", base), ("the head", head)):
            output, why = read_lock(part.profile["install_scripts"]["read"], file_at(root, commit, lock) or "", timeout)
            if output is None:
                results.append(Result("install-scripts", part.path, False, [f"{lock} at {name}: {why}"]))
                break
            found[name] = {line.strip() for line in output.splitlines() if line.strip()}
        else:
            new = sorted(found["the head"] - found["the base"])
            hits = [f"{lock}: {package} runs scripts on install, and no ADR accepted at {where} has "
                    f"\"- Allows install scripts: {package}\"" for package in new if package not in allowed]
            details = hits or [f"{package}: allowed by ADR-{allowed[package]}" for package in new]
            results.append(Result("install-scripts", part.path, not hits, details))
    return results


def conventions_commit(root: Path, base: str, head: str, others: dict[str, str]) -> tuple[str, str]:
    """The newest commit in the range named as conventions', or else the base, and how to name it in a result."""
    reference, where = base, "the base"
    for commit, _ in range_commits(root, base, head):
        if others.get(commit) == "conventions":
            reference, where = commit, f"the conventions commit {commit[:12]}"
    return reference, where


def read_versions(trees: Trees, parts: list[Part]) -> list[dict]:
    """The versions of the tools each part's checks ran, from its profile's `versions` command at the head (ADR 0037).
    Only recorded: a command that fails says so, and never fails the gate."""
    records = []
    for part in parts:
        problem = trees.prepare("head", part)
        if problem:
            lines = [f"not read: {problem}"]
        else:
            code, output = run(part.profile["versions"], trees.paths["head"] / part.path, trees.timeout)
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if code != 0 or not lines:
                lines = [f"not read (exit {code}): {'; '.join(lines) or 'no output'}"]
        records.append({"part": part.path, "profile": part.profile["name"], "versions": lines})
    return records


def parse_others(root: Path, values: list[str]) -> dict[str, str]:
    """`--others ROLE:COMMIT` values as {commit: role}."""
    others: dict[str, str] = {}
    problems = []
    for value in values:
        role, _, rev = value.partition(":")
        if role not in ROLE_PATHS or not rev:
            problems.append(f"--others {value}: use ROLE:COMMIT, with ROLE one of {', '.join(ROLE_PATHS)}")
            continue
        try:
            commit = commit_of(root, rev)
        except SetupError as error:
            problems += error.problems
            continue
        if others.get(commit, role) != role:
            problems.append(f"--others {value}: the commit is also named as {others[commit]}'s")
        others[commit] = role
    if problems:
        raise SetupError(problems)
    return others


def documents_commit(root: Path, base: str, head: str, others: dict[str, str]) -> str:
    """Where the design and the ADRs are read: the newest commit named as spec's, design's, or conventions', or else the base.

    Stops when such a commit comes after a commit that is not named, since the developer is then judged against
    documents that changed after their work started (ADR 0031, ADR 0032).
    """
    documents, developer = base, None
    for commit, _ in range_commits(root, base, head):
        role = others.get(commit)
        if role in DOCUMENT_ROLES:
            if developer is not None:
                raise SetupError([f"the commits named as other roles' do not match the range: {commit[:12]} ({role}): "
                                  f"comes after {developer[:12]}, which is not named; the documents are fixed before "
                                  "the developer's work"])
            documents = commit
        elif role is None:
            developer = developer or commit
    return documents


def check_others(root: Path, base: str, head: str, others: dict[str, str], qa: list[str], configs: list[str]) -> None:
    """Stop unless each commit named as another role's is in the range and changes only what that role may write (ADR 0029)."""
    commits = dict(range_commits(root, base, head))
    problems = [f"{commit[:12]} ({role}): not in the range" for commit, role in others.items() if commit not in commits]
    if others:  # without a list, a merge is checked like any commit (ADR 0028)
        problems += [f"{commit[:12]}: a merge in the range; a task run by deliver has none" for commit, parents in commits.items()
                     if len(parents) > 1]
    for commit, role in others.items():
        if commit not in commits or len(commits[commit]) != 1:
            continue
        parent = commits[commit][0]
        allowed = ROLE_PATHS[role] + {"qa": qa, "conventions": configs}.get(role, [])
        outside = [path for path in name_status(root, parent, commit) if not any(matches(path, p) for p in allowed)]
        problems += [f"{commit[:12]} ({role}): changes {path}, which a {role} commit may not" for path in outside]
        if role == "security-review":
            diff = git(root, "diff", "--no-color", "--no-ext-diff", "--text", "--no-textconv", "--unified=0", parent, commit,
                       "--", THREAT_MODEL)
            changed = [row for row in diff.split("\n") if row[:1] in ("+", "-") and not row.startswith(("+++ ", "--- "))]
            if any(not re.match(r"[+-]- Status: ", row) for row in changed):
                problems.append(f"{commit[:12]} (security-review): changes a line of {THREAT_MODEL} other than a \"Status\" line")
    if problems:
        raise SetupError(["the commits named as other roles' do not match the range: " + problem for problem in problems])


# --- A task's range, found by the gate itself (CI) -------------------------------------------------

STATE_DIR = "keyturn/internal/state"
TASK_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
STATE_COMMIT_RE = re.compile(r"- `([0-9a-f]{7,40})`: ([a-z-]+), round [1-9][0-9]*")
# The steps of the task state file whose commits are another role's; "implement" is the developer's.
LATER_ROLES = ("qa", "security-review", "review", "deliver", "merge")


def state_section(text: str, name: str) -> list[str]:
    """The lines of one "## " section of a task state file."""
    lines, inside = [], False
    for line in re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == name
        elif inside:
            lines.append(line.strip())
    return lines


def state_commits(text: str, where: str) -> list[tuple[str, str]]:
    """The "Commits" lines of a task state file, as (short hash, step), oldest first."""
    listed = []
    for line in state_section(text, "Commits"):
        if not line.startswith("- "):
            continue
        match = STATE_COMMIT_RE.fullmatch(line)
        if match is None:
            raise SetupError([f"{where}: a \"Commits\" line is not `- `<commit>`: <step>, round <n>`: {line}"])
        listed.append((match.group(1), match.group(2)))
    return listed


def conventions_recorded(text: str) -> bool:
    for line in state_section(text, "Steps"):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == "conventions":
            return cells[1] == "done"
    return False


def task_range(root: Path, task: str, default_rev: str, head_rev: str) -> tuple[str, list[str]]:
    """The base and the other roles' commits of a task's range, found as deliver finds them, without its session (ADR 0043).

    The base is where the task branch left the default branch (ADR 0032). The commits of spec, design, and conventions
    are read only from the state file as committed when the conventions step was recorded, never from a later version;
    the later roles' commits are read from the state file at the head, as after a resume, and each is still checked
    against what its role may write (ADR 0029).
    """
    if not TASK_RE.fullmatch(task):
        raise SetupError([f"--task {task}: not a task name (lowercase letters and digits with single hyphens)"])
    state = f"{STATE_DIR}/{task}.md"
    head = commit_of(root, head_rev)
    default = commit_of(root, default_rev)
    merge_base = subprocess.run(["git", "-C", str(root), "merge-base", default, head], capture_output=True, text=True, env=ENV)
    if merge_base.returncode != 0:
        raise SetupError([f"{default_rev} and {head_rev} have no commit in common"])
    base = merge_base.stdout.strip()
    added = git(root, "log", "--diff-filter=A", "--reverse", "--format=%H", f"{base}..{head}", "--", state).split()
    if not added:
        raise SetupError([f"{state}: not added on the task branch after it left {default_rev}"])
    first_parent = git(root, "rev-parse", f"{added[0]}^").strip()
    if first_parent != base:
        raise SetupError([f"{state} was added by {added[0][:12]}, whose parent is not where the task branch left "
                          f"{default_rev} ({base[:12]}); a ref was moved"])
    commits = [commit for commit, _ in range_commits(root, base, head)]

    def resolve(short: str, where: str, among: list[str]) -> str:
        """The commit a listed hash names, looked up only among the commits that version could list."""
        found = [commit for commit in among if commit.startswith(short)]
        if len(found) != 1:
            raise SetupError([f"{where}: `{short}` is {'not a' if not found else 'more than one'} commit it could list"])
        return found[0]

    recorded = None
    for commit in git(root, "log", "--reverse", "--format=%H", f"{base}..{head}", "--", state).split():
        text = file_at(root, commit, state)
        if text is not None and conventions_recorded(text):
            recorded = (commit, text)
            break
    if recorded is None:
        raise SetupError([f"{state}: the conventions step is not recorded yet, so the developer's work has not started; "
                          "the gate runs once implement has"])
    others: dict[str, str] = {}
    where = f"{state} at {recorded[0][:12]}"
    # The version at the record can list only the commits before it: a commit made later, whose hash a developer chose to
    # start the same way, is never one of them.
    before_record = commits[:commits.index(recorded[0])]
    for short, step in state_commits(recorded[1], where):
        if step in DOCUMENT_ROLES or step == "deliver":
            others[resolve(short, where, before_record)] = step

    text = file_at(root, head, state)
    if text is None:
        raise SetupError([f"{state}: missing at the head"])
    where = f"{state} at the head"
    listed: dict[str, str] = {}  # every listed commit's step, "implement" included
    for short, step in state_commits(text, where):
        commit = resolve(short, where, commits)
        if listed.get(commit, step) != step:
            raise SetupError([f"{where}: `{short}` is named as {step}'s, and as {listed[commit]}'s too"])
        listed[commit] = step
        if step in DOCUMENT_ROLES:
            if others.get(commit) != step:
                raise SetupError([f"{where}: `{short}` is named as {step}'s, which the state file did not say when "
                                  "conventions was recorded; a later line naming a document role is never trusted"])
        elif step in LATER_ROLES or step == "implement":
            role = None if step == "implement" else step
            if others.get(commit, role) != role:
                raise SetupError([f"{where}: `{short}` is named as {step}'s, and as {others[commit]}'s before"])
            if role is not None:
                others[commit] = role
        else:
            raise SetupError([f"{where}: `{short}`: {step} is not a step of the task state file"])
    # The newest state commit cannot list itself: the head, when no line lists it and it changes only the state file.
    if head not in listed and head not in others and name_status(root, f"{head}^", head) == [state]:
        others[head] = "deliver"
    return base, [f"{role}:{commit}" for commit, role in others.items()]


def gate(base_rev: str, head_rev: str, profiles_dir: Path, timeout: float,
         others_values: list[str]) -> tuple[str, str, list[Result], list[dict]]:
    root = repo_root()
    base, head = commit_of(root, base_rev), commit_of(root, head_rev)
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, head], env=ENV).returncode != 0:
        raise SetupError([f"{base_rev} is not an ancestor of {head_rev}: name the commit the change started from"])
    others = parse_others(root, others_values)
    with tempfile.TemporaryDirectory(prefix="keyturn-gate-") as temp:
        trees = Trees(root, base, head, Path(temp), timeout)
        try:
            parts = load_parts(trees.paths["head"], profiles_dir)
            documents = documents_commit(root, base, head, others)
            qa = qa_folders(root, documents)
            configs = [f"**/{pattern}" for part in parts for pattern in part.profile["protected"]]
            configs += [in_part(part, name) for part in parts if part.profile["pinned"] for name in part.profile["pinned"]["files"]]
            check_others(root, base, head, others, qa, configs)
            check_tools(parts)
            skip = set(others)
            results = [check_protected(changed_paths(root, base, head, skip), protected_patterns(parts, qa))]
            results += check_suppressions(root, base, head, parts, others, documents)
            results += check_pinned(root, *conventions_commit(root, base, head, others), head, parts, timeout)
            results += check_install_scripts(root, base, head, parts, others, timeout)
            results += check_test_count(trees, parts)
            results += check_profile(trees, parts)
            versions = read_versions(trees, parts)
        finally:
            trees.remove()
    return base, head, results, versions


def main() -> int:
    parser = argparse.ArgumentParser(description="Run keyturn's gate on a Git range (ADR 0028).")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--base", help="the commit the change started from")
    where.add_argument("--task", help="a task run by deliver: find the base and the other roles' commits from the branch and "
                                      "its state file, as in CI (ADR 0043); needs --default-branch")
    parser.add_argument("--default-branch", help="with --task: the default branch the task branch left (for example origin/main)")
    parser.add_argument("--head", default="HEAD", help="the last commit of the change (default: HEAD)")
    parser.add_argument("--log", type=Path, help="also write the result as JSON to this file")
    parser.add_argument("--profiles", type=Path, default=PLUGIN_ROOT / "profiles", help="the folder of stack profiles")
    parser.add_argument("--timeout-minutes", type=float, default=30, help="the limit for each command (default: 30)")
    parser.add_argument("--others", action="append", default=[], metavar="ROLE:COMMIT",
                        help="a commit in the range that is another role's (spec, design, conventions, qa, security-review, review, deliver); "
                             "repeat for each (ADR 0029, ADR 0032)")
    args = parser.parse_args()
    if args.task is not None and (args.others or args.default_branch is None):
        parser.error("--task needs --default-branch, and finds the other roles' commits itself (no --others)")
    if args.task is None and args.default_branch is not None:
        parser.error("--default-branch goes with --task")

    try:
        base_rev, others = args.base, args.others
        if args.task is not None:
            base_rev, others = task_range(repo_root(), args.task, args.default_branch, args.head)
        base, head, results, versions = gate(base_rev, args.head, args.profiles, args.timeout_minutes * 60, others)
    except SetupError as error:
        for problem in error.problems:
            print(f"setup error: {problem}", file=sys.stderr)
        return EXIT_SETUP
    except Exception as error:  # an unexpected error must never look like a pass
        print(f"setup error: unexpected: {error!r}", file=sys.stderr)
        return EXIT_SETUP
    passed = all(result.passed for result in results)
    for result in results:
        print(result.line())
    for record in versions:
        print(f"VERSIONS [{record['part']}]: {'; '.join(record['versions'])}")
    print(f"gate: {'passed' if passed else 'failed'} ({base[:12]}..{head[:12]})")
    if args.log is not None:
        record = {"base": base, "head": head, "passed": passed,
                  "checks": [{"check": r.check, "part": r.part, "passed": r.passed, "details": r.details} for r in results],
                  "versions": versions}
        try:
            args.log.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as error:
            print(f"setup error: cannot write the log {args.log}: {error.strerror or error}", file=sys.stderr)
            return EXIT_SETUP
    return EXIT_PASS if passed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
