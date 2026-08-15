# Optional Aseprite polish gate

Use Aseprite after deterministic normalization and before the visual approval gate. Aseprite is a pixel editor, not a semantic redraw model: use it to repair clusters, seams, anchors, contact points, palettes, and animation continuity, not to infer missing objects.

## Modes

- `cli`: `aseprite --version` exits successfully. Automated conversion or export may use the discovered binary.
- `manual_gui`: an executable exists but CLI startup fails, times out, or cannot join the macOS GUI session. Prepare the gate files and open them through an approved desktop-control tool or ask the user to open them in Aseprite. Do not retry a crashing CLI repeatedly.
- `unavailable`: no executable exists. Skip the optional gate and continue with the existing PNG workflow.

Probe the environment:

```bash
python3 scripts/aseprite_gate.py probe --json
```

`ASEPRITE_BIN` or `--aseprite /path/to/aseprite` overrides discovery. The default macOS candidates include the Applications bundle, a user-local `Aseprite-Codex.app`, and a local source build.

## Prepare a static or animated gate

Run once after normalization. Repeat `--input` in animation order:

```bash
python3 scripts/aseprite_gate.py prepare \
  --asset-id writing_desk \
  --input normalized/writing_desk.png \
  --palette palette.txt \
  --grid 32x32 --anchor 48,62 \
  --out aseprite-gate/writing_desk
```

The gate contains recorded `baseline/` frames, editable `working/` frames, an Aseprite-compatible `palette.gpl`, `gate.json`, and concise opening instructions. Open only `working/` files. `prepare` publishes the gate transactionally; `verify` rejects baseline files that differ from the current prepare record, rejects paths outside their declared directories, and rejects duplicate frame records before checking working frames. This local record catches accidental baseline edits; it is not intended to defend against deliberately modifying both a baseline and its record. For animation, import the ordered files as frames, preserve frame order and canvas size, and use onion skin to inspect anchor drift.

Use Aseprite features deliberately:

- native 1x preview for pixel-cluster readability;
- tiled mode for floors, walls, doors, and other seamless tiles;
- onion skin and linked cels for animation continuity;
- grid and guides for the declared logical grid and bottom-centre anchor;
- indexed palette with dithering disabled;
- slices or pivots as editable metadata, never baked into final PNGs.

Do not invent collision shapes. Keep reference layers hidden from export. Treat `.aseprite` files as editable sources only; canonical Godot input remains verified PNG frames plus the Pixel Convert manifest.

## Verify before promotion

```bash
python3 scripts/aseprite_gate.py verify --gate aseprite-gate/writing_desk
```

Every verification attempt first persists `awaiting_aseprite_review`, so an earlier success cannot approve later edits. It then requires a non-empty frame list, confirms that every baseline still matches its prepare-time digest, requires each working frame to contain at least one opaque pixel, and enforces canvas size, hard alpha, and the declared palette before marking `gate.json` as `verified`. It does not prove visual quality, seam quality, anchor alignment, or GUI rendering; inspect those at the normal A/B visual gate before building the Godot pack.
