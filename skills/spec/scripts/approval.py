#!/usr/bin/env python3
"""Check and record what the client approves: keyturn/client/requirements.md, by SHA-256. See ADR 0008 and ADR 0012.

Usage:
  approval.py attributes [--fix]       Check that client documents are checked out with LF.
                                       --fix adds the .gitattributes line and renormalizes; commit the result.
  approval.py send VERSION [--lang LANG]
                                       Check requirements.md before it is sent for approval, keep the approved
                                       translation, and print the hashes for the approvals.md row.
                                       --lang is the language of the translation the client reads; leave it out
                                       when the client reads requirements.md itself.
  approval.py status [--lang LANG]     Check the newest approvals.md row: whether requirements.md is still the
                                       version that was sent, the client's answer as written, and whether the kept
                                       translation is unchanged. "current" alone does not mean approved.

Every command prints its result, or every problem (one per line) and exits 1.
Paths are resolved from the root of the Git repository, whatever the current folder.
Needs Python 3.9 or later and Git. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

CLIENT_DIR = "keyturn/client"
REQUIREMENTS = f"{CLIENT_DIR}/requirements.md"
APPROVALS = f"{CLIENT_DIR}/approvals.md"
ATTRIBUTES_LINE = f"{CLIENT_DIR}/*.md text eol=lf"
KEYTURN_DIR = ".keyturn"

LANG_RE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")
SHA_RE = re.compile(r"[0-9a-f]{64}")
# The first line of a localize translation. Only the source hash is needed here.
TRANSLATION_HEADER_RE = re.compile(rb'^<!-- localize source="[^"]*" lang="[^"]*" sha256="([0-9a-f]{64})" sections="\d+" -->')
# A changelog row in requirements.md starts with the version number. No other table there does.
CHANGELOG_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|", re.MULTILINE)


class ApprovalError(Exception):
    """The command cannot go on. Holds every problem found."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


# Variables that tell Git which repository to use. They would override the current folder and `-C root`,
# for example when a Git hook runs this script, and the checks and staging would hit another repository.
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_PREFIX", "GIT_NAMESPACE",
)


def git_environment() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if name not in GIT_LOCATION_VARIABLES}


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=git_environment())


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, encoding="utf-8", env=git_environment()
    )
    if result.returncode != 0:
        raise ApprovalError(["not inside a Git repository"])
    return Path(result.stdout.strip())


def sha256(data: bytes) -> str:
    """The SHA-256 of a file's bytes, the same value as shasum -a 256 and as localize records."""
    return hashlib.sha256(data).hexdigest()


def read_bytes(root: Path, rel_path: str) -> bytes:
    try:
        return (root / rel_path).read_bytes()
    except FileNotFoundError:
        raise ApprovalError([f"{rel_path}: missing"]) from None
    except OSError as error:
        raise ApprovalError([f"{rel_path}: cannot read: {error.strerror or error}"]) from None


def translation_path(lang: str, name: str = "requirements.md") -> str:
    return f"{KEYTURN_DIR}/i18n/{lang}/{CLIENT_DIR}/{name}"


def kept_copy_path(lang: str, version: int) -> str:
    """Where the approved translation is kept: next to the current translation, so its links still work (ADR 0012)."""
    return translation_path(lang, f"requirements.v{version}.approved.md")


def attribute_problems(root: Path) -> list[str]:
    """Check the attributes Git actually applies, so a line that is overridden later in .gitattributes is caught too."""
    problems = []
    for rel_path in (REQUIREMENTS, APPROVALS):
        output = git(root, "check-attr", "text", "eol", "--", rel_path).stdout.decode("utf-8")
        values = dict(line.split(": ")[1:3] for line in output.splitlines())
        if values.get("text") != "set" or values.get("eol") != "lf":
            problems.append(
                f"{rel_path}: not checked out with LF (needs `{ATTRIBUTES_LINE}` in .gitattributes; "
                "run: approval.py attributes --fix)"
            )
    return problems


def cmd_attributes(root: Path, fix: bool) -> None:
    problems = attribute_problems(root)
    if not problems:
        print("ok")
        return
    if not fix:
        raise ApprovalError(problems)

    path = root / ".gitattributes"
    if path.is_symlink():
        raise ApprovalError([".gitattributes: is a symbolic link; not written through it"])
    try:
        text = path.read_bytes().decode("utf-8") if path.exists() else ""
        if text and not text.endswith("\n"):
            text += "\n"
        text += "# Client-facing documents are approved by the SHA-256 of their bytes, so every checkout writes them with LF.\n"
        text += ATTRIBUTES_LINE + "\n"
        path.write_bytes(text.encode("utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ApprovalError([f".gitattributes: cannot update: {getattr(error, 'strerror', None) or error}"]) from None

    problems = attribute_problems(root)
    if problems:  # a rule in another attributes file still wins
        raise ApprovalError(problems)
    staged = [".gitattributes"]
    # The attribute does not change blobs already committed with CRLF; renormalizing does (ADR 0012).
    if git(root, "ls-files", "--", CLIENT_DIR).stdout.strip():
        result = git(root, "add", "--renormalize", "--", CLIENT_DIR)
        if result.returncode != 0:
            raise ApprovalError([f"git add --renormalize failed: {result.stderr.decode('utf-8').strip()}"])
        staged.append(f"{CLIENT_DIR}/")
    git(root, "add", "--", ".gitattributes")
    print(f"added `{ATTRIBUTES_LINE}` to .gitattributes and staged {' and '.join(staged)}: commit now")


def changelog_version(text: str) -> int | None:
    versions = [int(number) for number in CHANGELOG_ROW_RE.findall(text)]
    return max(versions) if versions else None


def tracked_keyturn_problems(root: Path) -> list[str]:
    if git(root, "ls-files", "--", KEYTURN_DIR).stdout.strip():
        return [f"Git tracks files under {KEYTURN_DIR}/; translations are never committed, so nothing is kept there"]
    if git(root, "check-ignore", "-q", f"{KEYTURN_DIR}/").returncode != 0:
        return [f"{KEYTURN_DIR}/ is not ignored by Git, so a translation could be committed (run: localize.py ignore)"]
    return []


def source_problems(root: Path, version: int, source: bytes) -> list[str]:
    """Problems with requirements.md itself: it must be the committed version, with LF, and list this version."""
    problems = attribute_problems(root)
    if b"\r" in source:
        problems.append(f"{REQUIREMENTS}: contains a carriage return (CR); save it with LF line endings and commit it")
    committed = git(root, "show", f"HEAD:{REQUIREMENTS}")
    if committed.returncode != 0:
        problems.append(f"{REQUIREMENTS}: not committed; commit it before sending it")
    elif sha256(committed.stdout) != sha256(source):
        problems.append(f"{REQUIREMENTS}: differs from the committed version; commit it before sending it")
    newest = changelog_version(source.decode("utf-8", errors="replace"))
    if newest != version:
        found = "no changelog row" if newest is None else f"the newest changelog row is version {newest}"
        problems.append(f"{REQUIREMENTS}: {found}; add the row for version {version} before sending it")
    return problems


def translation_problems(root: Path, lang: str, source_sha: str, rel_kept: str) -> tuple[bytes, list[str]]:
    """Read the translation the client will read, and return it with its problems.

    It must be fresh, stay outside Git, and match any copy already kept for this version.
    """
    problems = tracked_keyturn_problems(root)
    rel_translation = translation_path(lang)
    try:
        translation = read_bytes(root, rel_translation)
    except ApprovalError as error:
        problems += [f"{problem} (translate {REQUIREMENTS} with localize first)" for problem in error.problems]
        return b"", problems
    header = TRANSLATION_HEADER_RE.match(translation)
    if not header or header.group(1).decode() != source_sha:
        problems.append(f"{rel_translation}: not a fresh translation of {REQUIREMENTS}; translate it with localize first")
    kept = root / rel_kept
    if os.path.lexists(kept) and (kept.is_symlink() or kept.read_bytes() != translation):
        problems.append(f"{rel_kept}: a different translation was already kept for this version")
    return translation, problems


def keep_translation(root: Path, rel_kept: str, translation: bytes) -> None:
    """Keep the translation sent for approval. A copy that exists was checked to be identical, so it stays as it is."""
    kept = root / rel_kept
    if kept.exists():
        return
    try:
        with open(kept, "xb") as file:  # "x": never overwrite a kept copy
            file.write(translation)
    except OSError as error:
        raise ApprovalError([f"{rel_kept}: cannot write: {error.strerror or error}"]) from None


def cmd_send(root: Path, version: int, lang: str | None) -> None:
    source = read_bytes(root, REQUIREMENTS)
    source_sha = sha256(source)
    problems = source_problems(root, version, source)
    if not lang:  # the client reads requirements.md itself
        if problems:
            raise ApprovalError(problems)
        print(f"source-sha256: {source_sha}")
        print("translation-sha256: none")
        return

    rel_kept = kept_copy_path(lang, version)
    translation, translation_issues = translation_problems(root, lang, source_sha, rel_kept)
    problems += translation_issues
    if problems:
        raise ApprovalError(problems)
    print(f"source-sha256: {source_sha}")
    keep_translation(root, rel_kept, translation)
    print(f"translation-sha256: {sha256(translation)}")
    print(f"kept: {rel_kept}")


def approval_rows(text: str) -> list[list[str]]:
    """The requirements.md rows of the approvals table, in file order (newest last).

    Columns are found by position, not by heading, because the headings are in the client's language.
    """
    rows = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 5 and cells[0] == "requirements.md" and cells[1].isdigit():
            rows.append(cells)
    return rows


def cmd_status(root: Path, lang: str | None) -> None:
    rows = approval_rows(read_bytes(root, APPROVALS).decode("utf-8", errors="replace"))
    if not rows:
        raise ApprovalError([f"{APPROVALS}: no row for requirements.md"])
    version, row_source, row_translation = int(rows[-1][1]), rows[-1][3], rows[-1][4]
    answer = rows[-1][6] if len(rows[-1]) > 6 and rows[-1][6] else "(empty)"
    if not SHA_RE.fullmatch(row_source):
        raise ApprovalError([f"{APPROVALS}: version {version}: the source SHA-256 is not a SHA-256"])

    problems = []
    if sha256(read_bytes(root, REQUIREMENTS)) == row_source:
        # "current" only means the file is the one sent; whether it is approved is the client's answer, shown as written.
        print(f"version {version}: current, answer: {answer}")
    else:
        problems.append(f"version {version}: stale ({REQUIREMENTS} changed since it was sent)")

    if not SHA_RE.fullmatch(row_translation):
        print(f"version {version}: no translation (the client read {REQUIREMENTS} itself)")
    elif not lang:
        problems.append(f"version {version}: the client read a translation; give its language with --lang")
    else:
        kept = kept_copy_path(lang, version)
        if not (root / kept).is_file():
            problems.append(f"{kept}: missing; the approved text cannot be shown again")
        elif sha256((root / kept).read_bytes()) != row_translation:
            problems.append(f"{kept}: changed since it was sent; it is not the text the client read")
        else:
            print(f"kept: {kept}")

    if problems:
        raise ApprovalError(problems)


def check_lang(lang: str) -> str:
    """Accept only language codes, so the code is safe to use as a folder name."""
    if not LANG_RE.fullmatch(lang):
        raise argparse.ArgumentTypeError(f"not a language code: {lang!r} (use e.g. ja, de, pt-BR)")
    return lang


def check_version(version: str) -> int:
    if not version.isdigit() or int(version) < 1:
        raise argparse.ArgumentTypeError(f"not a version number: {version!r} (use 1, 2, ...)")
    return int(version)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and record approvals of keyturn/client/requirements.md.")
    commands = parser.add_subparsers(dest="command", required=True)
    attributes = commands.add_parser("attributes", help="check that client documents are checked out with LF")
    attributes.add_argument("--fix", action="store_true", help="add the .gitattributes line and renormalize")
    send = commands.add_parser("send", help="check requirements.md before sending it, and keep the translation")
    send.add_argument("version", type=check_version)
    send.add_argument("--lang", type=check_lang)
    status = commands.add_parser("status", help="check the newest approval row")
    status.add_argument("--lang", type=check_lang)
    args = parser.parse_args()

    try:
        root = repo_root()
        if args.command == "attributes":
            cmd_attributes(root, args.fix)
        elif args.command == "send":
            cmd_send(root, args.version, args.lang)
        else:
            cmd_status(root, args.lang)
    except ApprovalError as error:
        for problem in error.problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
