#!/usr/bin/env python3
"""Check task state files, keyturn/internal/state/<task>.md, and list the tasks that can be resumed. See ADR 0011.

Usage:
  task_state.py check FILE [--now TIME]  Check one state file against templates/internal/state.md.
                                         Prints "ok" and where the task stands, or every problem and exits 1.
  task_state.py list [--now TIME]        For every local and remote branch task/<task>, check the state file on
                                         that branch and list the tasks that are not done.

--now is the current time, YYYY-MM-DDTHH:MMZ in UTC (default: the clock). It only decides whether a
"Can continue: after ..." time has passed; the check of the file itself never depends on it, so the same file
always gives the same verdict and the same problems, in the same order.

The allowed fields, values, sections, and steps are read from the template at every run, so the script cannot
drift from it. A template this script cannot read is reported as a problem, never worked around.
Needs Python 3.9 or later (and Git for `list`). Uses only the standard library.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TEMPLATE = Path(__file__).resolve().parents[3] / "templates" / "internal" / "state.md"
STATE_DIR = "keyturn/internal/state"

TIME_FORM = "YYYY-MM-DDTHH:MMZ"
TIME_FORMAT = "%Y-%m-%dT%H:%MZ"
TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z")
TASK_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
NUMBER_RE = re.compile(r"0|[1-9][0-9]*")
COMMIT_RE = re.compile(r"`[0-9a-f]{7,40}`")
PLACEHOLDER_RE = re.compile(r"<([^<>]+)>|" + re.escape(TIME_FORM))
LEFTOVER_PLACEHOLDER_RE = re.compile(r"<[a-z][^<>]*>")
FIELD_RE = re.compile(r"^- ([^:]+): (.*)$")
HISTORY_RE = re.compile(r"^- (.+?): (.+)$")

# What each placeholder in the template's values stands for.
PLACEHOLDER_KINDS = {
    "task": "task",
    "n": "number",
    "limit": "number",
    "what": "text",
    TIME_FORM: "time",
    "step name from the table below": "step",
}

# The values this script gives a meaning to. If the template drops one of them, the script must be updated with it.
MEANINGFUL_VALUES = {
    "Status": ["running", "stopped", "done"],
    "Current step": ["none"],
    "Stopped because": ["none", "usage limit", "waiting for the client"],
    "Can continue": ["now", "not applicable"],
}
MEANINGFUL_FIELDS = ["Task", "Branch", "Requirements version", "Rework", "Updated", *MEANINGFUL_VALUES]
MEANINGFUL_STEP_STATUSES = ["not started", "in progress", "done", "skipped"]
MEANINGFUL_SECTIONS = ["Summary", "Steps", "Open questions", "History"]
FINISHED_STEP_STATUSES = ("done", "skipped")


class Problems(Exception):
    """The command cannot go on. Holds every problem found."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


# --- Reading the template -----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Pattern:
    """One allowed value as the template writes it, with a regex that captures each placeholder."""

    text: str
    regex: re.Pattern
    kinds: tuple[str, ...]


@dataclass(frozen=True)
class Template:
    title: Pattern
    fields: dict[str, list[Pattern]]
    sections: list[str]
    table_header: list[str]
    steps: list[str]
    step_statuses: list[str]
    history_kinds: list[str]


def matching_close(text: str, start: int) -> int:
    """The index of the ">" that closes the "<" at start, counting nested brackets; -1 if there is none."""
    depth = 0
    for index in range(start, len(text)):
        depth += {"<": 1, ">": -1}.get(text[index], 0)
        if depth == 0:
            return index
    return -1


def split_top_level(text: str, separator: str) -> list[str]:
    parts, depth, start, index = [], 0, 0, 0
    while index < len(text):
        if text[index] in "<>":
            depth += 1 if text[index] == "<" else -1
        elif depth == 0 and text.startswith(separator, index):
            parts.append(text[start:index])
            start = index = index + len(separator)
            continue
        index += 1
    return parts + [text[start:]]


def alternatives(value: str) -> list[str]:
    """`<a | b>` gives ["a", "b"]; any other value, including a single placeholder like `<task>`, is one alternative."""
    if value.startswith("<") and matching_close(value, 0) == len(value) - 1:
        parts = split_top_level(value[1:-1], " | ")
        if len(parts) > 1:
            return parts
    return [value]


def compile_pattern(text: str) -> Pattern:
    if text in PLACEHOLDER_KINDS:  # an alternative described in words, such as "step name from the table below"
        return Pattern(text, re.compile("(.+)"), (PLACEHOLDER_KINDS[text],))
    regex, kinds, position = "", [], 0
    for match in PLACEHOLDER_RE.finditer(text):
        name = match.group(1) or match.group(0)
        if name not in PLACEHOLDER_KINDS:
            raise Problems([f"template: unknown placeholder <{name}> in {text!r}; update task_state.py"])
        regex += re.escape(text[position:match.start()]) + "(.+?)"
        kinds.append(PLACEHOLDER_KINDS[name])
        position = match.end()
    regex += re.escape(text[position:])
    return Pattern(text, re.compile(regex), tuple(kinds))


def table_cells(line: str) -> list[str] | None:
    line = line.strip()
    if len(line) < 2 or not (line.startswith("|") and line.endswith("|")):
        return None
    return [cell.strip() for cell in line[1:-1].split("|")]


def split_sections(lines: list[str]) -> tuple[list[tuple[int, str]], list[tuple[str, list[tuple[int, str]]]]]:
    """The numbered lines before the first "## " heading, and each section with its numbered lines, in file order."""
    head, sections = [], []
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append((number, line))
        else:
            head.append((number, line))
    return head, sections


def without_comments(text: str) -> str:
    """Blank out HTML comments but keep their line breaks, so line numbers stay right."""
    return re.sub(r"<!--.*?-->", lambda match: "\n" * match.group(0).count("\n"), text, flags=re.DOTALL)


def listed_step_statuses(raw_template: str) -> list[str]:
    """The step statuses are listed only in the comment above the steps table: "- Status: not started, ..., or skipped."
    The head has a "- Status:" field too, so only the Steps section is searched."""
    _, sections = split_sections(raw_template.splitlines())
    for name, numbered in sections:
        for _, line in numbered:
            if name == "Steps" and line.startswith("- Status: "):
                listed = line[len("- Status: "):].rstrip(".")
                return [status for status in re.split(r",\s*(?:or\s+)?|\s+or\s+", listed) if status]
    return []


def read_template(path: Path) -> Template:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise Problems([f"template {path}: cannot read: {error.strerror or error}"]) from None
    head, sections = split_sections(without_comments(raw).splitlines())
    section_lines = {name: [line for _, line in numbered] for name, numbered in sections}

    titles = [line for _, line in head if line.startswith("# ")]
    fields = {}
    for _, line in head:
        match = FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = [compile_pattern(text) for text in alternatives(match.group(2))]

    rows = [cells for cells in map(table_cells, section_lines.get("Steps", [])) if cells]

    history_kinds = []
    for line in section_lines.get("History", []):
        match = HISTORY_RE.match(line)
        if match:
            history_kinds = [text.split(":")[0] for text in alternatives(match.group(2))]

    template = Template(
        title=compile_pattern(titles[0][2:]) if titles else compile_pattern(""),
        fields=fields,
        sections=[name for name, _ in sections],
        table_header=rows[0] if rows else [],
        steps=[cells[0] for cells in rows[2:]],
        step_statuses=listed_step_statuses(raw),
        history_kinds=history_kinds,
    )
    problems = template_problems(template)
    if problems:
        raise Problems([f"template {path}: {problem}" for problem in problems])
    return template


def template_problems(template: Template) -> list[str]:
    """Everything this script relies on must still be in the template, or the check would be wrong without saying so."""
    problems = []
    if not template.title.text:
        problems.append("no title line")
    for field in MEANINGFUL_FIELDS:
        if field not in template.fields:
            problems.append(f'no field "{field}"; update task_state.py')
    for field, values in MEANINGFUL_VALUES.items():
        allowed = [pattern.text for pattern in template.fields.get(field, [])]
        problems += [f'field "{field}" no longer allows "{value}"; update task_state.py' for value in values if value not in allowed]
    for section in MEANINGFUL_SECTIONS:
        if section not in template.sections:
            problems.append(f'no section "{section}"; update task_state.py')
    if len(template.table_header) < 4 or template.table_header[:2] != ["Step", "Status"] or "Commit" not in template.table_header:
        problems.append("the steps table does not start with Step and Status, or has no Commit column; update task_state.py")
    if not template.steps:
        problems.append("the steps table has no steps")
    for status in MEANINGFUL_STEP_STATUSES:
        if status not in template.step_statuses:
            problems.append(f'step status "{status}" is no longer listed; update task_state.py')
    if not {"started", "stopped", "resumed", "done"} <= set(template.history_kinds):
        problems.append("the history line no longer lists started, stopped, resumed, and done; update task_state.py")
    return problems


# --- Checking a state file ----------------------------------------------------------------------------------------


def is_time(text: str) -> bool:
    if not TIME_RE.fullmatch(text):
        return False
    try:
        datetime.strptime(text, TIME_FORMAT)
    except ValueError:  # for example, month 13 or 24:00
        return False
    return True


def placeholder_problem(kind: str, text: str, steps: list[str]) -> str | None:
    if kind == "time" and not is_time(text):
        return f'"{text}" is not a UTC time in the form {TIME_FORM}'
    if kind == "number" and not NUMBER_RE.fullmatch(text):
        return f'"{text}" is not a whole number'
    if kind == "task" and not TASK_RE.fullmatch(text):
        return f'"{text}" is not a task name (lowercase letters, digits, and hyphens)'
    if kind == "step" and text not in steps:
        return f'"{text}" is not a step in the steps table'
    if kind == "text" and LEFTOVER_PLACEHOLDER_RE.search(text):
        return f'"{text}" still has a placeholder'
    return None


def value_problems(name: str, value: str, patterns: list[Pattern], steps: list[str]) -> list[str]:
    """No problems if the value is one of the allowed values. A value that has the right words but a wrong time,
    number, or name gets that specific problem; anything else is reported with the allowed values."""
    near_misses = []
    for pattern in patterns:
        match = pattern.regex.fullmatch(value)
        if not match:
            continue
        problems = [placeholder_problem(kind, text, steps) for kind, text in zip(pattern.kinds, match.groups())]
        problems = [problem for problem in problems if problem]
        if not problems:
            return []
        near_misses = near_misses or problems
    if near_misses:
        return [f'field "{name}": {problem}' for problem in near_misses]
    allowed = " | ".join(pattern.text for pattern in patterns)
    return [f'field "{name}": "{value}" is not one of the allowed values: {allowed}']


@dataclass
class StateFile:
    """What the checks found in the file. A field or step is here only if its value is allowed."""

    fields: dict[str, str]
    steps: dict[str, dict[str, str]]  # step name -> cells by column heading, only when the whole table is valid
    open_questions: list[str]
    history_kinds: list[str]


def check_head(head: list[tuple[int, str]], template: Template, state: StateFile) -> list[str]:
    problems, seen = [], {}
    title = next(((number, line) for number, line in head if line.strip()), (0, ""))
    if not title[1].startswith("# "):
        problems.append(f'the file does not start with the title "{template.title.text}"')
    elif value_problems("title", title[1][2:], [template.title], template.steps):
        problems.append(f'line {title[0]}: the title is not "{template.title.text}"')

    for number, line in head:
        if not line.strip() or (number, line) == title:
            continue
        match = FIELD_RE.match(line)
        if not match:
            problems.append(f"line {number}: not a field line (- Field: value)")
            continue
        name, value = match.group(1), match.group(2).strip()
        if name not in template.fields:
            problems.append(f'line {number}: unknown field "{name}"')
        elif name in seen:
            problems.append(f'line {number}: field "{name}" appears more than once (first on line {seen[name]})')
        else:
            seen[name] = number
            found = value_problems(name, value, template.fields[name], template.steps)
            problems += [f"line {number}: {problem}" for problem in found]
            if not found:
                state.fields[name] = value
    problems += [f'field "{name}": missing' for name in template.fields if name not in seen]
    return problems


def check_steps(lines: list[tuple[int, str]], template: Template, state: StateFile) -> list[str]:
    table = [(number, table_cells(line)) for number, line in lines if line.strip().startswith("|")]
    if not table:
        return ["Steps: no table"]
    problems = [f"line {number}: a table row must start and end with |" for number, cells in table if cells is None]
    if problems:
        return problems
    header_number, header = table[0]
    if header != template.table_header:
        return [f"line {header_number}: the table heading is not | {' | '.join(template.table_header)} |"]
    if len(table) < 2 or not all(re.fullmatch(r":?-+:?", cell) for cell in table[1][1]):
        return [f"line {header_number + 1}: the line under the table heading must be |---|...|"]

    rows, problems = [], []
    for number, cells in table[2:]:
        if len(cells) != len(header):
            problems.append(f"line {number}: has {len(cells)} columns instead of {len(header)}")
            continue
        row = dict(zip(header, cells))
        rows.append(row)
        problems += [f"line {number}: {problem}" for problem in step_row_problems(row, template)]

    names = [row["Step"] for row in rows]
    problems += [f'Steps: unknown step "{name}"' for name in names if name not in template.steps]
    problems += [f'Steps: step "{name}" appears more than once' for name in sorted(set(names), key=names.index) if names.count(name) > 1]
    problems += [f'Steps: step "{name}" is missing' for name in template.steps if name not in names]
    if not problems and names != template.steps:
        problems.append(f"Steps: the steps are not in order; the order is {', '.join(template.steps)}")
    if not problems:
        state.steps = {row["Step"]: row for row in rows}
    return problems


def step_row_problems(row: dict[str, str], template: Template) -> list[str]:
    step, status = row["Step"], row["Status"]
    if status not in template.step_statuses:
        allowed = ", ".join(template.step_statuses)
        return [f'step "{step}": status "{status}" is not one of the allowed values: {allowed}']
    problems = []
    if row["Commit"] and not COMMIT_RE.fullmatch(row["Commit"]):
        problems.append(f'step "{step}": the commit "{row["Commit"]}" is not a commit hash in backticks')
    if status == "done" and not row["Commit"]:
        problems.append(f'step "{step}": is done but has no commit (a step is done only when its outputs are committed)')
    if status == "skipped" and not row.get("Notes"):
        problems.append(f'step "{step}": is skipped but its notes do not say why')
    return problems


def check_open_questions(lines: list[tuple[int, str]], state: StateFile) -> list[str]:
    content = [(number, line.strip()) for number, line in lines if line.strip()]
    if [line for _, line in content] == ["None."]:
        return []
    if not content:
        return ['Open questions: empty; write "None." when nothing is waiting']
    problems = []
    for number, line in content:
        waiting_since = re.search(r"since (\S+?)\.? Blocks: \S", line)
        if not re.match(r"- \[?(decision card|requirements version) \d+\b", line):
            problems.append(f"line {number}: an open question starts with a decision card or a requirements version")
        elif not waiting_since:
            problems.append(f'line {number}: an open question says "since {TIME_FORM}" and "Blocks: ..."')
        else:
            if not is_time(waiting_since.group(1)):
                problems.append(f'line {number}: "{waiting_since.group(1)}" is not a UTC time in the form {TIME_FORM}')
            state.open_questions.append(line)
    return problems


def check_history(lines: list[tuple[int, str]], template: Template, state: StateFile) -> list[str]:
    content = [(number, line.strip()) for number, line in lines if line.strip()]
    if not content:
        return ["History: empty; the first line is the time the task started"]
    problems, previous = [], ""
    for number, line in content:
        match = HISTORY_RE.match(line)
        if not match:
            problems.append(f"line {number}: a history line is - {TIME_FORM}: what happened")
            continue
        time, kind = match.group(1), match.group(2).split(":")[0]
        if not is_time(time):
            problems.append(f'line {number}: "{time}" is not a UTC time in the form {TIME_FORM}')
        elif previous and time < previous:
            problems.append(f"line {number}: the history is not in time order (newest last)")
        else:
            previous = time
        if kind not in template.history_kinds:
            problems.append(f'line {number}: "{kind}" is not one of: {", ".join(template.history_kinds)}')
        state.history_kinds.append(kind)
    if state.history_kinds and state.history_kinds[0] != "started":
        problems.append('History: the first line is not "started"')
    return problems


def consistency_problems(state: StateFile, file_name: str | None) -> list[str]:
    """Checks across fields, so that where to continue is never a guess. Only values already found valid are used."""
    fields, problems = state.fields, []
    task = fields.get("Task")
    if task and fields.get("Branch") and fields["Branch"] != f"`task/{task}`":
        problems.append(f'field "Branch": is not `task/{task}`')
    if task and file_name and file_name != f"{task}.md":
        problems.append(f'field "Task": "{task}" does not match the file name {file_name}')
    rework = fields.get("Rework", "").split(" of ")
    if len(rework) == 2 and int(rework[0]) > int(rework[1]):
        problems.append('field "Rework": the count is above the limit')

    status, step, reason, can_continue = (fields.get(name) for name in ("Status", "Current step", "Stopped because", "Can continue"))
    if status == "done":
        problems += [f'field "{name}": is not "{value}", but Status is done'
                     for name, value in (("Current step", "none"), ("Stopped because", "none"), ("Can continue", "not applicable"))
                     if fields.get(name) not in (None, value)]
        unfinished = [name for name, row in state.steps.items() if row["Status"] not in FINISHED_STEP_STATUSES]
        problems += [f'step "{name}": is not done or skipped, but Status is done' for name in unfinished]
        if state.history_kinds and state.history_kinds[-1] != "done":
            problems.append('History: the last line is not "done", but Status is done')
    elif status in ("running", "stopped"):
        if step == "none":
            problems.append(f'field "Current step": is none, but Status is {status}')
        if status == "stopped" and reason == "none":
            problems.append('field "Stopped because": is none, but Status is stopped')
        if status == "running" and reason not in (None, "none"):
            problems.append('field "Stopped because": is not none, but Status is running')
        if step and step != "none" and state.steps:
            problems += current_step_problems(state, step)

    if reason == "usage limit" and can_continue and not can_continue.startswith("after "):
        problems.append('field "Can continue": a usage limit stop says when the limit resets (after ' + TIME_FORM + ")")
    if reason == "waiting for the client" and can_continue and not can_continue.startswith("when the client "):
        problems.append('field "Can continue": a stop waiting for the client says what the client must answer or approve')
    if can_continue and can_continue.startswith("when the client "):
        waited_for = can_continue.split(": ", 1)[1]  # "decision card 2" or "requirements version 1"
        if not any(re.search(rf"\b{re.escape(waited_for)}\b", line) for line in state.open_questions):
            problems.append(f'Open questions: "{waited_for}" is not listed, but the task waits for it')
    return problems


def current_step_problems(state: StateFile, step: str) -> list[str]:
    """The current step is the first step that is neither done nor skipped: every step before it is finished."""
    first_unfinished = next((name for name, row in state.steps.items() if row["Status"] not in FINISHED_STEP_STATUSES), None)
    if first_unfinished is None:
        return ['Steps: every step is done or skipped, but the task is not done']
    if step != first_unfinished:
        return [f'field "Current step": is "{step}", but the first step that is not done or skipped is "{first_unfinished}"']
    return []


def check_state(text: str, template: Template, file_name: str | None = None) -> tuple[StateFile, list[str]]:
    """Check one state file. The problems come in file order, then the checks across fields, always the same."""
    state = StateFile(fields={}, steps={}, open_questions=[], history_kinds=[])
    problems = []
    if "<!--" in text:
        problems.append("the file still has template comments (<!-- -->); delete them")
    for number, line in enumerate(text.splitlines(), start=1):
        leftover = LEFTOVER_PLACEHOLDER_RE.search(line)
        if leftover:
            problems.append(f"line {number}: placeholder {leftover.group(0)} is not filled in")

    head, sections = split_sections(text.splitlines())
    problems += check_head(head, template, state)

    names = [name for name, _ in sections]
    problems += [f'section "{name}": not in the template' for name in names if name not in template.sections]
    problems += [f'section "{name}": appears more than once' for name in sorted(set(names), key=names.index) if names.count(name) > 1]
    problems += [f'section "{name}": missing' for name in template.sections if name not in names]
    known = [name for name in names if name in template.sections]
    if len(set(known)) == len(known) and known != [name for name in template.sections if name in known]:
        problems.append(f"the sections are not in order; the order is {', '.join(template.sections)}")

    by_name = {name: lines for name, lines in sections}
    if "Summary" in by_name and not any(line.strip() for _, line in by_name["Summary"]):
        problems.append("Summary: empty")
    if "Steps" in by_name:
        problems += check_steps(by_name["Steps"], template, state)
    if "Open questions" in by_name:
        problems += check_open_questions(by_name["Open questions"], state)
    if "History" in by_name:
        problems += check_history(by_name["History"], template, state)
    return state, problems + consistency_problems(state, file_name)


# --- Reporting ----------------------------------------------------------------------------------------------------


def continue_verdict(can_continue: str, now: str) -> str:
    """Whether the task may go on now, as far as the file alone can tell."""
    if can_continue.startswith("after "):
        reset = can_continue[len("after "):]
        return "the time has passed" if now >= reset else f"not yet (now {now})"
    if can_continue.startswith("when the client "):
        return "only once the client's answer is recorded"
    if can_continue.startswith("when the maintainer decides"):
        return "only once the maintainer has decided"
    return ""


def describe(state: StateFile, now: str) -> list[str]:
    fields = state.fields
    step = fields["Current step"]
    step_status = f" ({state.steps[step]['Status']})" if step in state.steps else ""
    verdict = continue_verdict(fields["Can continue"], now)
    return [
        f"task: {fields['Task']}",
        f"status: {fields['Status']}",
        f"current step: {step}{step_status}",
        f"stopped because: {fields['Stopped because']}",
        f"can continue: {fields['Can continue']}" + (f": {verdict}" if verdict else ""),
    ]


def cmd_check(path: Path, template: Template, now: str) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise Problems([f"{path}: cannot read: {getattr(error, 'strerror', None) or error}"]) from None
    state, problems = check_state(text, template, path.name)
    if problems:
        raise Problems(problems)
    print("ok")
    for line in describe(state, now):
        print(line)


# --- Listing tasks on branches ------------------------------------------------------------------------------------

# Variables that tell Git which repository to use. They would override the current folder and `-C root`.
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_PREFIX", "GIT_NAMESPACE",
)


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    environment = {name: value for name, value in os.environ.items() if name not in GIT_LOCATION_VARIABLES}
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=environment)


def repo_root() -> Path:
    result = git(Path.cwd(), "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise Problems(["not inside a Git repository"])
    return Path(result.stdout.decode("utf-8").strip())


def task_branches(root: Path) -> dict[str, list[str]]:
    """Every branch task/<task>, local first, then on each remote, by task name."""
    output = git(root, "for-each-ref", "--format=%(refname)", "refs/heads/task/", "refs/remotes/").stdout.decode("utf-8")
    branches: dict[str, list[str]] = {}
    for ref in output.splitlines():
        local = re.fullmatch(r"refs/heads/(task/(.+))", ref)
        remote = re.fullmatch(r"refs/remotes/([^/]+/task/(.+))", ref)
        match = local or remote
        if match:
            branches.setdefault(match.group(2), []).append(match.group(1))
    return dict(sorted(branches.items()))


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return git(root, "merge-base", "--is-ancestor", older, newer).returncode == 0


def newest_branch(root: Path, branches: list[str]) -> tuple[str | None, list[str]]:
    """The branch that contains all the others (local first when they are the same), and notes about the others."""
    for candidate in branches:
        if all(is_ancestor(root, other, candidate) for other in branches):
            local = branches[0] if branches[0].startswith("task/") else None
            behind = local and local != candidate and not is_ancestor(root, candidate, local)
            notes = [f"{local} is behind {candidate}; fast-forward it before resuming"] if behind else []
            return candidate, notes
    return None, [f"{', '.join(branches)} have diverged; merge them before resuming, the newest state cannot be chosen"]


def cmd_list(template: Template, now: str) -> int:
    root = repo_root()
    listed, failed = 0, False
    for task, branches in task_branches(root).items():
        if not TASK_RE.fullmatch(task):
            print(f"{branches[0]}: not a task branch (a task name is lowercase letters, digits, and hyphens)")
            failed = True
            continue
        branch, notes = newest_branch(root, branches)
        problems = notes if branch is None else []
        state = None
        if branch:
            shown = git(root, "show", f"{branch}:{STATE_DIR}/{task}.md")
            if shown.returncode != 0:
                problems = [f"{STATE_DIR}/{task}.md: missing on {branch}"]
            else:
                state, problems = check_state(shown.stdout.decode("utf-8", errors="replace"), template, f"{task}.md")
        if problems:
            print(f"{task} ({branch or ', '.join(branches)}): cannot be resumed until these problems are fixed:")
            for problem in problems:
                print(f"  - {problem}")
            failed, listed = True, listed + 1
            continue
        if state.fields["Status"] == "done":
            continue
        print(f"{task} ({branch}):")
        for line in describe(state, now)[1:] + [f"note: {note}" for note in notes]:
            print(f"  {line}")
        listed += 1
    if not listed:
        print("no tasks to resume")
    return 1 if failed else 0


def check_now(value: str) -> str:
    if not is_time(value):
        raise argparse.ArgumentTypeError(f"not a UTC time in the form {TIME_FORM}: {value!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check keyturn task state files and list the tasks that can be resumed.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check one state file")
    check.add_argument("file", type=Path)
    listing = commands.add_parser("list", help="list the tasks on task/<task> branches that are not done")
    for command in (check, listing):
        command.add_argument("--now", type=check_now, default=datetime.now(timezone.utc).strftime(TIME_FORMAT))
    args = parser.parse_args()

    try:
        template = read_template(args.template)
        if args.command == "check":
            cmd_check(args.file, template, args.now)
            return 0
        return cmd_list(template, args.now)
    except Problems as error:
        for problem in error.problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
