#!/usr/bin/env python3
"""Read-only structural inventory for an itch.io asset-pack candidate.

This tool does not validate naming conventions, alpha, animation matrices,
Aseprite tags, frame order, or FPS. Those require asset-specific QA.
Godot project detection checks for `project.godot` and related resource files;
it does not identify or validate the Godot version.
Exit codes: 0 = inventory and any ZIP CRC verification completed without
errors, suspicious entries, invalid PNG headers, or incomplete ZIP CRC
verification, 1 = one or more of those problems were found, 2 = invalid input
or output usage.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import posixpath
import re
import stat
import struct
import sys
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".svg", ".bmp"}
SOURCE_EXTENSIONS = {".ase", ".aseprite", ".psd", ".kra", ".blend"}
AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac", ".m4a", ".aiff", ".aif", ".wma"}
MODEL_EXTENSIONS = {".fbx", ".obj", ".gltf", ".glb"}
GODOT_EXTENSIONS = {".godot", ".tscn", ".tres", ".gd", ".gdshader"}
DOCUMENT_NAMES = {
    "readme",
    "license",
    "licenses",
    "licence",
    "licences",
    "copying",
    "changelog",
    "credits",
    "attribution",
    "attributions",
    "third-party-notices",
}
DOCUMENT_BACKUP_MARKERS = {
    "backup",
    "backups",
    "copy",
    "copies",
    "draft",
    "drafts",
    "legacy",
    "old",
    "orig",
    "rej",
    "save",
    "temp",
    "temps",
    "tmp",
}
FORBIDDEN_DIRECTORY_MARKERS = {
    "backup",
    "backups",
    "draft",
    "drafts",
    "temp",
    "temps",
    "tmp",
}
FORBIDDEN_PARTS = {
    ".godot",
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__macosx",
    "node_modules",
    "temp",
    "tmp",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
}
FORBIDDEN_NAMES = {".ds_store", "desktop.ini", "thumbs.db"}
FORBIDDEN_SUFFIXES = {".ctex", ".import", ".tmp", ".log", ".bak", ".pyc", ".swp", ".swo", ".swn"}
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


@dataclass
class Report:
    root: str
    kind: str
    file_count: int = 0
    non_document_file_count: int = 0
    total_bytes: int = 0
    extensions: collections.Counter[str] = field(default_factory=collections.Counter)
    png_sizes: collections.Counter[str] = field(default_factory=collections.Counter)
    documents: set[str] = field(default_factory=set)
    root_documents: set[str] = field(default_factory=set)
    godot_files: list[str] = field(default_factory=list)
    suspicious: list[str] = field(default_factory=list)
    duplicate_entries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    inventory_complete: bool = True
    crc_test_complete: bool | None = None
    unreadable_entries: list[str] = field(default_factory=list)
    invalid_png_files: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "kind": self.kind,
            "file_count": self.file_count,
            "non_document_file_count": self.non_document_file_count,
            "total_bytes": self.total_bytes,
            "extensions": dict(self.extensions.most_common()),
            "png_sizes": dict(self.png_sizes.most_common()),
            "documents": sorted(self.documents),
            "root_documents": sorted(self.root_documents),
            "godot_files": self.godot_files,
            "suspicious": self.suspicious,
            "duplicate_entries": self.duplicate_entries,
            "notes": self.notes,
            "errors": self.errors,
            "inventory_complete": self.inventory_complete,
            "crc_test_complete": self.crc_test_complete,
            "unreadable_entries": self.unreadable_entries,
            "invalid_png_files": self.invalid_png_files,
        }


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if (
        len(data) < 33
        or data[:8] != b"\x89PNG\r\n\x1a\n"
        or struct.unpack(">I", data[8:12])[0] != 13
        or data[12:16] != b"IHDR"
        or zlib.crc32(data[12:29]) != struct.unpack(">I", data[29:33])[0]
    ):
        return None
    width, height = struct.unpack(">II", data[16:24])
    return (width, height) if 0 < width <= 0x7FFFFFFF and 0 < height <= 0x7FFFFFFF else None


def stem_is_document(path: str) -> bool:
    path = path.replace("\\", "/")
    file_path = Path(path)
    suffix_token = file_path.suffix.lower().lstrip(".")
    if (
        "~" in file_path.name
        or file_path.suffix.lower() in FORBIDDEN_SUFFIXES
        or suffix_token in DOCUMENT_BACKUP_MARKERS
    ):
        return False
    for parent in file_path.parent.parts:
        parent_tokens = {token for token in re.split(r"[._()\s-]+", parent.lower()) if token}
        if parent_tokens & DOCUMENT_BACKUP_MARKERS:
            return False
    name = re.sub(r"[._()\s-]+", "-", file_path.stem.lower()).strip("-")
    if is_numbered_document_copy(name):
        return False
    if name in DOCUMENT_NAMES:
        return True
    for document_name in DOCUMENT_NAMES:
        prefix = f"{document_name}-"
        if not name.startswith(prefix):
            continue
        qualifiers = {part for part in name[len(prefix) :].split("-") if part}
        return bool(qualifiers) and not qualifiers & DOCUMENT_BACKUP_MARKERS
    return False


def is_numbered_document_copy(normalized_stem: str) -> bool:
    """Return whether a document stem ends in an OS-style 1-99 copy number."""
    return any(
        re.fullmatch(r"[1-9]\d?", normalized_stem[len(document_name) + 1 :]) is not None
        for document_name in DOCUMENT_NAMES
        if normalized_stem.startswith(f"{document_name}-")
    )


def stem_looks_like_document(path: str) -> bool:
    file_path = Path(path.replace("\\", "/"))
    candidate = Path(file_path.name.rstrip("~"))
    if candidate.suffix.lower() in FORBIDDEN_SUFFIXES:
        candidate = Path(candidate.stem)
    name = re.sub(r"[._()\s-]+", "-", candidate.stem.lower()).strip("-")
    return name in DOCUMENT_NAMES or any(name.startswith(f"{document_name}-") for document_name in DOCUMENT_NAMES)


def is_suspicious(path: str) -> bool:
    has_literal_backslash = "\\" in path
    normalized = path.replace("\\", "/")
    raw_parts = Path(normalized).parts
    parts = {part.lower() for part in raw_parts}
    file_path = Path(normalized)
    name = file_path.name.lower()
    stem = file_path.stem.lower()
    suffix = file_path.suffix.lower()
    normalized_stem = re.sub(r"[._()\s-]+", "-", file_path.stem.lower()).strip("-")
    document_backup_name = any(
        normalized_stem.startswith(f"{document_name}-")
        and {
            token
            for token in normalized_stem[len(document_name) + 1 :].split("-")
            if token
        }
        & DOCUMENT_BACKUP_MARKERS
        for document_name in DOCUMENT_NAMES
    )
    parent_tokens = {
        token
        for parent in file_path.parent.parts
        for token in re.split(r"[._()\s-]+", parent.lower())
        if token
    }
    return (
        has_literal_backslash
        or normalized.startswith("/")
        or bool(re.match(r"^[a-zA-Z]:", normalized))
        or ":" in normalized
        or any(part == "." for part in normalized.split("/"))
        or "//" in normalized
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
        or ".." in parts
        or any(part.rstrip(". ") != part for part in raw_parts)
        or any(part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_NAMES for part in raw_parts)
        or bool(parts & FORBIDDEN_PARTS)
        or bool(parent_tokens & FORBIDDEN_DIRECTORY_MARKERS)
        or name in FORBIDDEN_NAMES
        or stem in {"temp", "tmp"}
        or name.startswith("._")
        or name.startswith(".#")
        or "~" in name
        or (name.startswith("#") and name.endswith("#"))
        or document_backup_name
        or is_numbered_document_copy(normalized_stem)
        or suffix.lstrip(".") in DOCUMENT_BACKUP_MARKERS
        or suffix in FORBIDDEN_SUFFIXES
    )


def is_suspicious_directory(path: str) -> bool:
    normalized = path.replace("\\", "/").rstrip("/")
    directory_tokens = {
        token
        for part in Path(normalized).parts
        for token in re.split(r"[._()\s-]+", part.lower())
        if token
    }
    return is_suspicious(normalized) or bool(directory_tokens & FORBIDDEN_DIRECTORY_MARKERS)


def inspect_entries(
    report: Report,
    entries: list[tuple[str, int, bytes | None]],
) -> None:
    for name, size, header in entries:
        normalized_name = name.replace("\\", "/")
        if normalized_name.endswith("/"):
            continue
        file_path = Path(normalized_name)
        document = stem_is_document(name)
        suspicious = is_suspicious(name)
        report.file_count += 1
        report.total_bytes += size
        suffix = file_path.suffix.lower() or "[no extension]"
        report.extensions[suffix] += 1
        if document:
            report.documents.add(file_path.name)
            if posixpath.dirname(normalized_name) == "":
                report.root_documents.add(file_path.name)
        if not stem_looks_like_document(name) and not suspicious:
            report.non_document_file_count += 1
        if suffix in GODOT_EXTENSIONS or file_path.name == "project.godot":
            report.godot_files.append(name)
        if suspicious:
            report.suspicious.append(name)
        if suffix == ".png" and header is not None:
            dimensions = png_dimensions(header)
            if dimensions:
                report.png_sizes[f"{dimensions[0]}x{dimensions[1]}"] += 1
            else:
                report.invalid_png_files.append(name)


def inspect_directory(root: Path) -> Report:
    report = Report(str(root), "directory")
    entries: list[tuple[str, int, bytes | None]] = []

    def record_walk_error(exc: OSError) -> None:
        try:
            relative = Path(exc.filename).relative_to(root).as_posix() if exc.filename else "[unknown directory]"
        except ValueError:
            relative = str(exc.filename)
        report.inventory_complete = False
        report.errors.append(f"Cannot scan directory {relative}: {exc}")

    for directory, directory_names, file_names in os.walk(root, topdown=True, followlinks=False, onerror=record_walk_error):
        directory_path = Path(directory)
        for name in list(directory_names):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if is_suspicious_directory(relative):
                report.suspicious.append(relative)
            if path.is_symlink():
                if relative not in report.suspicious:
                    report.suspicious.append(relative)
                directory_names.remove(name)
        directory_names.sort()
        for name in sorted(file_names):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                report.suspicious.append(relative)
                continue
            try:
                file_stat = path.stat()
                size = file_stat.st_size
                if not stat.S_ISREG(file_stat.st_mode):
                    report.errors.append(f"{relative}: not a regular file; skipped")
                    continue
                header = None
                if path.suffix.lower() == ".png":
                    with path.open("rb") as file:
                        header = file.read(33)
            except OSError as exc:
                report.errors.append(f"{relative}: {exc}")
                continue
            entries.append((relative, size, header))
    inspect_entries(report, entries)
    return report


def inspect_zip(root: Path) -> Report:
    report = Report(str(root), "zip")
    report.crc_test_complete = True
    entries: list[tuple[str, int, bytes | None]] = []
    unreadable_entries: set[str] = set()
    seen_names: dict[str, str] = {}
    duplicate_entries: list[str] = []
    collided_keys: set[str] = set()
    file_entries_by_key: dict[str, list[str]] = collections.defaultdict(list)
    file_entry_records: list[tuple[str, str]] = []
    try:
        with zipfile.ZipFile(root) as archive:
            for info in archive.infolist():
                header = None
                collision_key = posixpath.normpath(
                    unicodedata.normalize("NFC", info.filename.replace("\\", "/").casefold())
                ).rstrip("/")
                if collision_key in seen_names:
                    if collision_key not in collided_keys:
                        duplicate_entries.append(seen_names[collision_key])
                        collided_keys.add(collision_key)
                    duplicate_entries.append(info.filename)
                else:
                    seen_names[collision_key] = info.filename
                unix_mode = info.external_attr >> 16
                is_symlink = stat.S_ISLNK(unix_mode)
                is_directory = info.is_dir() or stat.S_ISDIR(unix_mode)
                stripped_directory_name = info.filename.rstrip("/\\")
                if is_directory and (not stripped_directory_name or is_suspicious_directory(stripped_directory_name)):
                    report.suspicious.append(info.filename)
                if not is_directory:
                    file_entries_by_key[collision_key].append(info.filename)
                    file_entry_records.append((collision_key, info.filename))
                if is_symlink:
                    report.suspicious.append(info.filename)
                    unreadable_entries.add(info.filename)
                is_encrypted = bool(info.flag_bits & 0x1)
                if not is_directory and is_encrypted:
                    unreadable_entries.add(info.filename)
                if not is_directory and not is_symlink and not is_encrypted:
                    try:
                        with archive.open(info) as file:
                            if Path(info.filename).suffix.lower() == ".png":
                                header = file.read(33)
                            while file.read(1024 * 1024):
                                pass
                    except (OSError, EOFError, UnicodeError, zlib.error, zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError) as exc:
                        report.errors.append(f"Cannot read ZIP entry {info.filename}: {exc}")
                        unreadable_entries.add(info.filename)
                        report.crc_test_complete = False
                        header = None
                if not is_directory:
                    entries.append((info.filename, info.file_size, header))
                if is_encrypted:
                    report.errors.append(f"Cannot read encrypted ZIP entry {info.filename} without a password")
                    report.crc_test_complete = False
            implicit_collisions: set[str] = set()
            for collision_key, original_name in file_entry_records:
                parent_key = posixpath.dirname(collision_key)
                while parent_key not in {"", ".", "/"}:
                    if parent_key in file_entries_by_key:
                        implicit_collisions.update(file_entries_by_key[parent_key])
                        implicit_collisions.add(original_name)
                    parent_key = posixpath.dirname(parent_key)
            for name in sorted(implicit_collisions):
                if name not in duplicate_entries:
                    duplicate_entries.append(name)
            if unreadable_entries:
                report.crc_test_complete = False
            report.unreadable_entries = sorted(unreadable_entries)
            report.duplicate_entries = sorted(duplicate_entries)
            if report.duplicate_entries:
                report.errors.append(
                    f"{len(report.duplicate_entries)} ZIP entries collide after cross-platform path normalization"
                )
    except (OSError, EOFError, UnicodeError, zlib.error, zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError) as exc:
        report.errors.append(f"Cannot read ZIP: {exc}")
        report.inventory_complete = False
        report.crc_test_complete = False
        return report
    inspect_entries(report, entries)
    return report


def add_notes(report: Report) -> None:
    if not report.inventory_complete:
        if report.kind == "zip":
            report.notes.append("ZIP inventory is unavailable because the central directory could not be read; do not infer missing contents from this report.")
            return
        report.notes.append("Directory scan is incomplete; file and byte totals exclude unscanned subtrees.")
    if report.inventory_complete:
        if report.file_count == 0:
            report.errors.append("No files found in the inspected tree; an empty asset pack is not a valid release candidate")
        else:
            if report.non_document_file_count == 0:
                report.errors.append("No non-document deliverable files found; a documentation-only asset pack is not a valid release candidate")
            normalized_root_documents = {name.lower() for name in report.root_documents}
            if not any(name.startswith("readme") for name in normalized_root_documents):
                report.errors.append("README is missing from the inspected root")
            if not any(name.startswith(("license", "licence", "copying")) for name in normalized_root_documents):
                report.errors.append("LICENSE or COPYING is missing from the inspected root")
    extensions = set(report.extensions)
    if ".png" in extensions and len(report.png_sizes) > 8:
        report.notes.append("Many PNG canvas sizes found; document which sizes are tiles, frames, previews, or source sheets.")
    if extensions & GODOT_EXTENSIONS:
        normalized_godot_paths = [Path(path.replace("\\", "/")) for path in report.godot_files]
        if not any(path.name == "project.godot" for path in normalized_godot_paths):
            report.notes.append("Godot resources found without project.godot; do not claim a standalone Godot project.")
        if not any(path.suffix.lower() == ".tscn" for path in normalized_godot_paths):
            report.notes.append("Godot files found without a scene; add a demo/entry scene before claiming demo-ready.")
    if extensions & IMAGE_EXTENSIONS and not (extensions & SOURCE_EXTENSIONS):
        report.notes.append("Rendered images found, but no editable source format detected; disclose that source files are not included.")
    if extensions & AUDIO_EXTENSIONS:
        report.notes.append("Audio detected; document codec, sample rate, channels, loop behavior, and license.")
    if extensions & MODEL_EXTENSIONS:
        report.notes.append("3D models detected; document units, axes, pivots, materials, textures, rig, and engine import versions.")
    if report.suspicious:
        report.notes.append(
            "Forbidden caches, history, editor metadata, system junk, temporary files, symlinks, or unsafe archive paths detected; "
            "file, byte, and extension totals include these suspicious entries and must not be treated as usable-content counts; "
            "exclude them from buyer ZIPs."
        )
    if report.duplicate_entries:
        report.notes.append(
            f"{len(report.duplicate_entries)} duplicate ZIP entr{'y' if len(report.duplicate_entries) == 1 else 'ies'} detected; "
            "file, byte, and extension totals include these entries and must not be treated as usable-content counts; "
            "rebuild the archive with unique paths."
        )
    if report.invalid_png_files:
        report.notes.append(
            f"{len(report.invalid_png_files)} PNG file{' has' if len(report.invalid_png_files) == 1 else 's have'} an invalid or truncated header; inspect or replace before release."
        )
    if report.unreadable_entries:
        report.notes.append(
            f"File and byte totals include {len(report.unreadable_entries)} unreadable ZIP entr{'y' if len(report.unreadable_entries) == 1 else 'ies'}; do not treat those totals as usable-content counts."
        )
    if report.crc_test_complete is False:
        report.notes.append("ZIP CRC verification did not complete; file and byte totals are structural inventory only, not verified usable-content counts.")


def render_markdown(report: Report) -> str:
    if report.inventory_complete:
        file_summary = str(report.file_count)
    elif report.kind == "zip":
        file_summary = "unavailable (ZIP directory unreadable)"
    else:
        file_summary = f"{report.file_count} (partial)"
    lines = [
        "# Asset Pack Audit",
        "",
        f"- Root: `{report.root}`",
        f"- Kind: `{report.kind}`",
        f"- Files: {file_summary}",
        f"- Non-document files: {report.non_document_file_count}",
        f"- Total bytes: {report.total_bytes}",
        f"- Inventory complete: {'yes' if report.inventory_complete else 'no'}",
        f"- CRC test complete: {'n/a' if report.crc_test_complete is None else 'yes' if report.crc_test_complete else 'no'}",
        f"- Unreadable entries: {len(report.unreadable_entries)}",
        f"- Invalid PNG files: {len(report.invalid_png_files)}",
        "",
        "## Extensions",
        "",
    ]
    if report.extensions:
        lines.extend(f"- `{ext}`: {count}" for ext, count in report.extensions.most_common())
    else:
        lines.append("- None detected")
    lines.extend(["", "## PNG canvas sizes", ""])
    if report.png_sizes:
        lines.extend(f"- `{size}`: {count}" for size, count in report.png_sizes.most_common())
    else:
        lines.append("- None detected")
    if report.invalid_png_files:
        lines.append("")
        lines.append("Invalid or truncated PNG headers:")
        lines.extend(f"- `{name}`" for name in report.invalid_png_files[:100])
        if len(report.invalid_png_files) > 100:
            lines.append(f"- … and {len(report.invalid_png_files) - 100} more")
    lines.extend(["", "## Documents", ""])
    if report.documents:
        lines.extend(f"- `{name}`" for name in sorted(report.documents))
    else:
        lines.append("- None detected")
    lines.extend(["", "## Root documents", ""])
    if report.root_documents:
        lines.extend(f"- `{name}`" for name in sorted(report.root_documents))
    else:
        lines.append("- None detected")
    lines.extend(["", "## Godot files", ""])
    if report.godot_files:
        lines.extend(f"- `{name}`" for name in report.godot_files[:50])
    else:
        lines.append("- None detected")
    if len(report.godot_files) > 50:
        lines.append(f"- … and {len(report.godot_files) - 50} more")
    lines.extend(["", "## Suspicious deliverable entries", ""])
    if report.suspicious:
        lines.extend(f"- `{name}`" for name in report.suspicious[:100])
    else:
        lines.append("- None detected")
    if len(report.suspicious) > 100:
        lines.append(f"- … and {len(report.suspicious) - 100} more")
    lines.extend(["", "## Duplicate ZIP entries", ""])
    if report.duplicate_entries:
        lines.extend(f"- `{name}`" for name in report.duplicate_entries[:100])
    else:
        lines.append("- None detected")
    if len(report.duplicate_entries) > 100:
        lines.append(f"- … and {len(report.duplicate_entries) - 100} more")
    lines.extend(["", "## Notes", ""])
    if report.notes:
        lines.extend(f"- {note}" for note in report.notes)
    else:
        lines.append("- None")
    lines.extend(["", "## Errors", ""])
    if report.errors:
        lines.extend(f"- {error}" for error in report.errors)
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Asset directory or ZIP to inspect")
    parser.add_argument("--markdown", action="store_true", help="Render a Markdown report instead of JSON")
    parser.add_argument("--output", type=Path, help="Write the report only to this path; stdout remains empty")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing report file; never overwrites the input or writes inside an audited directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.path.expanduser().resolve()
    if root.is_dir():
        report = inspect_directory(root)
    elif root.is_file() and root.suffix.lower() == ".zip":
        report = inspect_zip(root)
    else:
        print(f"error: expected a directory or .zip file: {root}", file=sys.stderr)
        return 2
    add_notes(report)
    content = render_markdown(report) if args.markdown else json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n"
    content_bytes = content.encode("utf-8", errors="backslashreplace")
    if args.output:
        output = args.output.expanduser().resolve()
        same_input = output.exists() and os.path.samefile(root, output)
        if output == root or same_input or (root.is_dir() and root in output.parents):
            print("error: output path must not overwrite the input or be inside the audited directory", file=sys.stderr)
            return 2
        if output.exists() and output.is_dir():
            print(f"error: output path is a directory: {output}", file=sys.stderr)
            return 2
        if output.exists() and not args.force:
            print(f"error: output file already exists; use --force to overwrite: {output}", file=sys.stderr)
            return 2
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content_bytes)
        except OSError as exc:
            print(f"error: cannot write output: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.buffer.write(content_bytes)
    return 1 if report.errors or report.suspicious or report.invalid_png_files or report.crc_test_complete is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
