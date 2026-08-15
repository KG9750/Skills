#!/usr/bin/env python3
"""Build a self-contained Godot 4 pixel-asset pack from a JSON specification."""

from __future__ import annotations

import argparse
import atexit
import json
import math
import re
import shutil
import tempfile
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9_]+$")


def required(value: dict, key: str, label: str):
    if key not in value:
        raise ValueError(f"{label} is missing required field: {key}")
    return value[key]


def ensure_name(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if not NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must contain lowercase letters, digits, and underscores: {value!r}")
    return value


def normalize_contact_points(value: dict, canvas: tuple[int, int], label: str) -> dict[str, list[int]]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object of named [x, y] points")
    points: dict[str, list[int]] = {}
    for raw_name, raw_point in value.items():
        name = ensure_name(raw_name, f"{label} name")
        if (
            not isinstance(raw_point, list)
            or len(raw_point) != 2
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in raw_point)
        ):
            raise ValueError(f"{label}.{name} must be an integer [x, y] point")
        point = [raw_point[0], raw_point[1]]
        if not (0 <= point[0] < canvas[0] and 0 <= point[1] < canvas[1]):
            raise ValueError(f"{label}.{name} must be inside the asset canvas")
        points[name] = point
    return points


def normalize_collision_polygon(value: object, label: str) -> list[list[int]] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError(f"{label} must contain at least three [x, y] points")
    points: list[list[int]] = []
    for raw_point in value:
        if (
            not isinstance(raw_point, list)
            or len(raw_point) != 2
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in raw_point)
        ):
            raise ValueError(f"{label} must contain integer [x, y] points")
        points.append([raw_point[0], raw_point[1]])
    return points


def positive_int_pair(value: object, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in value)
    ):
        raise ValueError(f"{label} must contain two positive integers")
    return value[0], value[1]


def round_up(value: int, step: int) -> int:
    return math.ceil(value / step) * step


def resource_path(path: Path, root: Path) -> str:
    return "res://" + path.relative_to(root).as_posix()


def validate_frame(
    image: Image.Image,
    expected_size: tuple[int, int],
    palette: set[tuple[int, int, int]],
    label: str,
) -> Image.Image:
    rgba = image.convert("RGBA")
    if rgba.size != expected_size:
        raise ValueError(f"{label} size is {rgba.size}, expected {expected_size}")
    colors = rgba.getcolors(maxcolors=65536)
    if colors is None:
        raise ValueError(f"{label} has too many colors")
    alpha = {color[3] for _, color in colors}
    if not alpha <= {0, 255} or 255 not in alpha:
        raise ValueError(f"{label} must use hard alpha and contain opaque pixels")
    opaque = {color[:3] for _, color in colors if color[3] == 255}
    if not opaque <= palette:
        raise ValueError(f"{label} contains colors outside the declared palette")
    return rgba


def make_sprite_frames(
    out: Path,
    pack_name: str,
    asset: dict,
    cell: tuple[int, int],
    atlas_name: str,
) -> None:
    frame_records = [
        record
        for animation in asset["animations"].values()
        for record in animation["frames"]
    ]
    lines = [
        f'[gd_resource type="SpriteFrames" load_steps={len(frame_records) + 2} format=3]',
        "",
        f'[ext_resource type="Texture2D" path="res://sprites/{atlas_name}" id="1_atlas"]',
        "",
    ]
    for record in frame_records:
        sub_id = f"AtlasTexture_{record['atlas_index']}"
        lines.extend(
            [
                f'[sub_resource type="AtlasTexture" id="{sub_id}"]',
                'atlas = ExtResource("1_atlas")',
                f"region = Rect2({record['atlas_index'] * cell[0]}, 0, {cell[0]}, {cell[1]})",
                "",
            ]
        )

    animation_blocks: list[str] = []
    for animation_name, animation in asset["animations"].items():
        frame_blocks = [
            '{\n"duration": 1.0,\n"texture": SubResource("AtlasTexture_%s")\n}' % record["atlas_index"]
            for record in animation["frames"]
        ]
        animation_blocks.append(
            "{\n"
            f'"frames": [{", ".join(frame_blocks)}],\n'
            f'"loop": {str(bool(animation["loop"])).lower()},\n'
            f'"name": &"{animation_name}",\n'
            f'"speed": {float(animation["fps"]):g}\n'
            "}"
        )
    lines.extend(["[resource]", f"animations = [{', '.join(animation_blocks)}]", ""])
    path = out / "resources" / f"{asset['id']}_sprite_frames.tres"
    path.write_text("\n".join(lines), encoding="utf-8")


def make_tileset(
    out: Path,
    spec: dict,
    assets: list[dict],
    cell: tuple[int, int],
    atlas_anchor: tuple[int, int],
    atlas_name: str,
) -> None:
    grid_w, grid_h = spec["grid"]
    has_collision = any(asset.get("collision_polygon") for asset in assets)
    lines = [
        '[gd_resource type="TileSet" load_steps=3 format=3]',
        "",
        f'[ext_resource type="Texture2D" path="res://sprites/{atlas_name}" id="1_atlas"]',
        "",
        '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_assets"]',
        'texture = ExtResource("1_atlas")',
        f"texture_region_size = Vector2i({cell[0]}, {cell[1]})",
    ]
    texture_origin_x = atlas_anchor[0] - cell[0] // 2
    texture_origin_y = (cell[1] - grid_h) // 2 - (cell[1] - atlas_anchor[1])
    for asset in assets:
        x = asset["tileset_atlas_coordinates"][0]
        lines.extend(
            [
                f"{x}:0/0 = 0",
                f"{x}:0/0/texture_origin = Vector2i({texture_origin_x}, {texture_origin_y})",
            ]
        )
        polygon = asset.get("collision_polygon")
        if polygon:
            points = ", ".join(f"{int(px)}, {int(py)}" for px, py in polygon)
            lines.append(
                f"{x}:0/0/physics_layer_0/polygon_0/points = PackedVector2Array({points})"
            )
    lines.extend(["", "[resource]", f"tile_size = Vector2i({grid_w}, {grid_h})"])
    if has_collision:
        lines.extend(["physics_layer_0/collision_layer = 1", "physics_layer_0/collision_mask = 1"])
    lines.extend(['sources/0 = SubResource("TileSetAtlasSource_assets")', ""])
    (out / "resources" / f"{spec['pack_name']}_tileset.tres").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def make_demo(
    out: Path,
    spec: dict,
    assets: list[dict],
    cell: tuple[int, int],
    atlas_anchor: tuple[int, int],
) -> None:
    pack_name = spec["pack_name"]
    ids = ", ".join(f'&"{asset["id"]}"' for asset in assets)
    frame_paths = ", ".join(
        f'"res://resources/{asset["id"]}_sprite_frames.tres"' for asset in assets
    )
    default_animations = ", ".join(f'&"{asset["tileset_animation"]}"' for asset in assets)
    coordinates = ", ".join(
        f"Vector2i({asset['tileset_atlas_coordinates'][0]}, 0)" for asset in assets
    )
    offsets = ", ".join(
        f"Vector2({asset['sprite_offset'][0]}, {asset['sprite_offset'][1]})" for asset in assets
    )
    animation_names = ", ".join(
        "[" + ", ".join(f'&"{name}"' for name in asset["animations"]) + "]"
        for asset in assets
    )
    animation_speeds = ", ".join(
        "[" + ", ".join(f'{float(animation["fps"]):g}' for animation in asset["animations"].values()) + "]"
        for asset in assets
    )
    animation_loops = ", ".join(
        "[" + ", ".join(str(bool(animation["loop"])).lower() for animation in asset["animations"].values()) + "]"
        for asset in assets
    )
    animation_frame_counts = ", ".join(
        "[" + ", ".join(str(len(animation["frames"])) for animation in asset["animations"].values()) + "]"
        for asset in assets
    )
    default_frame_counts = ", ".join(
        str(len(asset["animations"][asset["tileset_animation"]]["frames"])) for asset in assets
    )
    collision_counts = ", ".join("1" if asset.get("collision_polygon") else "0" for asset in assets)
    expected_texture_origin = (
        atlas_anchor[0] - cell[0] // 2,
        (cell[1] - spec["grid"][1]) // 2 - (cell[1] - atlas_anchor[1]),
    )
    script = f'''extends Node2D

const TILESET_PATH := "res://resources/{pack_name}_tileset.tres"
const ASSET_IDS := [{ids}]
const FRAME_PATHS := [{frame_paths}]
const DEFAULT_ANIMATIONS := [{default_animations}]
const ATLAS_COORDINATES := [{coordinates}]
const SPRITE_OFFSETS := [{offsets}]
const ANIMATION_NAMES := [{animation_names}]
const ANIMATION_SPEEDS := [{animation_speeds}]
const ANIMATION_LOOPS := [{animation_loops}]
const ANIMATION_FRAME_COUNTS := [{animation_frame_counts}]
const DEFAULT_FRAME_COUNTS := [{default_frame_counts}]
const COLLISION_COUNTS := [{collision_counts}]
const EXPECTED_TEXTURE_ORIGIN := Vector2i({expected_texture_origin[0]}, {expected_texture_origin[1]})


func _ready() -> void:
    RenderingServer.set_default_clear_color(Color("2b2523"))
    build_tileset_row()
    build_spriteframes_row()
    if "--qa" in OS.get_cmdline_user_args():
        verify_resources.call_deferred()


func build_tileset_row() -> void:
    var layer := TileMapLayer.new()
    layer.name = "TileSetPreview"
    layer.tile_set = load(TILESET_PATH)
    layer.position = Vector2(128, 150)
    layer.scale = Vector2(2.0, 2.0)
    add_child(layer)
    for index in range(ASSET_IDS.size()):
        layer.set_cell(Vector2i(index * 5, 0), 0, ATLAS_COORDINATES[index])


func build_spriteframes_row() -> void:
    for index in range(ASSET_IDS.size()):
        var sprite := AnimatedSprite2D.new()
        sprite.name = String(ASSET_IDS[index])
        sprite.sprite_frames = load(FRAME_PATHS[index])
        sprite.animation = DEFAULT_ANIMATIONS[index]
        sprite.offset = SPRITE_OFFSETS[index]
        sprite.position = Vector2(128 + index * 220, 400)
        sprite.scale = Vector2(2.0, 2.0)
        add_child(sprite)
        sprite.play(DEFAULT_ANIMATIONS[index])


func verify_resources() -> void:
    var tileset: TileSet = load(TILESET_PATH)
    var ok := tileset != null and tileset.get_source_count() == 1
    var source := tileset.get_source(0) as TileSetAtlasSource
    ok = ok and source != null
    for index in range(ASSET_IDS.size()):
        ok = ok and source.has_tile(ATLAS_COORDINATES[index])
        var tile_data := source.get_tile_data(ATLAS_COORDINATES[index], 0)
        ok = ok and tile_data.texture_origin == EXPECTED_TEXTURE_ORIGIN
        var collision_count := 0
        if tileset.get_physics_layers_count() > 0:
            collision_count = tile_data.get_collision_polygons_count(0)
        ok = ok and collision_count == COLLISION_COUNTS[index]
        var frames: SpriteFrames = load(FRAME_PATHS[index])
        ok = ok and frames != null
        var expected_names: Array = ANIMATION_NAMES[index]
        ok = ok and frames.get_animation_names().size() == expected_names.size()
        for animation_index in range(expected_names.size()):
            var animation_name: StringName = expected_names[animation_index]
            ok = ok and frames.has_animation(animation_name)
            ok = ok and frames.get_frame_count(animation_name) == ANIMATION_FRAME_COUNTS[index][animation_index]
            ok = ok and is_equal_approx(frames.get_animation_speed(animation_name), float(ANIMATION_SPEEDS[index][animation_index]))
            ok = ok and frames.get_animation_loop(animation_name) == ANIMATION_LOOPS[index][animation_index]
        var sprite := get_node_or_null(NodePath(String(ASSET_IDS[index]))) as AnimatedSprite2D
        ok = ok and sprite != null and sprite.offset == SPRITE_OFFSETS[index]
        if DEFAULT_FRAME_COUNTS[index] > 1:
            ok = ok and sprite.is_playing()
    if not ok:
        push_error("PIXEL_CONVERT_GODOT_QA_FAIL")
        get_tree().quit(1)
        return
    print("PIXEL_CONVERT_GODOT_QA_PASS tileset_sources=1 tiles=%s spriteframes=%s" % [ASSET_IDS.size(), ASSET_IDS.size()])
    get_tree().quit(0)
'''
    (out / "demo" / "main.gd").write_text(script, encoding="utf-8")
    (out / "demo" / "main.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://demo/main.gd" id="1_script"]\n\n'
        '[node name="Main" type="Node2D"]\nscript = ExtResource("1_script")\n',
        encoding="utf-8",
    )
    (out / "project.godot").write_text(
        f'''; Generated by Pixel Convert.
config_version=5

[application]
config/name="{pack_name}"
run/main_scene="res://demo/main.tscn"

[display]
window/size/viewport_width=960
window/size/viewport_height=540
window/stretch/mode="canvas_items"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/default_filters/use_nearest_mipmap_filter=false
textures/canvas_textures/default_texture_filter=0
''',
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    global Image
    try:
        from PIL import Image as PillowImage
    except ImportError as exc:
        raise SystemExit("Pillow is required. Use a Python runtime that passes: from PIL import Image") from exc
    Image = PillowImage

    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("pack spec must be a JSON object")
    pack_name = ensure_name(required(spec, "pack_name", "pack spec"), "pack_name")
    grid = positive_int_pair(required(spec, "grid", "pack spec"), "grid")
    raw_palette = spec.get("palette")
    if not isinstance(raw_palette, list) or not raw_palette:
        raise ValueError("palette must be a non-empty list of six-digit RGB hex colors")
    palette: set[tuple[int, int, int]] = set()
    for raw_color in raw_palette:
        if not isinstance(raw_color, str):
            raise ValueError(f"invalid palette color: {raw_color!r}")
        value = raw_color.removeprefix("#")
        if len(value) != 6:
            raise ValueError(f"invalid palette color: {raw_color!r}")
        try:
            palette.add(tuple(bytes.fromhex(value)))
        except ValueError as exc:
            raise ValueError(f"invalid palette color: {raw_color!r}") from exc
    if not palette:
        raise ValueError("palette is empty")
    raw_assets = spec.get("assets", [])
    if not isinstance(raw_assets, list) or not raw_assets:
        raise ValueError("assets must be a non-empty list")
    for index, raw_asset in enumerate(raw_assets):
        if not isinstance(raw_asset, dict):
            raise ValueError(f"assets[{index}] must be an object")
    asset_ids = [
        ensure_name(required(asset, "id", f"assets[{index}]"), "asset id")
        for index, asset in enumerate(raw_assets)
    ]
    duplicate_ids = sorted({asset_id for asset_id in asset_ids if asset_ids.count(asset_id) > 1})
    if duplicate_ids:
        raise ValueError("duplicate asset id: " + ", ".join(duplicate_ids))

    normalized_geometry: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for raw_asset in raw_assets:
        canvas = positive_int_pair(raw_asset.get("canvas"), f"{raw_asset['id']} canvas")
        anchor = tuple(raw_asset.get("anchor", ()))
        if (
            len(anchor) != 2
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in anchor)
            or not (0 <= anchor[0] < canvas[0] and 0 <= anchor[1] < canvas[1])
        ):
            raise ValueError(f"{raw_asset['id']} anchor must be an integer [x, y] point inside the canvas")
        normalized_geometry.append((canvas, anchor))
    left_extent = max(anchor[0] for _, anchor in normalized_geometry)
    right_extent = max(canvas[0] - anchor[0] for canvas, anchor in normalized_geometry)
    top_extent = max(anchor[1] for _, anchor in normalized_geometry)
    bottom_extent = max(canvas[1] - anchor[1] for canvas, anchor in normalized_geometry)
    cell = (
        round_up(left_extent + right_extent, grid[0]),
        round_up(top_extent + bottom_extent, grid[1]),
    )
    atlas_anchor = (left_extent, top_extent)
    final_out = args.out.resolve()
    if final_out.exists():
        if not final_out.is_dir():
            raise ValueError(f"output path is not a directory: {final_out}")
        if any(final_out.iterdir()):
            raise ValueError(f"output directory is not empty: {final_out}")
    final_out.parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=f".{final_out.name}.staging-", dir=final_out.parent))
    cleanup_staging = lambda: shutil.rmtree(out, ignore_errors=True)
    atexit.register(cleanup_staging)
    for directory in ("sprites/frames", "resources", "demo"):
        (out / directory).mkdir(parents=True, exist_ok=True)

    assets: list[dict] = []
    atlas_records: list[tuple[Image.Image, tuple[int, int]]] = []
    atlas_index = 0
    for raw_asset in raw_assets:
        asset_id = ensure_name(raw_asset["id"], "asset id")
        canvas = positive_int_pair(raw_asset.get("canvas"), f"{asset_id} canvas")
        anchor = tuple(raw_asset["anchor"])
        occupancy = positive_int_pair(raw_asset.get("occupancy"), f"{asset_id} occupancy")
        raw_directions = raw_asset.get("directions", [])
        if not isinstance(raw_directions, list):
            raise ValueError(f"{asset_id} directions must be a list")
        directions = [ensure_name(value, f"{asset_id} direction") for value in raw_directions]
        if len(directions) != len(set(directions)):
            raise ValueError(f"{asset_id} directions must be unique")
        contact_points = normalize_contact_points(
            raw_asset.get("contact_points", {}), canvas, f"{asset_id} contact_points"
        )
        collision_polygon = normalize_collision_polygon(
            raw_asset.get("collision_polygon"), f"{asset_id} collision_polygon"
        )
        placement = (atlas_anchor[0] - anchor[0], atlas_anchor[1] - anchor[1])
        if placement[0] < 0 or placement[1] < 0 or placement[0] + canvas[0] > cell[0] or placement[1] + canvas[1] > cell[1]:
            raise ValueError(f"{asset_id} cannot align to the shared atlas anchor")

        raw_animations = raw_asset.get("animations")
        if not isinstance(raw_animations, dict) or not raw_animations:
            raise ValueError(f"{asset_id} animations must not be empty")
        animations: dict[str, dict] = {}
        for animation_name, raw_animation in raw_animations.items():
            ensure_name(animation_name, "animation name")
            if not isinstance(raw_animation, dict):
                raise ValueError(f"{asset_id}/{animation_name} must be an object")
            raw_fps = raw_animation.get("fps", 1.0)
            if not isinstance(raw_fps, (int, float)) or isinstance(raw_fps, bool):
                raise ValueError(f"{asset_id}/{animation_name} fps must be a number")
            fps = float(raw_fps)
            if not math.isfinite(fps):
                raise ValueError(f"{asset_id}/{animation_name} fps must be finite")
            if fps <= 0:
                raise ValueError(f"{asset_id}/{animation_name} fps must be greater than zero")
            loop = raw_animation.get("loop", False)
            if not isinstance(loop, bool):
                raise ValueError(f"{asset_id}/{animation_name} loop must be a boolean")
            frames: list[dict] = []
            raw_frames = required(raw_animation, "frames", f"{asset_id}/{animation_name}")
            if not isinstance(raw_frames, list) or not raw_frames:
                raise ValueError(f"{asset_id}/{animation_name} frames must be a non-empty list")
            for frame_number, relative in enumerate(raw_frames):
                if not isinstance(relative, str) or not relative:
                    raise ValueError(
                        f"{asset_id}/{animation_name} frames[{frame_number}] must be a non-empty path string"
                    )
                source_path = (spec_path.parent / relative).resolve()
                image = validate_frame(
                    Image.open(source_path), canvas, palette, f"{asset_id}/{animation_name}/{frame_number}"
                )
                output_frame = out / "sprites" / "frames" / asset_id / f"{animation_name}_{frame_number:03d}.png"
                output_frame.parent.mkdir(parents=True, exist_ok=True)
                image.save(output_frame)
                record = {
                    "path": resource_path(output_frame, out),
                    "atlas_index": atlas_index,
                    "atlas_coordinates": [atlas_index, 0],
                    "placement": list(placement),
                }
                frames.append(record)
                atlas_records.append((image, placement))
                atlas_index += 1
            animations[animation_name] = {
                "fps": fps,
                "loop": loop,
                "frames": frames,
            }
            direction = raw_animation.get("direction")
            if direction is not None:
                direction = ensure_name(direction, f"{asset_id}/{animation_name} direction")
                if direction not in directions:
                    raise ValueError(
                        f"{asset_id}/{animation_name} direction {direction!r} is not declared in directions"
                    )
                animations[animation_name]["direction"] = direction
            raw_points = raw_animation.get("contact_points")
            if raw_points is not None:
                if isinstance(raw_points, list):
                    if len(raw_points) != len(frames):
                        raise ValueError(
                            f"{asset_id}/{animation_name} contact_points must match the frame count"
                        )
                    animations[animation_name]["contact_points"] = [
                        normalize_contact_points(points, canvas, f"{asset_id}/{animation_name} contact_points")
                        for points in raw_points
                    ]
                else:
                    animations[animation_name]["contact_points"] = normalize_contact_points(
                        raw_points, canvas, f"{asset_id}/{animation_name} contact_points"
                    )
        tileset_animation = raw_asset.get("tileset_animation", next(iter(animations)))
        if tileset_animation not in animations:
            raise ValueError(f"{asset_id} tileset_animation does not exist")
        default_frame = animations[tileset_animation]["frames"][0]
        asset = {
            "id": asset_id,
            "canvas": list(canvas),
            "occupancy": list(occupancy),
            "anchor": list(anchor),
            "directions": directions,
            "contact_points": contact_points,
            "sprite_offset": [cell[0] // 2 - atlas_anchor[0], cell[1] // 2 - atlas_anchor[1]],
            "collision_polygon": collision_polygon,
            "tileset_animation": tileset_animation,
            "tileset_atlas_coordinates": default_frame["atlas_coordinates"],
            "animations": animations,
        }
        assets.append(asset)

    atlas_name = f"{pack_name}_atlas.png"
    atlas = Image.new("RGBA", (cell[0] * len(atlas_records), cell[1]), (0, 0, 0, 0))
    for index, (frame, placement) in enumerate(atlas_records):
        atlas.alpha_composite(frame, (index * cell[0] + placement[0], placement[1]))
    atlas.save(out / "sprites" / atlas_name)

    for asset in assets:
        make_sprite_frames(out, pack_name, asset, cell, atlas_name)
    make_tileset(
        out,
        {**spec, "pack_name": pack_name, "grid": list(grid)},
        assets,
        cell,
        atlas_anchor,
        atlas_name,
    )
    make_demo(
        out,
        {**spec, "pack_name": pack_name, "grid": list(grid)},
        assets,
        cell,
        atlas_anchor,
    )

    manifest = {
        "generator": "pixel-convert",
        "pack_name": pack_name,
        "grid": list(grid),
        "palette": ["%02X%02X%02X" % color for color in sorted(palette)],
        "atlas": {
            "path": f"sprites/{atlas_name}",
            "cell": list(cell),
            "size": list(atlas.size),
            "anchor": list(atlas_anchor),
        },
        "tileset": f"resources/{pack_name}_tileset.tres",
        "godot_uid_sidecars": [],
        "assets": assets,
    }
    (out / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / ".gitignore").write_text(".godot/\n*.import\n*.ctex\n__pycache__/\n*.pyc\n", encoding="utf-8")
    if final_out.exists():
        final_out.rmdir()
    out.replace(final_out)
    atexit.unregister(cleanup_staging)
    print(
        f"PIXEL_BUILD_PASS pack={pack_name} assets={len(assets)} frames={len(atlas_records)} "
        f"atlas={atlas.width}x{atlas.height} out={final_out}"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
