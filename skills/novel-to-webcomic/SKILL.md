---
name: novel-to-webcomic
description: Use when adapting user-provided, licensed, or public-domain novels, chapters, outlines, or prose into comics, webtoons, manga, manhua, graphic-novel scripts, finished comic page assets, image prompts, asset manifests, and React/Vite webcomic webpages. Triggers include requests like 把小说改编成漫画, 直接出漫画, 成稿漫画网页, 小说转漫画网页, webtoon, manga, manhua, comic adaptation, storyboard, panel script, safe City Hunter-like urban action pacing, or webcomic reader.
---

# Novel to Webcomic

## Overview

Use this skill to turn prose into a web-ready comic adaptation. Default to Chinese-friendly narrative output when the user writes in Chinese, while keeping code, file names, and JSON keys in English.

The normal deliverable is a production-oriented package:

- `adaptation.md` for story beats, scene/page plan, captions, and dialogue.
- `visual-bible.md` for character, location, mood, palette, shot language, style boundaries, and image prompt rules.
- `public/asset-manifest.json` as the single runtime source of truth.
- Generated or user-provided comic assets under `public/panels/`.
- A React/Vite webcomic reader, either inside an existing app or copied from `assets/vite-webcomic-template/`.

## First Checks

1. Confirm the source is user-provided, licensed, public-domain, or summarized by the user. If the user asks to adapt a copyrighted novel they did not provide, ask for licensed text or a short user-written summary instead.
2. Avoid reproducing long passages from source prose. Convert scenes into visual action, shortened captions, and comic-native dialogue.
3. Choose an output mode:
   - `storyboard-panels`: one image per panel, best for pacing review.
   - `finished-comic-pages`: one image per finished comic page containing multiple internal panels, best when the user asks for 直接出漫画, 成稿, 不要分镜, or final comic artwork.
   - `html-overlay-dialogue`: artwork has no readable text; captions/dialogue are rendered by HTML for editability and mobile fit.
4. Identify art direction, rating/tone, chapter count, language, target reader, and whether images should be generated now or only planned.

## Style Reference Boundary

When the user names a famous manga, comic, artist, studio, or franchise, use only broad visual principles such as pacing, genre language, composition density, camera rhythm, lighting mood, or action clarity.

- Allowed: "都市动作漫画节奏、强烈斜线构图、冷峻城市惊险感."
- Avoid: copying a named artist's exact line style, character design, signature expressions, panel layouts, lettering, logos, or recognizable scenes.
- Image prompts should include negative constraints such as `no exact artist/style copy, no copied character design, no readable text, no logo, no watermark`.
- If the user cites *City Hunter*, 北条司, 80s urban hardboiled action comedy, or similar references, read `references/urban-action-style.md` and translate the reference into type structure, pacing, city staging, emotional reveals, and action clarity. Do not reproduce the source work's characters, gags, weapons staging, exact page designs, lettering, or recognizable scenes.

## Workflow

1. **Intake and scope**: collect source text, rights boundary, chapter boundaries, output mode, language, visual style, and publishing constraints.
2. **Adaptation**: extract beats, compress scenes, choose panel/page count, rewrite narration into visual action, and keep dialogue short.
3. **Visual bible**: define recurring character anchors, locations, props, palette, lighting, shot language, continuity rules, and style-reference boundaries.
4. **Image plan**: write prompts with character anchors, composition, mood, negative constraints, aspect ratio, and exact output path.
5. **Artwork production**: for final art, generate one style sample or first comic page before a large batch when the task allows iteration; copy selected outputs from `~/.codex/generated_images/...` into `public/panels/` and keep originals in place.
6. **Web build**: use an existing frontend if present; otherwise copy `assets/vite-webcomic-template/` into the project and populate `public/asset-manifest.json` and assets.
7. **QA**: run manifest validation, build the app, verify desktop/mobile rendering, confirm source links and controls work, and check assets load.

Read `references/adaptation-workflow.md` when planning story adaptation, output mode, comic scripts, or image prompts. Read `references/urban-action-style.md` when the user asks for City Hunter-like, 80s urban action, hardboiled comedy, private-justice, or stylish city suspense influence. Read `references/webcomic-app.md` when building or modifying the React/Vite reader.

## Build Web Apps Coordination

For a new webcomic webpage or reader UI, follow the Build Web Apps concept-first habit: define a concise visual direction before coding, then implement a real usable reader instead of a static mockup.

- Prefer React/Vite for new standalone webcomic pages.
- Keep the first screen focused on the comic title, chapter controls, source link if present, and the first panel/page or cover.
- Use real local state for chapter selection, reading progress, theme mode, and panel/page focus.
- Use generated or user-provided bitmap artwork for final production; placeholders are acceptable only for script/layout review.
- Browser-test at least one desktop viewport and one mobile viewport before delivery.

## Output Contract

When generating project files, use this minimum structure unless an existing app dictates a different convention:

```text
adaptation.md
visual-bible.md
webcomic-reader/
  package.json
  index.html
  public/
    asset-manifest.json
    panels/
  src/
```

`public/asset-manifest.json` is the runtime source of truth. Keep stable English keys:

```json
{
  "title": "Comic title",
  "subtitle": "Optional subtitle",
  "language": "zh-CN",
  "format": "finished-comic-pages",
  "source": "https://example.com/source-story",
  "chapters": [
    {
      "id": "chapter-01",
      "title": "Chapter title",
      "summary": "Short chapter summary",
      "panels": [
        {
          "id": "page-001",
          "image": "/panels/page-001.png",
          "alt": "Accessible description",
          "caption": "Optional caption",
          "dialogue": ["Optional speech line"],
          "sfx": "Optional SFX label",
          "panelRange": "1-6",
          "prompt": "Image generation prompt"
        }
      ]
    }
  ]
}
```

Use `c01-p001.png` style names for `storyboard-panels`; use `page-001.png` style names for `finished-comic-pages`.

## Quality Bar

- The adaptation should read like a comic production plan, not prose pasted into panels.
- Finished pages should be real comic artwork, not wireframe-like SVG placeholders, unless the user asked for rough structure.
- Character descriptions and generated artwork must stay consistent enough for chapter continuity.
- The webpage must be responsive, readable on mobile, keyboard accessible for key controls, and free of text/panel overlap.
- Run `scripts/validate_manifest.py` against the generated project before final delivery.
- Final answers should mention output mode, created assets, validation/build/browser checks, and any remaining placeholder or ungenerated art.
