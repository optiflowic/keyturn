#!/usr/bin/env python3
"""Print a short summary of a pull request's review state and its unresolved review threads.

Usage:
  pr_review.py NUMBER [--repo OWNER/NAME] [--now TIME] [--full]
  pr_review.py --input FILE [--now TIME] [--full]

It prints, in plain text:
- the review decision and the latest review of each reviewer;
- whether CodeRabbit has posted a rate limit comment, and until when it asked to wait;
- every review thread that is neither resolved nor outdated: file and line, who wrote it, how many replies it has
  and who wrote the last one, and the point itself in a few lines. HTML, collapsed <details> sections (analysis
  chains, run logs, prompts for AI agents, committable suggestions), and suggested diffs are stripped out.
  Unresolved threads that are outdated are only counted.

It only reads: it never replies, resolves, or asks for a review. It fetches the pull request with
`gh api graphql`, so it needs no credentials other than gh's. --input reads a saved response of the same query
instead (the tests use it).

--now is the current time, YYYY-MM-DDTHH:MMZ in UTC (default: the clock). It only decides whether a rate limit
wait has passed. --full prints each point in full instead of cutting it after a few lines.

This is a tool for developing keyturn, not something a skill runs.
Needs Python 3.9 or later and gh. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      title
      state
      reviewDecision
      latestReviews(first: 100) {
        nodes { author { login } state submittedAt }
      }
      reviewThreads(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          isResolved
          isOutdated
          path
          line
          startLine
          originalLine
          originalStartLine
          comments(first: 100) {
            nodes { author { login } body createdAt }
          }
        }
      }
      comments(last: 100) {
        nodes { author { login } body createdAt updatedAt }
      }
    }
  }
}
"""

TIME_FORM = "YYYY-MM-DDTHH:MMZ"
TIME_FORMAT = "%Y-%m-%dT%H:%MZ"
CODERABBIT = ("coderabbitai", "coderabbitai[bot]")

# A point is cut after this many lines and this many characters, unless --full is given.
MAX_LINES = 4
MAX_CHARS = 400

# CodeRabbit marks the summary comment with this while a review is held back by its rate limit.
RATE_LIMIT_MARKER = "<!-- This is an auto-generated comment: rate limited by coderabbit.ai -->"
# CodeRabbit replies with this when an `@coderabbitai review` command hits the rate limit.
RATE_LIMITED_REPLY = "Review rate limited."
WAIT_LINE_RE = re.compile(r"available in ([^.*\n]+)|wait \**([^*\n]+?)\** before", re.IGNORECASE)
DURATION_PART_RE = re.compile(r"(\d+)\s*(hour|minute|second)s?", re.IGNORECASE)

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
DETAILS_TAG_RE = re.compile(r"<details\b[^>]*>|</details\s*>", re.IGNORECASE)
FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})[ \t]*(\S*)[^\n]*\n(.*?)^\1\2[ \t]*$\n?", re.DOTALL | re.MULTILINE)
DIFF_FENCES = ("diff", "suggestion")
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
EMPHASIS_RE = re.compile(r"\*\*|__|(?<!\w)_(?=\S)|(?<=\S)_(?!\w)")


class Failure(Exception):
    """The summary cannot be printed."""


def strip_details(text: str) -> str:
    """Remove every <details> block, nested ones included. An unclosed block runs to the end of the text."""
    out = []
    depth = 0
    position = 0
    for tag in DETAILS_TAG_RE.finditer(text):
        closing = tag.group().startswith("</")
        if depth == 0 and not closing:
            out.append(text[position:tag.start()])
        if closing:
            depth = max(depth - 1, 0)
        else:
            depth += 1
        position = tag.end()
    if depth == 0:
        out.append(text[position:])
    return "".join(out)


def strip_diff_fences(text: str) -> str:
    """Remove fenced blocks of suggested changes (```diff, ```suggestion); other code blocks keep their content."""
    return FENCE_RE.sub(lambda m: "" if m.group(3).lower() in DIFF_FENCES else m.group(4), text)


def clean(body: str) -> list[str]:
    """Turn a comment body into plain lines, without HTML, collapsed sections, suggested diffs, or blank lines."""
    text = HTML_COMMENT_RE.sub("", body)
    text = strip_details(text)
    text = strip_diff_fences(text)
    text = HTML_TAG_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    text = EMPHASIS_RE.sub("", text)
    lines = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if line and not re.fullmatch(r"[-*_=`~>|\s]+", line):
            lines.append(line)
    return lines


def shorten(lines: list[str], full: bool) -> list[str]:
    if full:
        return lines
    out = []
    used = 0
    for line in lines[:MAX_LINES]:
        room = MAX_CHARS - used
        if len(line) > room:
            cut = line[:room].rsplit(" ", 1)[0] if " " in line[:room] else line[:room]
            out.append(cut + " …")
            return out
        out.append(line)
        used += len(line)
    if len(lines) > MAX_LINES:
        out[-1] += " …"
    return out


def login(node: dict) -> str:
    author = node.get("author") or {}
    return author.get("login") or "ghost"


def is_coderabbit(node: dict) -> bool:
    return login(node) in CODERABBIT


def parse_github_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def show_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def parse_duration(text: str) -> timedelta | None:
    seconds = 0
    found = False
    for amount, unit in DURATION_PART_RE.findall(text):
        found = True
        seconds += int(amount) * {"hour": 3600, "minute": 60, "second": 1}[unit.lower()]
    return timedelta(seconds=seconds) if found else None


def rate_limit(pr: dict, now: datetime) -> str:
    """Describe CodeRabbit's latest rate limit comment, or say there is none."""
    latest = None
    for comment in pr["comments"]["nodes"]:
        body = comment.get("body") or ""
        if not is_coderabbit(comment):
            continue
        if RATE_LIMIT_MARKER not in body and RATE_LIMITED_REPLY not in body:
            continue
        posted = parse_github_time(comment.get("updatedAt") or comment["createdAt"])
        if latest is None or posted > latest[0]:
            latest = (posted, body)
    if latest is None:
        return "none"
    posted, body = latest
    text = f"posted {show_time(posted)}"
    wait = None
    for match in WAIT_LINE_RE.finditer(HTML_COMMENT_RE.sub("", body)):
        wait = parse_duration(match.group(1) or match.group(2))
        if wait is not None:
            break
    if wait is None:
        text += ", no wait time given"
    else:
        until = posted + wait
        # Round up to the minute, so that the time shown is never before the wait is over.
        if until.second or until.microsecond:
            until = until.replace(second=0, microsecond=0) + timedelta(minutes=1)
        if until <= now:
            text += f", wait until {show_time(until)} (passed)"
        else:
            minutes = -(-int((until - now).total_seconds()) // 60)
            text += f", wait until {show_time(until)} ({minutes} min from now)"
    reviewed_after = [
        review for review in pr["latestReviews"]["nodes"]
        if is_coderabbit(review) and review.get("submittedAt") and parse_github_time(review["submittedAt"]) > posted
    ]
    if reviewed_after:
        text += "; CodeRabbit has reviewed since"
    return text


def lines_of(thread: dict) -> str:
    if thread.get("isOutdated") or thread.get("line") is None:
        end, start = thread.get("originalLine"), thread.get("originalStartLine")
    else:
        end, start = thread.get("line"), thread.get("startLine")
    if end is None:
        return ""
    if start is not None and start != end:
        return f":{start}-{end}"
    return f":{end}"


def summarize(data: dict, now: datetime, full: bool = False) -> str:
    try:
        pr = data["data"]["repository"]["pullRequest"]
    except (KeyError, TypeError):
        pr = None
    if not pr:
        errors = [error.get("message", "") for error in (data.get("errors") or []) if isinstance(error, dict)]
        raise Failure("no pull request in the response" + (": " + "; ".join(errors) if errors else ""))

    out = [f"PR #{pr['number']}: {pr['title']} ({pr['state'].lower()})"]
    decision = (pr.get("reviewDecision") or "none").lower().replace("_", " ")
    out.append(f"Review decision: {decision}")
    reviews = sorted(pr["latestReviews"]["nodes"], key=lambda review: review.get("submittedAt") or "")
    if reviews:
        out.append("Latest review per reviewer:")
        for review in reviews:
            when = review.get("submittedAt")
            when = show_time(parse_github_time(when)) if when else "not submitted"
            out.append(f"- {login(review)}: {review['state'].lower().replace('_', ' ')}, {when}")
    else:
        out.append("Latest review per reviewer: none")
    out.append(f"CodeRabbit rate limit: {rate_limit(pr, now)}")

    threads = pr["reviewThreads"]["nodes"]
    unresolved = [thread for thread in threads if not thread.get("isResolved")]
    listed = [thread for thread in unresolved if not thread.get("isOutdated")]
    heading = f"Unresolved threads: {len(listed)}"
    if len(unresolved) > len(listed):
        heading += f" (and {len(unresolved) - len(listed)} outdated, not listed)"
    out.append("")
    out.append(heading)
    if pr["reviewThreads"]["pageInfo"].get("hasNextPage"):
        out.append("Warning: the pull request has more than 100 review threads; only the first 100 were read.")
    for number, thread in enumerate(listed, 1):
        comments = thread["comments"]["nodes"]
        first = comments[0] if comments else {"body": ""}
        header = f"{number}. {thread.get('path') or '(no file)'}{lines_of(thread)} by {login(first)}"
        replies = comments[1:]
        if replies:
            header += f" ({len(replies)} {'reply' if len(replies) == 1 else 'replies'}, last by {login(replies[-1])})"
        out.append("")
        out.append(header)
        point = shorten(clean(first.get("body") or ""), full) or ["(no text)"]
        out.extend("   " + line for line in point)
    return "\n".join(out) + "\n"


def current_repo() -> str:
    return run_gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).strip()


def run_gh(args: list[str]) -> str:
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise Failure("gh is not installed or not on PATH") from None
    if result.returncode != 0:
        raise Failure(f"gh {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def fetch(repo: str, number: int) -> dict:
    owner, _, name = repo.partition("/")
    if not owner or not name:
        raise Failure(f"--repo must be OWNER/NAME, not {repo!r}")
    output = run_gh([
        "api", "graphql",
        "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}",
        "-f", f"query={QUERY}",
    ])
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise Failure(f"gh api graphql did not return JSON: {error}") from None


def check_now(value: str) -> datetime:
    try:
        return datetime.strptime(value, TIME_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be {TIME_FORM} in UTC, not {value!r}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a pull request's review state and unresolved review threads.")
    parser.add_argument("number", type=int, nargs="?", help="the pull request number")
    parser.add_argument("--repo", metavar="OWNER/NAME", help="the repository (default: the current one, from gh)")
    parser.add_argument("--input", type=Path, metavar="FILE", help="read a saved response of the query instead of calling gh")
    parser.add_argument(
        "--now", type=check_now, default=datetime.now(timezone.utc).strftime(TIME_FORMAT), metavar=TIME_FORM,
        help="the current UTC time (default: the clock); it only decides whether a rate limit wait has passed",
    )
    parser.add_argument("--full", action="store_true", help="print each point in full")
    args = parser.parse_args()
    if (args.number is None) == (args.input is None):
        parser.error("give either a pull request number or --input FILE")
    try:
        if args.input is not None:
            try:
                data = json.loads(args.input.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise Failure(f"cannot read {args.input}: {error}") from None
        else:
            data = fetch(args.repo or current_repo(), args.number)
        sys.stdout.write(summarize(data, args.now, args.full))
    except Failure as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
