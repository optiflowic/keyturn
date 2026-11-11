#!/usr/bin/env python3
"""Check task state files, keyturn/internal/state/<task>.md, and list the tasks that can be resumed. See ADR 0011.

Usage:
  task_state.py check FILE [--now TIME]  Check one state file against templates/internal/state.md.
                                         Prints "ok" and where the task stands, or every problem and exits 1.
  task_state.py list [--task TASK] [--now TIME]
                                         For every local and remote branch task/<task>, check the state file on
                                         that branch and list the tasks that are not done. With --task, only that
                                         task, even when it is done. Exits 1 if anything it lists has a problem.

Both commands print every problem as one line, "error: <where>: <problem>", on standard output.

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
        return f'"{text}" should be a UTC time in the form {TIME_FORM}'
    if kind == "number" and not NUMBER_RE.fullmatch(text):
        return f'"{text}" should be a whole number'
    if kind == "task" and not TASK_RE.fullmatch(text):
        return f'"{text}" should be a task name (lowercase letters, digits, and hyphens)'
    if kind == "step" and text not in steps:
        return f'"{text}" should be a step in the steps table'
    if kind == "text" and LEFTOVER_PLACEHOLDER_RE.search(text):
        return f'"{text}" should have its placeholder filled in'
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
    return [f'field "{name}": "{value}" should be one of: {allowed}']


@dataclass
class StateFile:
    """What the checks found in the file. A field or step is here only if its value is allowed."""

    fields: dict[str, str]
    steps: dict[str, dict[str, str]]  # step name -> cells by column heading, only when the whole table is valid
    open_questions: list[str]
    history_kinds: list[str]
    title_task: str | None = None


def check_head(head: list[tuple[int, str]], template: Template, state: StateFile) -> list[str]:
    problems, seen = [], {}
    title = next(((number, line) for number, line in head if line.strip()), (0, ""))
    title_match = template.title.regex.fullmatch(title[1][2:]) if title[1].startswith("# ") else None
    if not title_match or value_problems("title", title[1][2:], [template.title], template.steps):
        problems.append(f'line {title[0] or 1}: "{title[1]}" should be the title "# {template.title.text}"')
    else:
        state.title_task = title_match.group(1) if template.title.kinds else None

    for number, line in head:
        if not line.strip() or (number, line) == title:
            continue
        match = FIELD_RE.match(line)
        if not match:
            problems.append(f'line {number}: "{line}" should be a field line, "- Field: value"')
            continue
        name, value = match.group(1), match.group(2).strip()
        if name not in template.fields:
            problems.append(f'line {number}: "{name}" is not a field of the template')
        elif name in seen:
            problems.append(f'line {number}: field "{name}" should appear once, but is also on line {seen[name]}')
        else:
            seen[name] = number
            found = value_problems(name, value, template.fields[name], template.steps)
            problems += [f"line {number}: {problem}" for problem in found]
            if not found:
                state.fields[name] = value
    problems += [f'field "{name}": is missing' for name in template.fields if name not in seen]
    return problems


def check_steps(lines: list[tuple[int, str]], template: Template, state: StateFile) -> list[str]:
    table_lines = [(number, line.strip()) for number, line in lines if line.strip().startswith("|")]
    table = [(number, table_cells(line)) for number, line in table_lines]
    if not table:
        return ["Steps: should have the steps table"]
    problems = [f'line {number}: "{line}" should start and end with |' for number, line in table_lines if table_cells(line) is None]
    if problems:
        return problems
    header_number, header = table[0]
    if header != template.table_header:
        return [f"line {header_number}: the table heading should be | {' | '.join(template.table_header)} |, not | {' | '.join(header)} |"]
    if len(table) < 2 or not all(re.fullmatch(r":?-+:?", cell) for cell in table[1][1]):
        return [f"line {header_number + 1}: the line under the table heading should be |---|...|"]

    rows, problems = [], []
    for number, cells in table[2:]:
        if len(cells) != len(header):
            problems.append(f"line {number}: should have {len(header)} columns, not {len(cells)}")
            continue
        row = dict(zip(header, cells))
        rows.append(row)
        problems += [f"line {number}: {problem}" for problem in step_row_problems(row, template)]

    names = [row["Step"] for row in rows]
    problems += [f'Steps: "{name}" is not a step of the template' for name in names if name not in template.steps]
    problems += [f'Steps: step "{name}" should appear once' for name in sorted(set(names), key=names.index) if names.count(name) > 1]
    problems += [f'Steps: step "{name}" is missing' for name in template.steps if name not in names]
    if not problems and names != template.steps:
        problems.append(f"Steps: the steps should be in this order: {', '.join(template.steps)}")
    if not problems:
        state.steps = {row["Step"]: row for row in rows}
    return problems


def step_row_problems(row: dict[str, str], template: Template) -> list[str]:
    step, status = row["Step"], row["Status"]
    if status not in template.step_statuses:
        allowed = ", ".join(template.step_statuses)
        return [f'step "{step}": status "{status}" should be one of: {allowed}']
    problems = []
    if row["Commit"] and not COMMIT_RE.fullmatch(row["Commit"]):
        problems.append(f'step "{step}": commit "{row["Commit"]}" should be a commit hash in backticks')
    if status == "done" and not row["Commit"]:
        problems.append(f'step "{step}": is done, so it should have a commit (a step is done only when its outputs are committed)')
    if status == "skipped" and not row.get("Notes"):
        problems.append(f'step "{step}": is skipped, so its notes should say why')
    return problems


def check_open_questions(lines: list[tuple[int, str]], state: StateFile) -> list[str]:
    content = [(number, line.strip()) for number, line in lines if line.strip()]
    if [line for _, line in content] == ["None."]:
        return []
    if not content:
        return ['Open questions: should say "None." when nothing is waiting']
    problems = []
    for number, line in content:
        waiting_since = re.search(r"since (\S+?)\.? Blocks: \S", line)
        if not re.match(r"- \[?(decision card|requirements version) \d+\b", line):
            problems.append(f'line {number}: "{line}" should start with "- [decision card <n>](link)" or "- [requirements version <n>](link)"')
        elif not waiting_since:
            problems.append(f'line {number}: "{line}" should say "since {TIME_FORM}. Blocks: ..."')
        else:
            if not is_time(waiting_since.group(1)):
                problems.append(f'line {number}: "{waiting_since.group(1)}" should be a UTC time in the form {TIME_FORM}')
            state.open_questions.append(line)
    return problems


def check_history(lines: list[tuple[int, str]], template: Template, state: StateFile) -> list[str]:
    content = [(number, line.strip()) for number, line in lines if line.strip()]
    if not content:
        return [f'History: should have at least the line "- {TIME_FORM}: started"']
    problems, previous = [], ""
    for number, line in content:
        match = HISTORY_RE.match(line)
        if not match:
            problems.append(f'line {number}: "{line}" should be "- {TIME_FORM}: what happened"')
            continue
        time, kind = match.group(1), match.group(2).split(":")[0]
        if not is_time(time):
            problems.append(f'line {number}: "{time}" should be a UTC time in the form {TIME_FORM}')
        elif previous and time < previous:
            problems.append(f"line {number}: {time} should not be earlier than the line before it (newest last)")
        else:
            previous = time
        if kind not in template.history_kinds:
            problems.append(f'line {number}: "{kind}" should be one of: {", ".join(template.history_kinds)}')
        state.history_kinds.append(kind)
    if state.history_kinds and state.history_kinds[0] != "started":
        problems.append(f'History: the first line should be "started", not "{state.history_kinds[0]}"')
    return problems


def consistency_problems(state: StateFile, file_name: str | None) -> list[str]:
    """Checks across fields, so that where to continue is never a guess. Only values already found valid are used."""
    fields, problems = state.fields, []
    task = fields.get("Task")
    if task and state.title_task and state.title_task != task:
        problems.append(f'title: should name the task "{task}" from "Task:", not "{state.title_task}"')
    if task and fields.get("Branch") and fields["Branch"] != f"`task/{task}`":
        problems.append(f'field "Branch": should be `task/{task}`, not {fields["Branch"]}')
    if task and file_name and file_name != f"{task}.md":
        problems.append(f'field "Task": "{task}" should match the file name, {file_name}')
    rework = fields.get("Rework", "").split(" of ")
    if len(rework) == 2 and int(rework[0]) > int(rework[1]):
        problems.append(f'field "Rework": "{fields["Rework"]}" should not count more than the limit')

    status, step, reason, can_continue = (fields.get(name) for name in ("Status", "Current step", "Stopped because", "Can continue"))
    if status == "done":
        problems += [f'field "{name}": should be "{value}" when Status is done, not "{fields.get(name)}"'
                     for name, value in (("Current step", "none"), ("Stopped because", "none"), ("Can continue", "not applicable"))
                     if fields.get(name) not in (None, value)]
        unfinished = [name for name, row in state.steps.items() if row["Status"] not in FINISHED_STEP_STATUSES]
        problems += [f'step "{name}": should be done or skipped when Status is done' for name in unfinished]
        if state.history_kinds and state.history_kinds[-1] != "done":
            problems.append('History: the last line should be "done" when Status is done')
    elif status in ("running", "stopped"):
        if step == "none":
            problems.append(f'field "Current step": should name a step when Status is {status}, not "none"')
        if status == "stopped" and reason == "none":
            problems.append('field "Stopped because": should give the reason when Status is stopped, not "none"')
        if status == "running" and reason not in (None, "none"):
            problems.append(f'field "Stopped because": should be "none" when Status is running, not "{reason}"')
        if step and step != "none" and state.steps:
            problems += current_step_problems(state, step)

    if reason == "usage limit" and can_continue and not can_continue.startswith("after "):
        problems.append(f'field "Can continue": should be "after {TIME_FORM}" (when the limit resets) for a usage limit, not "{can_continue}"')
    if reason == "waiting for the client" and can_continue and not can_continue.startswith("when the client "):
        problems.append(f'field "Can continue": should say what the client must answer or approve ("when the client ..."), not "{can_continue}"')
    if can_continue and can_continue.startswith("when the client "):
        waited_for = can_continue.split(": ", 1)[1]  # "decision card 2" or "requirements version 1"
        if not any(re.search(rf"\b{re.escape(waited_for)}\b", line) for line in state.open_questions):
            problems.append(f'Open questions: should list "{waited_for}", which the task waits for')
    return problems


def current_step_problems(state: StateFile, step: str) -> list[str]:
    """The current step is the first step that is neither done nor skipped: every step before it is finished."""
    first_unfinished = next((name for name, row in state.steps.items() if row["Status"] not in FINISHED_STEP_STATUSES), None)
    if first_unfinished is None:
        return ['Steps: every step is done or skipped, so Status should be done']
    if step != first_unfinished:
        return [f'field "Current step": should be "{first_unfinished}", the first step that is not done or skipped, not "{step}"']
    return []


def check_state(text: str, template: Template, file_name: str | None = None) -> tuple[StateFile, list[str]]:
    """Check one state file. The problems come in file order, then the checks across fields, always the same."""
    state = StateFile(fields={}, steps={}, open_questions=[], history_kinds=[])
    problems = []
    if "<!--" in text:
        problems.append("the template comments (<!-- -->) should be deleted")
    for number, line in enumerate(text.splitlines(), start=1):
        leftover = LEFTOVER_PLACEHOLDER_RE.search(line)
        if leftover:
            problems.append(f"line {number}: placeholder {leftover.group(0)} should be filled in")

    head, sections = split_sections(text.splitlines())
    problems += check_head(head, template, state)

    names = [name for name, _ in sections]
    problems += [f'section "{name}": is not a section of the template' for name in names if name not in template.sections]
    problems += [f'section "{name}": should appear once' for name in sorted(set(names), key=names.index) if names.count(name) > 1]
    problems += [f'section "{name}": is missing' for name in template.sections if name not in names]
    known = [name for name in names if name in template.sections]
    if len(set(known)) == len(known) and known != [name for name in template.sections if name in known]:
        problems.append(f"the sections should be in this order: {', '.join(template.sections)}")

    by_name = {name: lines for name, lines in sections}
    if "Summary" in by_name and not any(line.strip() for _, line in by_name["Summary"]):
        problems.append("Summary: should not be empty")
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


def print_problems(where: str, problems: list[str]) -> None:
    """Both commands print problems the same way, so a reader or a script handles them the same way."""
    for problem in problems:
        print(f"error: {where}: {problem}")


def cmd_check(path: Path, template: Template, now: str) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print_problems(str(path), [f"cannot be read: {getattr(error, 'strerror', None) or error}"])
        return 1
    state, problems = check_state(text, template, path.name)
    if problems:
        print_problems(str(path), problems)
        return 1
    print("ok")
    for line in describe(state, now):
        print(line)
    return 0


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
        raise Problems([f"{Path.cwd()}: should be inside a Git repository"])
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


def newest_branch(root: Path, branches: list[str]) -> tuple[str | None, str]:
    """The branch that contains all the others (local first when they are the same), and a note or problem about them."""
    for candidate in branches:
        if all(is_ancestor(root, other, candidate) for other in branches):
            local = branches[0] if branches[0].startswith("task/") else None
            behind = local and local != candidate and not is_ancestor(root, candidate, local)
            return candidate, f"{local} is behind {candidate}; fast-forward it before resuming" if behind else ""
    return None, f"should not have diverged: {', '.join(branches)}; merge them before resuming, the newest state cannot be chosen"


def list_one(root: Path, task: str, branches: list[str], template: Template, now: str, show_done: bool) -> bool:
    """Print one task, or its problems. Returns False if it has problems."""
    if not TASK_RE.fullmatch(task):
        print_problems(branches[0], ["should be named task/<task>, with a task name of lowercase letters, digits, and hyphens"])
        return False
    branch, note = newest_branch(root, branches)
    if branch is None:
        print_problems(f"task/{task}", [note])
        return False
    where = f"{branch}:{STATE_DIR}/{task}.md"
    shown = git(root, "show", where)
    if shown.returncode != 0:
        print_problems(where, ["is missing"])
        return False
    state, problems = check_state(shown.stdout.decode("utf-8", errors="replace"), template, f"{task}.md")
    if problems:
        print_problems(where, problems)
        return False
    if state.fields["Status"] != "done" or show_done:
        print(f"{task} ({branch}):")
        for line in describe(state, now)[1:] + ([f"note: {note}"] if note else []):
            print(f"  {line}")
    return True


def cmd_list(template: Template, now: str, only_task: str | None) -> int:
    root = repo_root()
    branches_by_task = task_branches(root)
    if only_task is not None:
        if only_task not in branches_by_task:
            print_problems(f"task/{only_task}", ["has no local or remote branch"])
            return 1
        branches_by_task = {only_task: branches_by_task[only_task]}
    if not branches_by_task:
        print("no tasks to resume")
        return 0
    results = [list_one(root, task, branches, template, now, only_task is not None) for task, branches in branches_by_task.items()]
    return 0 if all(results) else 1


def check_now(value: str) -> str:
    if not is_time(value):
        raise argparse.ArgumentTypeError(f"should be a UTC time in the form {TIME_FORM}, not {value!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check keyturn task state files and list the tasks that can be resumed.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check one state file")
    check.add_argument("file", type=Path)
    listing = commands.add_parser("list", help="list the tasks on task/<task> branches that are not done")
    listing.add_argument("--task", help="list only this task, even when it is done")
    for command in (check, listing):
        command.add_argument(
            "--now", type=check_now, default=datetime.now(timezone.utc).strftime(TIME_FORMAT), metavar=TIME_FORM,
            help="the current UTC time (default: the clock); it only decides whether an 'after' time has passed",
        )
    args = parser.parse_args()

    try:
        template = read_template(args.template)
        if args.command == "check":
            return cmd_check(args.file, template, args.now)
        return cmd_list(template, args.now, args.task)
    except Problems as error:
        for problem in error.problems:
            print(f"error: {problem}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
