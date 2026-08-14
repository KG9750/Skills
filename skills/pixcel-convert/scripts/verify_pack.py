#!/usr/bin/env python3
"""Verify a Pixcel Convert pack and optionally load it with Godot."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path


FORBIDDEN_SUFFIXES = {".ctex", ".import", ".pyc"}
UID_RE = re.compile(r"^uid://[a-z0-9]+$")


ANIMATION_RE = re.compile(
    r'\{\n"frames": \[(.*?)\],\n"loop": (true|false),\n'
    r'"name": &"([^"]+)",\n"speed": ([^\n]+)\n\}',
    re.DOTALL,
)
SPRITEFRAMES_ATLAS_PATH_RE = re.compile(
    r'^\[ext_resource type="Texture2D" path="([^"]+)" id="1_atlas"\]$',
    re.MULTILINE,
)
ATLAS_TEXTURE_RE = re.compile(
    r'^\[sub_resource type="AtlasTexture" id="([^"]+)"\]\n'
    r'atlas = ExtResource\("([^"]+)"\)\n'
    r'region = Rect2\((-?\d+), (-?\d+), (-?\d+), (-?\d+)\)$',
    re.MULTILINE,
)


def parse_spriteframes(text: str, label: str) -> dict[str, dict]:
    animations: dict[str, dict] = {}
    for frame_text, loop, name, speed in ANIMATION_RE.findall(text):
        if name in animations:
            raise ValueError(f"SpriteFrames has duplicate animation name: {label}/{name}")
        animations[name] = {
            "frame_count": frame_text.count('"texture":'),
            "frame_resources": re.findall(r'SubResource\("([^"]+)"\)', frame_text),
            "loop": loop == "true",
            "fps": float(speed),
        }
    if not animations:
        raise ValueError(f"SpriteFrames has no readable animations: {label}")
    return animations


def parse_atlas_textures(text: str, label: str) -> tuple[str, dict[str, dict[str, object]]]:
    path_match = SPRITEFRAMES_ATLAS_PATH_RE.search(text)
    if path_match is None:
        raise ValueError(f"SpriteFrames atlas path is missing: {label}")
    textures: dict[str, dict[str, object]] = {}
    for sub_id, atlas_id, x, y, width, height in ATLAS_TEXTURE_RE.findall(text):
        if sub_id in textures:
            raise ValueError(f"SpriteFrames has duplicate AtlasTexture id: {label}/{sub_id}")
        textures[sub_id] = {
            "atlas_id": atlas_id,
            "region": [int(x), int(y), int(width), int(height)],
        }
    return path_match.group(1), textures


def verify_contact_points(value: dict, canvas: list[int], label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    for name, point in value.items():
        if (
            not isinstance(name, str)
            or not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in point)
        ):
            raise ValueError(f"{label} contains an invalid contact point")
        if not (0 <= point[0] < canvas[0] and 0 <= point[1] < canvas[1]):
            raise ValueError(f"{label}.{name} is outside the asset canvas")


def verify_asset_contract(asset: dict) -> None:
    canvas = asset.get("canvas")
    anchor = asset.get("anchor")
    if (
        not isinstance(canvas, list)
        or len(canvas) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in canvas)
    ):
        raise ValueError(f"{asset['id']} canvas must contain two positive integers")
    if (
        not isinstance(anchor, list)
        or len(anchor) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in anchor)
        or not (0 <= anchor[0] < canvas[0] and 0 <= anchor[1] < canvas[1])
    ):
        raise ValueError(f"{asset['id']} anchor must be inside the asset canvas")
    occupancy = asset.get("occupancy")
    if (
        not isinstance(occupancy, list)
        or len(occupancy) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in occupancy)
    ):
        raise ValueError(f"{asset['id']} occupancy must contain two positive integers")
    directions = asset.get("directions", [])
    if not isinstance(directions, list) or not all(isinstance(value, str) for value in directions):
        raise ValueError(f"{asset['id']} directions must be a list of strings")
    if len(directions) != len(set(directions)):
        raise ValueError(f"{asset['id']} directions must be unique")
    sprite_offset = asset.get("sprite_offset")
    if (
        not isinstance(sprite_offset, list)
        or len(sprite_offset) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in sprite_offset)
    ):
        raise ValueError(f"{asset['id']} sprite_offset must contain two integers")
    tileset_coordinates = asset.get("tileset_atlas_coordinates")
    if (
        not isinstance(tileset_coordinates, list)
        or len(tileset_coordinates) != 2
        or not all(
            isinstance(item, int) and not isinstance(item, bool) and item >= 0
            for item in tileset_coordinates
        )
    ):
        raise ValueError(f"{asset['id']} tileset_atlas_coordinates must contain two non-negative integers")
    verify_contact_points(asset.get("contact_points", {}), asset["canvas"], f"{asset['id']} contact_points")
    collision = asset.get("collision_polygon")
    if collision is not None and (
        not isinstance(collision, list)
        or len(collision) < 3
        or not all(
            isinstance(point, list)
            and len(point) == 2
            and all(isinstance(item, int) and not isinstance(item, bool) for item in point)
            for point in collision
        )
    ):
        raise ValueError(f"{asset['id']} collision_polygon must contain at least three integer [x, y] points")
    animations = asset.get("animations")
    if not isinstance(animations, dict) or not animations:
        raise ValueError(f"{asset['id']} animations must be a non-empty object")
    for animation_name, animation in animations.items():
        if not isinstance(animation, dict):
            raise ValueError(f"{asset['id']}/{animation_name} animation must be an object")
        frames = animation.get("frames")
        if not isinstance(frames, list) or not frames:
            raise ValueError(f"{asset['id']}/{animation_name} frames must be a non-empty list")
        for index, frame in enumerate(frames):
            label = f"{asset['id']}/{animation_name} frame[{index}]"
            if not isinstance(frame, dict):
                raise ValueError(f"{label} must be an object")
            if not isinstance(frame.get("path"), str) or not frame["path"]:
                raise ValueError(f"{label} path must be a non-empty string")
            atlas_index = frame.get("atlas_index")
            if not isinstance(atlas_index, int) or isinstance(atlas_index, bool) or atlas_index < 0:
                raise ValueError(f"{label} atlas_index must be a non-negative integer")
            atlas_coordinates = frame.get("atlas_coordinates")
            if (
                not isinstance(atlas_coordinates, list)
                or len(atlas_coordinates) != 2
                or not all(
                    isinstance(item, int) and not isinstance(item, bool) and item >= 0
                    for item in atlas_coordinates
                )
            ):
                raise ValueError(f"{label} atlas_coordinates must contain two non-negative integers")
            placement = frame.get("placement")
            if (
                not isinstance(placement, list)
                or len(placement) != 2
                or not all(isinstance(item, int) and not isinstance(item, bool) for item in placement)
            ):
                raise ValueError(f"{label} placement must contain two integers")
        if not isinstance(animation.get("loop"), bool):
            raise ValueError(f"{asset['id']}/{animation_name} loop must be a boolean")
        direction = animation.get("direction")
        if direction is not None and direction not in directions:
            raise ValueError(f"{asset['id']}/{animation_name} direction is not declared")
        contact_points = animation.get("contact_points")
        if contact_points is None:
            continue
        if isinstance(contact_points, list):
            if len(contact_points) != len(animation["frames"]):
                raise ValueError(f"{asset['id']}/{animation_name} contact points do not match frame count")
            for index, points in enumerate(contact_points):
                verify_contact_points(
                    points,
                    asset["canvas"],
                    f"{asset['id']}/{animation_name} contact_points[{index}]",
                )
        else:
            verify_contact_points(
                contact_points,
                asset["canvas"],
                f"{asset['id']}/{animation_name} contact_points",
            )


def verify_image(
    image: Image.Image,
    palette: set[tuple[int, int, int]],
    label: str,
    expected_size: tuple[int, int] | None = None,
) -> None:
    rgba = image.convert("RGBA")
    if expected_size is not None and rgba.size != expected_size:
        raise ValueError(f"{label} size is {rgba.size}, expected {expected_size}")
    colors = rgba.getcolors(maxcolors=65536)
    if colors is None:
        raise ValueError(f"{label} has too many colors")
    alpha = {color[3] for _, color in colors}
    if not alpha <= {0, 255} or 255 not in alpha:
        raise ValueError(f"{label} is not hard-alpha RGBA")
    opaque = {color[:3] for _, color in colors if color[3] == 255}
    if not opaque <= palette:
        raise ValueError(f"{label} contains colors outside the manifest palette")


def clean_import_cache(pack: Path) -> None:
    cache = pack / ".godot"
    if cache.exists():
        shutil.rmtree(cache)
    for path in pack.rglob("*"):
        if path.is_file() and path.suffix in {".import", ".ctex"}:
            path.unlink()


def collect_uid_sidecars(pack: Path) -> list[str]:
    sidecars: list[str] = []
    for path in sorted(pack.rglob("*.gd.uid")):
        script = Path(str(path)[:-4])
        if not script.is_file():
            raise ValueError(f"orphan Godot UID sidecar: {path.relative_to(pack)}")
        value = path.read_text(encoding="utf-8").strip()
        if UID_RE.fullmatch(value) is None:
            raise ValueError(f"invalid Godot UID sidecar: {path.relative_to(pack)}")
        sidecars.append(path.relative_to(pack).as_posix())
    return sidecars


def record_uid_sidecars(pack: Path) -> list[str]:
    sidecars = collect_uid_sidecars(pack)
    manifest_path = pack / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["godot_uid_sidecars"] = sidecars
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sidecars


def verify_sources(pack: Path) -> tuple[dict, int]:
    for relative in ("project.godot", "demo/main.tscn", "demo/main.gd"):
        if not (pack / relative).is_file():
            raise ValueError(f"required pack file is missing: {relative}")
    manifest = json.loads((pack / "asset_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("asset manifest must be a JSON object")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets or not all(isinstance(asset, dict) for asset in assets):
        raise ValueError("asset manifest assets must be a non-empty list of objects")
    declared_uid_sidecars = manifest.get("godot_uid_sidecars", [])
    if not isinstance(declared_uid_sidecars, list) or not all(
        isinstance(path, str) for path in declared_uid_sidecars
    ):
        raise ValueError("godot_uid_sidecars must be a list of paths")
    actual_uid_sidecars = collect_uid_sidecars(pack)
    if declared_uid_sidecars != actual_uid_sidecars:
        raise ValueError("Godot UID sidecars differ from the manifest")
    asset_ids = [asset.get("id") for asset in assets]
    if not all(isinstance(asset_id, str) and asset_id for asset_id in asset_ids):
        raise ValueError("every manifest asset must have a non-empty string id")
    duplicates = sorted({asset_id for asset_id in asset_ids if asset_ids.count(asset_id) > 1})
    if duplicates:
        raise ValueError("duplicate asset id in manifest: " + ", ".join(duplicates))
    raw_palette = manifest.get("palette")
    if not isinstance(raw_palette, list) or not raw_palette or not all(
        isinstance(value, str) for value in raw_palette
    ):
        raise ValueError("manifest palette must be a non-empty list of hex strings")
    try:
        palette = {tuple(bytes.fromhex(value)) for value in raw_palette}
    except ValueError as exc:
        raise ValueError("manifest palette contains an invalid RGB hex color") from exc
    atlas_manifest = manifest.get("atlas")
    if not isinstance(atlas_manifest, dict):
        raise ValueError("manifest atlas must be an object")
    atlas_relative_path = atlas_manifest.get("path")
    if not isinstance(atlas_relative_path, str) or not atlas_relative_path:
        raise ValueError("manifest atlas path must be a non-empty string")
    atlas_size = atlas_manifest.get("size")
    if (
        not isinstance(atlas_size, list)
        or len(atlas_size) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in atlas_size)
    ):
        raise ValueError("manifest atlas size must contain two positive integers")
    atlas_cell = atlas_manifest.get("cell")
    if (
        not isinstance(atlas_cell, list)
        or len(atlas_cell) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in atlas_cell)
    ):
        raise ValueError("manifest atlas cell must contain two positive integers")
    atlas_anchor = atlas_manifest.get("anchor")
    if (
        not isinstance(atlas_anchor, list)
        or len(atlas_anchor) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in atlas_anchor)
    ):
        raise ValueError("manifest atlas anchor must contain two non-negative integers")
    tileset_path = manifest.get("tileset")
    if not isinstance(tileset_path, str) or not tileset_path:
        raise ValueError("manifest tileset must be a non-empty path string")
    grid = manifest.get("grid")
    if (
        not isinstance(grid, list)
        or len(grid) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in grid)
    ):
        raise ValueError("manifest grid must contain two positive integers")
    atlas = Image.open(pack / atlas_relative_path).convert("RGBA")
    if list(atlas.size) != atlas_size:
        raise ValueError("atlas size does not match manifest")
    cell_w, cell_h = atlas_cell
    atlas_anchor_x, atlas_anchor_y = atlas_anchor
    grid_w, grid_h = grid
    for asset in manifest["assets"]:
        verify_asset_contract(asset)
    expected_anchor = [
        max(asset["anchor"][0] for asset in manifest["assets"]),
        max(asset["anchor"][1] for asset in manifest["assets"]),
    ]
    expected_cell = [
        math.ceil(
            (expected_anchor[0] + max(asset["canvas"][0] - asset["anchor"][0] for asset in manifest["assets"]))
            / grid_w
        ) * grid_w,
        math.ceil(
            (expected_anchor[1] + max(asset["canvas"][1] - asset["anchor"][1] for asset in manifest["assets"]))
            / grid_h
        ) * grid_h,
    ]
    if manifest["atlas"]["anchor"] != expected_anchor:
        raise ValueError("atlas anchor differs from asset anchor geometry")
    if manifest["atlas"]["cell"] != expected_cell:
        raise ValueError("atlas cell differs from asset anchor geometry")
    if list(atlas.size) != [cell_w * sum(
        len(animation["frames"])
        for asset in manifest["assets"]
        for animation in asset["animations"].values()
    ), cell_h]:
        raise ValueError("atlas dimensions differ from declared frame count and cell")
    demo_text = (pack / "demo" / "main.gd").read_text(encoding="utf-8")
    expected_offsets = ", ".join(
        f"Vector2({asset['sprite_offset'][0]}, {asset['sprite_offset'][1]})"
        for asset in manifest["assets"]
    )
    if f"const SPRITE_OFFSETS := [{expected_offsets}]" not in demo_text:
        raise ValueError("demo sprite offset values differ from the manifest")
    for asset in manifest["assets"]:
        if asset.get("tileset_animation") not in asset.get("animations", {}):
            raise ValueError(f"{asset['id']} tileset_animation does not exist")
    has_multiframe_default = any(
        len(asset["animations"][asset["tileset_animation"]]["frames"]) > 1
        for asset in manifest["assets"]
    )
    if has_multiframe_default and (
        "sprite.play(DEFAULT_ANIMATIONS[index])" not in demo_text
        or "sprite.is_playing()" not in demo_text
    ):
        raise ValueError("demo playback is not enabled and checked for a multiframe default animation")
    frame_count = 0
    declared_frames: set[str] = set()
    for asset in manifest["assets"]:
        tileset_animation = asset.get("tileset_animation")
        if tileset_animation not in asset["animations"]:
            raise ValueError(f"{asset['id']} tileset_animation does not exist")
        sprite_frames = pack / "resources" / f"{asset['id']}_sprite_frames.tres"
        text = sprite_frames.read_text(encoding="utf-8")
        actual_animations = parse_spriteframes(text, asset["id"])
        spriteframes_atlas_path, atlas_textures = parse_atlas_textures(text, asset["id"])
        expected_atlas_path = "res://" + atlas_relative_path
        if spriteframes_atlas_path != expected_atlas_path:
            raise ValueError(f"SpriteFrames atlas path differs for {asset['id']}")
        expected_texture_ids = {
            f"AtlasTexture_{record['atlas_index']}"
            for animation in asset["animations"].values()
            for record in animation["frames"]
        }
        if set(atlas_textures) != expected_texture_ids:
            raise ValueError(f"SpriteFrames AtlasTexture resources differ for {asset['id']}")
        expected_offset = [cell_w // 2 - atlas_anchor_x, cell_h // 2 - atlas_anchor_y]
        if asset.get("sprite_offset") != expected_offset:
            raise ValueError(f"manifest sprite offset differs for {asset['id']}")
        if set(actual_animations) != set(asset["animations"]):
            raise ValueError(f"SpriteFrames animation names differ for {asset['id']}")
        for animation_name, animation in asset["animations"].items():
            actual = actual_animations[animation_name]
            raw_fps = animation.get("fps")
            if not isinstance(raw_fps, (int, float)) or isinstance(raw_fps, bool):
                raise ValueError(
                    f"manifest animation fps must be a number: {asset['id']}/{animation_name}"
                )
            fps = float(raw_fps)
            if not math.isfinite(fps) or fps <= 0:
                raise ValueError(f"manifest animation fps must be finite and greater than zero: {asset['id']}/{animation_name}")
            if not math.isfinite(actual["fps"]):
                raise ValueError(f"SpriteFrames animation fps must be finite: {asset['id']}/{animation_name}")
            if not math.isclose(actual["fps"], fps, rel_tol=0.0, abs_tol=1e-6):
                raise ValueError(f"SpriteFrames animation fps differs for {asset['id']}/{animation_name}")
            if actual["loop"] is not bool(animation["loop"]):
                raise ValueError(f"SpriteFrames animation loop differs for {asset['id']}/{animation_name}")
            if actual["frame_count"] != len(animation["frames"]):
                raise ValueError(f"SpriteFrames animation frame count differs for {asset['id']}/{animation_name}")
            expected_resources = [f"AtlasTexture_{record['atlas_index']}" for record in animation["frames"]]
            if actual["frame_resources"] != expected_resources:
                raise ValueError(f"SpriteFrames frame resources differ for {asset['id']}/{animation_name}")
            for record, resource_id in zip(animation["frames"], expected_resources):
                frame_count += 1
                declared_frames.add(record["path"].removeprefix("res://"))
                frame = Image.open(pack / record["path"].removeprefix("res://")).convert("RGBA")
                verify_image(frame, palette, record["path"], tuple(asset["canvas"]))
                x, y = record["atlas_coordinates"]
                expected_placement = [atlas_anchor_x - asset["anchor"][0], atlas_anchor_y - asset["anchor"][1]]
                if record.get("placement") != expected_placement:
                    raise ValueError(f"manifest frame placement differs for {asset['id']}/{animation_name}")
                atlas_texture = atlas_textures.get(resource_id)
                if atlas_texture is None or atlas_texture["atlas_id"] != "1_atlas":
                    raise ValueError(f"SpriteFrames atlas reference differs for {asset['id']}/{animation_name}")
                expected_region = [x * cell_w, y * cell_h, cell_w, cell_h]
                if atlas_texture["region"] != expected_region:
                    raise ValueError(f"SpriteFrames atlas region differs for {asset['id']}/{animation_name}")
                placement_x, placement_y = record["placement"]
                expected = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
                expected.alpha_composite(frame, (placement_x, placement_y))
                actual = atlas.crop((x * cell_w, y * cell_h, (x + 1) * cell_w, (y + 1) * cell_h))
                if actual.tobytes() != expected.tobytes():
                    raise ValueError(f"atlas cell differs from {record['path']}")

    tileset = (pack / tileset_path).read_text(encoding="utf-8")
    expected_atlas_path = "res://" + atlas_relative_path
    if f'path="{expected_atlas_path}" id="1_atlas"' not in tileset:
        raise ValueError("TileSet atlas path differs from the manifest")
    if f"texture_region_size = Vector2i({cell_w}, {cell_h})" not in tileset:
        raise ValueError("TileSet texture region size differs from the manifest")
    if f"tile_size = Vector2i({grid_w}, {grid_h})" not in tileset:
        raise ValueError("TileSet tile size differs from the manifest")
    expected_origin = (
        atlas_anchor_x - cell_w // 2,
        (cell_h - grid_h) // 2 - (cell_h - atlas_anchor_y),
    )
    for asset in manifest["assets"]:
        x, y = asset["tileset_atlas_coordinates"]
        coordinate = re.escape(f"{x}:{y}")
        if re.search(rf"^{coordinate}/0 = 0$", tileset, re.MULTILINE) is None:
            raise ValueError(f"TileSet is missing {asset['id']}")
        expected_origin_line = re.escape(
            f"{x}:{y}/0/texture_origin = Vector2i({expected_origin[0]}, {expected_origin[1]})"
        )
        if re.search(rf"^{expected_origin_line}$", tileset, re.MULTILINE) is None:
            raise ValueError(f"TileSet texture origin differs for {asset['id']}")
        collision_count = len(
            re.findall(
                rf"^{x}:{y}/0/physics_layer_0/polygon_\d+/points =",
                tileset,
                re.MULTILINE,
            )
        )
        expected_collision_count = 1 if asset.get("collision_polygon") else 0
        if collision_count != expected_collision_count:
            raise ValueError(f"TileSet collision polygon count differs for {asset['id']}")
        if asset.get("collision_polygon"):
            expected_points = ", ".join(
                f"{int(px)}, {int(py)}" for px, py in asset["collision_polygon"]
            )
            expected_collision_line = re.escape(
                f"{x}:{y}/0/physics_layer_0/polygon_0/points = PackedVector2Array({expected_points})"
            )
            if re.search(rf"^{expected_collision_line}$", tileset, re.MULTILINE) is None:
                raise ValueError(f"TileSet collision polygon differs for {asset['id']}")

    expected_generated = declared_frames | {
        atlas_relative_path,
        tileset_path,
        *(f"resources/{asset['id']}_sprite_frames.tres" for asset in manifest["assets"]),
    }
    generated_patterns = (
        "sprites/frames/**/*.png",
        "sprites/*_atlas.png",
        "resources/*_tileset.tres",
        "resources/*_sprite_frames.tres",
    )
    actual_generated = {
        path.relative_to(pack).as_posix()
        for pattern in generated_patterns
        for path in pack.glob(pattern)
        if path.is_file()
    }
    undeclared = sorted(actual_generated - expected_generated)
    if undeclared:
        raise ValueError("undeclared generated file: " + ", ".join(undeclared))
    return manifest, frame_count


def verify_no_delivery_cache(pack: Path) -> None:
    forbidden: list[Path] = []
    if (pack / ".godot").exists():
        forbidden.append(pack / ".godot")
    for path in pack.rglob("*"):
        if path.is_file() and path.suffix in FORBIDDEN_SUFFIXES:
            forbidden.append(path)
        if path.is_dir() and path.name == "__pycache__":
            forbidden.append(path)
    if forbidden:
        raise ValueError("delivery contains generated cache: " + ", ".join(str(path) for path in forbidden))


def run_godot(pack: Path, godot: Path) -> str:
    import_run = subprocess.run(
        [str(godot), "--headless", "--editor", "--path", str(pack), "--quit-after", "20"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    if import_run.returncode != 0:
        raise RuntimeError("Godot import failed:\n" + import_run.stdout)
    qa_run = subprocess.run(
        [str(godot), "--headless", "--path", str(pack), "--", "--qa"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    if qa_run.returncode != 0 or "PIXCEL_CONVERT_GODOT_QA_PASS" not in qa_run.stdout:
        raise RuntimeError("Godot resource QA failed:\n" + qa_run.stdout)
    return next(line for line in qa_run.stdout.splitlines() if "PIXCEL_CONVERT_GODOT_QA_PASS" in line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--godot", type=Path)
    args = parser.parse_args()

    global Image
    try:
        from PIL import Image as PillowImage
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc
    Image = PillowImage
    pack = args.pack.resolve()

    verify_no_delivery_cache(pack)
    manifest, frame_count = verify_sources(pack)
    godot_result = None
    uid_sidecars = collect_uid_sidecars(pack)
    if args.godot:
        try:
            godot_result = run_godot(pack, args.godot.resolve())
        finally:
            clean_import_cache(pack)
            uid_sidecars = record_uid_sidecars(pack)
        verify_sources(pack)
        verify_no_delivery_cache(pack)
    print(
        f"PIXCEL_PACK_SOURCE_QA_PASS assets={len(manifest['assets'])} frames={frame_count} "
        f"atlas={manifest['atlas']['size'][0]}x{manifest['atlas']['size'][1]} hard_alpha=true palette=true"
    )
    if godot_result:
        print(godot_result)
        print(f"PIXCEL_PACK_DELIVERY_QA_PASS cache_free=true uid_sidecars={len(uid_sidecars)}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"error: {exc}") from exc
