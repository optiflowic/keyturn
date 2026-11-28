#!/usr/bin/env python3
"""The merge conditions of a task's pull request, checked from committed records only (ADR 0042, ADR 0046, ADR 0070).

Usage (from inside the project's repository):
  conditions.sh --task TASK --default-branch REV [--head REV]

It finds the task's base and the other roles' commits as the gate does in CI (ADR 0043), then checks, each reported as
one PASS or FAIL line:
  findings [review]           in keyturn/internal/review.md at the head: no high or medium finding is open, a finding
                              marked "accepted: decision card <n>" is a medium one, not a security one, and that card,
                              as it was before the developer's first commit, is answered, and the
                              report's "Reviewed change" ends at the developer's last commit
  findings [security-review]  the same in keyturn/internal/security-review.md, where no finding may be accepted
  acceptance                  the newest acceptance row of the task in keyturn/client/approvals.md says accepted, names
                              the documents commit (deliver's newest commit that changed the acceptance guide, the
                              test report, or the delivery report), and has the SHA-256 of the three documents at the
                              head; every commit after
                              the documents commit is merge's or deliver's and changes only the approvals, the state
                              file, or (merge's) a decision card (ADR 0047)

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
DOCUMENTS = ("keyturn/client/acceptance-guide.md", "keyturn/client/test-report.md", "keyturn/client/delivery-report.md")
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


def findings(text: str) -> list[tuple[str, dict[str, str]]] | None:
    """The findings of the "Findings" section, as (number, {field: value}) with the fields before the text.

    None when the section cannot be read: no "## Findings" heading, or text in it that is neither "None." nor
    findings under "### F-<n>" headings. A report that cannot be read never counts as one without findings.
    """
    lines = without_fences_and_comments(text)
    start = next((i + 1 for i, line in enumerate(lines) if re.fullmatch(r"## Findings[ \t]*", line)), None)
    if start is None:
        return None
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = [line.strip() for line in lines[start:end] if line.strip()]
    if body == ["None."]:
        return []
    if not body or not FINDING_RE.match(body[0]) or any(line.startswith("#") and not FINDING_RE.match(line) for line in body):
        return None
    found: list[tuple[str, dict[str, str]]] = []
    for line in body:  # stripped, as checked above: an indented heading or field still counts
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


def check_report(root: Path, head: str, role: str, developer_last: str, cards_at: str) -> Result:
    path = REPORTS[role]
    text = gate.file_at(root, head, path)
    if text is None:
        return Result(f"findings [{role}]", [f"{path}: missing at the head; the {role} step writes it"])
    problems = []
    # Read from what the report shows, never from a comment or a code block, and only when it says it once.
    ranges = list(RANGE_RE.finditer("\n".join(line.strip() for line in without_fences_and_comments(text))))
    reviewed = ranges[0] if len(ranges) == 1 else None
    if reviewed is None:
        problems.append(f"{path}: not exactly one \"Reviewed change\" line of the form <base>..<head> "
                        f"({len(ranges)} found)")
    elif not developer_last.startswith(reviewed.group(2)):
        problems.append(f"{path}: reviews up to {reviewed.group(2)}, not the developer's last commit "
                        f"{developer_last[:12]}; the {role} step runs again on it")
    found = findings(text)
    if found is None:
        problems.append(f"{path}: its \"Findings\" section cannot be read: it must be \"None.\" or findings under "
                        "\"### F-<n>: <title>\" headings, as the template has them")
        found = []
    for number, fields in found:
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
        if fields.get("Category", "").strip().lower() == "security":
            problems.append(f"{path}: {number}: a security finding is never accepted; it is fixed (ADR 0042)")
            continue
        # Only a card the design step asked, before the developer's work: a card made later (for example in the
        # merge step, ADR 0047) never accepts a finding.
        card = CARD.format(accepted.group(1))
        card_text = gate.file_at(root, cards_at, card)
        if card_text is None:
            problems.append(f"{path}: {number}: accepted on {card}, which did not exist before the developer's work")
        elif not card_answered(card_text):
            problems.append(f"{path}: {number}: accepted on {card}, which is not answered; an unanswered card "
                            "accepts nothing (ADR 0009)")
    return Result(f"findings [{role}]", problems)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(root: Path, commit: str, path: str) -> bytes | None:
    result = gate.subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, env=gate.ENV)
    return result.stdout if result.returncode == 0 else None


def deliver_row_commit(state_text: str) -> str | None:
    """The "Commit" of the deliver row of the state file's steps table, without its backticks."""
    for line in gate.state_section(state_text, "Steps"):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == "deliver":
            match = re.fullmatch(r"`([0-9a-f]{7,40})`", cells[3])
            return match.group(1) if match else None
    return None


def check_acceptance(root: Path, head: str, task: str, commits: list[str], others: dict[str, str]) -> Result:
    approval = load_approval()
    if (approval.APPROVALS, approval.DELIVERY_DOCUMENTS) != (APPROVALS, DOCUMENTS):
        raise SetupError([f"{APPROVAL_SCRIPT} names other files than this check; keyturn's copy is inconsistent"])
    state = f"{STATE_DIR}/{task}.md"
    problems: list[str] = []
    changed = {commit: gate.name_status(root, f"{commit}^", commit) for commit in commits}
    touching = [commit for commit in commits if any(path in DOCUMENTS for path in changed[commit])]
    if not touching:
        return Result("acceptance", [f"no commit on the task branch adds any of {', '.join(DOCUMENTS)}; "
                                     "deliver's last step commits them"])
    documents = touching[-1]
    recorded = deliver_row_commit(gate.file_at(root, head, state) or "")
    if recorded is None or not documents.startswith(recorded):
        problems.append(f"{state}: the deliver step's \"Commit\" is {recorded or '(none)'}, not the newest commit that "
                        f"changed a delivery document, {documents[:12]}; the documents the client "
                        "read are the ones the deliver step recorded")
    if others.get(documents) != "deliver":
        problems.append(f"{documents[:12]}: changes a delivery document, but is not deliver's")
    for commit in commits[commits.index(documents) + 1:]:
        role = others.get(commit)
        allowed = [APPROVALS, state] + ([CARD.format("*")] if role == "merge" else [])
        outside = [path for path in changed[commit] if not any(gate.matches(path, pattern) for pattern in allowed)]
        if role not in ("merge", "deliver") or outside:
            problems.append(f"{commit[:12]} ({role or 'not named'}): comes after the documents commit {documents[:12]}; "
                            f"only merge's and deliver's commits of {APPROVALS}, {state}, or (merge's) a decision card may"
                            + (f" (it changes {', '.join(outside)})" if outside else ""))
    text = gate.file_at(root, head, APPROVALS)
    rows = approval.acceptance_rows(text or "", task)
    if not rows:
        problems.append(f"{APPROVALS}: no acceptance row for {task} at the head; the merge step records it")
        return Result("acceptance", problems)
    row = rows[-1]
    if len(row) != approval.ACCEPTANCE_CELLS:
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} has {len(row)} cells, not "
                        f"{approval.ACCEPTANCE_CELLS}; a row that cannot be read is never an acceptance")
        return Result("acceptance", problems)
    answer, words = row[approval.ANSWER], row[approval.CLIENT_WORDS]
    if answer != "accepted":
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} says {answer or '(empty)'!r}, not accepted; "
                        "no answer is not acceptance (ADR 0009)")
    elif words in ("", "none"):
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} says accepted without the client's words")
    if row[2] != documents:
        problems.append(f"{APPROVALS}: the newest acceptance row of {task} names {row[2][:12] or '(nothing)'}, not the "
                        f"documents commit {documents[:12]}; the documents changed after they were sent")
    for path, cell in zip(DOCUMENTS, row[approval.SHAS]):
        data = blob(root, head, path)
        if data is None:
            problems.append(f"{path}: missing at the head")
        elif sha256(data) != cell:
            problems.append(f"{APPROVALS}: the SHA-256 of {Path(path).name} in the newest acceptance row of {task} "
                            "is not the one at the head; the client accepted another text")
    return Result("acceptance", problems)


def conditions(task: str, default_rev: str, head_rev: str, vouched: str = "") -> tuple[str, str, list[Result]]:
    root = gate.repo_root()
    base, others_values = gate.task_range(root, task, default_rev, head_rev, vouched)
    head = gate.commit_of(root, head_rev)
    others = gate.parse_others(root, others_values)
    commits = [commit for commit, _ in gate.range_commits(root, base, head)]
    developer = [commit for commit in commits if commit not in others]
    if not developer:
        raise SetupError(["the task branch has no developer commit; there is nothing to merge"])
    cards_at = gate.git(root, "rev-parse", f"{developer[0]}^").strip()
    results = [check_report(root, head, role, developer[-1], cards_at) for role in REPORTS]
    results.append(check_acceptance(root, head, task, commits, others))
    return base, head, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a task's merge conditions from committed records (ADR 0046).")
    parser.add_argument("--task", required=True, help="the task, whose branch is task/<task>")
    parser.add_argument("--default-branch", required=True, help="the default branch the task branch left (for example origin/main)")
    parser.add_argument("--head", default="HEAD", help="the head to check (default: HEAD)")
    parser.add_argument("--documents-vouched", default="", metavar="VALUE",
                        help="the value of the repository variable KEYTURN_DOCUMENTS, as for gate.sh --task (ADR 0057)")
    args = parser.parse_args()
    try:
        base, head, results = conditions(args.task, args.default_branch, args.head, args.documents_vouched)
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
