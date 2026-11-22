#!/usr/bin/env python3
"""Post the findings of a committed review report on the task's pull request, and nothing else (ADR 0041, ADR 0045).

Usage (from inside the project's repository, on the task's branch, after it was pushed):
  post_findings.py TASK ROLE COMMIT

ROLE is `review` or `security-review`; COMMIT is the commit of that role's report (keyturn/internal/review.md or
keyturn/internal/security-review.md) that deliver recorded. The report is read at COMMIT, never from the working tree.

It posts one review with the event COMMENT (a pull request's author cannot approve it or request changes on it, and the
agents and the client may share one account): a line comment for each finding whose location is a line of the pull
request's diff at the reviewed head, and the other findings in the review's text. The review's text ends with a marker
that names the report it was posted from. On a rerun, it compares the report with the one the newest marker names and
posts only what changed (new findings, findings whose status or text changed, findings no longer in the report); when the
report is the same, it posts nothing. The committed report stays the record; the post is not a merge condition.

Exit codes: 0 posted, or nothing new to post; 1 refused (no open pull request, it was not pushed, or GitHub refused the
post); 2 it could not run (a wrong branch, no origin, no gh, a report that is not at COMMIT).
Needs Python 3.9 or later, Git, and the GitHub CLI. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_branch  # noqa: E402  (the same checks of the branch, origin, and pull request as the push)
from task_branch import EXIT_DONE, EXIT_REFUSED, EXIT_SETUP, Refused, SetupError, git, run  # noqa: E402

REPORTS = {"review": "keyturn/internal/review.md", "security-review": "keyturn/internal/security-review.md"}
NAMES = {"review": "reviewer", "security-review": "security role"}
# Only a marker that ends a review counts; one before the end is quoted text.
END_MARKER_RE = re.compile(r"<!-- keyturn-findings: (review|security-review) ([0-9a-f]{40}) ([0-9a-f]{40}) -->\Z")
FINDING_RE = re.compile(r"^### (F-\d+): *(.*)$", re.MULTILINE)
FIELD_RE = re.compile(r"^- ([A-Za-z ]+): *(.*)$")
RANGE_RE = re.compile(r"^- Reviewed change: *`?([0-9a-f]{7,40})`?\.\.`?([0-9a-f]{7,40})`?", re.MULTILINE)
LOCATION_RE = re.compile(r"^`?([^`:\s][^`:]*?):(\d+)(?:-(\d+))?`?$")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
# GitHub refuses a text longer than this; the rest is in the committed report, which the post links.
MAX_TEXT = 60000


@dataclass(frozen=True)
class Finding:
    number: str
    title: str
    fields: tuple[tuple[str, str], ...]
    text: str

    def field(self, name: str) -> str:
        return dict(self.fields).get(name, "")


def quiet_mentions(text: str) -> str:
    """The report quotes code and documents, which are data: an @name in them must not notify anyone."""
    return re.sub(r"@(?=[A-Za-z0-9_-])", "@⁠", text)


FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def outside_fences(lines: list[str]) -> list[bool]:
    """For each line, whether it is outside a fenced block: a heading quoted in a fenced excerpt is the excerpt's text."""
    result, fence = [], None
    for line in lines:
        match = FENCE_RE.match(line)
        # A backtick fence's opening line has no other backtick (CommonMark): ```Use `cnt` here``` is inline code.
        if fence is None and match and match.group(1)[0] == "`" and "`" in line.strip()[len(match.group(1)):]:
            match = None
        if fence is None:
            result.append(match is None)
            if match:
                fence = match.group(1)
        else:
            result.append(False)
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                    and not line.strip()[len(match.group(1)):].strip():
                fence = None
    return result


def section(text: str, heading: str) -> str:
    lines = text.splitlines()
    outside = outside_fences(lines)
    start = next((i + 1 for i, line in enumerate(lines)
                  if outside[i] and re.fullmatch(rf"## {re.escape(heading)}[ \t]*", line)), None)
    if start is None:
        return ""
    end = next((i for i in range(start, len(lines)) if outside[i] and lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end]).strip()


def findings(text: str) -> dict[str, Finding]:
    """The report's findings by number, from its "Findings" section."""
    lines = section(text, "Findings").splitlines()
    outside = outside_fences(lines)
    found: dict[str, Finding] = {}
    heads = [(i, match) for i, line in enumerate(lines) if outside[i] and (match := FINDING_RE.match(line))]
    for index, (at, head) in enumerate(heads):
        end = heads[index + 1][0] if index + 1 < len(heads) else len(lines)
        fields, rest = [], []
        for line in "\n".join(lines[at + 1:end]).strip("\n").splitlines():
            match = FIELD_RE.match(line)
            if match and not rest:
                fields.append((match.group(1).strip(), match.group(2).strip()))
            else:
                rest.append(line)
        found[head.group(1)] = Finding(head.group(1), head.group(2).strip(), tuple(fields), "\n".join(rest).strip())
    return found


def commentable_lines(root: Path, base: str, head: str) -> dict[str, set[int]]:
    """The lines of each file at head that the pull request's diff shows (added and context lines), by path."""
    diff = git(root, "-c", "core.quotePath=false", "diff", "--no-color", "--no-ext-diff", "--find-renames", "-U3",
               base, head)
    lines: dict[str, set[int]] = {}
    path = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            continue
        match = HUNK_RE.match(line)
        if match and path is not None:
            start, count = int(match.group(1)), int(match.group(2) or "1")
            lines.setdefault(path, set()).update(range(start, start + count))
    return lines


def place(finding: Finding, lines: dict[str, set[int]]) -> dict | None:
    """Where a finding goes as a line comment, or None when its location is not a line of the diff."""
    match = LOCATION_RE.match(finding.field("Location"))
    if match is None:
        return None
    path, first = match.group(1).strip(), int(match.group(2))
    last = int(match.group(3) or first)
    shown = lines.get(path, set())
    if last not in shown:
        return None
    comment = {"path": path, "line": last, "side": "RIGHT"}
    # A range is one comment over its lines only when the diff shows them all (GitHub refuses one across hunks).
    if first < last and all(n in shown for n in range(first, last + 1)):
        comment.update(start_line=first, start_side="RIGHT")
    return comment


def describe(finding: Finding, bold: bool = False) -> str:
    """A finding as Markdown: under a heading in the review's text, or with a bold title in a line comment."""
    facts = ", ".join(value for value in (finding.field("Severity"), finding.field("Category")) if value)
    heading = f"{finding.number}: {finding.title}"
    lines = [f"**{heading}**" if bold else f"#### {heading}", ""]
    if facts:
        lines.append(f"{facts}; status: {finding.field('Status') or 'open'}")
    for name in ("Location", "Based on"):
        if finding.field(name):
            lines.append(f"- {name}: {finding.field(name)}")
    if finding.text:
        lines += ["", finding.text]
    return "\n".join(lines)


def changes(now: dict[str, Finding], before: dict[str, Finding] | None):
    """The findings to post: (new or changed ones, the ones gone from the report)."""
    if before is None:
        return list(now.values()), []
    posted = [finding for number, finding in now.items() if before.get(number) != finding]
    gone = [finding for number, finding in before.items() if number not in now]
    return posted, gone


def clip(text: str, link: str) -> str:
    if len(text) <= MAX_TEXT:
        return text
    return text[:MAX_TEXT].rstrip() + f"\n\n(Cut here: the rest is in the [committed report]({link}).)"


def report_at(root: Path, commit: str, path: str) -> str | None:
    result = run(["git", "show", f"{commit}:{path}"], root)
    return result.stdout if result.returncode == 0 else None


def own_markers(root: Path, number: int, role: str) -> list[tuple[str, str]]:
    """The markers of this role in the pull request's reviews by the signed-in account, oldest first: (blob, commit)."""
    login = task_branch.gh_api(root, "user", "--jq", ".login").strip()
    found = []
    for line in task_branch.gh_api(root, f"repos/{{repo}}/pulls/{number}/reviews", "--paginate",
                                   "--jq", ".[] | {login: .user.login, body: .body}").splitlines():
        if not line.strip():
            continue
        review = json.loads(line)
        if review.get("login") != login:
            continue
        # Only the marker that ends a review counts: one quoted in the report's text (from code it reviewed, say)
        # is the report's content, not a post.
        match = END_MARKER_RE.search((review.get("body") or "").rstrip())
        if match and match.group(1) == role:
            found.append((match.group(2), match.group(3)))
    return found


def cmd_post(root: Path, task: str, role: str, commit: str) -> None:
    branch = task_branch.check_task(root, task)
    path = REPORTS[role]
    resolved = run(["git", "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"], root)
    if resolved.returncode != 0:
        raise SetupError(f"{commit}: not a commit")
    commit = resolved.stdout.strip()
    if run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], root).returncode != 0:
        raise SetupError(f"{commit[:12]} is not on {branch}")
    text = report_at(root, commit, path)
    if text is None:
        raise SetupError(f"{path} is not in {commit[:12]}")
    blob = git(root, "rev-parse", f"{commit}:{path}")
    head = git(root, "rev-parse", "HEAD")
    # GitHub may take a few seconds to show a push on the pull request.
    deadline = time.monotonic() + float(os.environ.get("KEYTURN_PUSH_WAIT_SECONDS", "30"))
    while True:
        existing = task_branch.open_pull_request(root, branch)
        if existing is None:
            raise Refused(f"no open pull request from {branch}: open it first")
        if existing.get("headRefOid") == head:
            break
        if time.monotonic() >= deadline:
            raise Refused(f"{existing['url']} is not at {head[:12]}: push {branch} first")
        time.sleep(3)
    number = existing["number"]

    markers = own_markers(root, number, role)
    if markers and markers[-1][0] == blob:
        print(f"nothing new: the {role} report of {commit[:12]} is already on {existing['url']}")
        return
    before = None
    if markers:
        earlier = report_at(root, markers[-1][1], path)
        before = findings(earlier) if earlier is not None else None
    now = findings(text)
    posted, gone = changes(now, before)
    if before is not None and not posted and not gone:
        # Only the summary or the range moved: the pull request already shows every finding as it is.
        print(f"nothing new: no finding of the {role} report of {commit[:12]} changed since the last post on {existing['url']}")
        return

    link = f"https://github.com/{task_branch.origin_repository(root)}/blob/{commit}/{path}"
    reviewed = RANGE_RE.search(text)
    comments, in_text = [], []
    target = None
    if reviewed:
        target = run(["git", "rev-parse", "--verify", "--quiet", f"{reviewed.group(2)}^{{commit}}"], root).stdout.strip()
        if not target or run(["git", "merge-base", "--is-ancestor", target, commit], root).returncode != 0:
            target = None
    lines = {}
    if target:
        default = task_branch.default_branch(root)
        base = run(["git", "merge-base", f"refs/remotes/origin/{default}", target], root).stdout.strip()
        if base:
            lines = commentable_lines(root, base, target)
    fixed = [finding for finding in posted if finding.field("Status").lower() == "fixed"]
    for finding in posted:
        if finding in fixed:
            continue
        where = place(finding, lines)
        if where is None:
            in_text.append(finding)
        else:
            comments.append({**where, "body": clip(quiet_mentions(describe(finding, bold=True)), link)})

    def body(all_in_text: bool) -> str:
        title = text.splitlines()[0].lstrip("# ").strip() if text.strip() else role
        parts = [f"**keyturn {NAMES[role]}**: {title}", ""]
        if reviewed:
            parts += [f"Reviewed change: `{reviewed.group(1)}`..`{reviewed.group(2)}`", ""]
        summary = section(text, "Summary")
        if summary:
            parts += [summary, ""]
        if before is None and markers:
            parts += ["(The report this pull request was last given could not be read, so every finding is posted again.)", ""]
        elif before is not None:
            parts += ["What changed since the last post of this report:", ""]
        listed = [finding for finding in posted if finding not in fixed] if all_in_text else in_text
        for finding in listed:
            parts += [describe(finding), ""]
        if fixed:
            parts += ["Fixed: " + ", ".join(f"{f.number} ({f.title})" for f in fixed), ""]
        if gone:
            parts += ["No longer in the report: " + ", ".join(f"{f.number} ({f.title})" for f in gone), ""]
        if not now and before is None:
            parts += ["No findings.", ""]
        parts.append(f"The committed report is the record: [{path}]({link}).")
        return clip(quiet_mentions("\n".join(parts)), link) + f"\n\n<!-- keyturn-findings: {role} {blob} {commit} -->\n"

    def send(payload: dict) -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(payload, handle)
        try:
            return json.loads(task_branch.gh_api(root, f"repos/{{repo}}/pulls/{number}/reviews", "--method", "POST",
                                                 "--input", handle.name))
        finally:
            os.unlink(handle.name)

    payload = {"event": "COMMENT", "body": body(False), "comments": comments}
    if comments:
        payload["commit_id"] = target
    try:
        review = send(payload)
    except Refused as error:
        # A 422 means GitHub created no review (a line it could not place, a range across its hunks): post every finding
        # in the text instead. Any other failure may have created it, and a retry would post it twice; the next run
        # sees its marker instead.
        if not comments or not re.search(r"Unprocessable|HTTP 422|could not be resolved", str(error)):
            raise
        review = send({"event": "COMMENT", "body": body(True), "comments": []})
        comments = []
    print(f"posted the {role} report of {commit[:12]} on {existing['url']}: {len(comments)} line comments, "
          f"{len(posted) - len(comments) - len(fixed)} findings in the text, {len(fixed)} fixed "
          f"(review {review.get('id', '?')})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Post a review report's findings on the task's pull request (ADR 0045).")
    parser.add_argument("task", help="the task's name; its branch is task/<task>")
    parser.add_argument("role", choices=sorted(REPORTS))
    parser.add_argument("commit", help="the commit of the role's report, as deliver recorded it")
    args = parser.parse_args()
    try:
        cmd_post(task_branch.repo_root(), args.task, args.role, args.commit)
    except SetupError as error:
        print(f"setup error: {error}", file=sys.stderr)
        return EXIT_SETUP
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_DONE


if __name__ == "__main__":
    sys.exit(main())
