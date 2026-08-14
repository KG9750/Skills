#!/usr/bin/env python3
"""Normalize an animation group with one shared scale and stable source anchors."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from pathlib import Path


def apply_chroma_key(image, key: object, threshold: int, Image):
    if not isinstance(key, str):
        raise ValueError("background key must be a six-digit RGB hex string")
    value = key.strip().removeprefix("#")
    if len(value) != 6:
        raise ValueError("background key must be a six-digit RGB hex color")
    key_rgb = tuple(bytes.fromhex(value))
    rgba = image.convert("RGBA")
    output = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    src = rgba.load()
    dst = output.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = src[x, y]
            distance = math.sqrt((r - key_rgb[0]) ** 2 + (g - key_rgb[1]) ** 2 + (b - key_rgb[2]) ** 2)
            if a > 0 and distance > threshold:
                dst[x, y] = (r, g, b, a)
    return output


def load_palette(path: Path) -> tuple[tuple[int, int, int], ...]:
    colors = []
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


def luminance(color: tuple[int, int, int]) -> float:
    return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]


def nearest_color(color, palette):
    source_luminance = luminance(color)
    return min(
        palette,
        key=lambda candidate: (
            2 * (color[0] - candidate[0]) ** 2
            + 3 * (color[1] - candidate[1]) ** 2
            + (color[2] - candidate[2]) ** 2
            + 2 * (source_luminance - luminance(candidate)) ** 2
        ),
    )


def required(spec: dict, key: str, label: str):
    if key not in spec:
        raise ValueError(f"{label} is missing required field: {key}")
    return spec[key]


def paths_alias(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    if first == second:
        return True
    try:
        return first.samefile(second)
    except (FileNotFoundError, OSError):
        return False


def nearest_existing_directory(path: Path) -> Path:
    directory = path.parent.resolve()
    while not directory.exists():
        directory = directory.parent
    if not directory.is_dir():
        raise ValueError(f"output parent is not a directory: {directory}")
    return directory


def filesystem_is_case_insensitive(directory: Path) -> bool:
    probe_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".PixcelCaseProbe-", dir=directory, delete=False) as probe:
            probe_path = Path(probe.name)
        alias = probe_path.with_name(probe_path.name.swapcase())
        return alias.exists() and probe_path.samefile(alias)
    finally:
        if probe_path is not None:
            probe_path.unlink(missing_ok=True)


def output_identity(path: Path, case_insensitive: bool) -> str:
    value = str(path.resolve())
    return value.casefold() if case_insensitive else value


def integer_pair(value, label: str, *, positive: bool = False) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in value)
        or (positive and min(value) <= 0)
    ):
        requirement = "two positive integers" if positive else "two integers"
        raise ValueError(f"{label} must contain {requirement}")
    return tuple(value)


def integer_option(spec: dict, key: str, default: int) -> int:
    value = spec.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc

    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("animation spec must be a JSON object")
    canvas = integer_pair(required(spec, "canvas", "animation spec"), "canvas", positive=True)
    target_anchor = integer_pair(required(spec, "anchor", "animation spec"), "anchor")
    if not (0 <= target_anchor[0] < canvas[0] and 0 <= target_anchor[1] < canvas[1]):
        raise ValueError("anchor must be inside the canvas")
    padding = integer_option(spec, "padding", 2)
    if padding < 0:
        raise ValueError("padding must be non-negative")
    alpha_threshold = integer_option(spec, "alpha_threshold", 112)
    if not 1 <= alpha_threshold <= 255:
        raise ValueError("alpha_threshold must be between 1 and 255")
    key_threshold = integer_option(spec, "key_threshold", 40)
    if key_threshold < 0:
        raise ValueError("key_threshold must be non-negative")
    palette_path = required(spec, "palette", "animation spec")
    if not isinstance(palette_path, str) or not palette_path:
        raise ValueError("palette must be a non-empty relative path")
    palette = load_palette((spec_path.parent / palette_path).resolve())
    raw_frames = spec.get("frames", [])
    if not isinstance(raw_frames, list) or len(raw_frames) < 2:
        raise ValueError("animation normalization requires at least two frames")

    frames = []
    if not all(isinstance(frame, dict) for frame in raw_frames):
        raise ValueError("every animation frame must be an object")
    provided_anchors = ["source_anchor" in frame for frame in raw_frames]
    if any(provided_anchors) and not all(provided_anchors):
        raise ValueError("provide source_anchor for every frame or for none")
    input_paths: list[Path] = []
    frame_paths: list[tuple[Path, Path]] = []
    for index, raw in enumerate(raw_frames):
        input_path = required(raw, "input", f"frames[{index}]")
        output_path = required(raw, "output", f"frames[{index}]")
        if not isinstance(input_path, str) or not input_path:
            raise ValueError(f"frames[{index}].input must be a non-empty relative path")
        if not isinstance(output_path, str) or not output_path:
            raise ValueError(f"frames[{index}].output must be a non-empty relative path")
        resolved_input = (spec_path.parent / input_path).resolve()
        resolved_output = (spec_path.parent / output_path).resolve()
        input_paths.append(resolved_input)
        frame_paths.append((resolved_input, resolved_output))
    for index, (_, output_path) in enumerate(frame_paths):
        if any(paths_alias(output_path, input_path) for input_path in input_paths):
            raise ValueError(f"frames[{index}] output must not overwrite an input frame")
    case_modes: dict[Path, bool] = {}
    output_identities: list[str] = []
    for index, (_, output_path) in enumerate(frame_paths):
        probe_directory = nearest_existing_directory(output_path)
        case_insensitive = case_modes.setdefault(
            probe_directory,
            filesystem_is_case_insensitive(probe_directory),
        )
        identity = output_identity(output_path, case_insensitive)
        if identity in output_identities or any(
            paths_alias(output_path, previous[1]) for previous in frame_paths[:index]
        ):
            raise ValueError(f"frames[{index}] output duplicates another output")
        if output_path.exists():
            raise ValueError(f"frames[{index}] output already exists: {output_path}")
        output_identities.append(identity)

    for index, raw in enumerate(raw_frames):
        input_path = raw["input"]
        resolved_input, resolved_output = frame_paths[index]
        image = Image.open(resolved_input).convert("RGBA")
        key = raw.get("background_key", spec.get("background_key"))
        if key:
            image = apply_chroma_key(image, key, key_threshold, Image)
        elif image.getchannel("A").getextrema() == (255, 255):
            raise ValueError(
                f"frame {input_path} is fully opaque; provide background_key or remove the background first"
            )
        bbox = image.getchannel("A").point(
            lambda value: 255 if value >= alpha_threshold else 0
        ).getbbox()
        if bbox is None:
            raise ValueError(f"frame {input_path} has no opaque pixels after alpha threshold")
        frames.append({"raw": raw, "image": image, "bbox": bbox, "output_path": resolved_output})

    if all(provided_anchors):
        for frame in frames:
            frame["source_anchor"] = integer_pair(
                frame["raw"]["source_anchor"],
                f"frame {frame['raw']['input']} source_anchor",
            )
            source_x, source_y = frame["source_anchor"]
            source_w, source_h = frame["image"].size
            if not (0 <= source_x < source_w and 0 <= source_y < source_h):
                raise ValueError(
                    f"frame {frame['raw']['input']} source_anchor must be inside the source frame"
                )
    else:
        sizes = {frame["image"].size for frame in frames}
        if len(sizes) != 1:
            raise ValueError("frames with different source canvases require source_anchor")
        union = (
            min(frame["bbox"][0] for frame in frames),
            min(frame["bbox"][1] for frame in frames),
            max(frame["bbox"][2] for frame in frames),
            max(frame["bbox"][3] for frame in frames),
        )
        shared_anchor = ((union[0] + union[2]) // 2, union[3])
        for frame in frames:
            frame["source_anchor"] = shared_anchor

    canvas_w, canvas_h = canvas
    target_x, target_y = target_anchor
    available = (target_x - padding, canvas_w - padding - target_x, target_y - padding, canvas_h - padding - target_y)
    if min(available) < 0:
        raise ValueError("target anchor and padding do not fit inside canvas")
    extents = [0, 0, 0, 0]
    normalized_frames: list[tuple[Path, Image.Image]] = []
    for frame in frames:
        left, top, right, bottom = frame["bbox"]
        source_x, source_y = frame["source_anchor"]
        extents[0] = max(extents[0], source_x - left)
        extents[1] = max(extents[1], right - source_x)
        extents[2] = max(extents[2], source_y - top)
        extents[3] = max(extents[3], bottom - source_y)
    scales = [space / extent for space, extent in zip(available, extents) if extent > 0]
    if not scales:
        raise ValueError("animation frames have no measurable extent")
    scale = min(scales)
    if scale <= 0:
        raise ValueError("animation shared scale must be greater than zero")

    for frame in frames:
        left, top, right, bottom = frame["bbox"]
        crop = frame["image"].crop(frame["bbox"])
        source_x, source_y = frame["source_anchor"]
        scaled_left = math.floor((source_x - left) * scale)
        scaled_right = math.floor((right - source_x) * scale)
        scaled_top = math.floor((source_y - top) * scale)
        scaled_bottom = math.floor((bottom - source_y) * scale)
        size = (
            max(1, scaled_left + scaled_right),
            max(1, scaled_top + scaled_bottom),
        )
        crop = crop.resize(size, Image.Resampling.LANCZOS)
        anchor_in_crop = (scaled_left, scaled_top)
        origin = (target_x - anchor_in_crop[0], target_y - anchor_in_crop[1])
        if origin[0] < 0 or origin[1] < 0 or origin[0] + size[0] > canvas_w or origin[1] + size[1] > canvas_h:
            raise ValueError(f"frame {frame['raw']['input']} clips after shared transform")
        output = Image.new("RGBA", canvas, (0, 0, 0, 0))
        src = crop.load()
        dst = output.load()
        for y in range(size[1]):
            for x in range(size[0]):
                r, g, b, a = src[x, y]
                if a >= alpha_threshold:
                    dst[origin[0] + x, origin[1] + y] = (*nearest_color((r, g, b), palette), 255)
        if output.getchannel("A").getbbox() is None:
            raise ValueError(f"frame {frame['raw']['input']} has no opaque pixels after alpha threshold")
        normalized_frames.append((frame["output_path"], output))
    staged_outputs: list[tuple[Path, Path]] = []
    committed_outputs: list[Path] = []
    try:
        for output_path, output in normalized_frames:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".pixcel-animation-",
                suffix=".png",
                dir=output_path.parent,
            )
            os.close(descriptor)
            temporary_path = Path(temporary_name)
            staged_outputs.append((temporary_path, output_path))
            output.save(temporary_path, format="PNG")
        for temporary_path, output_path in staged_outputs:
            temporary_path.replace(output_path)
            committed_outputs.append(output_path)
    except Exception:
        for output_path in committed_outputs:
            output_path.unlink(missing_ok=True)
        raise
    finally:
        for temporary_path, _ in staged_outputs:
            temporary_path.unlink(missing_ok=True)
    print(f"PIXCEL_ANIMATION_NORMALIZE_PASS frames={len(frames)} scale={scale:.6f} anchor={target_anchor}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
