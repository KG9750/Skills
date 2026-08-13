import argparse
import json
import importlib.util
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_asset_pack.py"
README_TEMPLATE = Path(__file__).parents[1] / "assets" / "release-candidate" / "README.template.md"
SPEC = importlib.util.spec_from_file_location("audit_asset_pack", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def png_header(width: int = 32, height: int = 48) -> bytes:
    chunk = b"IHDR" + struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + chunk + struct.pack(">I", AUDIT.zlib.crc32(chunk))


def png_file(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", AUDIT.zlib.crc32(payload))

    ihdr = struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
    rows = b"".join(b"\x00" + b"\x00" * (width * 4) for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", AUDIT.zlib.compress(rows)) + chunk(b"IEND", b"")


class AuditAssetPackTests(unittest.TestCase):
    def test_png_header_validation(self) -> None:
        self.assertEqual(AUDIT.png_dimensions(png_header()), (32, 48))
        self.assertIsNone(AUDIT.png_dimensions(b"not a png"))
        bad_crc = bytearray(png_header())
        bad_crc[-1] ^= 1
        self.assertIsNone(AUDIT.png_dimensions(bytes(bad_crc)))
        self.assertIsNone(AUDIT.png_dimensions(png_header(0, 48)))
        self.assertIsNone(AUDIT.png_dimensions(png_header(32, 0)))
        self.assertIsNone(AUDIT.png_dimensions(png_header(0xFFFFFFFF, 48)))
        self.assertEqual(AUDIT.png_dimensions(png_header(0x7FFFFFFF, 1)), (0x7FFFFFFF, 1))

    def test_document_and_suspicious_path_heuristics(self) -> None:
        self.assertTrue(AUDIT.stem_is_document(r"Product\LICENSE-MIT.txt"))
        self.assertTrue(AUDIT.stem_is_document("Product/LICENSE (MIT).txt"))
        self.assertTrue(AUDIT.stem_is_document("Product/README (ENG).md"))
        self.assertTrue(AUDIT.stem_is_document("Product/CHANGELOG (2024-06).md"))
        self.assertTrue(AUDIT.stem_is_document("Product/README (2024).md"))
        self.assertTrue(AUDIT.stem_is_document("Product/THIRD-PARTY-NOTICES.txt"))
        self.assertTrue(AUDIT.stem_is_document("Product/LICENSES.txt"))
        self.assertTrue(AUDIT.stem_is_document("Product/LICENCES.txt"))
        self.assertTrue(AUDIT.stem_is_document("Product/ATTRIBUTIONS.txt"))
        self.assertTrue(AUDIT.stem_is_document("Product/COPYING"))
        self.assertFalse(AUDIT.stem_is_document("Product/README (old).md"))
        self.assertFalse(AUDIT.stem_is_document("Product/backups/README.md"))
        self.assertFalse(AUDIT.stem_is_document("Product/drafts/LICENSE.txt"))
        self.assertFalse(AUDIT.stem_is_document("Product/README.txt.bak"))
        self.assertFalse(AUDIT.stem_is_document("Product/README.md~"))
        self.assertFalse(AUDIT.stem_is_document("README.old"))
        self.assertFalse(AUDIT.stem_is_document("LICENSE.backup"))
        self.assertFalse(AUDIT.stem_is_document("LICENSE.temp"))
        self.assertFalse(AUDIT.stem_is_document("README (2).md"))
        self.assertFalse(AUDIT.stem_is_document("LICENSE(1).txt"))
        self.assertTrue(AUDIT.stem_looks_like_document("Product/backups/README.md"))
        self.assertTrue(AUDIT.stem_looks_like_document("Product/README.txt.bak"))
        self.assertTrue(AUDIT.stem_looks_like_document("Product/README.md~"))
        self.assertFalse(AUDIT.stem_looks_like_document("Product/hero.png"))
        self.assertTrue(AUDIT.is_suspicious("Product/notes.md~"))
        self.assertTrue(AUDIT.is_suspicious("Product/hero~.png"))
        self.assertTrue(AUDIT.is_suspicious("Product/hero.swp"))
        self.assertTrue(AUDIT.is_suspicious("Product/.hero.png.swo"))
        self.assertTrue(AUDIT.is_suspicious("Product/#hero.png#"))
        self.assertTrue(AUDIT.is_suspicious("Product/.#hero.dat"))
        self.assertTrue(AUDIT.is_suspicious("Product/__pycache__"))
        self.assertTrue(AUDIT.is_suspicious("Product/backups/hero.png"))
        self.assertTrue(AUDIT.is_suspicious("Product/draft notes/hero.png"))
        self.assertTrue(AUDIT.is_suspicious_directory("Product/backups"))
        self.assertTrue(AUDIT.is_suspicious_directory("Product/draft notes"))
        self.assertTrue(AUDIT.is_suspicious("README.old"))
        self.assertTrue(AUDIT.is_suspicious("LICENSE.backup"))
        self.assertTrue(AUDIT.is_suspicious("README (old).md"))
        self.assertTrue(AUDIT.is_suspicious("LICENSE-backup.txt"))
        self.assertTrue(AUDIT.is_suspicious(r"Product\Thumbs.db"))
        self.assertTrue(AUDIT.is_suspicious(r"Product\hero.dat"))
        self.assertTrue(AUDIT.is_suspicious("Product/.godot/cache.bin"))
        self.assertTrue(AUDIT.is_suspicious("../evil.txt"))
        self.assertTrue(AUDIT.is_suspicious("/absolute/evil.txt"))
        self.assertTrue(AUDIT.is_suspicious(r"C:\absolute\evil.txt"))
        self.assertTrue(AUDIT.is_suspicious("C:relative-evil.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/C:evil.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/a:b.png"))
        self.assertTrue(AUDIT.is_suspicious("Product/.../evil.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/.. /evil.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/evil.txt."))
        self.assertTrue(AUDIT.is_suspicious("Product/evil\x00name.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/evil\nname.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/temp.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/tmp.json"))
        self.assertTrue(AUDIT.is_suspicious("Product/temp/notes.txt"))
        self.assertTrue(AUDIT.is_suspicious("Product/tmp/notes.txt"))
        self.assertTrue(AUDIT.is_suspicious("./hero.png"))
        self.assertTrue(AUDIT.is_suspicious("Product/./README.md"))
        self.assertTrue(AUDIT.is_suspicious("Product//LICENSE.txt"))
        for name in ("CON.md", "aux.txt", "prn", "nul.png", "com1.dat", "COM9", "lpt1.txt", "LPT9.bin"):
            self.assertTrue(AUDIT.is_suspicious(f"Product/{name}"))
        self.assertTrue(AUDIT.is_suspicious("Product/CON/hero.png"))
        self.assertFalse(AUDIT.is_suspicious("Product/console.md"))
        self.assertFalse(AUDIT.is_suspicious("Product/com10.dat"))
        self.assertFalse(AUDIT.is_suspicious("Product/.gitignore"))
        self.assertFalse(AUDIT.is_suspicious("Product/.gitattributes"))

    def test_healthy_nonempty_zip_reports_sizes_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "healthy.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("README.md", "Import instructions")
                archive.writestr("LICENSE.txt", "License terms")
                archive.writestr("Product/sprites/hero.png", png_file(16, 24))
                archive.writestr("Product/sprites/prop.png", png_file(32, 32))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["crc_test_complete"])
        self.assertEqual(report["png_sizes"], {"16x24": 1, "32x32": 1})
        self.assertEqual(report["file_count"], 4)
        self.assertEqual(report["non_document_file_count"], 2)
        self.assertEqual(report["root_documents"], ["LICENSE.txt", "README.md"])
        self.assertEqual(report["errors"], [])

    def test_backslash_directory_is_not_counted(self) -> None:
        report = AUDIT.Report("fixture", "zip")
        AUDIT.inspect_entries(report, [("Product\\", 0, None), (r"Product\README.md", 4, None)])
        self.assertEqual(report.file_count, 1)
        self.assertEqual(report.documents, {"README.md"})
        self.assertEqual(report.root_documents, set())
        self.assertEqual(report.non_document_file_count, 0)

    def test_invalid_png_is_reported(self) -> None:
        report = AUDIT.Report("fixture", "directory")
        AUDIT.inspect_entries(report, [("fake.png", 3, b"bad")])
        AUDIT.add_notes(report)
        self.assertEqual(report.invalid_png_files, ["fake.png"])
        self.assertTrue(any("invalid or truncated header" in note for note in report.notes))

    def test_invalid_png_exits_one_in_directory_and_zip_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "fake.png").write_bytes(b"bad")
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("README.md", "readme")
                archive.writestr("fake.png", b"bad")

            for candidate in (root, archive_path):
                with self.subTest(kind=candidate.suffix or "directory"):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(candidate)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    report = json.loads(result.stdout)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(report["invalid_png_files"], ["fake.png"])
                    if candidate == archive_path:
                        self.assertTrue(report["crc_test_complete"])

    def test_backup_readme_does_not_satisfy_document_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md~").write_text("backup", encoding="utf-8")
            report = AUDIT.inspect_directory(root)
            AUDIT.add_notes(report)

        self.assertEqual(report.documents, set())
        self.assertEqual(report.non_document_file_count, 0)
        self.assertTrue(any("README is missing" in error for error in report.errors))
        self.assertTrue(any("LICENSE or COPYING is missing" in error for error in report.errors))
        self.assertTrue(any("documentation-only asset pack" in error for error in report.errors))

    def test_plural_legal_document_names_are_recognized_in_directory_and_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            for name in ("LICENSES.txt", "LICENCES.txt", "ATTRIBUTIONS.txt"):
                (root / name).write_text("terms", encoding="utf-8")
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                for name in ("LICENSES.txt", "LICENCES.txt", "ATTRIBUTIONS.txt"):
                    archive.writestr(name, "terms")

            directory_report = AUDIT.inspect_directory(root)
            zip_report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(directory_report)
            AUDIT.add_notes(zip_report)

        expected = {"ATTRIBUTIONS.txt", "LICENCES.txt", "LICENSES.txt"}
        self.assertEqual(directory_report.documents, expected)
        self.assertEqual(zip_report.documents, expected)
        self.assertEqual(directory_report.non_document_file_count, 0)
        self.assertEqual(zip_report.non_document_file_count, 0)
        self.assertTrue(any("README is missing" in error for error in directory_report.errors))
        self.assertTrue(any("README is missing" in error for error in zip_report.errors))
        self.assertFalse(any("LICENSE or COPYING is missing" in error for error in directory_report.errors))
        self.assertFalse(any("LICENSE or COPYING is missing" in error for error in zip_report.errors))

    def test_copying_is_a_license_document_in_directory_and_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "COPYING").write_text("terms", encoding="utf-8")
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("COPYING", "terms")

            directory_report = AUDIT.inspect_directory(root)
            zip_report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(directory_report)
            AUDIT.add_notes(zip_report)

        for report in (directory_report, zip_report):
            self.assertEqual(report.documents, {"COPYING"})
            self.assertEqual(report.non_document_file_count, 0)
            self.assertTrue(any("documentation-only asset pack" in error for error in report.errors))
            self.assertTrue(any("README is missing" in error for error in report.errors))
            self.assertFalse(any("LICENSE or COPYING is missing" in error for error in report.errors))

    def test_required_document_matrix_in_directory_and_zip(self) -> None:
        cases = {
            "none": ((), 1),
            "readme-only": (("README.md",), 1),
            "license-only": (("LICENSE.txt",), 1),
            "both": (("README.md", "LICENSE.txt"), 0),
            "readme-copying": (("README.md", "COPYING"), 0),
        }
        with tempfile.TemporaryDirectory() as directory:
            for label, (documents, expected_exit) in cases.items():
                root = Path(directory) / label
                root.mkdir()
                (root / "asset.dat").write_bytes(b"asset")
                for name in documents:
                    (root / name).write_text("document", encoding="utf-8")
                archive_path = Path(directory) / f"{label}.zip"
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr("asset.dat", b"asset")
                    for name in documents:
                        archive.writestr(name, "document")

                for candidate in (root, archive_path):
                    with self.subTest(label=label, kind=candidate.suffix or "directory"):
                        result = subprocess.run(
                            [sys.executable, str(SCRIPT), str(candidate)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        report = json.loads(result.stdout)
                        self.assertEqual(result.returncode, expected_exit)
                        has_license = any(name in {"LICENSE.txt", "COPYING"} for name in documents)
                        self.assertEqual(
                            any("README is missing" in error for error in report["errors"]),
                            "README.md" not in documents,
                        )
                        self.assertEqual(
                            any("LICENSE or COPYING is missing" in error for error in report["errors"]),
                            not has_license,
                        )

    def test_nested_documents_do_not_satisfy_root_document_gate(self) -> None:
        for wrapper in ("docs", "Product"):
            with self.subTest(wrapper=wrapper), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "pack"
                nested = root / wrapper
                nested.mkdir(parents=True)
                (nested / "README.md").write_text("readme", encoding="utf-8")
                (nested / "LICENSE.txt").write_text("license", encoding="utf-8")
                (nested / "asset.dat").write_bytes(b"asset")
                archive_path = Path(directory) / "pack.zip"
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr(f"{wrapper}/README.md", "readme")
                    archive.writestr(f"{wrapper}/LICENSE.txt", "license")
                    archive.writestr(f"{wrapper}/asset.dat", b"asset")

                for candidate in (root, archive_path):
                    with self.subTest(kind=candidate.suffix or "directory"):
                        result = subprocess.run(
                            [sys.executable, str(SCRIPT), str(candidate)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        report = json.loads(result.stdout)
                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(report["documents"], ["LICENSE.txt", "README.md"])
                        self.assertEqual(report["root_documents"], [])
                        self.assertTrue(any("README is missing from the inspected root" in error for error in report["errors"]))
                        self.assertTrue(any("LICENSE or COPYING is missing from the inspected root" in error for error in report["errors"]))

    def test_editor_backup_is_suspicious_and_cannot_supply_deliverable_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "LICENSE.txt").write_text("license", encoding="utf-8")
            (root / "notes.md~").write_text("backup", encoding="utf-8")
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("README.md", "readme")
                archive.writestr("LICENSE.txt", "license")
                archive.writestr("notes.md~", "backup")

            for candidate in (root, archive_path):
                with self.subTest(kind=candidate.suffix or "directory"):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(candidate)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    report = json.loads(result.stdout)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(report["non_document_file_count"], 0)
                    self.assertEqual(report["suspicious"], ["notes.md~"])
                    self.assertTrue(any("documentation-only asset pack" in error for error in report["errors"]))

    def test_backup_extensions_cannot_supply_root_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            backup_names = (
                "README.old",
                "LICENSE.backup",
                "README.orig",
                "README.md.orig",
                "LICENSE.rej",
                "LICENSE.save",
            )
            for name in backup_names:
                (root / name).write_bytes(b"backup")
            (root / "asset.dat").write_bytes(b"asset")
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                for name in backup_names:
                    archive.writestr(name, b"backup")
                archive.writestr("asset.dat", b"asset")

            for candidate in (root, archive_path):
                with self.subTest(kind=candidate.suffix or "directory"):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(candidate)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    report = json.loads(result.stdout)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(report["root_documents"], [])
                    self.assertEqual(report["non_document_file_count"], 1)
                    self.assertCountEqual(report["suspicious"], backup_names)
                    self.assertTrue(any("README is missing" in error for error in report["errors"]))
                    self.assertTrue(any("LICENSE or COPYING is missing" in error for error in report["errors"]))

    def test_editor_backup_variants_cannot_supply_deliverable_content(self) -> None:
        variants = {
            "terminal-tilde": ("hero.png~", png_file(2, 2)),
            "mid-tilde-png": ("hero~.png", png_file(2, 2)),
            "mid-tilde-data": ("hero~.dat", b"backup"),
            "vim-swp": ("hero.swp", b"swap"),
            "vim-swo": (".hero.png.swo", b"swap"),
            "vim-swn": ("hero.swn", b"swap"),
            "emacs-autosave": ("#hero.dat#", b"autosave"),
            "emacs-lock": (".#hero.dat", b"lock"),
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for label, (backup_name, backup_content) in variants.items():
                root = base / label
                root.mkdir()
                (root / "README.md").write_text("readme", encoding="utf-8")
                (root / "LICENSE.txt").write_text("license", encoding="utf-8")
                (root / backup_name).write_bytes(backup_content)
                archive_path = base / f"{label}.zip"
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr("README.md", "readme")
                    archive.writestr("LICENSE.txt", "license")
                    archive.writestr(backup_name, backup_content)

                for candidate in (root, archive_path):
                    with self.subTest(label=label, kind=candidate.suffix or "directory"):
                        result = subprocess.run(
                            [sys.executable, str(SCRIPT), str(candidate)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        report = json.loads(result.stdout)
                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(report["non_document_file_count"], 0)
                        self.assertEqual(report["suspicious"], [backup_name])
                        self.assertTrue(any("documentation-only asset pack" in error for error in report["errors"]))

    @unittest.skipUnless(os.name == "posix", "literal backslash filename requires POSIX")
    def test_literal_backslash_filename_is_suspicious_in_directory_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "LICENSE.txt").write_text("license", encoding="utf-8")
            literal_name = r"Product\hero.dat"
            (root / literal_name).write_bytes(b"asset")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["suspicious"], [literal_name])
        self.assertEqual(report["non_document_file_count"], 0)

    def test_numbered_document_copies_cannot_satisfy_root_gate(self) -> None:
        cases = {
            "numbered-readme": ("README (2).md", "LICENSE.txt", "README is missing"),
            "numbered-license": ("LICENSE(1).txt", "README.md", "LICENSE or COPYING is missing"),
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for label, (numbered_name, valid_name, expected_error) in cases.items():
                root = base / label
                root.mkdir()
                (root / numbered_name).write_text("copy", encoding="utf-8")
                (root / valid_name).write_text("valid", encoding="utf-8")
                (root / "asset.dat").write_bytes(b"asset")
                archive_path = base / f"{label}.zip"
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr(numbered_name, "copy")
                    archive.writestr(valid_name, "valid")
                    archive.writestr("asset.dat", b"asset")

                for candidate in (root, archive_path):
                    with self.subTest(label=label, kind=candidate.suffix or "directory"):
                        result = subprocess.run(
                            [sys.executable, str(SCRIPT), str(candidate)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        report = json.loads(result.stdout)
                        self.assertEqual(result.returncode, 1)
                        self.assertNotIn(numbered_name, report["root_documents"])
                        self.assertEqual(report["suspicious"], [numbered_name])
                        self.assertTrue(any(expected_error in error for error in report["errors"]))

    def test_year_qualified_documents_remain_valid_in_directory_and_zip(self) -> None:
        files = {
            "README (2024).md": b"readme",
            "LICENSE (MIT).txt": b"license",
            "CHANGELOG (2024-06).md": b"changes",
            "asset.dat": b"asset",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            for name, content in files.items():
                (root / name).write_bytes(content)
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                for name, content in files.items():
                    archive.writestr(name, content)

            for candidate in (root, archive_path):
                with self.subTest(kind=candidate.suffix or "directory"):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(candidate)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    report = json.loads(result.stdout)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(report["suspicious"], [])
                    self.assertCountEqual(
                        report["root_documents"],
                        ["README (2024).md", "LICENSE (MIT).txt", "CHANGELOG (2024-06).md"],
                    )

    def test_backup_directories_cannot_supply_deliverable_content(self) -> None:
        for backup_directory in ("backups", "draft notes"):
            with self.subTest(directory=backup_directory), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "pack"
                nested = root / backup_directory
                nested.mkdir(parents=True)
                (root / "README.md").write_text("readme", encoding="utf-8")
                (root / "LICENSE.txt").write_text("license", encoding="utf-8")
                (nested / "hero.dat").write_bytes(b"backup")
                archive_path = Path(directory) / "pack.zip"
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr("README.md", "readme")
                    archive.writestr("LICENSE.txt", "license")
                    archive.writestr(f"{backup_directory}/", b"")
                    archive.writestr(f"{backup_directory}/hero.dat", b"backup")

                for candidate in (root, archive_path):
                    with self.subTest(kind=candidate.suffix or "directory"):
                        result = subprocess.run(
                            [sys.executable, str(SCRIPT), str(candidate)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        report = json.loads(result.stdout)
                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(report["non_document_file_count"], 0)
                        self.assertIn(f"{backup_directory}/hero.dat", report["suspicious"])
                        self.assertTrue(any("documentation-only asset pack" in error for error in report["errors"]))

    def test_empty_backup_directories_are_suspicious_in_both_modes(self) -> None:
        for backup_directory in ("backups", "draft notes"):
            with self.subTest(directory=backup_directory), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "pack"
                (root / backup_directory).mkdir(parents=True)
                directory_report = AUDIT.inspect_directory(root)

                archive_path = Path(directory) / "pack.zip"
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr(f"{backup_directory}/", b"")
                zip_report = AUDIT.inspect_zip(archive_path)

                self.assertEqual(directory_report.suspicious, [backup_directory])
                self.assertEqual(zip_report.suspicious, [f"{backup_directory}/"])

    def test_documentation_only_directory_and_zip_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("README.md", "readme")

            for candidate in (root, archive_path):
                with self.subTest(kind=candidate.suffix or "directory"):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(candidate)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    report = json.loads(result.stdout)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(report["file_count"], 1)
                    self.assertEqual(report["non_document_file_count"], 0)
                    self.assertTrue(any("documentation-only asset pack" in error for error in report["errors"]))
                    if candidate == archive_path:
                        self.assertTrue(report["crc_test_complete"])

    def test_crc_corruption_is_an_error_and_unreadable_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "bad.zip"
            payload = b"crc-test-payload"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("Product/broken.png", png_header(16, 16) + payload)
            data = bytearray(archive_path.read_bytes())
            data[data.index(payload)] ^= 1
            archive_path.write_bytes(data)

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertTrue(report.errors)
        self.assertEqual(report.unreadable_entries, ["Product/broken.png"])
        self.assertTrue(any("totals include 1 unreadable" in note for note in report.notes))
        self.assertNotIn("16x16", report.png_sizes)

    def test_png_with_valid_header_and_corrupt_tail_is_not_sized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "tail-bad.zip"
            payload = b"tail-corruption-marker" + bytes(range(256)) * 8
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("Product/broken.png", png_header(64, 64) + payload)
            data = bytearray(archive_path.read_bytes())
            data[data.index(payload) + len(b"tail-corruption-marker") + 10] ^= 1
            archive_path.write_bytes(data)

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertEqual(report.unreadable_entries, ["Product/broken.png"])
        self.assertNotIn("64x64", report.png_sizes)
        self.assertFalse(report.crc_test_complete)

    def test_corrupted_deflate_stream_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "deflate-bad.zip"
            content = png_header(16, 16) + bytes(range(256)) * 8
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("Product/broken.png", content)
            data = bytearray(archive_path.read_bytes())
            name_length = int.from_bytes(data[26:28], "little")
            extra_length = int.from_bytes(data[28:30], "little")
            compressed_size = int.from_bytes(data[18:22], "little")
            compressed_start = 30 + name_length + extra_length
            data[compressed_start + compressed_size // 2] ^= 0xFF
            archive_path.write_bytes(data)

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertTrue(report.errors)
        self.assertEqual(report.unreadable_entries, ["Product/broken.png"])
        self.assertTrue(any("Cannot read ZIP entry" in error for error in report.errors))

    def test_corrupted_deflate_cli_exits_one_with_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "deflate-bad.zip"
            content = bytes(range(256)) * 8
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("Product/README.md", content)
            data = bytearray(archive_path.read_bytes())
            name_length = int.from_bytes(data[26:28], "little")
            extra_length = int.from_bytes(data[28:30], "little")
            compressed_size = int.from_bytes(data[18:22], "little")
            compressed_start = 30 + name_length + extra_length
            data[compressed_start + compressed_size // 2] ^= 0xFF
            archive_path.write_bytes(data)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path), "--markdown"],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("## Errors", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_zip_hazards_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "hazards.zip"
            symlink = zipfile.ZipInfo("Product/linked.png")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o755) << 16
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr(symlink, "hero.png")
                    archive.writestr(r"Product\README.md", "readme")
                    archive.writestr("../evil.txt", "first")
                    archive.writestr("../evil.txt", "second")

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertIn("Product/linked.png", report.suspicious)
        self.assertIn(r"Product\README.md", report.suspicious)
        self.assertIn("../evil.txt", report.suspicious)
        self.assertEqual(report.duplicate_entries, ["../evil.txt", "../evil.txt"])
        self.assertIn("Product/linked.png", report.unreadable_entries)
        self.assertNotIn("Product/linked.png", report.invalid_png_files)
        self.assertTrue(any("duplicate ZIP entr" in note for note in report.notes))

    def test_case_insensitive_duplicate_paths_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "case-collision.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("Product/good.png", png_header())
                archive.writestr("Product/Good.png", png_header())

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertEqual(report.duplicate_entries, ["Product/Good.png", "Product/good.png"])
        self.assertTrue(report.errors)
        self.assertTrue(any("duplicate ZIP entries" in note for note in report.notes))

    def test_unicode_normalization_collision_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "unicode-collision.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("Product/caf\u00e9.png", png_header())
                archive.writestr("Product/cafe\u0301.png", png_header())

            report = AUDIT.inspect_zip(archive_path)

        self.assertEqual(report.duplicate_entries, ["Product/cafe\u0301.png", "Product/caf\u00e9.png"])

    def test_dot_and_repeated_separator_collisions_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "normalized-collision.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("Product/./README.md", "first")
                archive.writestr("Product/README.md", "second")
                archive.writestr("Product//LICENSE.txt", "first")
                archive.writestr("Product/LICENSE.txt", "second")

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertEqual(
            report.duplicate_entries,
            ["Product/./README.md", "Product//LICENSE.txt", "Product/LICENSE.txt", "Product/README.md"],
        )
        self.assertTrue(report.errors)

    def test_lone_noncanonical_zip_paths_are_suspicious(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "noncanonical.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("./hero.png", png_header())
                archive.writestr("Product/./README.md", "readme")
                archive.writestr("Product//LICENSE.txt", "license")

            report = AUDIT.inspect_zip(archive_path)

        self.assertEqual(
            report.suspicious,
            ["./hero.png", "Product/./README.md", "Product//LICENSE.txt"],
        )

    def test_traversal_only_zip_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "traversal.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("README.md", "readme")
                archive.writestr("LICENSE.txt", "license")
                archive.writestr("../evil.txt", "unsafe")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["suspicious"], ["../evil.txt"])
        self.assertEqual(
            report["errors"],
            [
                "No non-document deliverable files found; a documentation-only asset pack is not a valid release candidate"
            ],
        )
        self.assertTrue(report["crc_test_complete"])

    def test_directory_mode_bit_without_slash_is_not_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "directory-bit.zip"
            directory_entry = zipfile.ZipInfo("Product")
            directory_entry.create_system = 3
            directory_entry.external_attr = (stat.S_IFDIR | 0o755) << 16
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr(directory_entry, b"")
                archive.writestr("Product/README.md", "readme")

            report = AUDIT.inspect_zip(archive_path)

        self.assertEqual(report.file_count, 1)
        self.assertNotIn("[no extension]", report.extensions)

    def test_file_and_directory_name_collision_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "file-directory-collision.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("Product", "file")
                archive.writestr("Product/", "")
                archive.writestr("Product/README.md", "readme")

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertEqual(report.duplicate_entries, ["Product", "Product/", "Product/README.md"])
        self.assertTrue(any("duplicate ZIP entries" in note for note in report.notes))

    def test_file_and_implicit_descendant_collision_is_reported_in_both_orders(self) -> None:
        for child_first in (False, True):
            with self.subTest(child_first=child_first), tempfile.TemporaryDirectory() as directory:
                archive_path = Path(directory) / "implicit-directory-collision.zip"
                entries = [("Product", "file"), ("Product/README.md", "readme")]
                if child_first:
                    entries.reverse()
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    for name, content in entries:
                        archive.writestr(name, content)

                report = AUDIT.inspect_zip(archive_path)
                AUDIT.add_notes(report)

            self.assertEqual(report.duplicate_entries, ["Product", "Product/README.md"])
            self.assertTrue(report.errors)

    def test_root_directory_entry_is_suspicious(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "root-entry.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("/", b"")
                archive.writestr("README.md", "readme")

            report = AUDIT.inspect_zip(archive_path)

        self.assertEqual(report.suspicious, ["/"])
        self.assertEqual(report.file_count, 1)

    def test_duplicate_collision_counts_every_entry_and_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "duplicates.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                    archive.writestr("a.txt", "first")
                    archive.writestr("a.txt", "second")
                    archive.writestr("a.txt", "third")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["duplicate_entries"], ["a.txt", "a.txt", "a.txt"])
        self.assertTrue(any("3 ZIP entries collide" in error for error in report["errors"]))
        self.assertTrue(any("totals include these entries" in note for note in report["notes"]))
        self.assertTrue(any("must not be treated as usable-content counts" in note for note in report["notes"]))

    def test_symlink_only_zip_exits_one_when_crc_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "symlink.zip"
            symlink = zipfile.ZipInfo("linked.png")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o755) << 16
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr(symlink, "hero.png")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["crc_test_complete"])
        self.assertEqual(report["unreadable_entries"], ["linked.png"])

    def test_encrypted_png_has_one_root_cause_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "encrypted.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("secret.png", png_header())
                archive.writestr("README.md", "readme")
                archive.writestr("LICENSE.txt", "license")
            data = bytearray(archive_path.read_bytes())
            local = data.index(b"PK\x03\x04")
            central = data.index(b"PK\x01\x02")
            data[local + 6 : local + 8] = (int.from_bytes(data[local + 6 : local + 8], "little") | 1).to_bytes(2, "little")
            data[central + 8 : central + 10] = (int.from_bytes(data[central + 8 : central + 10], "little") | 1).to_bytes(2, "little")
            archive_path.write_bytes(data)

            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertEqual(report.unreadable_entries, ["secret.png"])
        self.assertFalse(report.crc_test_complete)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("encrypted ZIP entry", report.errors[0])

    def test_incomplete_zip_inventory_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "truncated.zip"
            archive_path.write_bytes(b"not a zip")
            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertFalse(report.inventory_complete)
        self.assertFalse(report.crc_test_complete)
        self.assertTrue(report.errors)

    def test_invalid_utf8_zip_name_returns_structured_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "invalid-utf8.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("x.txt", "payload")
            data = bytearray(archive_path.read_bytes())
            local = data.index(b"PK\x03\x04")
            central = data.index(b"PK\x01\x02")
            local_flags = int.from_bytes(data[local + 6 : local + 8], "little") | 0x800
            central_flags = int.from_bytes(data[central + 8 : central + 10], "little") | 0x800
            data[local + 6 : local + 8] = local_flags.to_bytes(2, "little")
            data[central + 8 : central + 10] = central_flags.to_bytes(2, "little")
            local_name_start = local + 30
            central_name_start = central + 46
            data[local_name_start] = 0xE9
            data[central_name_start] = 0xE9
            archive_path.write_bytes(data)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["inventory_complete"])
        self.assertTrue(any("Cannot read ZIP" in error for error in report["errors"]))
        self.assertNotIn("Traceback", result.stderr)

    def test_unsupported_compression_is_a_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "unsupported.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("README.md", "readme")
            data = bytearray(archive_path.read_bytes())
            local = data.index(b"PK\x03\x04")
            central = data.index(b"PK\x01\x02")
            data[local + 8 : local + 10] = (99).to_bytes(2, "little")
            data[central + 10 : central + 12] = (99).to_bytes(2, "little")
            archive_path.write_bytes(data)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["unreadable_entries"], ["README.md"])
        self.assertTrue(report["errors"])

    def test_each_non_png_zip_entry_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "two-bad.zip"
            first = b"first-payload"
            second = b"second-payload"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("README.md", first)
                archive.writestr("notes.txt", second)
                archive.writestr("LICENSE.txt", "license")
            data = bytearray(archive_path.read_bytes())
            data[data.index(first)] ^= 1
            data[data.index(second)] ^= 1
            archive_path.write_bytes(data)
            report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(report)

        self.assertFalse(report.crc_test_complete)
        self.assertEqual(report.unreadable_entries, ["README.md", "notes.txt"])
        self.assertEqual(len(report.errors), 2)
        self.assertTrue(any("CRC verification did not complete" in note for note in report.notes))

    def test_directory_walk_error_is_reported(self) -> None:
        error = PermissionError(13, "Permission denied", "/tmp/pack/locked")
        def fake_walk(*args, **kwargs):
            kwargs["onerror"](error)
            return iter(())

        with mock.patch.object(AUDIT.os, "walk", side_effect=fake_walk):
            report = AUDIT.inspect_directory(Path("/tmp/pack"))
            AUDIT.add_notes(report)

        self.assertTrue(report.errors)
        self.assertIn("Cannot scan directory locked", report.errors[0])
        self.assertFalse(report.inventory_complete)
        self.assertTrue(any("Directory scan is incomplete" in note for note in report.notes))
        self.assertFalse(any("README is missing" in error for error in report.errors))
        self.assertFalse(any("LICENSE or COPYING is missing" in error for error in report.errors))
        markdown = AUDIT.render_markdown(report)
        self.assertIn("- Files: 0 (partial)", markdown)
        self.assertIn("- Inventory complete: no", markdown)
        self.assertNotIn("ZIP directory unreadable", markdown)

    def test_empty_forbidden_directories_are_suspicious_in_both_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            (root / "tmp").mkdir(parents=True)
            (root / "temp").mkdir()
            directory_report = AUDIT.inspect_directory(root)

            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("tmp/", b"")
                archive.writestr("temp/", b"")
                archive.writestr("__MACOSX/", b"")
            zip_report = AUDIT.inspect_zip(archive_path)
            AUDIT.add_notes(directory_report)
            AUDIT.add_notes(zip_report)

        self.assertEqual(directory_report.suspicious, ["temp", "tmp"])
        self.assertEqual(zip_report.suspicious, ["tmp/", "temp/", "__MACOSX/"])
        self.assertTrue(any("totals include these suspicious entries" in note for note in directory_report.notes))
        self.assertTrue(any("must not be treated as usable-content counts" in note for note in zip_report.notes))

    def test_pycache_directory_is_suspicious_in_both_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            (root / "__pycache__").mkdir(parents=True)
            directory_report = AUDIT.inspect_directory(root)

            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr("__pycache__/", b"")
            zip_report = AUDIT.inspect_zip(archive_path)

        self.assertEqual(directory_report.suspicious, ["__pycache__"])
        self.assertEqual(zip_report.suspicious, ["__pycache__/"])

    def test_readme_template_does_not_hardcode_license_txt(self) -> None:
        template = README_TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("See `LICENSE.txt`.", template)
        self.assertIn("{{license filename}}", template)

    def test_symlinked_directory_is_flagged_and_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            outside = Path(directory) / "outside"
            outside.mkdir()
            (outside / "secret.png").write_bytes(png_header())
            (root / "linked-dir").symlink_to(outside, target_is_directory=True)

            report = AUDIT.inspect_directory(root)

        self.assertEqual(report.file_count, 0)
        self.assertEqual(report.suspicious, ["linked-dir"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO is not supported on this platform")
    def test_fifo_png_is_skipped_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            os.mkfifo(root / "pipe.png")

            report = AUDIT.inspect_directory(root)

        self.assertEqual(report.file_count, 0)
        self.assertTrue(any("not a regular file" in error for error in report.errors))

    def test_main_returns_one_for_directory_walk_error(self) -> None:
        error_report = AUDIT.Report("fixture", "directory")
        error_report.errors.append("Cannot scan directory locked: Permission denied")
        args = argparse.Namespace(path=Path("/tmp/pack"), markdown=False, output=None, force=False)
        with mock.patch.object(AUDIT, "parse_args", return_value=args), mock.patch.object(
            AUDIT.Path, "is_dir", return_value=True
        ), mock.patch.object(AUDIT, "inspect_directory", return_value=error_report), mock.patch.object(
            AUDIT.sys.stdout.buffer, "write"
        ):
            status = AUDIT.main()

        self.assertEqual(status, 1)

    def test_main_json_output_file_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "LICENSE.txt").write_text("license", encoding="utf-8")
            (root / "asset.dat").write_bytes(b"asset")
            output = Path(directory) / "report.json"
            ok = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            invalid = subprocess.run(
                [sys.executable, str(SCRIPT), str(Path(directory) / "missing")],
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(ok.returncode, 0)
        self.assertEqual(ok.stdout, "")
        self.assertEqual(ok.stderr, "")
        self.assertEqual(payload["kind"], "directory")
        self.assertEqual(invalid.returncode, 2)

    def test_output_cannot_overwrite_or_enter_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("README.md", "readme")
            overwrite = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path), "--output", str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertTrue(zipfile.is_zipfile(archive_path))

            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            inside = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(root / "report.json")],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(overwrite.returncode, 2)
        self.assertEqual(inside.returncode, 2)

    @unittest.skipUnless(hasattr(os, "link"), "Hardlinks are not supported on this platform")
    def test_force_output_hardlink_cannot_overwrite_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "pack.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("README.md", "readme")
            alias_path = Path(directory) / "alias.zip"
            os.link(archive_path, alias_path)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(archive_path),
                    "--output",
                    str(alias_path),
                    "--force",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            still_zip = zipfile.is_zipfile(archive_path)

        self.assertEqual(result.returncode, 2)
        self.assertTrue(still_zip)

    def test_output_directory_and_nested_parent_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "LICENSE.txt").write_text("license", encoding="utf-8")
            (root / "asset.dat").write_bytes(b"asset")
            output_directory = Path(directory) / "reports"
            output_directory.mkdir()
            refused = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(output_directory)],
                capture_output=True,
                text=True,
                check=False,
            )
            nested = Path(directory) / "new" / "nested" / "report.json"
            created = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(nested)],
                capture_output=True,
                text=True,
                check=False,
            )
            nested_exists = nested.exists()

        self.assertEqual(refused.returncode, 2)
        self.assertEqual(created.returncode, 0)
        self.assertTrue(nested_exists)

    def test_existing_output_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "LICENSE.txt").write_text("license", encoding="utf-8")
            (root / "asset.dat").write_bytes(b"asset")
            output = Path(directory) / "report.md"
            output.write_text("keep", encoding="utf-8")
            refused = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--markdown", "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            unchanged = output.read_text(encoding="utf-8")
            forced = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--markdown", "--output", str(output), "--force"],
                capture_output=True,
                text=True,
                check=False,
            )
            replaced = output.read_text(encoding="utf-8")

        self.assertEqual(refused.returncode, 2)
        self.assertEqual(unchanged, "keep")
        self.assertEqual(forced.returncode, 0)
        self.assertTrue(replaced.startswith("# Asset Pack Audit"))

    def test_empty_directory_and_zip_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "empty"
            root.mkdir()
            archive_path = Path(directory) / "empty.zip"
            with zipfile.ZipFile(archive_path, "w"):
                pass
            directory_only_archive = Path(directory) / "directory-only.zip"
            with zipfile.ZipFile(directory_only_archive, "w") as archive:
                archive.writestr("Pack/", b"")
            directory_report = AUDIT.inspect_directory(root)
            zip_report = AUDIT.inspect_zip(archive_path)
            directory_only_report = AUDIT.inspect_zip(directory_only_archive)
            AUDIT.add_notes(directory_report)
            AUDIT.add_notes(zip_report)
            AUDIT.add_notes(directory_only_report)
            directory_result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            zip_result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            directory_only_result = subprocess.run(
                [sys.executable, str(SCRIPT), str(directory_only_archive)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(directory_report.file_count, 0)
        self.assertEqual(zip_report.file_count, 0)
        self.assertEqual(directory_only_report.file_count, 0)
        self.assertTrue(zip_report.crc_test_complete)
        self.assertTrue(directory_only_report.crc_test_complete)
        self.assertTrue(any("No files found" in error for error in directory_report.errors))
        self.assertTrue(any("No files found" in error for error in zip_report.errors))
        self.assertTrue(any("No files found" in error for error in directory_only_report.errors))
        self.assertEqual(directory_result.returncode, 1)
        self.assertEqual(zip_result.returncode, 1)
        self.assertEqual(directory_only_result.returncode, 1)

    def test_non_ascii_stdout_works_with_ascii_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            (root / "caf\u00e9.tmp").write_text("junk", encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "ascii"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--markdown"],
                capture_output=True,
                check=False,
                env=environment,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("caf\u00e9.tmp".encode("utf-8"), result.stdout)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_surrogate_filename_is_safely_encoded_in_reports(self) -> None:
        report = AUDIT.Report("fixture", "directory")
        AUDIT.inspect_entries(report, [("caf\udce9.tmp", 1, None)])
        args = argparse.Namespace(path=Path("/tmp/pack"), markdown=False, output=None, force=False)
        with mock.patch.object(AUDIT, "parse_args", return_value=args), mock.patch.object(
            AUDIT.Path, "is_dir", return_value=True
        ), mock.patch.object(AUDIT, "inspect_directory", return_value=report), mock.patch.object(
            AUDIT.sys.stdout.buffer, "write"
        ) as write:
            status = AUDIT.main()

        self.assertEqual(status, 1)
        emitted = write.call_args.args[0]
        self.assertIn(b"caf\\udce9.tmp", emitted)

    def test_godot_and_missing_document_errors(self) -> None:
        report = AUDIT.Report("fixture", "directory")
        AUDIT.inspect_entries(report, [("effects/material.tres", 1, None)])
        AUDIT.add_notes(report)
        self.assertTrue(any("README is missing from the inspected root" in error for error in report.errors))
        self.assertTrue(any("LICENSE or COPYING is missing from the inspected root" in error for error in report.errors))
        self.assertTrue(any("without project.godot" in note for note in report.notes))
        self.assertTrue(any("without a scene" in note for note in report.notes))

    def test_backslash_godot_paths_do_not_emit_missing_project_or_scene_notes(self) -> None:
        report = AUDIT.Report("fixture", "zip")
        AUDIT.inspect_entries(
            report,
            [(r"Product\project.godot", 1, None), (r"Product\demo.tscn", 1, None)],
        )
        AUDIT.add_notes(report)

        self.assertEqual(report.godot_files, [r"Product\project.godot", r"Product\demo.tscn"])
        self.assertFalse(any("without project.godot" in note for note in report.notes))
        self.assertFalse(any("without a scene" in note for note in report.notes))

    def test_media_source_and_many_png_size_notes(self) -> None:
        report = AUDIT.Report("fixture", "directory")
        entries = [(f"images/{index}.png", 33, png_header(index + 1, index + 1)) for index in range(9)]
        entries.extend(
            [
                ("audio/theme.ogg", 1, None),
                ("models/prop.glb", 1, None),
            ]
        )
        AUDIT.inspect_entries(report, entries)
        AUDIT.add_notes(report)

        self.assertTrue(any("Many PNG canvas sizes" in note for note in report.notes))
        self.assertTrue(any("no editable source format" in note for note in report.notes))
        self.assertTrue(any("Audio detected" in note for note in report.notes))
        self.assertTrue(any("3D models detected" in note for note in report.notes))

    def test_long_lists_show_continuation_counts(self) -> None:
        report = AUDIT.Report("fixture", "directory")
        report.invalid_png_files = [f"bad-{index}.png" for index in range(105)]
        report.suspicious = [f"junk-{index}.tmp" for index in range(103)]
        markdown = AUDIT.render_markdown(report)
        self.assertIn("… and 5 more", markdown)
        self.assertIn("… and 3 more", markdown)

    def test_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            root.mkdir()
            outside = Path(directory) / "outside.png"
            outside.write_bytes(png_header())
            (root / "linked.png").symlink_to(outside)

            report = AUDIT.inspect_directory(root)
            AUDIT.add_notes(report)

        self.assertEqual(report.file_count, 0)
        self.assertEqual(report.suspicious, ["linked.png"])


if __name__ == "__main__":
    unittest.main()
