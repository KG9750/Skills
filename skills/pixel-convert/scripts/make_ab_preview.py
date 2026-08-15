#!/usr/bin/env python3
"""Create a native-to-4x visual-gate sheet for a semantic redraw."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


def paths_alias(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    if first == second:
        return True
    try:
        return first.samefile(second)
    except (FileNotFoundError, OSError):
        return False


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    image = Image.new("RGB", size, (216, 206, 178))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(185, 173, 145))
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", required=True, type=Path)
    parser.add_argument("--semantic", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    global Image, ImageDraw, ImageFont
    try:
        from PIL import Image as PillowImage, ImageDraw as PillowImageDraw, ImageFont as PillowImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc
    Image, ImageDraw, ImageFont = PillowImage, PillowImageDraw, PillowImageFont

    output_path = args.out.resolve()
    input_paths = [args.concept.resolve(), args.semantic.resolve()]
    if args.baseline:
        input_paths.append(args.baseline.resolve())
    if any(paths_alias(output_path, input_path) for input_path in input_paths):
        raise ValueError("output path must differ from every input")

    items = [("SOURCE CONCEPT", Image.open(input_paths[0]).convert("RGBA"), False)]
    if args.baseline:
        items.append(("AUTO BASELINE", Image.open(input_paths[2]).convert("RGBA"), True))
    items.append(("SEMANTIC REDRAW", Image.open(input_paths[1]).convert("RGBA"), True))

    pixel_items = [image for _, image, is_pixel in items if is_pixel]
    max_native_w = max(image.width for image in pixel_items)
    max_native_h = max(image.height for image in pixel_items)
    panel_width = max(420, max_native_w * 4 + 36)
    native_zone_height = max(72, max_native_h + 24)
    four_x_zone_height = max(220, max_native_h * 4 + 24)
    panel_height = 100 + native_zone_height + four_x_zone_height
    output = Image.new("RGB", (panel_width * len(items), panel_height), (216, 206, 178))
    draw = ImageDraw.Draw(output)
    font = ImageFont.load_default()
    for index, (label, image, pixel_scale) in enumerate(items):
        x0 = index * panel_width
        draw.text((x0 + 18, 18), label, fill=(43, 37, 35), font=font)
        if pixel_scale:
            draw.text((x0 + 18, 44), "NATIVE 1X", fill=(43, 37, 35), font=font)
            native_panel = checkerboard((panel_width - 36, native_zone_height))
            native_panel.paste(
                image,
                ((native_panel.width - image.width) // 2, (native_panel.height - image.height) // 2),
                image,
            )
            output.paste(native_panel, (x0 + 18, 64))

            four_x_y = 76 + native_zone_height
            draw.text((x0 + 18, four_x_y), "NEAREST 4X", fill=(43, 37, 35), font=font)
            four_x = image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST)
            four_x_panel = checkerboard((panel_width - 36, four_x_zone_height))
            four_x_panel.paste(
                four_x,
                ((four_x_panel.width - four_x.width) // 2, (four_x_panel.height - four_x.height) // 2),
                four_x,
            )
            output.paste(four_x_panel, (x0 + 18, four_x_y + 20))
        else:
            panel = checkerboard((panel_width - 36, panel_height - 72))
            concept = image.copy()
            concept.thumbnail((panel.width - 24, panel.height - 24), Image.Resampling.LANCZOS)
            panel.paste(concept, ((panel.width - concept.width) // 2, (panel.height - concept.height) // 2), concept)
            output.paste(panel, (x0 + 18, 54))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pixel-preview-",
        suffix=".png",
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        output.save(temporary_path, format="PNG")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(f"PIXEL_AB_PREVIEW_PASS panels={len(items)} native=1x nearest=4x output={output_path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
