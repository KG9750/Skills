#!/usr/bin/env python3
"""Behavior tests for the Pixel Convert command-line tools."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

try:
    import resource
except ImportError:
    resource = None


ROOT = Path(__file__).resolve().parents[1]
NORMALIZE = ROOT / "scripts" / "normalize_sprite.py"
BUILD = ROOT / "scripts" / "build_godot_pack.py"
VERIFY = ROOT / "scripts" / "verify_pack.py"
PREVIEW = ROOT / "scripts" / "make_ab_preview.py"
NORMALIZE_ANIMATION = ROOT / "scripts" / "normalize_animation.py"
ASEPRITE_GATE = ROOT / "scripts" / "aseprite_gate.py"
GODOT = Path(os.environ.get("GODOT_BIN", "/Applications/Godot.app/Contents/MacOS/Godot"))
HAS_FILE_SIZE_LIMIT = resource is not None and hasattr(resource, "RLIMIT_FSIZE")


def run_tool(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def run_tool_with_file_limit(
    limit: int, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    if not HAS_FILE_SIZE_LIMIT:
        raise RuntimeError("file-size limit tests require POSIX resource.RLIMIT_FSIZE")

    def set_file_limit() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))

    return subprocess.run(
        [sys.executable, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
        preexec_fn=set_file_limit,
    )


def write_pack_fixture(root: Path, assets: list[dict]) -> Path:
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(root / "frame.png")
    spec = {
        "pack_name": "test_pack",
        "grid": [32, 32],
        "palette": ["FF0000"],
        "assets": assets,
    }
    path = root / "pack.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def static_asset(asset_id: str = "prop", fps: float = 1.0) -> dict:
    return {
        "id": asset_id,
        "canvas": [32, 32],
        "occupancy": [1, 1],
        "anchor": [16, 30],
        "animations": {"idle": {"fps": fps, "loop": False, "frames": ["frame.png"]}},
    }


def component_sizes(image: Image.Image, rgb: tuple[int, int, int]) -> list[tuple[int, int]]:
    pixels = image.convert("RGB")
    pending = {
        (x, y)
        for y in range(pixels.height)
        for x in range(pixels.width)
        if pixels.getpixel((x, y)) == rgb
    }
    sizes: list[tuple[int, int]] = []
    while pending:
        start = pending.pop()
        stack = [start]
        points = [start]
        while stack:
            x, y = stack.pop()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in pending:
                    pending.remove(neighbor)
                    stack.append(neighbor)
                    points.append(neighbor)
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        sizes.append((max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    return sizes


class PixelConvertTests(unittest.TestCase):
    def test_suite_collects_without_resource_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sitecustomize.py").write_text(
                "import sys\nsys.modules['resource'] = None\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(root)

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "PixelConvertTests.test_builder_rejects_non_object_pack_spec_without_traceback",
                    "-v",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("OK", result.stdout)

    def test_aseprite_probe_distinguishes_cli_and_manual_gui(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working = root / "working-aseprite"
            working.write_text("#!/bin/sh\necho 'Aseprite 1.3'\n", encoding="utf-8")
            working.chmod(0o755)
            cli = run_tool(str(ASEPRITE_GATE), "probe", "--aseprite", str(working))
            self.assertIn("mode=cli", cli.stdout)

            failing = root / "failing-aseprite"
            failing.write_text("#!/bin/sh\nexit 134\n", encoding="utf-8")
            failing.chmod(0o755)
            manual = run_tool(str(ASEPRITE_GATE), "probe", "--aseprite", str(failing))
            self.assertIn("mode=manual_gui", manual.stdout)

    def test_aseprite_gate_prepares_and_verifies_normalized_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(frame).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
            frame.save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"

            run_tool(
                str(ASEPRITE_GATE),
                "prepare",
                "--asset-id",
                "test_prop",
                "--input",
                str(root / "frame.png"),
                "--palette",
                str(root / "palette.txt"),
                "--grid",
                "8x8",
                "--anchor",
                "4,7",
                "--out",
                str(gate),
                "--no-probe",
            )

            self.assertTrue((gate / "baseline/frame_000.png").exists())
            self.assertTrue((gate / "working/frame_000.png").exists())
            self.assertTrue((gate / "palette.gpl").exists())
            run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate))
            manifest = json.loads((gate / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "verified")

    def test_aseprite_gate_rejects_palette_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop",
                "--input", str(root / "frame.png"),
                "--palette", str(root / "palette.txt"),
                "--grid", "4x4", "--anchor", "2,3",
                "--out", str(gate), "--no-probe",
            )
            edited = Image.open(gate / "working/frame_000.png").convert("RGBA")
            edited.putpixel((0, 0), (0, 0, 255, 255))
            edited.save(gate / "working/frame_000.png")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the declared palette", result.stdout)

    def test_aseprite_gate_rejects_erased_working_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop",
                "--input", str(root / "frame.png"),
                "--palette", str(root / "palette.txt"),
                "--grid", "4x4", "--anchor", "2,3",
                "--out", str(gate), "--no-probe",
            )
            Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(gate / "working/frame_000.png")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("contains no opaque pixels", result.stdout.lower())
            manifest = json.loads((gate / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "awaiting_aseprite_review")

    def test_aseprite_failed_reverify_clears_stale_verified_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop",
                "--input", str(root / "frame.png"),
                "--palette", str(root / "palette.txt"),
                "--grid", "4x4", "--anchor", "2,3",
                "--out", str(gate), "--no-probe",
            )
            run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate))
            Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(gate / "working/frame_000.png")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("contains no opaque pixels", result.stdout.lower())
            manifest = json.loads((gate / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "awaiting_aseprite_review")

    def test_aseprite_malformed_reverify_clears_stale_verified_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop", "--input", root / "frame.png",
                "--palette", root / "palette.txt", "--grid", "4x4", "--anchor", "2,3",
                "--out", gate, "--no-probe",
            )
            run_tool(str(ASEPRITE_GATE), "verify", "--gate", gate)
            manifest_path = gate / "gate.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("asset_id")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", gate, check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required field: asset_id", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["status"],
                "awaiting_aseprite_review",
            )

    def test_aseprite_gate_reports_malformed_canvas_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop", "--input", root / "frame.png",
                "--palette", root / "palette.txt", "--grid", "4x4", "--anchor", "2,3",
                "--out", gate, "--no-probe",
            )
            manifest_path = gate / "gate.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["canvas"] = None
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", gate, check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("canvas must contain two positive integers", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["status"],
                "awaiting_aseprite_review",
            )

    def test_aseprite_gate_reports_malformed_palette_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop", "--input", root / "frame.png",
                "--palette", root / "palette.txt", "--grid", "4x4", "--anchor", "2,3",
                "--out", gate, "--no-probe",
            )
            manifest_path = gate / "gate.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["palette"] = None
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", gate, check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("palette must be a non-empty list", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["status"],
                "awaiting_aseprite_review",
            )

    def test_aseprite_gate_rejects_modified_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n0000FF\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop",
                "--input", str(root / "frame.png"),
                "--palette", str(root / "palette.txt"),
                "--grid", "4x4", "--anchor", "2,3",
                "--out", str(gate), "--no-probe",
            )
            Image.new("RGBA", (4, 4), (0, 0, 255, 255)).save(gate / "baseline/frame_000.png")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("baseline frame changed", result.stdout.lower())
            manifest = json.loads((gate / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "awaiting_aseprite_review")

    def test_aseprite_prepare_rejects_invalid_grid_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"

            result = run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop",
                "--input", str(root / "frame.png"),
                "--palette", str(root / "palette.txt"),
                "--grid", "0x4", "--anchor", "2,3",
                "--out", str(gate), "--no-probe",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("grid must contain two positive integers", result.stdout.lower())
            self.assertFalse(gate.exists())
            self.assertEqual(list(root.glob(".gate.staging-*")), [])

    def test_aseprite_verify_reports_missing_required_fields_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            gate = Path(directory)
            (gate / "gate.json").write_text(
                json.dumps({"asset_id": "test_prop", "palette": ["FF0000"], "frames": []}),
                encoding="utf-8",
            )

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gate manifest is missing required field: canvas", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / "frame.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            gate = root / "gate"
            run_tool(
                str(ASEPRITE_GATE), "prepare",
                "--asset-id", "test_prop", "--input", str(root / "frame.png"),
                "--palette", str(root / "palette.txt"), "--grid", "4x4", "--anchor", "2,3",
                "--out", str(gate), "--no-probe",
            )
            manifest_path = gate / "gate.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("asset_id")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gate manifest is missing required field: asset_id", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["status"],
                "awaiting_aseprite_review",
            )

    def test_aseprite_verify_rejects_zero_frame_gate_without_status_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            gate = Path(directory)
            manifest_path = gate / "gate.json"
            manifest_path.write_text(
                json.dumps({
                    "asset_id": "test_prop",
                    "canvas": [4, 4],
                    "palette": ["FF0000"],
                    "frames": [],
                    "status": "awaiting_aseprite_review",
                }),
                encoding="utf-8",
            )

            result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frames must be a non-empty list", result.stdout.lower())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["status"],
                "awaiting_aseprite_review",
            )

    def test_aseprite_verify_rejects_invalid_frame_paths_and_duplicates(self) -> None:
        cases = (
            (
                "same_path",
                lambda frames: frames[0].update({"baseline": frames[0]["working"]}),
                "baseline path must stay inside baseline",
            ),
            (
                "working_escape",
                lambda frames: frames[0].update({"working": "../outside.png"}),
                "working path must stay inside working",
            ),
            (
                "duplicate_record",
                lambda frames: frames.append(dict(frames[0])),
                "duplicate gate frame path",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                frame = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(frame).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                frame.save(root / "frame.png")
                (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
                gate = root / "gate"
                run_tool(
                    str(ASEPRITE_GATE), "prepare", "--asset-id", "test_prop",
                    "--input", str(root / "frame.png"), "--palette", str(root / "palette.txt"),
                    "--grid", "8x8", "--anchor", "4,7", "--out", str(gate), "--no-probe",
                )
                manifest_path = gate / "gate.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest["frames"])
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(ASEPRITE_GATE), "verify", "--gate", str(gate), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout.lower())
                self.assertNotIn("aseprite_gate_verify_pass", result.stdout.lower())
                self.assertEqual(
                    json.loads(manifest_path.read_text(encoding="utf-8"))["status"],
                    "awaiting_aseprite_review",
                )

    def test_chroma_key_preserves_existing_transparency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle((3, 4, 4, 6), fill=(255, 0, 0, 255))
            source.save(root / "source.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            run_tool(
                str(NORMALIZE),
                str(root / "source.png"),
                str(root / "output.png"),
                "--canvas",
                "8x8",
                "--anchor",
                "4,7",
                "--palette",
                str(root / "palette.txt"),
                "--background-key",
                "FF00FF",
                "--padding",
                "0",
            )

            output = Image.open(root / "output.png").convert("RGBA")
            self.assertEqual(output.getpixel((0, 0))[3], 0)
            self.assertEqual(output.getpixel((1, 1))[3], 0)
            self.assertEqual(output.getpixel((7, 7))[3], 0)

    def test_static_normalizer_accepts_transparent_indexed_png(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("P", (8, 8), 0)
            source.putpalette([255, 0, 255, 255, 0, 0] + [0] * (254 * 3))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=1)
            source.save(root / "source.png", transparency=0)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), root / "source.png", root / "output.png",
                "--canvas", "8x8", "--anchor", "4,7",
                "--palette", root / "palette.txt", "--padding", "0",
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("pixel_normalize_pass", result.stdout.lower())
            output = Image.open(root / "output.png").convert("RGBA")
            self.assertEqual(output.getchannel("A").getextrema(), (0, 255))

    def test_static_normalizer_supports_off_center_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
            source.putpixel((0, 0), (255, 0, 0, 0))
            source.save(root / "source.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            run_tool(
                str(NORMALIZE), str(root / "source.png"), str(root / "output.png"),
                "--canvas", "8x8", "--anchor", "6,7",
                "--palette", str(root / "palette.txt"), "--padding", "0",
            )

            bbox = Image.open(root / "output.png").convert("RGBA").getchannel("A").getbbox()
            self.assertIsNotNone(bbox)
            assert bbox is not None
            self.assertGreaterEqual(bbox[0], 4)
            self.assertLessEqual(bbox[2], 8)
            self.assertEqual(bbox[3], 7)

    def test_static_normalizer_rejects_same_input_and_output_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
            source_path = root / "source.png"
            source.save(source_path)
            before = source_path.read_bytes()
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), source_path, source_path,
                "--canvas", "4x4", "--anchor", "2,3",
                "--palette", root / "palette.txt", "--padding", "0",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("input and output paths must differ", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertEqual(source_path.read_bytes(), before)

    def test_static_normalizer_rejects_casefolded_input_output_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
            source_path = root / "Source.PNG"
            source.save(source_path)
            before = source_path.read_bytes()
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), source_path, root / "source.png",
                "--canvas", "4x4", "--anchor", "2,3",
                "--palette", root / "palette.txt", "--padding", "0",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("input and output paths must differ", result.stdout.lower())
            self.assertEqual(source_path.read_bytes(), before)

    def test_static_normalizer_rejects_empty_result_after_alpha_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 80))
            source.save(root / "source.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), root / "source.png", root / "output.png",
                "--canvas", "8x8", "--anchor", "4,7",
                "--palette", root / "palette.txt", "--padding", "0",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no opaque pixels after alpha threshold", result.stdout.lower())
            self.assertFalse((root / "output.png").exists())

    def test_static_normalizer_uses_alpha_threshold_for_foreground_bbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 10))
            source.save(root / "source.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), root / "source.png", root / "output.png",
                "--canvas", "8x8", "--anchor", "4,7",
                "--palette", root / "palette.txt", "--padding", "0",
                "--alpha-threshold", "1", check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("pixel_normalize_pass", result.stdout.lower())
            self.assertIsNotNone(Image.open(root / "output.png").convert("RGBA").getchannel("A").getbbox())

    def test_static_normalizer_rejects_zero_alpha_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
            source.save(root / "source.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), root / "source.png", root / "output.png",
                "--canvas", "8x8", "--anchor", "4,7",
                "--palette", root / "palette.txt", "--padding", "0",
                "--alpha-threshold", "0", check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("alpha threshold must be between 1 and 255", result.stdout.lower())
            self.assertNotIn("pixel_normalize_pass", result.stdout.lower())
            self.assertFalse((root / "output.png").exists())

    def test_static_normalizer_rejects_negative_key_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.new("RGB", (8, 8), (255, 0, 255))
            ImageDraw.Draw(source).rectangle((2, 2, 5, 6), fill=(255, 0, 0))
            source.save(root / "source.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")

            result = run_tool(
                str(NORMALIZE), root / "source.png", root / "output.png",
                "--canvas", "8x8", "--anchor", "4,7",
                "--palette", root / "palette.txt", "--padding", "0",
                "--background-key", "FF00FF", "--key-threshold", "-1",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("key threshold must be non-negative", result.stdout.lower())
            self.assertNotIn("pixel_normalize_pass", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse((root / "output.png").exists())

    @unittest.skipUnless(HAS_FILE_SIZE_LIMIT, "requires POSIX resource.RLIMIT_FSIZE")
    def test_static_normalizer_preserves_existing_output_when_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Image.effect_noise((64, 64), 100).convert("RGBA")
            source.putalpha(
                Image.effect_noise((64, 64), 100).point(lambda value: 255 if value > 127 else 0)
            )
            source.save(root / "source.png")
            (root / "palette.txt").write_text(
                "\n".join(f"{value:02X}{value:02X}{value:02X}" for value in range(256)) + "\n",
                encoding="utf-8",
            )
            previous = b"PREVIOUS_VALID_OUTPUT"
            output = root / "output.png"
            output.write_bytes(previous)

            result = run_tool_with_file_limit(
                256,
                str(NORMALIZE), root / "source.png", output,
                "--canvas", "64x64", "--anchor", "32,63",
                "--palette", root / "palette.txt", "--padding", "0",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("pixel_normalize_pass", result.stdout.lower())
            self.assertEqual(output.read_bytes(), previous)
            self.assertFalse(any(root.glob(".pixel-static-*.png")))

    def test_animation_group_uses_one_scale_and_shared_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame_a = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            frame_b = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            ImageDraw.Draw(frame_a).rectangle((40, 60, 59, 89), fill=(255, 0, 0, 255))
            ImageDraw.Draw(frame_b).rectangle((30, 60, 69, 89), fill=(255, 0, 0, 255))
            frame_a.save(root / "a.png")
            frame_b.save(root / "b.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [64, 64],
                "anchor": [32, 62],
                "palette": "palette.txt",
                "padding": 2,
                "frames": [
                    {"input": "a.png", "output": "out_a.png", "source_anchor": [50, 90]},
                    {"input": "b.png", "output": "out_b.png", "source_anchor": [50, 90]},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            run_tool(str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"))

            out_a = Image.open(root / "out_a.png").convert("RGBA").getchannel("A").getbbox()
            out_b = Image.open(root / "out_b.png").convert("RGBA").getchannel("A").getbbox()
            self.assertIsNotNone(out_a)
            self.assertIsNotNone(out_b)
            assert out_a is not None and out_b is not None
            width_a = out_a[2] - out_a[0]
            width_b = out_b[2] - out_b[0]
            self.assertGreaterEqual(width_b, width_a * 1.8)
            self.assertEqual(out_a[3], 62)
            self.assertEqual(out_b[3], 62)

    def test_animation_normalizer_rejects_source_anchor_outside_source_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (30, 40), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((5, 5, 24, 34), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [64, 64],
                "anchor": [32, 62],
                "palette": "palette.txt",
                "padding": 2,
                "frames": [
                    {"input": "a.png", "output": "out_a.png", "source_anchor": [50, 90]},
                    {"input": "b.png", "output": "out_b.png", "source_anchor": [50, 90]},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source_anchor must be inside the source frame", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())
            self.assertFalse((root / "out_b.png").exists())

    def test_animation_normalizer_rejects_opaque_frames_without_background_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (16, 16), (255, 0, 0)).save(root / "a.png")
            Image.new("RGB", (16, 16), (255, 0, 0)).save(root / "b.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [16, 16],
                "anchor": [8, 14],
                "palette": "palette.txt",
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION),
                "--spec",
                str(root / "animation.json"),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("background_key", result.stdout)
            self.assertFalse((root / "out_a.png").exists())

    def test_animation_normalizer_rejects_negative_key_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGB", (8, 8), (255, 0, 255))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "background_key": "FF00FF",
                "key_threshold": -1,
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("key_threshold must be non-negative", result.stdout.lower())
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())
            self.assertFalse((root / "out_b.png").exists())

    def test_animation_normalizer_rejects_zero_shared_scale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((4, 4, 11, 13), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            original = b"existing output"
            (root / "out/second.png").parent.mkdir(parents=True)
            (root / "out/second.png").write_bytes(original)
            spec = {
                "canvas": [32, 32],
                "anchor": [0, 30],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "out_a.png", "source_anchor": [8, 14]},
                    {"input": "b.png", "output": "out_b.png", "source_anchor": [8, 14]},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION),
                "--spec",
                str(root / "animation.json"),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("scale must be greater than zero", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())

    def test_animation_normalizer_handles_rounding_at_exact_fit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (4, 2), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((0, 0, 2, 0), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [2, 2],
                "anchor": [1, 1],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "out_a.png", "source_anchor": [1, 1]},
                    {"input": "b.png", "output": "out_b.png", "source_anchor": [1, 1]},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            run_tool(str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"))

            self.assertTrue((root / "out_a.png").exists())
            self.assertTrue((root / "out_b.png").exists())

    def test_animation_normalizer_reports_missing_required_fields_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "animation.json").write_text(json.dumps({"anchor": [4, 7]}), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required field: canvas", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())

    def test_animation_normalizer_reports_invalid_numeric_options_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": None,
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("padding must be an integer", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())

    def test_animation_normalizer_reports_non_string_background_key_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGB", (8, 8), (255, 0, 255))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "background_key": 7,
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("background key must be a six-digit rgb hex string", result.stdout.lower())
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())
            self.assertFalse((root / "out_b.png").exists())

    def test_animation_normalizer_rejects_path_conflicts_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            before_a = (root / "a.png").read_bytes()
            before_b = (root / "b.png").read_bytes()
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [4, 4],
                "anchor": [2, 3],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "normalized_a.png"},
                    {"input": "b.png", "output": "a.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frames[1] output must not overwrite an input frame", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse((root / "normalized_a.png").exists())
            self.assertEqual((root / "a.png").read_bytes(), before_a)
            self.assertEqual((root / "b.png").read_bytes(), before_b)

    def test_animation_normalizer_rejects_casefolded_input_output_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("A.PNG", "B.PNG"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            before_a = (root / "A.PNG").read_bytes()
            before_b = (root / "B.PNG").read_bytes()
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [4, 4],
                "anchor": [2, 3],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "A.PNG", "output": "a.png"},
                    {"input": "B.PNG", "output": "normalized_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frames[0] output must not overwrite an input frame", result.stdout.lower())
            self.assertFalse((root / "normalized_b.png").exists())
            self.assertEqual((root / "A.PNG").read_bytes(), before_a)
            self.assertEqual((root / "B.PNG").read_bytes(), before_b)

    def test_animation_normalizer_rejects_empty_frame_before_writing_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(first).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
            first.save(root / "a.png")
            second = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            ImageDraw.Draw(second).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 80))
            second.save(root / "b.png")
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frame b.png has no opaque pixels after alpha threshold", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())
            self.assertFalse((root / "out_b.png").exists())

    def test_animation_normalizer_rejects_zero_alpha_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "alpha_threshold": 0,
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("alpha_threshold must be between 1 and 255", result.stdout.lower())
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertFalse((root / "out_a.png").exists())
            self.assertFalse((root / "out_b.png").exists())

    def test_animation_normalizer_uses_alpha_threshold_for_foreground_bbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 10))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "alpha_threshold": 1,
                "frames": [
                    {"input": "a.png", "output": "out_a.png"},
                    {"input": "b.png", "output": "out_b.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", root / "animation.json", check=False
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertTrue((root / "out_a.png").exists())
            self.assertTrue((root / "out_b.png").exists())

    def test_animation_normalizer_rejects_duplicate_outputs_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "shared.png"},
                    {"input": "b.png", "output": "shared.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frames[1] output duplicates another output", result.stdout.lower())
            self.assertFalse((root / "shared.png").exists())

    def test_animation_normalizer_rejects_casefolded_new_outputs_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probe = root / "case_probe"
            probe.write_text("probe", encoding="utf-8")
            if not (root / "CASE_PROBE").exists():
                self.skipTest("filesystem is case-sensitive")
            probe.unlink()
            for name, color in (("a.png", (255, 0, 0, 255)), ("b.png", (0, 0, 255, 255))):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=color)
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n0000FF\n", encoding="utf-8")
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "normalized.png"},
                    {"input": "b.png", "output": "NORMALIZED.PNG"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frames[1] output duplicates another output", result.stdout.lower())
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertFalse((root / "normalized.png").exists())

    def test_animation_normalizer_rejects_existing_outputs_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            original = b"existing output"
            (root / "out").mkdir()
            (root / "out/second.png").write_bytes(original)
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "out/first.png"},
                    {"input": "b.png", "output": "out/second.png"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertIn("output already exists", result.stdout.lower())
            self.assertFalse((root / "out/first.png").exists())
            self.assertEqual((root / "out/second.png").read_bytes(), original)
            self.assertFalse(any(root.rglob(".pixel-animation-*.png")))

    def test_animation_normalizer_commit_failure_rolls_back_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a.png", "b.png"):
                image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle((2, 2, 5, 6), fill=(255, 0, 0, 255))
                image.save(root / name)
            (root / "palette.txt").write_text("FF0000\n", encoding="utf-8")
            too_long = "x" * 300 + ".png"
            spec = {
                "canvas": [8, 8],
                "anchor": [4, 7],
                "palette": "palette.txt",
                "padding": 0,
                "frames": [
                    {"input": "a.png", "output": "out/first.png"},
                    {"input": "b.png", "output": f"out/{too_long}"},
                ],
            }
            (root / "animation.json").write_text(json.dumps(spec), encoding="utf-8")

            result = run_tool(
                str(NORMALIZE_ANIMATION), "--spec", str(root / "animation.json"), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("pixel_animation_normalize_pass", result.stdout.lower())
            self.assertFalse((root / "out/first.png").exists())
            self.assertFalse(any(root.rglob(".pixel-animation-*.png")))

    def test_builder_rejects_duplicate_asset_ids_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("same"), static_asset("same")])
            output = root / "pack"
            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate asset id", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_non_positive_animation_fps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset(fps=0.0)])
            output = root / "pack"
            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fps must be greater than zero", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_non_finite_animation_fps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset(fps=float("inf"))])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fps must be finite", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_boolean_animation_fps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset(fps=True)])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fps must be a number", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_build_pass", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_non_boolean_animation_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset()
            asset["animations"]["idle"]["loop"] = "false"
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("loop must be a boolean", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_non_integer_contact_points(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset()
            asset["contact_points"] = {"muzzle": ["7", 8.9]}
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be an integer [x, y] point", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_malformed_palette_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset()])
            data = json.loads(spec.read_text(encoding="utf-8"))
            data["palette"] = ["FF0000", "FF0000FF"]
            spec.write_text(json.dumps(data), encoding="utf-8")
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid palette color", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_reports_missing_required_fields_without_traceback(self) -> None:
        cases = (
            ("pack_name", lambda data: data.pop("pack_name"), "pack spec is missing required field: pack_name"),
            ("asset_id", lambda data: data["assets"][0].pop("id"), "assets[0] is missing required field: id"),
            (
                "animation_frames",
                lambda data: data["assets"][0]["animations"]["idle"].pop("frames"),
                "prop/idle is missing required field: frames",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                data = json.loads(spec.read_text(encoding="utf-8"))
                mutate(data)
                spec.write_text(json.dumps(data), encoding="utf-8")
                output = root / "pack"

                result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertFalse(output.exists())

    def test_builder_reports_grid_and_frame_type_errors_without_traceback(self) -> None:
        cases = (
            ("missing_grid", lambda data: data.pop("grid"), "pack spec is missing required field: grid"),
            (
                "null_frames",
                lambda data: data["assets"][0]["animations"]["idle"].update({"frames": None}),
                "prop/idle frames must be a non-empty list",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                data = json.loads(spec.read_text(encoding="utf-8"))
                mutate(data)
                spec.write_text(json.dumps(data), encoding="utf-8")
                output = root / "pack"

                result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertFalse(output.exists())

    def test_builder_rejects_non_object_pack_spec_without_traceback(self) -> None:
        for value in (None, 123):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = root / "pack.json"
                spec.write_text(json.dumps(value), encoding="utf-8")
                output = root / "pack"

                result = run_tool(str(BUILD), "--spec", spec, "--out", output, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("pack spec must be a json object", result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_build_pass", result.stdout.lower())
                self.assertFalse(output.exists())

    def test_builder_rejects_animation_that_is_not_an_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("prop")
            asset["animations"]["idle"] = []
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("prop/idle must be an object", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_build_pass", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_asset_that_is_not_an_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(root / "frame.png")
            spec = {
                "pack_name": "test_pack",
                "grid": [32, 32],
                "palette": ["FF0000"],
                "assets": [[]],
            }
            spec_path = root / "pack.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec_path), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("assets[0] must be an object", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_build_pass", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_rejects_frame_path_that_is_not_a_non_empty_string(self) -> None:
        for frame in (7, None, ""):
            with self.subTest(frame=frame), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                asset = static_asset("prop")
                asset["animations"]["idle"]["frames"] = [frame]
                spec = write_pack_fixture(root, [asset])
                output = root / "pack"

                result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("prop/idle frames[0] must be a non-empty path string", result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_build_pass", result.stdout.lower())
                self.assertFalse(output.exists())

    def test_builder_supports_tall_and_bottom_row_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (32, 64), (255, 0, 0, 255)).save(root / "frame.png")
            asset = static_asset("tall")
            asset["canvas"] = [32, 64]
            asset["occupancy"] = [1, 2]
            asset["anchor"] = [16, 63]
            spec = write_pack_fixture(root, [asset])
            Image.new("RGBA", (32, 64), (255, 0, 0, 255)).save(root / "frame.png")
            output = root / "pack"

            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            run_tool(str(VERIFY), "--pack", str(output))

            manifest = json.loads((output / "asset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["atlas"]["anchor"], [16, 63])
            tileset = (output / "resources/test_pack_tileset.tres").read_text(encoding="utf-8")
            self.assertIn("texture_origin = Vector2i(0, 15)", tileset)

    def test_builder_supports_off_center_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("off_center")
            asset["anchor"] = [20, 30]
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            run_tool(str(VERIFY), "--pack", str(output))

            manifest = json.loads((output / "asset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["atlas"]["anchor"], [20, 30])
            self.assertEqual(manifest["assets"][0]["sprite_offset"], [-4, -14])
            tileset = (output / "resources/test_pack_tileset.tres").read_text(encoding="utf-8")
            self.assertIn("texture_origin = Vector2i(4, -2)", tileset)

    @unittest.skipUnless(GODOT.is_file(), "Godot binary is unavailable")
    def test_tall_pack_passes_real_godot_resource_qa(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("tall")
            asset["canvas"] = [32, 64]
            asset["occupancy"] = [1, 2]
            asset["anchor"] = [16, 62]
            asset["collision_polygon"] = [[-8, -4], [8, -4], [8, 4], [-8, 4]]
            spec = write_pack_fixture(root, [asset])
            Image.new("RGBA", (32, 64), (255, 0, 0, 255)).save(root / "frame.png")
            output = root / "pack"

            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            result = run_tool(str(VERIFY), "--pack", str(output), "--godot", str(GODOT))

            self.assertIn("PIXEL_CONVERT_GODOT_QA_PASS", result.stdout)
            self.assertIn("PIXEL_PACK_DELIVERY_QA_PASS", result.stdout)
            self.assertIn("uid_sidecars=1", result.stdout)
            self.assertFalse((output / ".godot").exists())
            uid_path = output / "demo/main.gd.uid"
            self.assertTrue(uid_path.is_file())
            manifest = json.loads((output / "asset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["godot_uid_sidecars"], ["demo/main.gd.uid"])
            self.assertIn("physics_layer_0", (output / "resources/test_pack_tileset.tres").read_text(encoding="utf-8"))

    def test_verifier_cleans_cache_and_reports_cleanly_when_godot_import_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            fake_godot = root / "fake-godot"
            fake_godot.write_text(
                "#!/bin/sh\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = \"--path\" ]; then shift; pack_path=$1; break; fi\n"
                "  shift\n"
                "done\n"
                "mkdir -p \"$pack_path/.godot\"\n"
                "printf cache > \"$pack_path/.godot/probe\"\n"
                "printf cache > \"$pack_path/sprites/generated.import\"\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_godot.chmod(fake_godot.stat().st_mode | stat.S_IXUSR)

            result = run_tool(
                str(VERIFY), "--pack", str(output), "--godot", str(fake_godot), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error: godot import failed", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())
            self.assertFalse((output / ".godot").exists())
            self.assertFalse((output / "sprites/generated.import").exists())

    def test_verifier_cleans_cache_and_reports_cleanly_when_godot_qa_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            fake_godot = root / "fake-godot"
            fake_godot.write_text(
                "#!/bin/sh\n"
                "is_editor=false\n"
                "previous=\n"
                "for argument in \"$@\"; do\n"
                "  if [ \"$previous\" = \"--path\" ]; then pack_path=$argument; fi\n"
                "  if [ \"$argument\" = \"--editor\" ]; then is_editor=true; fi\n"
                "  previous=$argument\n"
                "done\n"
                "mkdir -p \"$pack_path/.godot\"\n"
                "printf cache > \"$pack_path/.godot/probe\"\n"
                "printf cache > \"$pack_path/sprites/generated.ctex\"\n"
                "if [ \"$is_editor\" = true ]; then exit 0; fi\n"
                "printf 'uid://abc123' > \"$pack_path/demo/main.gd.uid\"\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_godot.chmod(fake_godot.stat().st_mode | stat.S_IXUSR)

            result = run_tool(
                str(VERIFY), "--pack", str(output), "--godot", str(fake_godot), check=False
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error: godot resource qa failed", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())
            self.assertFalse((output / ".godot").exists())
            self.assertFalse((output / "sprites/generated.ctex").exists())
            manifest = json.loads((output / "asset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["godot_uid_sidecars"], ["demo/main.gd.uid"])

    def test_builder_rejects_invalid_occupancy_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset()
            asset["occupancy"] = "not_a_footprint"
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("occupancy must contain two positive integers", result.stdout.lower())
            self.assertFalse(output.exists())

    def test_builder_failure_leaves_no_partial_or_staging_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = static_asset("first")
            second = static_asset("second")
            second["animations"]["idle"]["frames"] = ["missing.png"]
            spec = write_pack_fixture(root, [first, second])
            output = root / "pack"

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".pack.staging-*")), [])

    def test_builder_refuses_to_merge_into_non_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("user file", encoding="utf-8")

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not empty", result.stdout.lower())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "user file")
            self.assertEqual(sorted(path.name for path in output.iterdir()), ["keep.txt"])

    def test_builder_rejects_output_file_with_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset()])
            output = root / "pack"
            output.write_text("user file", encoding="utf-8")

            result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output path is not a directory", result.stdout.lower())
            self.assertEqual(output.read_text(encoding="utf-8"), "user file")

    def test_builder_rejects_empty_animations_and_bad_collision_before_writing(self) -> None:
        cases = []
        empty = static_asset("empty")
        empty["animations"] = {}
        cases.append((empty, "animations must not be empty"))
        collision = static_asset("collision")
        collision["collision_polygon"] = "not-a-polygon"
        cases.append((collision, "collision_polygon"))
        for asset, expected in cases:
            with self.subTest(asset=asset["id"]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [asset])
                output = root / "pack"
                result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout.lower())
                self.assertFalse(output.exists())

    def test_demo_plays_the_selected_animation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("animated")
            asset["animations"]["idle"] = {
                "fps": 8.0,
                "loop": True,
                "frames": ["frame.png", "frame.png"],
            }
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))

            demo = (output / "demo" / "main.gd").read_text(encoding="utf-8")
            self.assertIn("sprite.play(DEFAULT_ANIMATIONS[index])", demo)

    def test_builder_preserves_direction_and_contact_point_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("turret")
            asset["directions"] = ["n", "e"]
            asset["contact_points"] = {"base": [16, 30]}
            asset["animations"]["fire_n"] = {
                "direction": "n",
                "fps": 8.0,
                "loop": False,
                "frames": ["frame.png", "frame.png"],
                "contact_points": [
                    {"muzzle": [16, 4]},
                    {"muzzle": [16, 2]},
                ],
            }
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"

            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))

            built = json.loads((output / "asset_manifest.json").read_text(encoding="utf-8"))
            turret = built["assets"][0]
            self.assertEqual(turret["directions"], ["n", "e"])
            self.assertEqual(turret["contact_points"], {"base": [16, 30]})
            self.assertEqual(turret["animations"]["fire_n"]["direction"], "n")
            self.assertEqual(
                turret["animations"]["fire_n"]["contact_points"],
                [{"muzzle": [16, 4]}, {"muzzle": [16, 2]}],
            )

    def test_builder_rejects_directions_that_is_not_a_list(self) -> None:
        for directions in ("south", None, {"south": True}):
            with self.subTest(directions=directions), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                asset = static_asset()
                asset["directions"] = directions
                spec = write_pack_fixture(root, [asset])
                output = root / "pack"

                result = run_tool(str(BUILD), "--spec", str(spec), "--out", str(output), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("directions must be a list", result.stdout.lower())
                self.assertNotIn("pixel_pack_build_pass", result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertFalse(output.exists())

    def test_builder_reports_non_string_names_cleanly(self) -> None:
        cases = ("pack_name", "asset_id", "animation_direction", "direction_item")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                asset = static_asset()
                if case == "asset_id":
                    asset["id"] = 7
                elif case == "animation_direction":
                    asset["directions"] = ["south"]
                    asset["animations"]["idle"]["direction"] = 7
                elif case == "direction_item":
                    asset["directions"] = [7]
                spec_path = write_pack_fixture(root, [asset])
                if case == "pack_name":
                    spec = json.loads(spec_path.read_text(encoding="utf-8"))
                    spec["pack_name"] = 7
                    spec_path.write_text(json.dumps(spec), encoding="utf-8")
                output = root / "pack"

                result = run_tool(
                    str(BUILD), "--spec", str(spec_path), "--out", str(output), check=False
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("must be a string", result.stdout.lower())
                self.assertNotIn("pixel_pack_build_pass", result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertFalse(output.exists())

    def test_ab_preview_contains_exact_native_and_four_x_views(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (20, 20), (0, 0, 255, 255)).save(root / "concept.png")
            Image.new("RGBA", (3, 2), (255, 0, 0, 255)).save(root / "semantic.png")

            run_tool(
                str(PREVIEW),
                "--concept",
                str(root / "concept.png"),
                "--semantic",
                str(root / "semantic.png"),
                "--out",
                str(root / "preview.png"),
            )

            sizes = component_sizes(Image.open(root / "preview.png"), (255, 0, 0))
            self.assertIn((3, 2), sizes)
            self.assertIn((12, 8), sizes)

    def test_ab_preview_rejects_output_aliasing_any_input(self) -> None:
        for target in ("concept.png", "semantic.png", "baseline.png"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                Image.new("RGBA", (20, 20), (0, 0, 255, 255)).save(root / "concept.png")
                Image.new("RGBA", (3, 2), (255, 0, 0, 255)).save(root / "semantic.png")
                Image.new("RGBA", (3, 2), (0, 255, 0, 255)).save(root / "baseline.png")
                before = {path.name: path.read_bytes() for path in root.glob("*.png")}

                result = run_tool(
                    str(PREVIEW), "--concept", root / "concept.png",
                    "--semantic", root / "semantic.png", "--baseline", root / "baseline.png",
                    "--out", root / target, check=False,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("output path must differ from every input", result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertEqual({path.name: path.read_bytes() for path in root.glob("*.png")}, before)

    @unittest.skipUnless(HAS_FILE_SIZE_LIMIT, "requires POSIX resource.RLIMIT_FSIZE")
    def test_ab_preview_preserves_existing_output_when_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGBA", (64, 64), (0, 0, 255, 255)).save(root / "concept.png")
            Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(root / "semantic.png")
            output = root / "preview.png"
            previous = b"PREVIOUS_PREVIEW_BYTES"
            output.write_bytes(previous)

            result = run_tool_with_file_limit(
                64,
                str(PREVIEW), "--concept", root / "concept.png",
                "--semantic", root / "semantic.png", "--out", output,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("pixel_ab_preview_pass", result.stdout.lower())
            self.assertEqual(output.read_bytes(), previous)
            self.assertFalse(any(root.glob(".pixel-preview-*.png")))

    def test_verifier_rejects_duplicate_manifest_asset_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            manifest_path = output / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"].append(manifest["assets"][0])
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate asset id", result.stdout.lower())

    def test_verifier_reports_missing_manifest_assets_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", spec, "--out", output)
            manifest_path = output / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("assets")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", output, check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stdout.lower())
            self.assertIn("assets", result.stdout.lower())
            self.assertNotIn("traceback", result.stdout.lower())
            self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())

    def test_verifier_reports_malformed_manifest_contracts_cleanly(self) -> None:
        cases = ("palette", "atlas", "asset_id", "directions")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", spec, "--out", output)
                manifest_path = output / "asset_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if case == "palette":
                    manifest["palette"] = None
                elif case == "atlas":
                    manifest["atlas"] = None
                elif case == "asset_id":
                    manifest["assets"][0].pop("id")
                else:
                    manifest["assets"][0]["directions"] = [{}]
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(VERIFY), "--pack", output, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error:", result.stdout.lower())
                self.assertIn("id" if case == "asset_id" else case, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())

    def test_verifier_reports_missing_atlas_fields_cleanly(self) -> None:
        for field in ("path", "size", "cell", "anchor"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", spec, "--out", output)
                manifest_path = output / "asset_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["atlas"].pop(field)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(VERIFY), "--pack", output, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error:", result.stdout.lower())
                self.assertIn(field, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())

    def test_verifier_reports_missing_derived_manifest_fields_cleanly(self) -> None:
        cases = (
            "tileset",
            "sprite_offset",
            "tileset_atlas_coordinates",
            "frame_path",
            "frame_atlas_index",
            "frame_atlas_coordinates",
            "frame_placement",
            "frame_type",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", spec, "--out", output)
                manifest_path = output / "asset_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                asset = manifest["assets"][0]
                frame = asset["animations"]["idle"]["frames"][0]
                if case == "tileset":
                    manifest.pop("tileset")
                elif case in {"sprite_offset", "tileset_atlas_coordinates"}:
                    asset.pop(case)
                elif case == "frame_type":
                    asset["animations"]["idle"]["frames"][0] = "frame.png"
                else:
                    frame.pop(case.removeprefix("frame_"))
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(VERIFY), "--pack", output, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error:", result.stdout.lower())
                self.assertIn("frame" if case.startswith("frame_") else case, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())

    def test_verifier_reports_missing_grid_and_animations_cleanly(self) -> None:
        cases = ("grid", "animations")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", spec, "--out", output)
                manifest_path = output / "asset_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if case == "grid":
                    manifest.pop("grid")
                else:
                    manifest["assets"][0].pop("animations")
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(VERIFY), "--pack", output, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(case, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())

    def test_verifier_checks_spriteframes_animation_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("animated")
            asset["animations"]["idle"] = {
                "fps": 8.0,
                "loop": True,
                "frames": ["frame.png", "frame.png"],
            }
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            resource = output / "resources" / "animated_sprite_frames.tres"
            text = resource.read_text(encoding="utf-8").replace('"speed": 8', '"speed": 9')
            resource.write_text(text, encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("animation fps", result.stdout.lower())

    def test_verifier_rejects_non_numeric_manifest_fps(self) -> None:
        for fps in (True, "1.0"):
            with self.subTest(fps=fps), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", spec, "--out", output)
                manifest_path = output / "asset_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["assets"][0]["animations"]["idle"]["fps"] = fps
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(VERIFY), "--pack", output, check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("fps must be a number", result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())
                self.assertNotIn("pixel_pack_source_qa_pass", result.stdout.lower())

    def test_verifier_rejects_non_boolean_loop_and_non_integer_contact_points(self) -> None:
        cases = (
            (
                "loop",
                lambda asset: asset["animations"]["idle"].update({"loop": "false"}),
                "loop must be a boolean",
            ),
            (
                "contact_point",
                lambda asset: asset.update({"contact_points": {"muzzle": ["7", 8.9]}}),
                "invalid contact point",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset()])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
                manifest_path = output / "asset_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest["assets"][0])
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                result = run_tool(str(VERIFY), "--pack", str(output), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout.lower())
                self.assertNotIn("traceback", result.stdout.lower())

    def test_verifier_checks_spriteframes_atlas_region_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            resource = output / "resources/prop_sprite_frames.tres"
            original = resource.read_text(encoding="utf-8")

            for label, changed, expected in (
                ("region", original.replace("region = Rect2(0, 0, 32, 32)", "region = Rect2(32, 0, 32, 32)"), "atlas region"),
                ("path", original.replace("res://sprites/test_pack_atlas.png", "res://sprites/wrong.png"), "atlas path"),
            ):
                with self.subTest(label=label):
                    resource.write_text(changed, encoding="utf-8")
                    result = run_tool(str(VERIFY), "--pack", str(output), check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stdout.lower())
                    resource.write_text(original, encoding="utf-8")

    def test_verifier_rejects_tampered_atlas_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            atlas_path = output / "sprites/test_pack_atlas.png"
            atlas = Image.open(atlas_path).convert("RGBA")
            atlas.putpixel((0, 0), (0, 0, 0, 0))
            atlas.save(atlas_path)

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("atlas cell differs", result.stdout.lower())

    def test_verifier_checks_required_files_tileset_metadata_and_frame_size(self) -> None:
        mutations = ("project", "scene", "tileset_path", "region_size", "frame_size")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
                if mutation == "project":
                    (output / "project.godot").unlink()
                elif mutation == "scene":
                    (output / "demo/main.tscn").unlink()
                elif mutation == "tileset_path":
                    path = output / "resources/test_pack_tileset.tres"
                    path.write_text(path.read_text(encoding="utf-8").replace(
                        "res://sprites/test_pack_atlas.png", "res://sprites/wrong.png"
                    ), encoding="utf-8")
                elif mutation == "region_size":
                    path = output / "resources/test_pack_tileset.tres"
                    path.write_text(path.read_text(encoding="utf-8").replace(
                        "texture_region_size = Vector2i(32, 32)", "texture_region_size = Vector2i(16, 16)"
                    ), encoding="utf-8")
                else:
                    Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
                        output / "sprites/frames/prop/idle_000.png"
                    )
                result = run_tool(str(VERIFY), "--pack", str(output), check=False)
                self.assertNotEqual(result.returncode, 0)

    def test_verifier_checks_tileset_origin_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("tall")
            asset["canvas"] = [32, 64]
            asset["occupancy"] = [1, 2]
            asset["anchor"] = [16, 62]
            spec = write_pack_fixture(root, [asset])
            Image.new("RGBA", (32, 64), (255, 0, 0, 255)).save(root / "frame.png")
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            tileset = output / "resources/test_pack_tileset.tres"
            tileset.write_text(tileset.read_text(encoding="utf-8").replace(
                "texture_origin = Vector2i(0, 14)", "texture_origin = Vector2i(0, -16)"
            ), encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("texture origin", result.stdout.lower())

    def test_verifier_matches_complete_multidigit_tileset_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset(f"asset_{index}") for index in range(11)])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            tileset = output / "resources/test_pack_tileset.tres"
            text = "\n".join(
                line for line in tileset.read_text(encoding="utf-8").splitlines()
                if not line.startswith("0:0/0")
            )
            tileset.write_text(text + "\n", encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tileset is missing asset_0", result.stdout.lower())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = [static_asset(f"asset_{index}") for index in range(11)]
            for index in (0, 10):
                assets[index]["collision_polygon"] = [[-8, -4], [8, -4], [8, 4], [-8, 4]]
            spec = write_pack_fixture(root, assets)
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            tileset = output / "resources/test_pack_tileset.tres"
            original = (
                "0:0/0/physics_layer_0/polygon_0/points = "
                "PackedVector2Array(-8, -4, 8, -4, 8, 4, -8, 4)"
            )
            tileset.write_text(
                tileset.read_text(encoding="utf-8").replace(
                    original,
                    "0:0/0/physics_layer_0/polygon_0/points = PackedVector2Array(0, 0, 1, 0, 1, 1)",
                ),
                encoding="utf-8",
            )

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("collision polygon differs for asset_0", result.stdout.lower())

    def test_verifier_checks_demo_sprite_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            demo = output / "demo" / "main.gd"
            text = demo.read_text(encoding="utf-8").replace(
                "const SPRITE_OFFSETS := [Vector2(0, -14)]",
                "const SPRITE_OFFSETS := [Vector2(0, -13)]",
            )
            demo.write_text(text, encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("sprite offset", result.stdout.lower())

    def test_verifier_checks_tileset_collision_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("solid")
            asset["collision_polygon"] = [[-8, -4], [8, -4], [8, 4], [-8, 4]]
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            tileset = output / "resources" / "test_pack_tileset.tres"
            text = "\n".join(
                line for line in tileset.read_text(encoding="utf-8").splitlines()
                if "/physics_layer_0/polygon_" not in line
            )
            tileset.write_text(text + "\n", encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("collision polygon count", result.stdout.lower())

    def test_verifier_rejects_undeclared_generated_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            (output / "resources" / "orphan_sprite_frames.tres").write_text(
                "[gd_resource type=\"SpriteFrames\" format=3]\n",
                encoding="utf-8",
            )

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("undeclared generated file", result.stdout.lower())

    def test_source_verifier_rejects_delivery_cache_without_deleting_it(self) -> None:
        cases = (
            Path(".godot/imported/texture.ctex"),
            Path("sprites/texture.import"),
            Path("sprites/texture.ctex"),
        )
        for relative in cases:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = write_pack_fixture(root, [static_asset("prop")])
                output = root / "pack"
                run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
                cached = output / relative
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(b"generated cache")

                result = run_tool(str(VERIFY), "--pack", str(output), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("delivery contains generated cache", result.stdout.lower())
                self.assertTrue(cached.is_file())

    def test_verifier_rejects_undeclared_godot_uid_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            (output / "demo/main.gd.uid").write_text("uid://abc123\n", encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uid sidecars differ from the manifest", result.stdout.lower())

    def test_verifier_checks_direction_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("turret")
            asset["directions"] = ["n"]
            asset["animations"]["idle"]["direction"] = "n"
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            manifest_path = output / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"][0]["animations"]["idle"]["direction"] = "e"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("direction", result.stdout.lower())

    def test_verifier_checks_occupancy_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            manifest_path = output / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"][0]["occupancy"] = [1, 0]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("occupancy", result.stdout.lower())

    def test_verifier_rejects_missing_tileset_animation_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = write_pack_fixture(root, [static_asset("prop")])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            manifest_path = output / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"][0]["tileset_animation"] = "missing"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tileset_animation does not exist", result.stdout.lower())
            self.assertNotIn("keyerror", result.stdout.lower())

    def test_demo_qa_checks_all_animation_metadata_and_playing_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("animated")
            asset["animations"]["run"] = {
                "fps": 6.0,
                "loop": True,
                "frames": ["frame.png", "frame.png"],
            }
            asset["tileset_animation"] = "run"
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))

            demo = (output / "demo" / "main.gd").read_text(encoding="utf-8")
            self.assertIn("const ANIMATION_NAMES", demo)
            self.assertIn("get_animation_speed", demo)
            self.assertIn("get_animation_loop", demo)
            self.assertIn("get_frame_count", demo)
            self.assertIn("sprite.is_playing()", demo)
            self.assertIn("get_collision_polygons_count", demo)

    def test_verifier_requires_demo_playback_for_multiframe_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = static_asset("animated")
            asset["animations"]["idle"] = {
                "fps": 8.0,
                "loop": True,
                "frames": ["frame.png", "frame.png"],
            }
            spec = write_pack_fixture(root, [asset])
            output = root / "pack"
            run_tool(str(BUILD), "--spec", str(spec), "--out", str(output))
            demo = output / "demo" / "main.gd"
            demo.write_text(
                demo.read_text(encoding="utf-8").replace(
                    "        sprite.play(DEFAULT_ANIMATIONS[index])\n", ""
                ),
                encoding="utf-8",
            )

            result = run_tool(str(VERIFY), "--pack", str(output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("playback", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
