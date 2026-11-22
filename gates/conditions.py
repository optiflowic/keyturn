#!/usr/bin/env python3
"""The merge conditions of a task's pull request, checked from committed records only (ADR 0042, ADR 0046).

Usage (from inside the project's repository):
  conditions.sh --task TASK --default-branch REV [--head REV]

It finds the task's base and the other roles' commits as the gate does in CI (ADR 0043), then checks, each reported as
one PASS or FAIL line:
  findings [review]           in keyturn/internal/review.md at the head: no high or medium finding is open, a finding
                              marked "accepted: decision card <n>" is a medium one and that card is answered, and the
                              report's "Reviewed change" ends at the developer's last commit
  findings [security-review]  the same in keyturn/internal/security-review.md, where no finding may be accepted
  acceptance                  the newest acceptance row of the task in keyturn/client/approvals.md says accepted, names
                              the documents commit (deliver's newest commit that changed the acceptance guide or the
                              delivery report), and has the SHA-256 of both documents at the head; every commit after
                              the documents commit is merge's or deliver's and changes only the approvals or the state file

It never runs the project's code, so it needs no stack tools. The translations the client read are local to the PM and
are not checked here; `approval.py accept-status` checks them before the PM records the answer.

Exit codes: 0 every condition holds; 1 at least one does not; 2 the check could not run (setup error).
Needs Python 3.9 or later and Git. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate  # the gate's helpers, next to this file

SetupError = gate.SetupError


APPROVAL_SCRIPT = gate.PLUGIN_ROOT / "skills" / "spec" / "scripts" / "approval.py"


def load_approval():
    """approval.py of the spec skill, which owns the acceptance row's format (ADR 0046)."""
    try:
        spec = importlib.util.spec_from_file_location("keyturn_approval", APPROVAL_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as error:
        raise SetupError([f"cannot load {APPROVAL_SCRIPT}: {error}"]) from error
    return module


EXIT_PASS, EXIT_FAIL, EXIT_SETUP = 0, 1, 2
REPORTS = {"review": "keyturn/internal/review.md", "security-review": "keyturn/internal/security-review.md"}
APPROVALS = "keyturn/client/approvals.md"
DOCUMENTS = ("keyturn/client/acceptance-guide.md", "keyturn/client/delivery-report.md")
STATE_DIR = gate.STATE_DIR
CARD = "keyturn/client/decision-card-{}.md"

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FINDING_RE = re.compile(r"^### (F-\d+)\b")
FIELD_RE = re.compile(r"^- ([A-Za-z ]+): *(.*?)\s*$")
RANGE_RE = re.compile(r"^- Reviewed change: *`?([0-9a-f]{7,40})`?\.\.`?([0-9a-f]{7,40})`?\s*$", re.MULTILINE)
ACCEPTED_RE = re.compile(r"accepted: decision card ([1-9][0-9]*)")
SEVERITIES = ("high", "medium", "low")
DATE_RE = re.compile(r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b")
PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")


class Result:
    def __init__(self, check: str, problems: list[str]):
        self.check, self.problems = check, problems

    @property
    def passed(self) -> bool:
        return not self.problems

    def lines(self) -> list[str]:
        if self.passed:
            return [f"PASS {self.check}"]
        return [f"FAIL {self.check}: {problem}" for problem in self.problems]


def without_fences_and_comments(text: str) -> list[str]:
    """The report's lines outside code fences, with HTML comments removed, so a template example never counts."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines, fence = [], None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is None and match:
            fence = match.group(1)[0]
            continue
        if fence is not None:
            if match and match.group(1)[0] == fence:
                fence = None
            continue
        lines.append(line)
    return lines


def findings(text: str) -> list[tuple[str, dict[str, str]]]:
    """The findings of the "Findings" section, as (number, {field: value}) with the fields before the text."""
    lines = without_fences_and_comments(text)
    start = next((i + 1 for i, line in enumerate(lines) if re.fullmatch(r"## Findings[ \t]*", line)), None)
    if start is None:
        return []
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    found: list[tuple[str, dict[str, str]]] = []
    for line in lines[start:end]:
        head = FINDING_RE.match(line)
        if head:
            found.append((head.group(1), {}))
            continue
        field = FIELD_RE.match(line)
        if found and field and field.group(1).strip() not in found[-1][1]:
            found[-1][1][field.group(1).strip()] = field.group(2)
    return found


def card_answered(text: str) -> bool:
    """Whether a decision card's last section ("Your answer") is filled in: a date, and no template placeholder.

    The card is in the client's language, so its headings and its "Status" word are not read; the date is ISO in every
    language, and an unanswered card still has the template's text in angle brackets.
    """
    lines = without_fences_and_comments(text)
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not starts:
        return False
    last = "\n".join(lines[starts[-1] + 1:])
    return bool(DATE_RE.search(last)) and not PLACEHOLDER_RE.search(last)


def check_report(root: Path, head: str, role: str, developer_last: str) -> Result:
    path = REPORTS[role]
    text = gate.file_at(root, head, path)
    if text is None:
        return Result(f"findings [{role}]", [f"{path}: missing at the head; the {role} step writes it"])
    problems = []
    reviewed = RANGE_RE.search(text)
    if reviewed is None:
        problems.append(f"{path}: no \"Reviewed change\" line of the form <base>..<head>")
    elif not developer_last.startswith(reviewed.group(2)):
        problems.append(f"{path}: reviews up to {reviewed.group(2)}, not the developer's last commit "
                        f"{developer_last[:12]}; the {role} step runs again on it")
    for number, fields in findings(text):
        severity, status = fields.get("Severity", ""), fields.get("Status", "")
        if severity not in SEVERITIES:
            problems.append(f"{path}: {number}: the severity is {severity or '(missing)'!r}; use high, medium, or low")
            continue
        if status == "fixed" or (status == "open" and severity == "low"):
            continue
        if status == "open":
            problems.append(f"{path}: {number}: a {severity} finding is open")
            continue
        accepted = ACCEPTED_RE.fullmatch(status)
        if accepted is None:
            problems.append(f"{path}: {number}: the status is {status or '(missing)'!r}; use open, fixed, "
                            "or accepted: decision card <n>")
            continue
        if role != "review":
            problems.append(f"{path}: {number}: a security finding is never accepted; it is fixed (ADR 0042)")
            continue
        if severity != "medium":
            problems.append(f"{path}: {number}: only a medium finding may be accepted on a decision card, "
                            f"not a {severity} one (ADR 0042)")
            continue
        card = CARD.format(accepted.group(1))
        card_text = gate.file_at(root, head, card)
        if card_text is None:
            problems.append(f"{path}: {number}: accepted on {card}, which is missing at the head")
        elif not card_answered(card_text):
            problems.append(f"{path}: {number}: accepted on {card}, which is not answered; an unanswered card "
                            "accepts nothing (ADR 0009)")
    return Result(f"findings [{role}]", problems)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(root: Path, commit: str, path: str) -> bytes | None:
    result = gate.subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, env=gate.ENV)
    return result.stdout if result.returncode == 0 else None


def check_acceptance(root: Path, head: str, task: str, commits: list[str], others: dict[str, str]) -> Result:
    approval = load_approval()
    if (approval.APPROVALS, approval.DELIVERY_DOCUMENTS) != (APPROVALS, DOCUMENTS):
        raise SetupError([f"{APPROVAL_SCRIPT} names other files than this check; keyturn's copy is inconsistent"])
    state = f"{STATE_DIR}/{task}.md"
    problems: list[str] = []
    changed = {commit: gate.name_status(root, f"{commit}^", commit) for commit in commits}
    touching = [commit for commit in commits if any(path in DOCUMENTS for path in changed[commit])]
    if not touching:
        return Result("acceptance", [f"no commit on the task branch adds {DOCUMENTS[0]} or {DOCUMENTS[1]}; "
                                     "deliver's last step commits them"])
    documents = touching[-1]
    if others.get(documents) != "deliver":
        problems.append(f"{documents[:12]}: changes the acceptance guide or the delivery report, but is not deliver's")
    for commit in commits[commits.index(documents) + 1:]:
        role = others.get(commit)
        outside = [path for path in changed[commit] if path not in (APPROVALS, state)]
        if role not in ("merge", "deliver") or outside:
            problems.append(f"{commit[:12]} ({role or 'not named'}): comes after the documents commit {documents[:12]}; "
                            f"only merge's and deliver's commits of {APPROVALS} or {state} may"
                            + (f" (it changes {', '.join(outside)})" if outside else ""))
    text = gate.file_at(root, head, APPROVALS)
    rows = approval.acceptance_rows(text or "", task)
    if not rows:
        problems.append(f"{APPROVALS}: no acceptance row for {task} at the head; the merge step records it")
        return Result("acceptance", problems)
    row = rows[-1]
    answer, words = row[approval.ANSWER], row[approval.CLIENT_WORDS]
    if answer != "accepted":
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} says {answer or '(empty)'!r}, not accepted; "
                        "no answer is not acceptance (ADR 0009)")
    elif words in ("", "none"):
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} says accepted without the client's words")
    if row[2] != documents:
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} names {row[2][:12] or '(nothing)'}, not the "
                        f"documents commit {documents[:12]}; the documents changed after they were sent")
    for path, cell in zip(DOCUMENTS, row[4:6]):
        data = blob(root, head, path)
        if data is None:
            problems.append(f"{path}: missing at the head")
        elif sha256(data) != cell:
            problems.append(f"{APPROVALS}: the SHA-256 of {Path(path).name} in the newest acceptance row of {task} "
                            "is not the one at the head; the client accepted another text")
    return Result("acceptance", problems)


def conditions(task: str, default_rev: str, head_rev: str) -> tuple[str, str, list[Result]]:
    root = gate.repo_root()
    base, others_values = gate.task_range(root, task, default_rev, head_rev)
    head = gate.commit_of(root, head_rev)
    others = gate.parse_others(root, others_values)
    commits = [commit for commit, _ in gate.range_commits(root, base, head)]
    developer = [commit for commit in commits if commit not in others]
    if not developer:
        raise SetupError(["the task branch has no developer commit; there is nothing to merge"])
    results = [check_report(root, head, role, developer[-1]) for role in REPORTS]
    results.append(check_acceptance(root, head, task, commits, others))
    return base, head, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a task's merge conditions from committed records (ADR 0046).")
    parser.add_argument("--task", required=True, help="the task, whose branch is task/<task>")
    parser.add_argument("--default-branch", required=True, help="the default branch the task branch left (for example origin/main)")
    parser.add_argument("--head", default="HEAD", help="the head to check (default: HEAD)")
    args = parser.parse_args()
    try:
        base, head, results = conditions(args.task, args.default_branch, args.head)
    except SetupError as error:
        for problem in error.problems:
            print(f"setup error: {problem}", file=sys.stderr)
        return EXIT_SETUP
    except Exception as error:  # an unexpected error must never look like a pass
        print(f"setup error: unexpected: {error!r}", file=sys.stderr)
        return EXIT_SETUP
    for result in results:
        for line in result.lines():
            print(line)
    passed = all(result.passed for result in results)
    print(f"conditions: {'hold' if passed else 'do not hold'} ({base[:12]}..{head[:12]})")
    return EXIT_PASS if passed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
