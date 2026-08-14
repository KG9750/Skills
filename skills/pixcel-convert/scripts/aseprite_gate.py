#!/usr/bin/env python3
"""Prepare and verify an optional Aseprite pixel-polish gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import atexit
from pathlib import Path


def required(value: dict, key: str, label: str):
    if key not in value:
        raise ValueError(f"{label} is missing required field: {key}")
    return value[key]


def gate_frame_path(gate: Path, value: object, directory: str, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty relative path")
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{label} path must stay inside {directory}/")
    resolved = (gate / relative).resolve()
    expected_parent = (gate / directory).resolve()
    try:
        resolved.relative_to(expected_parent)
    except ValueError as exc:
        raise ValueError(f"{label} path must stay inside {directory}/") from exc
    return resolved


def parse_pair(value: str, separator: str) -> tuple[int, int]:
    try:
        left, right = value.lower().split(separator, 1)
        return int(left), int(right)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected INT{separator}INT, got {value!r}") from exc


def parse_grid(value: str) -> tuple[int, int]:
    return parse_pair(value, "x")


def parse_anchor(value: str) -> tuple[int, int]:
    return parse_pair(value, ",")


def positive_int_pair(value: object, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in value)
    ):
        raise ValueError(f"{label} must contain two positive integers")
    return tuple(value)


def load_palette(path: Path) -> tuple[tuple[int, int, int], ...]:
    colors: list[tuple[int, int, int]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip().removeprefix("#")
        if not value or value.startswith("//"):
            continue
        if len(value) != 6:
            raise ValueError(f"invalid palette color: {raw!r}")
        colors.append(tuple(bytes.fromhex(value)))
    if not colors:
        raise ValueError("palette is empty")
    return tuple(colors)


def candidate_binaries(explicit: Path | None) -> list[Path]:
    if explicit:
        return [explicit.expanduser().resolve(strict=False)]
    env_binary = os.environ.get("ASEPRITE_BIN")
    if env_binary:
        return [Path(env_binary).expanduser().resolve(strict=False)]
    candidates: list[Path] = []
    found = shutil.which("aseprite")
    if found:
        candidates.append(Path(found))
    home = Path.home()
    candidates.extend(
        [
            home / "Applications/Aseprite-Codex.app/Contents/MacOS/aseprite",
            Path("/Applications/Aseprite.app/Contents/MacOS/aseprite"),
            home / "Projects/Aseprite/build/bin/Aseprite.app/Contents/MacOS/aseprite",
        ]
    )
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved not in unique:
            unique.append(resolved)
    return unique


def probe_aseprite(explicit: Path | None, timeout: float) -> dict:
    existing = [path for path in candidate_binaries(explicit) if path.is_file() and os.access(path, os.X_OK)]
    if not existing:
        return {"mode": "unavailable", "binary": None, "detail": "no executable found"}

    failures: list[str] = []
    for binary in existing:
        try:
            result = subprocess.run(
                [str(binary), "--version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            failures.append(f"{binary}: timed out")
            continue
        except OSError as exc:
            failures.append(f"{binary}: launch failed: {exc}")
            continue

        output = result.stdout.strip()
        if result.returncode == 0:
            return {"mode": "cli", "binary": str(binary), "detail": output or "CLI probe passed"}
        detail = f"{binary}: exited {result.returncode}"
        if output:
            detail += f": {output.splitlines()[-1]}"
        failures.append(detail)
    return {"mode": "manual_gui", "binary": str(existing[0]), "detail": "; ".join(failures)}


def inspect_frame(path: Path, expected_size: tuple[int, int], palette: set[tuple[int, int, int]]) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc

    with Image.open(path) as source:
        image = source.convert("RGBA")
    if image.size != expected_size:
        raise ValueError(f"{path} has size {image.size}, expected {expected_size}")
    alpha_channel = image.getchannel("A")
    alpha = set(alpha_channel.get_flattened_data() if hasattr(alpha_channel, "get_flattened_data") else alpha_channel.getdata())
    if not alpha <= {0, 255}:
        raise ValueError(f"{path} contains partial alpha")
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    opaque = {color[:3] for color in pixels if color[3] == 255}
    if not opaque:
        raise ValueError(f"{path} contains no opaque pixels")
    if not opaque <= palette:
        raise ValueError(f"{path} contains colors outside the declared palette")


def write_gpl(path: Path, palette: tuple[tuple[int, int, int], ...], name: str) -> None:
    lines = ["GIMP Palette", f"Name: {name}", "Columns: 8", "#"]
    for red, green, blue in palette:
        lines.append(f"{red:3d} {green:3d} {blue:3d}\t#{red:02X}{green:02X}{blue:02X}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def command_probe(args: argparse.Namespace) -> int:
    result = probe_aseprite(args.aseprite, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else (
        f"ASEPRITE_PROBE mode={result['mode']} binary={result['binary']} detail={result['detail']}"
    ))
    return 2 if args.require_cli and result["mode"] != "cli" else 0


def command_prepare(args: argparse.Namespace) -> int:
    output = args.out.resolve()
    if min(args.grid) <= 0:
        raise ValueError("grid must contain two positive integers")
    if output.exists():
        if not output.is_dir():
            raise ValueError(f"output path is not a directory: {output}")
        if any(output.iterdir()):
            raise ValueError(f"output directory is not empty: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    cleanup_staging = lambda: shutil.rmtree(staging, ignore_errors=True)
    atexit.register(cleanup_staging)

    palette_values = load_palette(args.palette)
    palette = set(palette_values)
    inputs = [path.resolve() for path in args.input]
    if not inputs:
        raise ValueError("at least one input frame is required")

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc
    with Image.open(inputs[0]) as first:
        canvas = first.size
    anchor = args.anchor
    if not (0 <= anchor[0] < canvas[0] and 0 <= anchor[1] < canvas[1]):
        raise ValueError("anchor must be inside the canvas")
    for frame in inputs:
        inspect_frame(frame, canvas, palette)

    baseline_dir = staging / "baseline"
    working_dir = staging / "working"
    baseline_dir.mkdir()
    working_dir.mkdir()
    frames: list[dict] = []
    for index, source in enumerate(inputs):
        name = f"frame_{index:03d}.png"
        baseline = baseline_dir / name
        working = working_dir / name
        shutil.copy2(source, baseline)
        shutil.copy2(source, working)
        frames.append({
            "baseline": f"baseline/{name}",
            "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
            "working": f"working/{name}",
        })

    write_gpl(staging / "palette.gpl", palette_values, args.asset_id)
    probe = probe_aseprite(args.aseprite, args.timeout) if args.probe else {
        "mode": "manual_gui",
        "binary": str(args.aseprite.resolve()) if args.aseprite else None,
        "detail": "probe skipped",
    }
    manifest = {
        "schema_version": 1,
        "asset_id": args.asset_id,
        "status": "awaiting_aseprite_review",
        "mode": probe["mode"],
        "aseprite_binary": probe["binary"],
        "canvas": list(canvas),
        "grid": list(args.grid),
        "anchor": list(anchor),
        "palette": ["%02X%02X%02X" % color for color in palette_values],
        "frames": frames,
    }
    (staging / "gate.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    instructions = f"""ASEPRITE OPTIONAL POLISH GATE

Asset: {args.asset_id}
Canvas: {canvas[0]}x{canvas[1]}
Logical grid: {args.grid[0]}x{args.grid[1]}
Bottom-centre anchor: {anchor[0]},{anchor[1]}
Mode: {probe['mode']}

1. Open the PNG files in working/ with Aseprite.
2. Load palette.gpl and keep every opaque pixel in that palette.
3. Preserve canvas size, frame order, hard alpha, and the declared anchor.
4. Inspect at native 1x and tiled/onion-skin views as applicable.
5. Save back to the same working/frame_NNN.png files.
6. Run: python3 "{Path(__file__).resolve()}" verify --gate "{output}"

Do not edit baseline/. Do not add collision geometry or bake guides into the PNG.
"""
    (staging / "OPEN_IN_ASEPRITE.txt").write_text(instructions, encoding="utf-8")
    if output.exists():
        output.rmdir()
    staging.replace(output)
    atexit.unregister(cleanup_staging)
    print(
        f"ASEPRITE_GATE_PREPARE_PASS asset={args.asset_id} frames={len(frames)} "
        f"canvas={canvas[0]}x{canvas[1]} mode={probe['mode']} out={output}"
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    gate = args.gate.resolve()
    manifest_path = gate / "gate.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("gate manifest must be a JSON object")
    manifest["status"] = "awaiting_aseprite_review"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    asset_id = required(manifest, "asset_id", "gate manifest")
    canvas = positive_int_pair(required(manifest, "canvas", "gate manifest"), "gate manifest canvas")
    raw_palette = required(manifest, "palette", "gate manifest")
    if not isinstance(raw_palette, list) or not raw_palette or not all(
        isinstance(value, str) for value in raw_palette
    ):
        raise ValueError("gate manifest palette must be a non-empty list of hex strings")
    try:
        palette = {tuple(bytes.fromhex(value)) for value in raw_palette}
    except ValueError as exc:
        raise ValueError("gate manifest palette contains an invalid RGB hex color") from exc
    frames = required(manifest, "frames", "gate manifest")
    if not isinstance(frames, list) or not frames:
        raise ValueError("gate manifest frames must be a non-empty list")
    seen_baselines: set[Path] = set()
    seen_working: set[Path] = set()
    for index, record in enumerate(frames):
        baseline_name = required(record, "baseline", f"gate manifest frames[{index}]")
        working_name = required(record, "working", f"gate manifest frames[{index}]")
        baseline = gate_frame_path(gate, baseline_name, "baseline", "baseline")
        working = gate_frame_path(gate, working_name, "working", "working")
        if baseline in seen_baselines or working in seen_working:
            raise ValueError("duplicate gate frame path")
        seen_baselines.add(baseline)
        seen_working.add(working)
        if hashlib.sha256(baseline.read_bytes()).hexdigest() != record.get("baseline_sha256"):
            raise ValueError(f"baseline frame changed: {baseline_name}")
        inspect_frame(working, canvas, palette)
    manifest["status"] = "verified"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"ASEPRITE_GATE_VERIFY_PASS asset={asset_id} frames={len(frames)} "
        f"canvas={canvas[0]}x{canvas[1]} opaque=true hard_alpha=true palette_only=true"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe")
    probe.add_argument("--aseprite", type=Path)
    probe.add_argument("--timeout", type=float, default=5.0)
    probe.add_argument("--json", action="store_true")
    probe.add_argument("--require-cli", action="store_true")
    probe.set_defaults(function=command_probe)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--asset-id", required=True)
    prepare.add_argument("--input", action="append", required=True, type=Path)
    prepare.add_argument("--out", required=True, type=Path)
    prepare.add_argument("--palette", required=True, type=Path)
    prepare.add_argument("--grid", required=True, type=parse_grid)
    prepare.add_argument("--anchor", required=True, type=parse_anchor)
    prepare.add_argument("--aseprite", type=Path)
    prepare.add_argument("--timeout", type=float, default=5.0)
    prepare.add_argument("--probe", action=argparse.BooleanOptionalAction, default=True)
    prepare.set_defaults(function=command_prepare)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--gate", required=True, type=Path)
    verify.set_defaults(function=command_verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.function(args))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
