#!/usr/bin/env python3
"""keyturn's gate: run a project's stack-profile checks and the guardrail checks on a Git range. See ADR 0028.

Usage (from inside the project's repository, with the head commit checked out and nothing uncommitted):
  gate.sh --base REV [--head REV] [--log FILE] [--profiles DIR] [--timeout-minutes N]

Checks, in this order, each reported as one PASS or FAIL line:
  protected-paths  no change in the range to a protected path ("Guardrails" 1)
  suppressions     no new suppression comment, unless the same line names an accepted ADR that existed at the base
  test-count       no part has fewer tests at the head than at the base
  <profile check>  each check its profile names (build, test, lint, ...), run in the part's folder

Exit codes: 0 every check passed; 1 at least one check failed; 2 the gate could not run (setup error).
Needs Python 3.9 or later and Git. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
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

# Paths no developer change may touch, whatever the profiles say ("Guardrails" 1). QA's folders come from the design,
# and each profile adds its linter configs, wherever in the repository they are. The handoff notes are the developer's, so `keyturn/internal/` is not listed whole.
FIXED_PROTECTED = (
    CONFIG_PATH,
    DESIGN_PATH,
    "keyturn/internal/conventions.md",
    f"{ADR_DIR}/**",
    ".github/workflows/**",
)

PROFILE_FIELDS = {"name", "tools", "checks", "count_tests", "source_files", "suppressions", "protected"}
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")
EXIT_PASS, EXIT_FAIL, EXIT_SETUP = 0, 1, 2


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
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, input=input_text)
    if result.returncode != 0:
        raise SetupError([f"git {' '.join(args)}: {result.stderr.strip() or f'exit {result.returncode}'}"])
    return result.stdout


def repo_root() -> Path:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0:
        raise SetupError(["not inside a Git repository: run the gate from the project's repository"])
    return Path(result.stdout.strip())


def commit_of(root: Path, rev: str) -> str:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SetupError([f"{rev}: not a commit in this repository"])
    return result.stdout.strip()


def file_at(root: Path, commit: str, path: str) -> str | None:
    """A file's text at a commit, or None if it is not there."""
    result = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def changed_paths(root: Path, base: str, head: str) -> list[str]:
    """Every path the range adds, changes, deletes, or renames (a rename gives both its old and new path)."""
    fields = git(root, "diff", "--name-status", "-z", "-M", "--no-ext-diff", base, head).split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        count = 2 if status[:1] in ("R", "C") else 1
        paths.extend(fields[index + 1:index + 1 + count])
        index += 1 + count
    return paths


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
    patch = git(root, "-c", "core.quotePath=false", "diff", "--no-color", "--no-ext-diff", "-M", "--unified=0",
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
    result = subprocess.run([sys.executable, str(PROJECT_CONFIG), "check"], cwd=root, capture_output=True, text=True)
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
    return folders


def check_tools(parts: list[Part]) -> None:
    missing = []
    for part in parts:
        for tool in part.profile["tools"]:
            if shutil.which(tool["command"]) is None:
                missing.append(f"{tool['command']} (profile {part.profile['name']}) is not installed: {tool['install']}")
    if missing:
        raise SetupError(sorted(set(missing)))


def check_checkout(root: Path, head: str) -> None:
    if git(root, "rev-parse", "HEAD").strip() != head:
        raise SetupError([f"the working tree is not at the head ({head[:12]}): check it out before running the gate"])
    if git(root, "status", "--porcelain", "--untracked-files=normal").strip():
        raise SetupError(["the working tree has uncommitted changes: commit or remove them, so the gate checks the head as committed"])


# --- Checks --------------------------------------------------------------------------------------

def protected_patterns(parts: list[Part], qa: list[str]) -> list[str]:
    patterns = list(FIXED_PROTECTED) + qa
    for part in parts:
        # Anywhere in the repository: `conventions` puts a config above the part when the part's folder is one the developer may change.
        patterns += [f"**/{pattern}" for pattern in part.profile["protected"]]
    return sorted(set(patterns), key=patterns.index)


def check_protected(paths: list[str], patterns: list[str]) -> Result:
    hits = sorted({f"{path} (matches {pattern})" for path in paths for pattern in patterns if matches(path, pattern)})
    return Result("protected-paths", None, not hits, hits)


def accepted_adrs(root: Path, base: str) -> set[str]:
    """The numbers of the project's ADRs that were accepted at the base, so that none the range adds can approve anything."""
    listing = git(root, "ls-tree", "-z", "--name-only", f"{base}:{ADR_DIR}") if file_at(root, base, ADR_DIR) is not None else ""
    numbers = set()
    for name in filter(None, listing.split("\0")):
        match = re.fullmatch(r"(\d{4})-.*\.md", name)
        text = file_at(root, base, f"{ADR_DIR}/{name}") if match else None
        if text and re.search(r"^- Status: accepted\b", text, re.M):
            numbers.add(match.group(1))
    return numbers


def check_suppressions(root: Path, base: str, head: str, parts: list[Part]) -> list[Result]:
    added = added_lines(root, base, head)
    approved = accepted_adrs(root, base)
    results = []
    for part in parts:
        patterns = [re.compile(pattern) for pattern in part.profile["suppressions"]]
        hits = []
        for path, number, text in added:
            name = PurePosixPath(path).name
            if not part.contains(path) or not any(matches(name, glob) for glob in part.profile["source_files"]):
                continue
            if any(pattern.search(text) for pattern in patterns):
                named = ADR_REF_RE.findall(text)
                if not any(adr in approved for adr in named):
                    reason = f"names ADR-{', ADR-'.join(named)}, not accepted at the base" if named else "names no accepted ADR"
                    hits.append(f"{path}:{number}: {text.strip()} ({reason})")
        results.append(Result("suppressions", part.path, not hits, hits))
    return results


def run(command: list[str], cwd: Path, timeout: float) -> tuple[int, str]:
    """Run a profile's command; return its exit code and the end of its output."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
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
    if code != 0 or not last.isdigit():
        return None, f"count_tests failed (exit {code}): {output or 'no output'}"
    return int(last), ""


def check_test_count(root: Path, base: str, parts: list[Part], timeout: float) -> list[Result]:
    results = []
    with tempfile.TemporaryDirectory(prefix="keyturn-gate-") as temp:
        tree = Path(temp) / "base"
        git(root, "worktree", "add", "--detach", "--quiet", str(tree), base)
        try:
            for part in parts:
                before, why_before = count_tests(part, tree, timeout)
                after, why_after = count_tests(part, root, timeout)
                if before is None or after is None:
                    details = [f"at the base: {why_before}" if before is None else "", f"at the head: {why_after}" if after is None else ""]
                    results.append(Result("test-count", part.path, False, [d for d in details if d]))
                elif after < before:
                    results.append(Result("test-count", part.path, False, [f"{before} tests at the base, {after} at the head"]))
                else:
                    results.append(Result("test-count", part.path, True, [f"{before} tests at the base, {after} at the head"]))
        finally:
            subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force", str(tree)], capture_output=True)
    return results


def check_profile(root: Path, parts: list[Part], timeout: float) -> list[Result]:
    results = []
    for part in parts:
        for check in part.profile["checks"]:
            code, output = run(check["run"], root / part.path, timeout)
            details = [] if code == 0 else [f"exit {code}: {output or 'no output'}"]
            results.append(Result(check["name"], part.path, code == 0, details))
    return results


def gate(base_rev: str, head_rev: str, profiles_dir: Path, timeout: float) -> tuple[str, str, list[Result]]:
    root = repo_root()
    base, head = commit_of(root, base_rev), commit_of(root, head_rev)
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, head]).returncode != 0:
        raise SetupError([f"{base_rev} is not an ancestor of {head_rev}: name the commit the change started from"])
    check_checkout(root, head)
    parts = load_parts(root, profiles_dir)
    qa = qa_folders(root, base)
    check_tools(parts)
    results = [check_protected(changed_paths(root, base, head), protected_patterns(parts, qa))]
    results += check_suppressions(root, base, head, parts)
    results += check_test_count(root, base, parts, timeout)
    results += check_profile(root, parts, timeout)
    return base, head, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run keyturn's gate on a Git range (ADR 0028).")
    parser.add_argument("--base", required=True, help="the commit the change started from")
    parser.add_argument("--head", default="HEAD", help="the last commit of the change (default: HEAD)")
    parser.add_argument("--log", type=Path, help="also write the result as JSON to this file")
    parser.add_argument("--profiles", type=Path, default=PLUGIN_ROOT / "profiles", help="the folder of stack profiles")
    parser.add_argument("--timeout-minutes", type=float, default=30, help="the limit for each command (default: 30)")
    args = parser.parse_args()

    try:
        base, head, results = gate(args.base, args.head, args.profiles, args.timeout_minutes * 60)
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
