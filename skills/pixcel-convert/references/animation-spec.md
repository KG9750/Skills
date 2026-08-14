# Animation normalization specification

`normalize_animation.py` consumes one JSON object. All file paths are relative to the specification file. Normalize one animation group per spec so every frame uses one shared scale and contact-anchor transform.

```json
{
  "canvas": [64, 64],
  "anchor": [32, 62],
  "palette": "palette.txt",
  "padding": 2,
  "alpha_threshold": 112,
  "background_key": "FF00FF",
  "key_threshold": 40,
  "frames": [
    {
      "input": "source/idle_00.png",
      "output": "normalized/idle_00.png",
      "source_anchor": [48, 90]
    },
    {
      "input": "source/idle_01.png",
      "output": "normalized/idle_01.png",
      "source_anchor": [48, 90]
    }
  ]
}
```

## Rules

- `canvas`: required target `[width, height]` using two positive integers.
- `anchor`: required integer contact point inside the target canvas.
- `palette`: required non-empty path to a text palette containing one six-digit RGB hex color per line.
- `frames`: required array with at least two entries in playback order.
- Frame `input` and `output`: required non-empty relative paths. Every output must be new, distinct from every input, and distinct from every other output under the target filesystem's case rules. The command validates and stages the complete group before publishing any output; if staging or commit fails, it removes this run's partial outputs and temporary files.
- Frame `source_anchor`: optional integer point inside that source frame's canvas, in source-image coordinates. Supply it for every frame or none. Recalculate it after cropping; do not reuse sheet-space coordinates. When omitted, all source images must share one canvas and the normalizer derives one anchor from the union foreground bounds.
- `padding`: optional non-negative target-canvas inset; default `2`.
- `alpha_threshold`: optional integer output hard-alpha and foreground cutoff in `1..255`; default `112`. Every normalized frame must retain at least one opaque pixel after this cutoff or the complete group fails before any output is written.
- `background_key`: optional six-digit RGB chroma-key string shared by all frames. A frame may override it with its own `background_key`.
- `key_threshold`: optional non-negative integer chroma-key color-distance threshold; default `40`.

Use transparent source frames whenever possible. Fully opaque input requires a background key. The command validates required group and frame fields before writing output frames and reports normal file, JSON, and contract failures as `error:` diagnostics.
