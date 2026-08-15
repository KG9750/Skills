#!/usr/bin/env python3
"""Normalize one semantic redraw to a palette-bound, hard-alpha sprite canvas."""

from __future__ import annotations

import argparse
import math
import os
import tempfile
from pathlib import Path


def parse_pair(value: str, separator: str) -> tuple[int, int]:
    try:
        left, right = value.lower().split(separator, 1)
        return int(left), int(right)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected INT{separator}INT, got {value!r}") from exc


def parse_canvas(value: str) -> tuple[int, int]:
    return parse_pair(value, "x")


def parse_anchor(value: str) -> tuple[int, int]:
    return parse_pair(value, ",")


def paths_alias(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    if first == second:
        return True
    try:
        return first.samefile(second)
    except (FileNotFoundError, OSError):
        return False


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


def luminance(color: tuple[int, int, int]) -> float:
    r, g, b = color
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def nearest_color(
    color: tuple[int, int, int], palette: tuple[tuple[int, int, int], ...]
) -> tuple[int, int, int]:
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


def apply_chroma_key(image: Image.Image, key: str, threshold: int) -> Image.Image:
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


def normalize(
    source: Image.Image,
    canvas: tuple[int, int],
    anchor: tuple[int, int],
    palette: tuple[tuple[int, int, int], ...],
    padding: int,
    alpha_threshold: int,
) -> Image.Image:
    source = source.convert("RGBA")
    mask = source.getchannel("A").point(lambda value: 255 if value >= alpha_threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("source has no opaque pixels after alpha threshold")
    subject = source.crop(bbox)

    canvas_w, canvas_h = canvas
    anchor_x, anchor_y = anchor
    if not (0 <= anchor_x < canvas_w and 0 <= anchor_y < canvas_h):
        raise ValueError("anchor must be inside the canvas")
    available_w = 2 * min(anchor_x - padding, canvas_w - padding - anchor_x)
    available_h = anchor_y - padding
    if available_w <= 0 or available_h <= 0:
        raise ValueError("padding leaves no room for the subject")

    scale = min(available_w / subject.width, available_h / subject.height)
    size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
    subject = subject.resize(size, Image.Resampling.LANCZOS)

    x0 = anchor_x - size[0] // 2
    y0 = anchor_y - size[1]
    if x0 < 0 or y0 < 0 or x0 + size[0] > canvas_w or y0 + size[1] > canvas_h:
        raise ValueError("normalized subject would clip outside the canvas")

    result = Image.new("RGBA", canvas, (0, 0, 0, 0))
    src = subject.load()
    dst = result.load()
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, a = src[x, y]
            if a >= alpha_threshold:
                dst[x0 + x, y0 + y] = (*nearest_color((r, g, b), palette), 255)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--canvas", required=True, type=parse_canvas)
    parser.add_argument("--anchor", required=True, type=parse_anchor)
    parser.add_argument("--palette", required=True, type=Path)
    parser.add_argument("--background-key")
    parser.add_argument("--key-threshold", type=int, default=40)
    parser.add_argument("--alpha-threshold", type=int, default=112)
    parser.add_argument("--padding", type=int, default=2)
    args = parser.parse_args()

    if not 1 <= args.alpha_threshold <= 255:
        raise ValueError("alpha threshold must be between 1 and 255")
    if args.key_threshold < 0:
        raise ValueError("key threshold must be non-negative")

    global Image
    try:
        from PIL import Image as PillowImage
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc
    Image = PillowImage

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if paths_alias(input_path, output_path):
        raise ValueError("input and output paths must differ")

    source = Image.open(input_path)
    if args.background_key:
        source = apply_chroma_key(source, args.background_key, args.key_threshold)
    else:
        source = source.convert("RGBA")
    if not args.background_key and source.getchannel("A").getextrema() == (255, 255):
        raise ValueError("input has no transparent pixels; provide --background-key or remove the background first")

    palette = load_palette(args.palette)
    result = normalize(
        source,
        args.canvas,
        args.anchor,
        palette,
        args.padding,
        args.alpha_threshold,
    )
    bbox = result.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("normalized result has no opaque pixels after alpha threshold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pixel-static-",
        suffix=".png",
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        result.save(temporary_path, format="PNG")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    colors = {color[:3] for _, color in result.getcolors(maxcolors=65536) or [] if color[3] == 255}
    print(
        f"PIXEL_NORMALIZE_PASS output={output_path} size={result.size} "
        f"bbox={bbox} colors={len(colors)} hard_alpha=true"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
