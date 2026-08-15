# Pack specification

`build_godot_pack.py` consumes one JSON file. Frame paths are relative to the specification file.

```json
{
  "pack_name": "ming_hearths_desk",
  "grid": [32, 32],
  "palette": ["2B2523", "4A2F27", "6B4030", "936040", "E8DFC5"],
  "assets": [
    {
      "id": "writing_desk",
      "canvas": [96, 64],
      "occupancy": [3, 2],
      "anchor": [48, 62],
      "directions": ["n", "ne", "e", "se", "s", "sw", "w", "nw"],
      "contact_points": {"base": [48, 62]},
      "tileset_animation": "idle",
      "animations": {
        "idle": {
          "fps": 1.0,
          "loop": false,
          "frames": ["sprites/writing_desk.png"]
        }
      }
    }
  ]
}
```

## Rules

- `pack_name`: string containing lowercase letters, digits, and underscores.
- `grid`: required Godot logical tile size as two positive integers.
- `palette`: allowed opaque RGB colors, six-digit hex without `#`.
- `canvas`: exact dimensions of every frame belonging to the asset.
- `occupancy`: logical grid footprint as two positive integers `[columns, rows]` for documentation and placement.
- `anchor`: integer contact point inside the asset canvas, normally the bottom-centre ground contact. Off-centre and bottom-row anchors are supported when the visible sprite or effect requires them; use the same point in normalization and pack building.
- Asset `id`, animation names, and direction names are strings containing lowercase letters, digits, and underscores.
- `directions`: optional JSON list of unique direction-name strings supported by this asset. Declare every value used by an animation's `direction`.
- Asset `contact_points`: optional named canvas-space points shared by all animations, for example `base`, `interaction`, or `muzzle_rest`. Every coordinate must be a JSON integer; numeric strings, booleans, and floats are invalid.
- `collision_polygon`: optional Godot local coordinates around the tile origin. Omit it when the user or project has not defined collision; never copy a sample rectangle as an approved footprint.
- `tileset_animation`: animation whose first frame becomes the TileSet tile.
- `animations`: one or more named JSON objects; each animation requires a non-empty list of non-empty string frame paths, and all frames must use the declared canvas and anchor. `fps` must be a JSON number, not a boolean, and must be finite and greater than zero. `loop`, when present, must be a JSON boolean.
- Animation `direction`: optional direction name; it must appear in the asset's `directions` list.
- Animation `contact_points`: optional named point object used by every frame, or an array of named point objects with exactly one entry per frame. Use the per-frame form for moving muzzles, hands, sockets, or effect origins.

Named contact points use integer `[x, y]` coordinates inside the declared asset canvas. The builder preserves directions and contact points in `asset_manifest.json`; it does not infer them from pixels.

The builder creates one horizontal atlas with a uniform cell large enough for every asset's left, right, top, and bottom extents relative to its declared anchor. It derives one shared atlas anchor from those extents, aligns every frame to it, and records the atlas coordinates, placement, TileSet texture origin, and AnimatedSprite2D offset required to preserve the same contact point. Do not hand-edit those derived values.

The output is transactional. The builder writes to a sibling staging directory and renames it only after the complete pack succeeds. It accepts an absent or empty output directory and rejects a non-empty output directory instead of merging or overwriting files.

The generated manifest includes `godot_uid_sidecars`. It is empty before engine import. On Godot 4.4+, `verify_pack.py --godot` retains valid `.gd.uid` files beside their matching scripts and records their pack-relative paths in this list.
