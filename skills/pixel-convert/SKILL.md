---
name: pixel-convert
description: Convert concept art or reference sheets into clean pixel-art sprites, tiles, static props, and animation frames that Godot can load directly. Use for concept-to-pixel workflows, 16x16/32x32 logical-grid asset packs, semantic redraws, transparent sprite normalization, optional Aseprite refinement, atlas construction, TileSet and SpriteFrames generation, Godot demo scenes, or verification of Godot-ready pixel assets.
---

# Pixel Convert

Turn concept images into approved semantic pixel redraws, then package them as source PNGs, atlases, Godot TileSets, SpriteFrames, manifests, and a runnable demo. Treat automatic pixelization as a baseline, never as final art.

## Establish the contract

Before generating, record:

- art direction, perspective, light direction, outline policy, palette, and cultural or world constraints;
- logical grid, target canvas for each asset, occupancy, bottom-centre anchor, collision footprint, and whether over-cell effects are allowed;
- required semantic anchors: the small parts that must remain recognizable after reduction;
- animation names, directions, frame counts, FPS, looping, muzzle/contact points, and frame-to-frame anchor invariants;
- target Godot version and whether the asset belongs in TileSet, SpriteFrames, or both.

Resolve conflicts between construction facts and the visible reference before generation. Preserve the supplied viewing angle; describe hidden parts as construction facts, not as features that must be made visible. Ask when a requested visible count would require changing perspective.

Do not invent a collision footprint. Omit collision when it is unspecified, or label a temporary footprint as provisional and request confirmation before formal integration.

Do not silently force every object into one grid cell. A 32x32 grid is a placement contract; furniture or effects may use 96x64, 128x64, or another multi-cell canvas.

## Run the gated workflow

1. **Inspect and separate**
   - Preserve the original concept sheet.
   - Crop one object per file with enough padding.
   - Name assets in lowercase snake_case.
   - Reject ambiguous crops before generation.

2. **Create a diagnostic baseline only when useful**
   - Automatic quantizers such as Hermes SNES may provide an A/B baseline.
   - Never promote a block-downsampled, dithered result without semantic review.

3. **Perform semantic redraw**
   - Use the available `imagegen` skill for raster generation or editing; read its `SKILL.md` before acting.
   - Supply the concept crop as the shape and object reference.
   - List every required semantic anchor explicitly.
   - Request crisp pixel clusters, flat chroma-key or transparent background, no cast shadow, no dithering, and no text.
   - Read [references/semantic-redraw.md](references/semantic-redraw.md) before writing the prompt.

4. **Normalize deterministically**
   - Remove the background before final reduction.
   - Resize once to the declared canvas while preserving aspect ratio.
   - Map to the approved project palette without dithering.
   - Use alpha values 0 or 255 only, keep the hard-alpha threshold in `1..255`, and reject a thresholded result that contains no opaque pixels. Treat PNG transparency by its decoded alpha channel, including indexed PNGs with a `tRNS` transparency entry.
   - Preserve negative spaces; do not cut broad rectangles through furniture.
   - Do not add a blanket one-pixel outline or delete isolated pixels automatically. Apply those operations only to observed defects.
   - Run `scripts/normalize_sprite.py` for a static sprite. For animation, read [references/animation-spec.md](references/animation-spec.md), then run `scripts/normalize_animation.py` once per group so every frame shares one scale and target anchor; do not normalize animation frames independently. Use the same declared contact anchor for normalization and pack building; off-centre and bottom-row anchors are supported when intentionally specified.
   - When chroma-key removal is used, supply a six-digit RGB key and a non-negative integer color-distance threshold.
   - Keep normalization inputs and outputs at different paths. Both normalizers reject filesystem aliases so the source crop or frame cannot be overwritten. Static output is staged beside the destination and atomically replaced; animation outputs must be new, unique across the group under the target filesystem's case rules, and are published only after the complete group is staged successfully.

5. **Use the optional Aseprite polish gate when it adds value**
   - Use Aseprite for observed pixel-cluster defects, tile seams, palette cleanup, anchor/contact-point alignment, or animation continuity. Do not use it as a substitute for semantic redraw.
   - Read [references/aseprite-gate.md](references/aseprite-gate.md), then run `scripts/aseprite_gate.py probe`.
   - In `cli` mode, automation may use the discovered binary. In `manual_gui` mode, prepare the gate and use an approved desktop-control tool or ask the user to open the working PNGs. In `unavailable` mode, keep the existing PNG workflow.
   - Run `scripts/aseprite_gate.py prepare` only on normalized frames. Preserve the recorded baselines, edit only working frames, and run `verify` after every edit before promotion; each verification clears any earlier `verified` state until the current working frames pass. Verify detects a baseline that differs from the current prepare record. The local record is an accidental-change check, not protection against deliberately editing both the baseline and its record.
   - Treat `.aseprite` as editable source. Keep verified PNGs and the Pixel Convert manifest as canonical Godot inputs.

6. **Stop at the visual gate**
   - Produce an A/B sheet showing every pixel result at native 1x and exact nearest-neighbour 4x, alongside the concept crop. Never reduce the requested 4x view to 2x or 3x to fit a fixed panel.
   - Run `scripts/make_ab_preview.py` to create the review sheet.
   - Write the review sheet to a separate path. The preview tool rejects an output that aliases the concept, semantic redraw, or optional baseline, and replaces an existing preview only after the new PNG saves successfully.
   - Inspect silhouette, semantic anchors, value separation, negative spaces, palette, and anchor.
   - Obtain user approval for at least one representative asset before batch conversion.
   - Remove rejected assets from current PNGs, atlas cells, resources, manifests, demos, and previews when the user explicitly says not to retain them. Keep the immutable original concept sheet unless asked otherwise.

7. **Build the Godot pack**
   - Define the pack with the JSON contract in [references/spec-schema.md](references/spec-schema.md).
   - Run `scripts/build_godot_pack.py --spec <spec.json> --out <pack-dir>`.
   - Generate a uniform atlas whose shared anchor is derived from every asset's declared contact-point extents, plus a geometrically aligned TileSet, one SpriteFrames resource per asset, manifest, project settings, and a demo scene that starts each selected animation.
   - Build into an absent or empty output directory. The builder rejects non-empty outputs and publishes a complete staging build atomically.
   - Use Nearest filtering and disable nearest mipmap filtering in `project.godot`.

8. **Verify honestly**
   - Run `scripts/verify_pack.py --pack <pack-dir>` for source QA of PNGs, atlas geometry, SpriteFrames regions, TileSet metadata/origin, required project/demo files, manifest contracts, and cache hygiene.
   - Source QA is non-mutating and rejects pre-existing `.godot/`, `.ctex`, and `.import` cache instead of deleting it. Clean a deliberate test copy before verification; do not point source QA at a working directory whose generated cache must be preserved.
   - If a Godot binary is available, add `--godot <binary>` to perform clean import and actual resource loading. The verifier removes cache generated by that invocation and records valid script UID sidecars even when import or resource QA fails.
   - Read [references/godot-validation.md](references/godot-validation.md) before reporting results.
   - Do not describe static text checks as Godot loading, Headless loading as a GUI screenshot, or a resource readback as a Viewport render.

9. **Clean the delivery**
   - Deliver source PNGs, palette/spec, atlas, `.tres`, `.tscn`, scripts, manifest, demo, license, and preview.
   - Exclude `.godot/`, `.ctex`, `.import`, `__pycache__/`, and `.pyc` files. Keep valid Godot 4.4+ `.gd.uid` script sidecars generated by engine import; `verify_pack.py --godot` records their paths in the manifest.
   - Preserve unrelated user files and do not publish, commit, or overwrite release assets without explicit approval.

## Commands

Normalize an approved semantic redraw:

```bash
python3 scripts/normalize_sprite.py input.png output.png \
  --canvas 96x64 --anchor 48,62 --palette palette.txt \
  --background-key FF00FF
```

Omit `--background-key` when the input already has transparency; otherwise replace `FF00FF` with the declared six-digit chroma key.

Normalize a complete animation with one shared transform:

```bash
python3 scripts/normalize_animation.py --spec animation_spec.json
```

Create the visual-gate sheet:

```bash
python3 scripts/make_ab_preview.py --concept crop.png \
  --baseline automatic.png --semantic final.png --out comparison.png
```

Prepare and verify an optional Aseprite polish gate:

```bash
python3 scripts/aseprite_gate.py probe --json
python3 scripts/aseprite_gate.py prepare --asset-id prop \
  --input prop.png --palette palette.txt --grid 32x32 --anchor 48,62 \
  --out aseprite-gate/prop
python3 scripts/aseprite_gate.py verify --gate aseprite-gate/prop
```

Build a Godot-ready pack:

```bash
python3 scripts/build_godot_pack.py --spec pack_spec.json --out godot-pack
```

Verify source files and optionally Godot loading:

```bash
python3 scripts/verify_pack.py --pack godot-pack
python3 scripts/verify_pack.py --pack godot-pack --godot /path/to/Godot
```

Use a Python runtime with Pillow installed. In Codex, call the workspace-dependency locator to obtain the bundled Python path. Elsewhere, select a runtime that passes `python3 -c "from PIL import Image"`. Do not assume the system Python contains Pillow.

## Acceptance criteria

Accept an asset only when:

- semantic anchors remain readable at 1x and 4x;
- when the optional Aseprite gate is used, its `gate.json` status is `verified`, every prepare-time baseline is unchanged, and every working frame contains opaque pixels and passes canvas, hard-alpha, and palette checks;
- canvas, occupancy, anchor, collision, directions, and animations match the declared contract;
- alpha is hard, colors belong to the approved palette, and no chroma-key color remains;
- every frame PNG matches its canvas, each atlas cell matches the canonical PNG, and SpriteFrames/TileSet reference the matching atlas path, region, and contact-point geometry;
- Godot loads the TileSet, SpriteFrames, scene, and script without parse or resource errors;
- evidence labels state exactly what was and was not verified.
