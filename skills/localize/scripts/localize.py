#!/usr/bin/env python3
"""Bookkeeping for local translations: hashes, sections, and the cache.

The AI tool does the translating. This script only decides what needs
translating and assembles the result, so it works with any tool.

Commands (run from anywhere inside the repository):

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

I18N_DIR = Path(".keyturn") / "i18n"
WORK_DIR = I18N_DIR / ".work"

SOURCE_MARKER = '<!-- localize source="{path}" lang="{lang}" sha256="{sha}" -->'
SECTION_MARKER = '<!-- localize-section sha256="{sha}" -->'
SOURCE_MARKER_RE = re.compile(r'^<!-- localize source="(.*)" lang="(.*)" sha256="([0-9a-f]{64})" -->$')
SECTION_MARKER_RE = re.compile(r'^<!-- localize-section sha256="([0-9a-f]{64})" -->$')
WORK_HEADER = "<!-- localize: translate the text between markers; keep every marker line as it is -->"
WORK_MARKER = "<!-- localize-section {number} -->"
WORK_MARKER_RE = re.compile(r"^<!-- localize-section (\d+) -->$")

HEADING_RE = re.compile(r"^#{1,6}\s")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}


class LocalizeError(Exception):
    """A problem the user can fix; printed without a traceback."""


@dataclass
class Section:
    sha: str
    text: str


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_sections(text: str, is_markdown: bool) -> list[Section]:
    """Split Markdown at headings outside code fences. Other files are one section."""
    if not is_markdown:
        return [Section(sha256(text), text)] if text else []

    chunks: list[list[str]] = [[]]
    in_fence = False
    for line in text.splitlines(keepends=True):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        starts_section = HEADING_RE.match(line) and not in_fence
        if starts_section and chunks[-1]:
            chunks.append([])
        chunks[-1].append(line)

    joined = ["".join(chunk) for chunk in chunks if chunk]
    return [Section(sha256(chunk), chunk) for chunk in joined]


def parse_marked_file(text: str) -> tuple[str | None, dict[str, str]]:
    """Read a translation or work file: (source sha, {section sha: translated text})."""
    source_sha = None
    sections: dict[str, str] = {}
    current_sha = None
    current_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        source_match = SOURCE_MARKER_RE.match(line.rstrip("\n"))
        section_match = SECTION_MARKER_RE.match(line.rstrip("\n"))
        if source_match and source_sha is None:
            source_sha = source_match.group(3)
        elif section_match:
            if current_sha is not None:
                sections[current_sha] = "".join(current_lines)
            current_sha = section_match.group(1)
            current_lines = []
        elif current_sha is not None:
            current_lines.append(line)

    if current_sha is not None:
        sections[current_sha] = "".join(current_lines)
    return source_sha, sections


def render_marked_file(rel_path: str, lang: str, source_sha: str, sections: list[Section]) -> str:
    parts = [SOURCE_MARKER.format(path=rel_path, lang=lang, sha=source_sha) + "\n"]
    for section in sections:
        parts.append(SECTION_MARKER.format(sha=section.sha) + "\n")
        parts.append(section.text)
        if not section.text.endswith("\n"):
            parts.append("\n")
    return "".join(parts)


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise LocalizeError("not inside a Git repository")
    return Path(result.stdout.strip())


def check_lang(lang: str) -> str:
    if not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", lang):
        raise argparse.ArgumentTypeError(f"not a language code: {lang!r} (use e.g. ja, de, pt-BR)")
    return lang


def resolve_source(root: Path, path: str) -> tuple[Path, str]:
    """Return the source file and its path relative to the root, refusing paths outside it."""
    source = (Path.cwd() / path).resolve()
    try:
        rel_path = source.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise LocalizeError(f"{path} is outside the repository") from None
    if rel_path.startswith(".keyturn/"):
        raise LocalizeError(f"{path} is inside .keyturn/ and is not translated")
    if not source.is_file():
        raise LocalizeError(f"{path} is not a file")
    return source, rel_path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise LocalizeError(f"{path} is not UTF-8 text") from None


def translation_status(root: Path, lang: str, rel_path: str, source_sha: str) -> str:
    target = root / I18N_DIR / lang / rel_path
    if not target.is_file():
        return "missing"
    recorded_sha, _ = parse_marked_file(read_text(target))
    return "fresh" if recorded_sha == source_sha else "stale"


def cmd_status(lang: str, paths: list[str]) -> None:
    root = repo_root()
    for path in paths:
        source, rel_path = resolve_source(root, path)
        source_sha = sha256(read_text(source))
        print(f"{translation_status(root, lang, rel_path, source_sha)} {rel_path}")


def work_paths(root: Path, lang: str, rel_path: str) -> tuple[Path, Path]:
    work_file = root / WORK_DIR / lang / rel_path
    return work_file, work_file.with_name(work_file.name + ".localize.json")


def write_work_file(work_file: Path, sections: list[Section]) -> None:
    parts = [WORK_HEADER + "\n"]
    for number, section in enumerate(sections, start=1):
        parts.append(WORK_MARKER.format(number=number) + "\n")
        parts.append(section.text)
    work_file.write_text("".join(parts), encoding="utf-8")


def read_work_file(work_file: Path, expected_count: int) -> list[str]:
    """Return the translated text of each numbered section, in order."""
    texts: dict[int, list[str]] = {}
    current = None
    for line in read_text(work_file).splitlines(keepends=True):
        marker = WORK_MARKER_RE.match(line.rstrip("\n"))
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


def cmd_prepare(lang: str, path: str) -> None:
    root = repo_root()
    source, rel_path = resolve_source(root, path)
    source_text = read_text(source)
    source_sha = sha256(source_text)

    if translation_status(root, lang, rel_path, source_sha) == "fresh":
        print(f"fresh {rel_path}: nothing to translate")
        return

    target = root / I18N_DIR / lang / rel_path
    _, translated = parse_marked_file(read_text(target)) if target.is_file() else (None, {})
    sections = split_sections(source_text, source.suffix.lower() in MARKDOWN_SUFFIXES)

    to_translate: list[Section] = []
    for section in sections:
        already_listed = any(s.sha == section.sha for s in to_translate)
        if section.sha not in translated and not already_listed:
            to_translate.append(section)

    work_file, hashes_file = work_paths(root, lang, rel_path)
    work_file.parent.mkdir(parents=True, exist_ok=True)
    write_work_file(work_file, to_translate)
    hashes = {"source_sha256": source_sha, "sections": [s.sha for s in to_translate]}
    hashes_file.write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")

    reused = len(sections) - len(to_translate)
    print(f"work file: {work_file.relative_to(root).as_posix()}")
    print(f"sections to translate: {len(to_translate)} (reused: {reused})")


def cmd_apply(lang: str, path: str) -> None:
    root = repo_root()
    source, rel_path = resolve_source(root, path)
    source_text = read_text(source)
    source_sha = sha256(source_text)

    work_file, hashes_file = work_paths(root, lang, rel_path)
    if not (work_file.is_file() and hashes_file.is_file()):
        raise LocalizeError(f"no work file for {rel_path}; run prepare first")
    hashes = json.loads(read_text(hashes_file))
    if hashes["source_sha256"] != source_sha:
        raise LocalizeError(f"{rel_path} changed after prepare; run prepare again")
    new_texts = read_work_file(work_file, len(hashes["sections"]))
    new_sections = dict(zip(hashes["sections"], new_texts))

    target = root / I18N_DIR / lang / rel_path
    _, old_sections = parse_marked_file(read_text(target)) if target.is_file() else (None, {})
    available = {**old_sections, **new_sections}

    merged: list[Section] = []
    for section in split_sections(source_text, source.suffix.lower() in MARKDOWN_SUFFIXES):
        if section.sha not in available:
            raise LocalizeError(f"no translation for a section of {rel_path}; run prepare again")
        merged.append(Section(section.sha, available[section.sha]))

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_marked_file(rel_path, lang, source_sha, merged), encoding="utf-8")
    work_file.unlink()
    hashes_file.unlink()
    print(f"fresh {rel_path}: {target.relative_to(root).as_posix()}")


def cmd_ignore() -> None:
    root = repo_root()
    probe = (I18N_DIR / "probe").as_posix()
    ignored = subprocess.run(["git", "check-ignore", "-q", probe], cwd=root).returncode == 0
    if ignored:
        print(".keyturn/ is already git-ignored")
        return

    exclude_path = subprocess.run(
        ["git", "rev-parse", "--git-path", "info/exclude"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.strip()
    exclude_file = root / exclude_path
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_file.read_text(encoding="utf-8") if exclude_file.is_file() else ""
    separator = "" if existing == "" or existing.endswith("\n") else "\n"
    exclude_file.write_text(existing + separator + ".keyturn/\n", encoding="utf-8")
    print(f"added .keyturn/ to {exclude_path}")


def main() -> int:
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
