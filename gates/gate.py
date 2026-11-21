#!/usr/bin/env python3
"""keyturn's gate: run a project's stack-profile checks and the guardrail checks on a Git range. See ADR 0028.

Usage (from inside the project's repository; the base and the head are checked out in temporary worktrees, so only committed files count):
  gate.sh --base REV [--head REV] [--others ROLE:COMMIT ...] [--log FILE] [--profiles DIR] [--timeout-minutes N]

Checks, in this order, each reported as one PASS or FAIL line:
  protected-paths  no change in the range to a protected path ("Guardrails" 1)
  suppressions     no new suppression comment, unless the same line names an accepted ADR that existed at the base
  test-count       no part has fewer tests at the head than at the base
  <profile check>  each check its profile names (build, test, lint, ...), run in the part's folder at the head,
                   after the profile's setup commands (for example, installing dependencies)

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

# What a commit named as another role's may change (ADR 0029). QA's folders from the design are added for "qa", and a
# "security" commit may change only the "Status" lines of the threat model.
THREAT_MODEL = "keyturn/internal/threat-model.md"
ROLE_PATHS = {
    "qa": ["keyturn/internal/test-report.md"],
    "security": ["keyturn/internal/security-review.md", THREAT_MODEL],
    "review": ["keyturn/internal/review.md"],
    "deliver": ["keyturn/internal/state/**"],
}

PROFILE_FIELDS = {"name", "tools", "setup", "checks", "count_tests", "source_files", "suppressions", "protected"}
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")
EXIT_PASS, EXIT_FAIL, EXIT_SETUP = 0, 1, 2

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
    if not is_command(profile["count_tests"]):
        problems.append(f"{where}: count_tests: must be a command, as a non-empty list of words")
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
        raise SetupError([f"{DESIGN_PATH}: missing at the base; the gate needs its \"QA's tests\" section"])
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


def accepted_adrs(root: Path, base: str) -> dict[str, list[str]]:
    """What each of the project's ADRs accepted at the base allows, by number, so that none the range adds can approve anything.

    Only the lines before the first "## " heading count: "- Status: accepted", and one "- Allows: <text>" line per suppression it allows.
    """
    listing = git(root, "ls-tree", "-z", "--name-only", f"{base}:{ADR_DIR}") if file_at(root, base, ADR_DIR) is not None else ""
    allows: dict[str, list[str]] = {}
    for name in filter(None, listing.split("\0")):
        match = re.fullmatch(r"(\d{4})-.*\.md", name)
        text = file_at(root, base, f"{ADR_DIR}/{name}") if match else None
        if not text:
            continue
        header = re.split(r"^## ", text, maxsplit=1, flags=re.M)[0]
        if re.search(r"^- Status: accepted\s*$", header, re.M):
            allows[match.group(1)] = [value.strip() for value in re.findall(r"^- Allows: (.+)$", header, re.M) if value.strip()]
    return allows


def check_suppressions(root: Path, base: str, head: str, parts: list[Part], skip: set[str]) -> list[Result]:
    if skip:  # commit by commit, leaving out the other roles' commits
        added = [line for commit, parents in range_commits(root, base, head) if commit not in skip
                 for line in added_lines(root, parents[0], commit)]
    else:
        added = added_lines(root, base, head)
    approved = accepted_adrs(root, base)
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
                # Approved only by an ADR that was accepted at the base and allows what this line writes.
                if not any(allowed in text for adr in named for allowed in approved.get(adr, [])):
                    if not named:
                        reason = "names no accepted ADR"
                    elif not any(adr in approved for adr in named):
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


def check_others(root: Path, base: str, head: str, others: dict[str, str], qa: list[str]) -> None:
    """Stop unless each commit named as another role's is in the range and changes only what that role may write (ADR 0029)."""
    commits = dict(range_commits(root, base, head))
    problems = [f"{commit[:12]} ({role}): not in the range" for commit, role in others.items() if commit not in commits]
    problems += [f"{commit[:12]}: a merge in the range; a task run by deliver has none" for commit, parents in commits.items()
                 if len(parents) > 1]
    for commit, role in others.items():
        if commit not in commits or len(commits[commit]) != 1:
            continue
        parent = commits[commit][0]
        allowed = ROLE_PATHS[role] + (qa if role == "qa" else [])
        outside = [path for path in name_status(root, parent, commit) if not any(matches(path, p) for p in allowed)]
        problems += [f"{commit[:12]} ({role}): changes {path}, which a {role} commit may not" for path in outside]
        if role == "security":
            diff = git(root, "diff", "--no-color", "--no-ext-diff", "--text", "--no-textconv", "--unified=0", parent, commit,
                       "--", THREAT_MODEL)
            changed = [row for row in diff.split("\n") if row[:1] in ("+", "-") and not row.startswith(("+++ ", "--- "))]
            if any(not re.match(r"[+-]- Status: ", row) for row in changed):
                problems.append(f"{commit[:12]} (security): changes a line of {THREAT_MODEL} other than a \"Status\" line")
    if problems:
        raise SetupError(["the commits named as other roles' do not match the range: " + problem for problem in problems])


def gate(base_rev: str, head_rev: str, profiles_dir: Path, timeout: float,
         others_values: list[str]) -> tuple[str, str, list[Result]]:
    root = repo_root()
    base, head = commit_of(root, base_rev), commit_of(root, head_rev)
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, head], env=ENV).returncode != 0:
        raise SetupError([f"{base_rev} is not an ancestor of {head_rev}: name the commit the change started from"])
    others = parse_others(root, others_values)
    with tempfile.TemporaryDirectory(prefix="keyturn-gate-") as temp:
        trees = Trees(root, base, head, Path(temp), timeout)
        try:
            parts = load_parts(trees.paths["head"], profiles_dir)
            qa = qa_folders(root, base)
            check_others(root, base, head, others, qa)
            check_tools(parts)
            skip = set(others)
            results = [check_protected(changed_paths(root, base, head, skip), protected_patterns(parts, qa))]
            results += check_suppressions(root, base, head, parts, skip)
            results += check_test_count(trees, parts)
            results += check_profile(trees, parts)
        finally:
            trees.remove()
    return base, head, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run keyturn's gate on a Git range (ADR 0028).")
    parser.add_argument("--base", required=True, help="the commit the change started from")
    parser.add_argument("--head", default="HEAD", help="the last commit of the change (default: HEAD)")
    parser.add_argument("--log", type=Path, help="also write the result as JSON to this file")
    parser.add_argument("--profiles", type=Path, default=PLUGIN_ROOT / "profiles", help="the folder of stack profiles")
    parser.add_argument("--timeout-minutes", type=float, default=30, help="the limit for each command (default: 30)")
    parser.add_argument("--others", action="append", default=[], metavar="ROLE:COMMIT",
                        help="a commit in the range that is another role's (qa, security, review, deliver); repeat for each (ADR 0029)")
    args = parser.parse_args()

    try:
        base, head, results = gate(args.base, args.head, args.profiles, args.timeout_minutes * 60, args.others)
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
    print(f"gate: {'passed' if passed else 'failed'} ({base[:12]}..{head[:12]})")
    if args.log is not None:
        record = {"base": base, "head": head, "passed": passed,
                  "checks": [{"check": r.check, "part": r.part, "passed": r.passed, "details": r.details} for r in results]}
        try:
            args.log.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as error:
            print(f"setup error: cannot write the log {args.log}: {error.strerror or error}", file=sys.stderr)
            return EXIT_SETUP
    return EXIT_PASS if passed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
