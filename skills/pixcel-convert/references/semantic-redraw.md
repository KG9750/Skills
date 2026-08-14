# Semantic redraw prompt contract

Use the concept crop as a reference, not as pixels to shrink blindly.

## Prompt template

```text
Use case: style-transfer
Asset type: Godot 2D pixel-art <prop/character/tile/effect>, ultimately used on a <W>x<H> canvas occupying <columns>x<rows> logical <grid> cells.
Input image: the supplied crop is the sole shape and object reference.
Primary request: redraw the same object as clean, readable handcrafted pixel art while preserving its proportions and viewing angle.
Required semantic anchors: <list every small feature that defines the object>.
Style: deliberate pixel clusters, crisp hard edges, no antialiasing, no dithering, no noisy single-pixel texture.
Lighting: <direction>; use clearly separated value groups.
Palette: <project palette and material colors>; avoid pure black unless the project requires it.
Outline: exterior silhouette only when needed; interior construction lines use lighter darks.
Composition: entire object visible, centred around the declared anchor, clean negative spaces, no cropping.
Background: perfectly flat solid <chroma key>, no gradient, texture, floor, shadow, reflection, or lighting variation. Do not use the key color in the subject.
Avoid: missing semantic anchors, added objects, distorted legs or barrels, filled negative spaces, painterly shading, text, labels, watermark, grid overlay.
```

List only features that should be visible from the supplied angle. If an object structurally has four legs but the reference angle occludes one or more, preserve the angle and request clean separation of the visible legs; do not expose hidden legs or rotate the object merely to satisfy a count.

## Visual gate

Judge at both native size and nearest-neighbour 4x:

- silhouette matches the concept;
- the defining small objects are still individually readable;
- foreground and interior negative spaces are clean;
- highlights describe material and form instead of becoming noise;
- the asset does not become a dark mass after palette mapping;
- anchor and contact points do not drift.

Reject and regenerate when semantic objects disappear, perspective changes materially, legs or barrels merge, background leaks into holes, or broad cleanup rectangles remove structural pixels.

## Animation additions

For each animation state, repeat these invariants in the prompt:

- identical canvas and bottom-centre anchor;
- unchanged body proportions and palette;
- declared direction and angle;
- explicit origin for bullets, beams, flames, doors, feet, or contact effects;
- no frame cropping or camera motion;
- timing described by pose or effect phase, not merely “make it animated.”
