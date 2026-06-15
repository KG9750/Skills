#!/usr/bin/env python3
"""Render a Xiaohongshu carousel package from a JSON spec."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("Pillow is required. Install with: python3 -m pip install pillow") from exc


WIDTH = 1080
HEIGHT = 1440
MARGIN = 92
CARD_RADIUS = 32
KAMI_PARCHMENT = "#f5f4ed"
KAMI_IVORY = "#faf9f5"
KAMI_BORDER = "#e8e6dc"
KAMI_BORDER_SOFT = "#e5e3d8"
KAMI_BRAND = "#1B365D"
KAMI_TAG_BG = "#EEF2F7"
KAMI_NEAR_BLACK = "#141413"
KAMI_OLIVE = "#504e49"
KAMI_STONE = "#6b6a64"
GOLD_STAR = (207, 154, 45)
DEFAULT_MAX_SKETCHES = 0
GENERATED_FILES = {
    "caption.md",
    "manifest.json",
    "publish-checklist.md",
    "publish-payload.json",
}
ASCII_TOKEN_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_+-=<>*/\\|^~`#$%&@.:()[]{}")
LINE_START_FORBIDDEN = set("，。！？；：、,.!?;:)]}）】》”’」』")
GITHUB_COVER_KICKER = "Github高星好活儿"
GITHUB_REPO_PATH_RE = re.compile(r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b")
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")


@dataclass
class Fonts:
    title: ImageFont.FreeTypeFont
    headline: ImageFont.FreeTypeFont
    subhead: ImageFont.FreeTypeFont
    body: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render XHS post cards and zip the package.")
    parser.add_argument("spec", type=Path, help="Path to post_spec.json")
    parser.add_argument("--out", type=Path, default=Path("xhs-package"), help="Output directory")
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    return parser.parse_args()


def load_spec(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    slides = data.get("slides")
    caption = data.get("caption", {})
    if not isinstance(slides, list) or not 5 <= len(slides) <= 10:
        raise SystemExit("spec.slides must contain 5-10 slides.")
    if not data.get("title"):
        raise SystemExit("spec.title is required.")
    if not caption.get("body"):
        raise SystemExit("spec.caption.body is required.")
    hashtags = caption.get("hashtags")
    if not isinstance(hashtags, list):
        raise SystemExit("spec.caption.hashtags must contain at least 10 tags.")
    normalized_hashtags: list[str] = []
    seen_hashtags: set[str] = set()
    for tag in hashtags:
        normalized = str(tag).strip().lstrip("#").strip()
        if not normalized or normalized in seen_hashtags:
            continue
        normalized_hashtags.append(normalized)
        seen_hashtags.add(normalized)
    if len(normalized_hashtags) < 10:
        raise SystemExit("spec.caption.hashtags must contain at least 10 non-empty unique tags.")
    caption["hashtags"] = normalized_hashtags
    data["caption"] = caption
    for index, slide in enumerate(slides, start=1):
        if not slide.get("headline"):
            raise SystemExit(f"slides[{index}] requires headline.")
    validate_github_project_cover(data)
    return data


def is_github_project_post(data: dict[str, Any]) -> bool:
    for source in data.get("sources") or []:
        url = str(source.get("url", "")).lower()
        name = str(source.get("name", "")).lower()
        if "github.com" in url or "raw.githubusercontent.com" in url or "github" in name:
            return True
    return False


def validate_github_project_cover(data: dict[str, Any]) -> None:
    if not is_github_project_post(data):
        return
    cover = data["slides"][0]
    if str(cover.get("kicker", "")).strip() != GITHUB_COVER_KICKER:
        raise SystemExit(f'GitHub project cover kicker must be "{GITHUB_COVER_KICKER}".')
    cover_parts = [
        str(cover.get("headline", "")),
        str(cover.get("subhead", "")),
        str(cover.get("footer", "")),
        *(str(bullet) for bullet in cover.get("bullets") or []),
    ]
    cover_text = "\n".join(cover_parts)
    if "github.com" in cover_text.lower() or "raw.githubusercontent.com" in cover_text.lower():
        raise SystemExit("GitHub project cover must not contain repository URLs.")
    if GITHUB_REPO_PATH_RE.search(cover_text):
        raise SystemExit("GitHub project cover must not contain owner/repo paths.")
    bullets = [str(bullet).strip() for bullet in cover.get("bullets") or [] if str(bullet).strip()]
    bullets_text = "\n".join(bullets)
    scenario_bullets = [bullet for bullet in bullets if "适用" in bullet]
    if not scenario_bullets:
        raise SystemExit("GitHub project cover bullets must include a concrete applicable scenario.")
    scenario_text = scenario_bullets[0]
    if len(scenario_text) < 18 or " / " in scenario_text or "/" in scenario_text:
        raise SystemExit("GitHub project applicable scenario must be meaningful, not a compressed slash-separated keyword list.")
    if "Last Update" not in bullets_text or not DATE_RE.search(bullets_text) or "★" not in bullets_text:
        raise SystemExit('GitHub project cover metadata must use "Last Update：YYYY-MM-DD · <stars> ★".')


def hex_to_rgb(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not isinstance(value, str):
        return fallback
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return fallback
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def find_font() -> str | None:
    home = Path.home()
    candidates = [
        str(home / ".local/share/fonts/kami/TsangerJinKai02-W05.ttf"),
        str(home / ".local/share/fonts/kami/TsangerJinKai02-W04.ttf"),
        str(home / ".agents/skills/kami/assets/fonts/TsangerJinKai02-W05.ttf"),
        str(home / ".agents/skills/kami/assets/fonts/TsangerJinKai02-W04.ttf"),
        str(home / "Library/Fonts/TsangerJinKai02-W05.ttf"),
        str(home / "Library/Fonts/TsangerJinKai02-W04.ttf"),
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def make_fonts() -> Fonts:
    font_path = find_font()
    if font_path:
        return Fonts(
            title=ImageFont.truetype(font_path, 56),
            headline=ImageFont.truetype(font_path, 74),
            subhead=ImageFont.truetype(font_path, 37),
            body=ImageFont.truetype(font_path, 39),
            small=ImageFont.truetype(font_path, 28),
        )
    return Fonts(
        title=ImageFont.load_default(),
        headline=ImageFont.load_default(),
        subhead=ImageFont.load_default(),
        body=ImageFont.load_default(),
        small=ImageFont.load_default(),
    )


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def tokenize_for_wrap(text: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            tokens.append(" ")
            index += 1
            continue
        if char in ASCII_TOKEN_CHARS:
            start = index
            index += 1
            while index < len(text) and text[index] in ASCII_TOKEN_CHARS:
                index += 1
            tokens.append(text[start:index])
            continue
        tokens.append(char)
        index += 1
    return tokens


def append_line(lines: list[str], line: str) -> None:
    line = line.strip()
    if not line:
        return
    if lines and line[0] in LINE_START_FORBIDDEN:
        lines[-1] += line[0]
        line = line[1:].lstrip()
        if not line:
            return
    lines.append(line)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for token in tokenize_for_wrap(paragraph):
            if token == " " and not current:
                continue
            test = current + token
            if text_width(draw, test, font) <= max_width or not current:
                current = test
            elif token and token[0] in LINE_START_FORBIDDEN:
                current += token
            else:
                append_line(lines, current)
                current = token.lstrip()
        if current:
            append_line(lines, current)
    return lines


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 12,
    max_lines: int | None = None,
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, font, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip("。,.，、 ") + "..."
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        box = draw.textbbox((x, y), line or " ", font=font)
        y += box[3] - box[1] + line_gap
    return y


def draw_text_block_with_gold_star(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 12,
    max_lines: int | None = None,
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, font, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip("。,.，、 ") + "..."
    for line in lines:
        cursor_x = x
        for segment_index, segment in enumerate(line.split("★")):
            if segment:
                draw.text((cursor_x, y), segment, font=font, fill=fill)
                cursor_x += text_width(draw, segment, font)
            if segment_index < line.count("★"):
                draw.text((cursor_x, y), "★", font=font, fill=GOLD_STAR)
                cursor_x += text_width(draw, "★", font)
        box = draw.textbbox((x, y), line or " ", font=font)
        y += box[3] - box[1] + line_gap
    return y


def text_line_count(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> int:
    return len(wrap_text(draw, text, font, max_width))


def add_warning(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def is_generated_output_file(path: Path) -> bool:
    if path.name in GENERATED_FILES:
        return True
    return path.name.startswith("slide-") and path.suffix.lower() == ".png"


def prepare_output_dir(out_dir: Path, spec_path: Path) -> Path:
    out_dir = out_dir.resolve()
    protected = {Path("/").resolve(), Path.home().resolve(), Path.cwd().resolve(), spec_path.parent.resolve()}
    if out_dir in protected:
        raise SystemExit(f"Refusing to use unsafe output directory: {out_dir}")
    if out_dir.exists():
        if not out_dir.is_dir():
            raise SystemExit(f"Output path exists and is not a directory: {out_dir}")
        unsafe = [path for path in out_dir.rglob("*") if path.is_dir() or not is_generated_output_file(path)]
        if unsafe:
            sample = ", ".join(str(path.relative_to(out_dir)) for path in unsafe[:3])
            raise SystemExit(f"Refusing to delete non-package files in {out_dir}: {sample}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    return out_dir


def fit_headline(
    draw: ImageDraw.ImageDraw,
    font_path: str | None,
    text: str,
    max_width: int,
    target_size: int,
    max_lines: int = 3,
) -> ImageFont.ImageFont:
    if not font_path:
        return ImageFont.load_default()
    size = target_size
    while size >= 48:
        font = ImageFont.truetype(font_path, size)
        if len(wrap_text(draw, text, font, max_width)) <= max_lines:
            return font
        size -= 4
    return ImageFont.truetype(font_path, 48)


def draw_footer(
    draw: ImageDraw.ImageDraw,
    footer: str,
    fonts: Fonts,
    stone: tuple[int, int, int],
    border_soft: tuple[int, int, int],
    accent_soft: tuple[int, int, int],
    width: int,
    height: int,
    max_width: int,
) -> None:
    draw.line((MARGIN, height - 154, width - MARGIN, height - 154), fill=border_soft, width=2)
    draw.line((MARGIN, height - 154, MARGIN + 96, height - 154), fill=accent_soft, width=4)
    draw_text_block(draw, (MARGIN, height - 124), footer, fonts.small, stone, max_width, line_gap=9, max_lines=2)


def theme_rgb(theme: dict[str, Any], key: str, default: str) -> tuple[int, int, int]:
    return hex_to_rgb(theme.get(key, default), hex_to_rgb(default, (0, 0, 0)))


def soften(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(min(255, math.floor(c + (255 - c) * amount)) for c in color)


def text_signal(slide: dict[str, Any]) -> str:
    parts = [str(slide.get("headline", "")), str(slide.get("subhead", "")), str(slide.get("footer", ""))]
    parts.extend(str(item) for item in slide.get("bullets") or [])
    return " ".join(parts)


def infer_sketch_type(slide: dict[str, Any]) -> str:
    text = text_signal(slide)
    keyword_map = [
        (("房间", "收纳", "整理", "家", "桌面", "玄关"), "home"),
        (("清单", "检查", "步骤", "保存", "计划", "行动"), "checklist"),
        (("时间", "小时", "效率", "日程", "周末"), "clock"),
        (("学习", "阅读", "笔记", "考试", "知识"), "book"),
        (("想法", "创意", "灵感", "方法", "原则"), "bulb"),
        (("趋势", "数据", "增长", "变化", "对比"), "chart"),
    ]
    for keywords, sketch_type in keyword_map:
        if any(keyword in text for keyword in keywords):
            return sketch_type
    return "leaf"


def explicit_sketch_type(slide: dict[str, Any]) -> str | None:
    sketch = slide.get("sketch")
    if sketch is None:
        return None
    if isinstance(sketch, str):
        return sketch.strip().lower()
    if isinstance(sketch, dict):
        if sketch.get("enabled") is False:
            return "none"
        value = sketch.get("type", "auto")
        return str(value).strip().lower()
    return None


def select_sketches(spec: dict[str, Any]) -> dict[int, str]:
    options = spec.get("illustrations") or spec.get("illustration") or {}
    if not isinstance(options, dict):
        options = {}
    mode = str(options.get("mode", "off")).lower()
    if mode in {"off", "none", "false"}:
        return {}
    try:
        max_sketches = int(options.get("max_slides", DEFAULT_MAX_SKETCHES))
    except (TypeError, ValueError):
        max_sketches = DEFAULT_MAX_SKETCHES
    max_sketches = max(0, min(max_sketches, len(spec["slides"])))

    selected: dict[int, str] = {}
    explicit_skips: set[int] = set()
    if spec.get("cover_background") or spec["slides"][0].get("cover_background"):
        explicit_skips.add(1)
    for index, slide in enumerate(spec["slides"], start=1):
        sketch_type = explicit_sketch_type(slide)
        if sketch_type in {"none", "off", "false"}:
            explicit_skips.add(index)
            continue
        if sketch_type and sketch_type != "auto" and len(selected) < max_sketches:
            selected[index] = sketch_type

    if len(selected) >= max_sketches:
        return selected

    if mode in {"cover", "cover-only"} and 1 not in explicit_skips:
        selected.setdefault(1, infer_sketch_type(spec["slides"][0]))
        return dict(list(selected.items())[:max_sketches])

    candidates = [1, len(spec["slides"])]
    candidates.extend(range(2, len(spec["slides"])))
    for index in candidates:
        if len(selected) >= max_sketches:
            break
        if index in selected or index in explicit_skips:
            continue
        selected[index] = infer_sketch_type(spec["slides"][index - 1])
    return selected


def sketch_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: tuple[int, int, int],
    width: int = 3,
) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")
    if len(points) >= 2:
        offset_points = [(x + 2, y - 1 if i % 2 == 0 else y + 1) for i, (x, y) in enumerate(points)]
        draw.line(offset_points, fill=fill, width=max(1, width - 1), joint="curve")


def sketch_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=10, outline=fill, width=width)
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 3, y1 - 1, x2 - 2, y2 + 2), radius=10, outline=fill, width=1)


def draw_leaf(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    stem_x = x + size // 2
    sketch_line(draw, [(stem_x, y + size), (stem_x - 6, y + size * 2 // 3), (stem_x, y + size // 3)], color, 3)
    for dx, dy, side in [(-52, 42, -1), (42, 64, 1), (-42, 86, -1), (34, 106, 1)]:
        cx = stem_x + dx
        cy = y + dy
        box = (cx - 34, cy - 18, cx + 34, cy + 18)
        start, end = (210, 35) if side < 0 else (145, 330)
        draw.arc(box, start=start, end=end, fill=color, width=3)
        sketch_line(draw, [(stem_x, cy + 4), (cx, cy)], color, 2)


def draw_checklist(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    sketch_rect(draw, (x + 28, y + 10, x + size - 28, y + size - 8), color, 3)
    for row in range(3):
        yy = y + 48 + row * 48
        sketch_line(draw, [(x + 54, yy), (x + 66, yy + 12), (x + 90, yy - 14)], color, 3)
        sketch_line(draw, [(x + 112, yy), (x + size - 58, yy)], color, 3)


def draw_clock(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    box = (x + 26, y + 26, x + size - 26, y + size - 26)
    draw.ellipse(box, outline=color, width=3)
    draw.ellipse((box[0] + 4, box[1] - 2, box[2] + 2, box[3] + 3), outline=color, width=1)
    cx = x + size // 2
    cy = y + size // 2
    sketch_line(draw, [(cx, cy), (cx, cy - 54)], color, 3)
    sketch_line(draw, [(cx, cy), (cx + 44, cy + 26)], color, 3)
    for tx, ty in [(cx, y + 44), (cx, y + size - 44), (x + 44, cy), (x + size - 44, cy)]:
        draw.ellipse((tx - 3, ty - 3, tx + 3, ty + 3), fill=color)


def draw_book(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    mid = x + size // 2
    top = y + 44
    bottom = y + size - 34
    sketch_line(draw, [(mid, top + 12), (mid, bottom)], color, 3)
    sketch_line(draw, [(mid, top + 12), (x + 40, top), (x + 42, bottom - 10), (mid, bottom)], color, 3)
    sketch_line(draw, [(mid, top + 12), (x + size - 40, top), (x + size - 42, bottom - 10), (mid, bottom)], color, 3)
    for offset in [32, 58]:
        sketch_line(draw, [(x + 64, top + offset), (mid - 22, top + offset + 8)], color, 2)
        sketch_line(draw, [(mid + 22, top + offset + 6), (x + size - 64, top + offset)], color, 2)


def draw_bulb(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    cx = x + size // 2
    draw.arc((cx - 54, y + 34, cx + 54, y + 142), 195, -15, fill=color, width=3)
    sketch_line(draw, [(cx - 34, y + 124), (cx - 22, y + 160), (cx + 22, y + 160), (cx + 34, y + 124)], color, 3)
    for row in range(3):
        sketch_line(draw, [(cx - 30, y + 170 + row * 14), (cx + 30, y + 166 + row * 14)], color, 2)
    for angle in [0, 45, 135, 180]:
        radians = math.radians(angle)
        sx = cx + int(math.cos(radians) * 76)
        sy = y + 92 - int(math.sin(radians) * 76)
        ex = cx + int(math.cos(radians) * 98)
        ey = y + 92 - int(math.sin(radians) * 98)
        sketch_line(draw, [(sx, sy), (ex, ey)], color, 2)


def draw_chart(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    left = x + 34
    bottom = y + size - 34
    sketch_line(draw, [(left, y + 38), (left, bottom), (x + size - 28, bottom)], color, 3)
    points = [
        (left + 20, bottom - 28),
        (left + 66, bottom - 62),
        (left + 112, bottom - 52),
        (left + 160, bottom - 104),
    ]
    sketch_line(draw, points, color, 4)
    for px, py in points:
        draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=color)


def draw_home(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    roof_y = y + 48
    sketch_line(draw, [(x + 34, y + 106), (x + size // 2, roof_y), (x + size - 34, y + 106)], color, 3)
    sketch_rect(draw, (x + 56, y + 104, x + size - 56, y + size - 30), color, 3)
    sketch_rect(draw, (x + 84, y + 142, x + 128, y + 196), color, 2)
    sketch_line(draw, [(x + 152, y + 148), (x + size - 86, y + 148)], color, 3)
    sketch_line(draw, [(x + 152, y + 178), (x + size - 104, y + 178)], color, 2)


def draw_sketch_icon(draw: ImageDraw.ImageDraw, sketch_type: str, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    sketch_type = (sketch_type or "leaf").lower()
    drawers = {
        "leaf": draw_leaf,
        "plant": draw_leaf,
        "checklist": draw_checklist,
        "check": draw_checklist,
        "clock": draw_clock,
        "time": draw_clock,
        "book": draw_book,
        "bulb": draw_bulb,
        "idea": draw_bulb,
        "chart": draw_chart,
        "home": draw_home,
        "house": draw_home,
    }
    drawers.get(sketch_type, draw_leaf)(draw, x, y, size, color)


def resolve_asset_path(path_value: str, asset_root: Path) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return asset_root / path


def normalize_cover_background(spec: dict[str, Any], slide: dict[str, Any]) -> dict[str, Any] | None:
    background = slide.get("cover_background") or spec.get("cover_background")
    if background is None:
        return None
    if isinstance(background, str):
        return {"path": background}
    if isinstance(background, dict):
        if background.get("enabled") is False:
            return None
        return background
    return None


def paste_cover_background(
    image: Image.Image,
    background: dict[str, Any],
    asset_root: Path,
    bounds: tuple[int, int, int, int],
) -> str:
    path_value = background.get("path") or background.get("asset")
    if not path_value:
        return ""
    asset_path = resolve_asset_path(str(path_value), asset_root)
    if not asset_path.exists():
        raise SystemExit(f"cover background asset not found: {asset_path}")

    x1, y1, x2, y2 = bounds
    target_size = (x2 - x1, y2 - y1)
    with Image.open(asset_path) as source:
        cover = source.convert("RGBA")
    cover = ImageOps.fit(cover, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    try:
        blur = float(background.get("blur", 0))
    except (TypeError, ValueError):
        blur = 0
    if blur > 0:
        cover = cover.filter(ImageFilter.GaussianBlur(radius=min(blur, 12)))

    try:
        opacity = float(background.get("opacity", 0.58))
    except (TypeError, ValueError):
        opacity = 0.58
    opacity = max(0.05, min(1.0, opacity))
    alpha = cover.getchannel("A").point(lambda value: int(value * opacity))
    cover.putalpha(alpha)

    mask = Image.new("L", target_size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, target_size[0], target_size[1]), radius=CARD_RADIUS, fill=255)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay.paste(cover, (x1, y1), mask)
    image.alpha_composite(overlay)

    try:
        wash = int(background.get("wash", 72))
    except (TypeError, ValueError):
        wash = 72
    wash = max(0, min(255, wash))
    if wash:
        wash_layer = Image.new("RGBA", target_size, (250, 249, 245, wash))
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay.paste(wash_layer, (x1, y1), mask)
        image.alpha_composite(overlay)

    try:
        text_wash = int(background.get("text_wash", 136))
    except (TypeError, ValueError):
        text_wash = 136
    text_wash = max(0, min(255, text_wash))
    if text_wash:
        text_safe = Image.new("RGBA", image.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_safe)
        text_draw.rounded_rectangle(
            (x1 + 20, y1 + 108, x2 - 20, y1 + 735),
            radius=36,
            fill=(250, 249, 245, text_wash),
        )
        image.alpha_composite(text_safe)
    return str(path_value)


def render_slide(
    slide: dict[str, Any],
    index: int,
    total: int,
    spec: dict[str, Any],
    out_path: Path,
    width: int,
    height: int,
    sketch_type: str | None = None,
    asset_root: Path | None = None,
) -> None:
    theme = spec.get("theme", {})
    bg = theme_rgb(theme, "background", KAMI_PARCHMENT)
    card = theme_rgb(theme, "card", KAMI_IVORY)
    accent = theme_rgb(theme, "accent", KAMI_BRAND)
    if theme.get("tag_bg"):
        tag_bg = theme_rgb(theme, "tag_bg", KAMI_TAG_BG)
    elif theme.get("accent"):
        tag_bg = soften(accent, 0.9)
    else:
        tag_bg = hex_to_rgb(KAMI_TAG_BG, (238, 242, 247))
    text = theme_rgb(theme, "text", KAMI_NEAR_BLACK)
    muted = theme_rgb(theme, "muted", KAMI_OLIVE)
    stone = theme_rgb(theme, "stone", KAMI_STONE)
    border = theme_rgb(theme, "border", KAMI_BORDER)
    border_soft = theme_rgb(theme, "border_soft", KAMI_BORDER_SOFT)
    accent_soft = soften(accent, 0.86)

    image = Image.new("RGBA", (width, height), bg + (255,))
    draw = ImageDraw.Draw(image)
    fonts = make_fonts()
    font_path = find_font()

    # Warm paper panel, tuned to Kami's restrained editorial rhythm.
    panel_bounds = (48, 48, width - 48, height - 48)
    draw.rounded_rectangle(
        panel_bounds,
        radius=CARD_RADIUS,
        fill=card,
        outline=border,
        width=2,
    )
    if index == 1 and asset_root:
        cover_background = normalize_cover_background(spec, slide)
        if cover_background:
            rendered_background = paste_cover_background(image, cover_background, asset_root, panel_bounds)
            if rendered_background:
                slide["_cover_background"] = rendered_background

    kicker = str(slide.get("kicker") or f"{index:02d}")
    footer = str(slide.get("footer") or spec.get("author") or spec.get("title"))
    max_width = width - MARGIN * 2
    warnings = slide.setdefault("_warnings", [])
    if index == 1:
        draw.text((MARGIN, 94), kicker[:12], font=fonts.small, fill=accent)
        draw.line((MARGIN, 128, MARGIN + 112, 128), fill=accent_soft, width=4)
        draw.text((width - 136, 88), f"{index}/{total}", font=fonts.small, fill=stone)

        y = 190
        cover_x = MARGIN
        cover_width = width - (MARGIN * 2)
        headline = str(slide["headline"])
        headline_font = fit_headline(draw, font_path, headline, cover_width, 132, max_lines=4)
        if getattr(headline_font, "size", 0) <= 64:
            add_warning(warnings, "cover headline had to shrink near the minimum size")
        if text_line_count(draw, headline, headline_font, cover_width) > 4:
            add_warning(warnings, "cover headline exceeds 4 lines and was truncated")
        y = draw_text_block(draw, (cover_x, y), headline, headline_font, text, cover_width, line_gap=18, max_lines=4)

        subhead = slide.get("subhead")
        if subhead:
            y += 26
            if text_line_count(draw, str(subhead), fonts.subhead, cover_width) > 2:
                add_warning(warnings, "cover subhead exceeds 2 lines and was truncated")
            y = draw_text_block(draw, (cover_x, y), str(subhead), fonts.subhead, muted, cover_width, line_gap=13, max_lines=2)

        bullets = slide.get("bullets") or []
        if bullets:
            if len(bullets) > 3:
                add_warning(warnings, "cover has more than 3 bullets; extra bullets were omitted")
            info_bottom = height - 178
            rendered_bullets = [str(bullet).strip() for bullet in bullets[:3] if str(bullet).strip()]
            body_box = draw.textbbox((0, 0), "Hg", font=fonts.body)
            body_line_height = body_box[3] - body_box[1] + 18
            needed_height = 112
            for bullet_text in rendered_bullets:
                needed_height += min(text_line_count(draw, bullet_text, fonts.body, cover_width - 64), 2) * body_line_height + 10
            info_top = max(y + 40, info_bottom - max(240, needed_height))
            if info_top < y + 36:
                add_warning(warnings, "cover title block is too close to the info panel")
            if info_bottom - info_top < 190:
                add_warning(warnings, "cover info panel has limited vertical space")
            info_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            info_draw = ImageDraw.Draw(info_layer)
            info_draw.rounded_rectangle(
                (MARGIN, info_top, width - MARGIN, info_bottom),
                radius=28,
                fill=(250, 249, 245, 188),
            )
            image.alpha_composite(info_layer)
            draw = ImageDraw.Draw(image)
            y = info_top + 38
            for bullet_text in rendered_bullets:
                if text_line_count(draw, bullet_text, fonts.body, cover_width - 64) > 2:
                    add_warning(warnings, "cover bullet exceeds 2 lines and was truncated")
                dot_y = y + 22
                draw.ellipse((cover_x + 10, dot_y, cover_x + 20, dot_y + 10), fill=accent)
                y = draw_text_block_with_gold_star(
                    draw,
                    (cover_x + 40, y),
                    bullet_text,
                    fonts.body,
                    text,
                    cover_width - 64,
                    line_gap=18,
                    max_lines=2,
                )
                y += 10
                if y > info_bottom - 48:
                    add_warning(warnings, "cover bullets overflowed the info panel; later bullets may be hidden")
                    break

        draw.text((MARGIN, height - 118), footer, font=fonts.small, fill=stone)
        image.convert("RGB").save(out_path, "PNG")
        return

    draw.rounded_rectangle((72, 72, 170, 120), radius=12, fill=tag_bg)
    draw.text((121, 96), kicker[:4], font=fonts.small, anchor="mm", fill=accent)
    draw.text((width - 136, 88), f"{index}/{total}", font=fonts.small, fill=stone)

    y = 184
    headline_x = MARGIN + 30
    headline_width = max_width - 30
    headline = str(slide["headline"])
    headline_font = fit_headline(draw, font_path, headline, headline_width, 74)
    if getattr(headline_font, "size", 0) <= 48:
        add_warning(warnings, "slide headline had to shrink to the minimum size")
    if text_line_count(draw, headline, headline_font, headline_width) > 3:
        add_warning(warnings, "slide headline exceeds 3 lines and was truncated")
    draw.rounded_rectangle((MARGIN, y + 12, MARGIN + 7, y + 132), radius=3, fill=accent)
    y = draw_text_block(draw, (headline_x, y), headline, headline_font, text, headline_width, line_gap=16, max_lines=3)

    subhead = slide.get("subhead")
    if subhead:
        y += 26
        if text_line_count(draw, str(subhead), fonts.subhead, headline_width) > 3:
            add_warning(warnings, "slide subhead exceeds 3 lines and was truncated")
        y = draw_text_block(draw, (headline_x, y), str(subhead), fonts.subhead, muted, headline_width, line_gap=13, max_lines=3)

    bullets = slide.get("bullets") or []
    if bullets:
        if len(bullets) > 5:
            add_warning(warnings, "slide has more than 5 bullets; extra bullets were omitted")
        y += 64
        for bullet_index, bullet in enumerate(bullets[:5], start=1):
            bullet_text = str(bullet).strip()
            if not bullet_text:
                continue
            if text_line_count(draw, bullet_text, fonts.body, max_width - 60) > 3:
                add_warning(warnings, f"slide bullet {bullet_index} exceeds 3 lines and was truncated")
            draw.text((MARGIN + 2, y), "–", font=fonts.body, fill=accent)
            y = draw_text_block(
                draw,
                (MARGIN + 48, y),
                bullet_text,
                fonts.body,
                text,
                max_width - 60,
                line_gap=18,
                max_lines=3,
            )
            y += 24
            if y > height - 230:
                add_warning(warnings, "slide content overflowed; later bullets may be hidden")
                break

    if sketch_type and y < height - 430:
        sketch_size = 220
        sketch_x = width - MARGIN - sketch_size - 8
        sketch_y = max(y + 38, height - 540)
        if sketch_y + sketch_size < height - 176:
            draw_sketch_icon(draw, sketch_type, sketch_x, sketch_y, sketch_size, soften(accent, 0.52))

    draw_footer(draw, footer, fonts, stone, border_soft, accent_soft, width, height, max_width)

    image.convert("RGB").save(out_path, "PNG")


def write_caption(spec: dict[str, Any], out_dir: Path) -> None:
    caption = spec.get("caption", {})
    hashtags = caption.get("hashtags") or []
    tag_line = " ".join(f"#{str(tag).lstrip('#')}" for tag in hashtags)
    content = [
        f"# {spec['title']}",
        "",
        str(caption.get("body", "")).strip(),
        "",
        tag_line,
        "",
    ]
    (out_dir / "caption.md").write_text("\n".join(content), encoding="utf-8")


def write_checklist(spec: dict[str, Any], out_dir: Path) -> None:
    items = [
        "# 小红书手工发布检查清单",
        "",
        "- 按文件名顺序上传图片：slide-01.png、slide-02.png、...",
        "- 从 caption.md 粘贴标题、正文和话题标签。",
        "- 如使用半自动发布辅助，只允许填充草稿；最终发布按钮必须由用户手动确认。",
        "- 检查话题标签是否准确，删掉不贴题的标签。",
        "- 发布前用手机预览每一页，确认文字没有被裁切。",
        "- 复核事实、名称、价格、日期、截图和引用来源。",
        "- 未验证前，不暗示官方背书、确定收益或平台保证。",
        "",
        f"图片数量：{len(spec['slides'])}",
    ]
    (out_dir / "publish-checklist.md").write_text("\n".join(items) + "\n", encoding="utf-8")


def write_publish_payload(spec: dict[str, Any], out_dir: Path, image_names: list[str]) -> None:
    caption = spec.get("caption", {})
    payload = {
        "mode": "manual-or-publish-assist",
        "policy": {
            "allowed": [
                "open official Xiaohongshu creator page",
                "upload slide images in order",
                "fill title, body, and hashtags into a draft",
            ],
            "stop_before": [
                "final publish button",
                "schedule/submit confirmation",
                "captcha, QR login, SMS, or device verification",
            ],
        },
        "title": spec["title"],
        "body": str(caption.get("body", "")).strip(),
        "hashtags": [str(tag).lstrip("#") for tag in caption.get("hashtags") or []],
        "images": [
            {
                "name": name,
                "path": str((out_dir / name).resolve()),
            }
            for name in image_names
        ],
        "caption_file": str((out_dir / "caption.md").resolve()),
        "creator_url": "https://creator.xiaohongshu.com/",
    }
    (out_dir / "publish-payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_manifest(spec: dict[str, Any], image_names: list[str], sketch_map: dict[int, str]) -> dict[str, Any]:
    visuals = {}
    warnings = {}
    for index, slide in enumerate(spec["slides"], start=1):
        image_name = f"slide-{index:02d}.png"
        if slide.get("_cover_background"):
            cover_background = normalize_cover_background(spec, slide) or {}
            visual_entry = {"type": "cover_background", "value": slide["_cover_background"]}
            for key in ("prompt", "art_direction", "accepted_asset", "rejected_assets", "rejection_reason"):
                if cover_background.get(key):
                    visual_entry[key] = cover_background[key]
            visuals[image_name] = visual_entry
        elif index in sketch_map:
            visuals[image_name] = {"type": "sketch", "value": sketch_map[index]}
        if slide.get("_warnings"):
            warnings[image_name] = slide["_warnings"]
    return {
        "title": spec["title"],
        "subtitle": spec.get("subtitle", ""),
        "author": spec.get("author", ""),
        "sources": spec.get("sources", []),
        "images": image_names,
        "caption_file": "caption.md",
        "checklist_file": "publish-checklist.md",
        "publish_payload_file": "publish-payload.json",
        "alt_text": [slide.get("alt") or slide.get("headline") for slide in spec["slides"]],
        "visuals": visuals,
        "warnings": warnings,
    }


def zip_dir(out_dir: Path) -> Path:
    zip_path = out_dir.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(out_dir))
    return zip_path


def main() -> None:
    args = parse_args()
    spec = load_spec(args.spec)
    out_dir = prepare_output_dir(args.out, args.spec)

    image_names: list[str] = []
    total = len(spec["slides"])
    sketch_map = select_sketches(spec)
    for index, slide in enumerate(spec["slides"], start=1):
        name = f"slide-{index:02d}.png"
        render_slide(slide, index, total, spec, out_dir / name, args.width, args.height, sketch_map.get(index), args.spec.parent)
        image_names.append(name)

    write_caption(spec, out_dir)
    write_checklist(spec, out_dir)
    write_publish_payload(spec, out_dir, image_names)
    manifest = build_manifest(spec, image_names, sketch_map)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = zip_dir(out_dir)

    print(json.dumps({"out_dir": str(out_dir), "zip": str(zip_path), "images": image_names}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
