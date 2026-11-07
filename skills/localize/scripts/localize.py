#!/usr/bin/env python3
"""Bookkeeping for local translations: hashes, sections, and the cache.

The AI tool does the translating. This script only decides what needs
translating and assembles the result, so it works with any tool.

Commands (run from anywhere inside the repository; PATH is relative to the
repository root):

  status  LANG PATH...  Print fresh, stale, or missing for each translation.
  prepare LANG PATH     Write a work file with the sections to translate.
  apply   LANG PATH     Merge the translated work file into the translation.
  ignore                Make sure .keyturn/ is git-ignored, without committing.

Layout, relative to the repository root:

  .keyturn/i18n/<lang>/<path>        translation of <path>
  .keyturn/i18n/.work/<lang>/<path>  work file for the AI to translate
  .keyturn/i18n/.work/<lang>/<path>.localize.json  hashes for the work file (not for the AI)

The work file marks sections with short numbers instead of hashes, because
models copying long hashes by hand sometimes get a character wrong.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

KEYTURN_DIR = ".keyturn"
I18N_DIR = Path(KEYTURN_DIR) / "i18n"
WORK_DIR = I18N_DIR / ".work"

SOURCE_MARKER = '<!-- localize source="{path}" lang="{lang}" sha256="{sha}" -->'
SECTION_MARKER = '<!-- localize-section sha256="{sha}" -->'
SOURCE_MARKER_RE = re.compile(r'^<!-- localize source="(.*)" lang="(.*)" sha256="([0-9a-f]{64})" -->$')
SECTION_MARKER_RE = re.compile(r'^<!-- localize-section sha256="([0-9a-f]{64})" -->$')
WORK_HEADER = "<!-- localize: translate the text between markers; keep every marker line as it is -->"
WORK_MARKER = "<!-- localize-section {number} -->"
WORK_MARKER_RE = re.compile(r"^<!-- localize-section (\d+) -->$")

HEADING_RE = re.compile(r"^ {0,3}#{1,6}(\s|$)")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}


class LocalizeError(Exception):
    """A problem the user can fix; printed without a traceback."""


@dataclass
class Section:
    """A piece of a file and the hash of its source text."""

    sha: str
    text: str


@dataclass
class Source:
    """A source file: its path from the repository root, hash, and sections."""

    rel_path: str
    sha: str
    sections: list[Section]


def sha256(text: str) -> str:
    """Hash text exactly as stored, line endings included."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    """Read UTF-8 text without translating line endings, so CRLF changes are seen."""
    try:
        with open(path, encoding="utf-8", newline="") as file:
            return file.read()
    except UnicodeDecodeError:
        raise LocalizeError(f"{path} is not UTF-8 text") from None


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text without translating line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(text)


def next_fence(line: str, open_fence: str | None) -> str | None:
    """Return the open code fence after this line, following CommonMark.

    A fence closes only with the same character, at least as many of them as
    the opener, and nothing but spaces after it.
    """
    match = FENCE_RE.match(line.rstrip("\r\n"))
    if not match:
        return open_fence
    marker, rest = match.groups()
    if open_fence is None:
        if marker[0] == "`" and "`" in rest:
            return None  # not a fence: backtick fences cannot have backticks in the info string
        return marker
    closes = marker[0] == open_fence[0] and len(marker) >= len(open_fence) and rest.strip() == ""
    return None if closes else open_fence


def split_sections(text: str, is_markdown: bool) -> list[Section]:
    """Split Markdown at headings outside code fences. Other files are one section."""
    if not is_markdown:
        return [Section(sha256(text), text)] if text else []

    chunks: list[list[str]] = [[]]
    open_fence = None
    for line in text.splitlines(keepends=True):
        starts_section = open_fence is None and HEADING_RE.match(line)
        if starts_section and chunks[-1]:
            chunks.append([])
        chunks[-1].append(line)
        open_fence = next_fence(line, open_fence)

    joined = ["".join(chunk) for chunk in chunks if chunk]
    return [Section(sha256(chunk), chunk) for chunk in joined]


def parse_translation(text: str) -> tuple[str | None, list[Section]]:
    """Read a translation file: the recorded source hash and its sections in order."""
    source_sha = None
    sections: list[Section] = []
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        source_match = SOURCE_MARKER_RE.match(bare)
        section_match = SECTION_MARKER_RE.match(bare)
        if source_match and source_sha is None and not sections:
            source_sha = source_match.group(3)
        elif section_match:
            sections.append(Section(section_match.group(1), ""))
        elif sections:
            sections[-1].text += line
    return source_sha, sections


def render_translation(source: Source, lang: str, sections: list[Section]) -> str:
    """Write the source marker, then each section after its hash marker."""
    parts = [SOURCE_MARKER.format(path=source.rel_path, lang=lang, sha=source.sha) + "\n"]
    for section in sections:
        parts.append(SECTION_MARKER.format(sha=section.sha) + "\n")
        parts.append(section.text)
        if not section.text.endswith("\n"):
            parts.append("\n")
    return "".join(parts)


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a Git command in the repository and capture its output."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def repo_root() -> Path:
    """Return the root of the repository that contains the current folder."""
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0:
        raise LocalizeError("not inside a Git repository")
    return Path(result.stdout.strip())


def refuse_tracked_keyturn_files(root: Path) -> None:
    """Stop if Git tracks anything under .keyturn/, because ignore rules do not protect it."""
    tracked = git(root, "ls-files", "--", KEYTURN_DIR).stdout.split()
    if tracked:
        listed = ", ".join(tracked[:5]) + (" ..." if len(tracked) > 5 else "")
        raise LocalizeError(
            f"Git tracks files under {KEYTURN_DIR}/ ({listed}); localize writes nothing "
            "there until they are untracked"
        )


def check_lang(lang: str) -> str:
    """Accept only language codes, so the code is safe to use as a folder name."""
    if not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", lang):
        raise argparse.ArgumentTypeError(f"not a language code: {lang!r} (use e.g. ja, de, pt-BR)")
    return lang


def load_source(root: Path, path: str) -> Source:
    """Read a source file given relative to the root, refusing paths outside it."""
    source_file = (root / path).resolve()
    try:
        rel_path = source_file.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise LocalizeError(f"{path} is outside the repository") from None
    if rel_path == KEYTURN_DIR or rel_path.startswith(KEYTURN_DIR + "/"):
        raise LocalizeError(f"{path} is inside {KEYTURN_DIR}/ and is not translated")
    if not source_file.is_file():
        raise LocalizeError(f"{path} is not a file in the repository")

    text = read_text(source_file)
    is_markdown = source_file.suffix.lower() in MARKDOWN_SUFFIXES
    return Source(rel_path, sha256(text), split_sections(text, is_markdown))


def target_path(root: Path, lang: str, source: Source) -> Path:
    """Return where the translation of the source lives."""
    return root / I18N_DIR / lang / source.rel_path


def work_paths(root: Path, lang: str, source: Source) -> tuple[Path, Path]:
    """Return the work file for the AI and the hashes file that only this script reads."""
    work_file = root / WORK_DIR / lang / source.rel_path
    return work_file, work_file.with_name(work_file.name + ".localize.json")


def existing_sections(target: Path) -> tuple[str | None, list[Section]]:
    """Read a translation if there is one."""
    return parse_translation(read_text(target)) if target.is_file() else (None, [])


def translation_status(root: Path, lang: str, source: Source) -> str:
    """fresh only if the recorded hash matches and every section marker is intact."""
    target = target_path(root, lang, source)
    if not target.is_file():
        return "missing"
    recorded_sha, sections = existing_sections(target)
    intact = [s.sha for s in sections] == [s.sha for s in source.sections]
    return "fresh" if recorded_sha == source.sha and intact else "stale"


def write_work_file(work_file: Path, sections: list[Section]) -> None:
    """Write the sections to translate, each after a short numbered marker."""
    parts = [WORK_HEADER + "\n"]
    for number, section in enumerate(sections, start=1):
        parts.append(WORK_MARKER.format(number=number) + "\n")
        parts.append(section.text)
    write_text(work_file, "".join(parts))


def read_work_file(work_file: Path, expected_count: int) -> list[str]:
    """Return the translated text of each numbered section, in order."""
    texts: dict[int, list[str]] = {}
    current = None
    for line in read_text(work_file).splitlines(keepends=True):
        marker = WORK_MARKER_RE.match(line.rstrip("\r\n"))
        if marker:
            current = int(marker.group(1))
            if current in texts:
                raise LocalizeError(f"section marker {current} appears twice in {work_file.name}")
            texts[current] = []
        elif current is not None:
            texts[current].append(line)

    expected = set(range(1, expected_count + 1))
    if set(texts) != expected:
        missing = sorted(expected - set(texts))
        raise LocalizeError(
            f"the work file is missing section markers {missing}; keep every "
            "localize-section marker and run apply again"
        )
    return ["".join(texts[number]) for number in sorted(texts)]


def cmd_status(lang: str, paths: list[str]) -> None:
    """Print fresh, stale, or missing for each path."""
    root = repo_root()
    for path in paths:
        source = load_source(root, path)
        print(f"{translation_status(root, lang, source)} {source.rel_path}")


def cmd_prepare(lang: str, path: str) -> None:
    """Write the sections that have no translation yet, numbered, plus their hashes."""
    root = repo_root()
    refuse_tracked_keyturn_files(root)
    source = load_source(root, path)
    if translation_status(root, lang, source) == "fresh":
        print(f"fresh {source.rel_path}: nothing to translate")
        return

    _, old_sections = existing_sections(target_path(root, lang, source))
    translated = {s.sha for s in old_sections}
    to_translate: list[Section] = []
    for section in source.sections:
        if section.sha not in translated:
            to_translate.append(section)
            translated.add(section.sha)  # a repeated section is translated once

    work_file, hashes_file = work_paths(root, lang, source)
    write_work_file(work_file, to_translate)
    hashes = {"source_sha256": source.sha, "sections": [s.sha for s in to_translate]}
    write_text(hashes_file, json.dumps(hashes, indent=2) + "\n")

    reused = len(source.sections) - len(to_translate)
    print(f"work file: {work_file.relative_to(root).as_posix()}")
    print(f"sections to translate: {len(to_translate)} (reused: {reused})")


def cmd_apply(lang: str, path: str) -> None:
    """Merge the translated work file with the reused sections, in source order."""
    root = repo_root()
    refuse_tracked_keyturn_files(root)
    source = load_source(root, path)

    work_file, hashes_file = work_paths(root, lang, source)
    if not (work_file.is_file() and hashes_file.is_file()):
        raise LocalizeError(f"no work file for {source.rel_path}; run prepare first")
    hashes = json.loads(read_text(hashes_file))
    if hashes["source_sha256"] != source.sha:
        raise LocalizeError(f"{source.rel_path} changed after prepare; run prepare again")
    new_texts = read_work_file(work_file, len(hashes["sections"]))

    target = target_path(root, lang, source)
    _, old_sections = existing_sections(target)
    available = {s.sha: s.text for s in old_sections}
    available.update(zip(hashes["sections"], new_texts))

    merged: list[Section] = []
    for section in source.sections:
        if section.sha not in available:
            raise LocalizeError(f"no translation for a section of {source.rel_path}; run prepare again")
        merged.append(Section(section.sha, available[section.sha]))

    write_text(target, render_translation(source, lang, merged))
    work_file.unlink()
    hashes_file.unlink()
    print(f"fresh {source.rel_path}: {target.relative_to(root).as_posix()}")


def cmd_ignore() -> None:
    """Add .keyturn/ to the local exclude file unless Git already ignores it."""
    root = repo_root()
    refuse_tracked_keyturn_files(root)
    probe = (I18N_DIR / "probe").as_posix()
    if git(root, "check-ignore", "-q", probe).returncode == 0:
        print(f"{KEYTURN_DIR}/ is already git-ignored")
        return

    exclude_path = git(root, "rev-parse", "--git-path", "info/exclude").stdout.strip()
    exclude_file = root / exclude_path
    existing = read_text(exclude_file) if exclude_file.is_file() else ""
    separator = "" if existing == "" or existing.endswith("\n") else "\n"
    write_text(exclude_file, existing + separator + KEYTURN_DIR + "/\n")
    print(f"added {KEYTURN_DIR}/ to {exclude_path}")


def main() -> int:
    """Parse the command line and run one command."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="show whether translations are up to date")
    status.add_argument("lang", type=check_lang)
    status.add_argument("paths", nargs="+")

    for name, help_text in [("prepare", "write the sections to translate"), ("apply", "merge the translated sections")]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("lang", type=check_lang)
        command.add_argument("path")

    commands.add_parser("ignore", help="git-ignore .keyturn/ without committing")

    args = parser.parse_args()
    try:
        if args.command == "status":
            cmd_status(args.lang, args.paths)
        elif args.command == "prepare":
            cmd_prepare(args.lang, args.path)
        elif args.command == "apply":
            cmd_apply(args.lang, args.path)
        else:
            cmd_ignore()
    except LocalizeError as error:
        print(f"localize: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
