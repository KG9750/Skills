#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("export_artifacts.py")
SPEC = importlib.util.spec_from_file_location("doc_style_ch_exporter", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load exporter")
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)


class ExporterTests(unittest.TestCase):
    def test_parse_viewport(self) -> None:
        self.assertEqual(EXPORTER.parse_viewport("1600x2000"), (1600, 2000))
        self.assertEqual(EXPORTER.parse_viewport("1080×1350"), (1080, 1350))

    def test_rejects_bad_viewports(self) -> None:
        for value in ("1600", "wide", "719x1000", "1000x9000"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    EXPORTER.parse_viewport(value)

    def test_reads_output_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.html"
            path.write_text(
                '<html data-output-profile="image"></html>',
                encoding="utf-8",
            )
            self.assertEqual(EXPORTER.html_profile(path), "image")

    def test_rejects_html_without_output_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.html"
            path.write_text("<html></html>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "data-output-profile"):
                EXPORTER.html_profile(path)

    def test_finds_explicit_browser(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            browser = Path(directory) / "browser"
            browser.write_text("#!/bin/sh\n", encoding="utf-8")
            browser.chmod(0o755)
            self.assertEqual(EXPORTER.find_browser(browser), browser.resolve())

    def test_rejects_missing_explicit_browser(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "not executable"):
            EXPORTER.find_browser(Path("/definitely/missing/browser"))

    def test_builds_offline_pdf_command(self) -> None:
        command = EXPORTER.build_pdf_command(
            Path("/browser"),
            Path("/profile"),
            "file:///tmp/report.html",
            Path("/tmp/report.pdf"),
        )
        self.assertIn("--host-resolver-rules=MAP * 0.0.0.0, EXCLUDE localhost", command)
        self.assertIn("--print-to-pdf=/tmp/report.pdf", command)
        self.assertEqual(command[-1], "file:///tmp/report.html")

    def test_builds_fixed_canvas_png_command(self) -> None:
        command = EXPORTER.build_png_command(
            Path("/browser"),
            Path("/profile"),
            "file:///tmp/image.html",
            Path("/tmp/image.png"),
            (1600, 2000),
        )
        self.assertIn("--window-size=1600,2000", command)
        self.assertIn("--force-device-scale-factor=1", command)
        self.assertIn("--screenshot=/tmp/image.png", command)

    def test_verifies_pdf_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            path.write_bytes(b"%PDF-1.7\n" + b"0" * 128)
            EXPORTER.verify_pdf(path)
            path.write_bytes(b"not a pdf")
            with self.assertRaisesRegex(RuntimeError, "invalid PDF"):
                EXPORTER.verify_pdf(path)

    def test_reads_and_verifies_png_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
            path.write_bytes(header + struct.pack(">II", 1600, 2000) + b"\x08\x06\x00\x00\x00")
            self.assertEqual(EXPORTER.png_dimensions(path), (1600, 2000))
            EXPORTER.verify_png(path, (1600, 2000))
            with self.assertRaisesRegex(RuntimeError, "expected 1080x1350"):
                EXPORTER.verify_png(path, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
