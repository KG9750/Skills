---
name: novel-to-webcomic
description: Adapt user-provided, licensed, or public-domain prose into comic scripts, storyboards, finished page assets, image prompts, manifests, and React/Vite webcomic readers. Use for 小说改编漫画, 直接出漫画, webtoon, manga, manhua, storyboard, panel script, 成稿漫画网页, 都市动作漫画, hardboiled action-comedy cases, source-safe retro urban action pacing, or City Hunter technique analysis.
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

Finished artwork and rough comic bases must not contain empty white speech balloons,
caption boxes, or other dialogue placeholders baked into the image. Generate clean
art only, then add readable Chinese captions/dialogue later through an HTML/SVG/CSS
lettering layer that draws its own white-backed text boxes.

## First Checks

1. Confirm the source is user-provided, licensed, public-domain, or summarized by the user. If the user asks to adapt a copyrighted novel they did not provide, ask for licensed text or a short user-written summary instead.
2. Avoid reproducing long passages from source prose. Convert scenes into visual action, shortened captions, and comic-native dialogue.
3. Choose an output mode:
   - `storyboard-panels`: one image per panel, best for pacing review.
   - `finished-comic-pages`: one image per finished comic page containing multiple internal panels, best when the user asks for 直接出漫画, 成稿, 不要分镜, or final comic artwork.
   - `html-overlay-dialogue`: artwork has no readable text; captions/dialogue are rendered by HTML for editability and mobile fit.
4. Identify art direction, rating/tone, chapter count, language, target reader, whether images should be generated now or only planned, and whether the final lettering should be HTML, SVG, or CSS overlay.
5. For long prose, do not move directly from manuscript paragraphs to panels. First extract a chapter spine, select only scenes that change plot, emotion, or power relation, then break those scenes into page turns and panel beats.
6. Separate lettering types before final output: dialogue/speech should be visibly distinguished from captions, and final visible Chinese dialogue must be wrapped in Chinese quotation marks inside the lettering box unless the user requests another convention. Captions/descriptions stay unquoted.

## Style Reference Boundary

When the user names a famous manga, comic, artist, studio, or franchise, use only broad visual principles such as pacing, genre language, composition density, camera rhythm, lighting mood, or action clarity.

- Allowed: "都市动作漫画节奏、强烈斜线构图、冷峻城市惊险感."
- Avoid: copying a named artist's exact line style, character design, signature expressions, panel layouts, lettering, logos, or recognizable scenes.
- Image prompts should include negative constraints such as `no exact artist/style copy, no copied character design, no readable text, no blank speech balloons, no blank caption boxes, no logo, no watermark`.
- If the user cites *City Hunter*, 北条司, 80s urban hardboiled action comedy, or similar references, read `references/urban-action-style.md` and translate the reference into type structure, pacing, city staging, emotional reveals, and action clarity. Do not reproduce the source work's characters, gags, weapons staging, exact page designs, lettering, or recognizable scenes.

## Retro Urban Action Manga Mode

Use this mode inside `novel-to-webcomic` when the user asks for 都市动作漫画, 侦探漫画, 委托型漫画, hardboiled action-comedy storyboards, retro 1980s-1990s urban manga mood, or City Hunter technique analysis.

- Build original cases, characters, locations, visual motifs, and panel plans. Do not create a separate skill handoff.
- Translate City Hunter-era influence into craft language: cinematic manga paneling, realistic city backgrounds, adult-proportion character design, clear action causality, pressure-release comedy timing, and commission-driven story structure.
- Do not ask for work "in the style of Tsukasa Hojo", "北条司风格", or any living-artist imitation. Avoid franchise character names, exact props, catchphrases, costumes, layouts, gags, or recognizable scenes.
- Modernize dated sexual-comedy dynamics. Preserve ego puncture, status loss, social misread, slapstick consequence, and fast tonal recovery without normalizing harassment.

Before writing panels or prompts, define the craft spine:

1. **City function**: assign each location a job, such as commission point, information point, surveillance perch, chase corridor, retreat point, or emotional quiet point.
2. **Action causality**: every action sequence needs a target, obstacle, tactical choice, visible consequence, and changed power relation.
3. **Distance map**: track who is close, separated, watching, blocked, or crossing a threshold.
4. **Tone switch**: place comedy after pressure has accumulated, then return quickly to the case objective.
5. **Character states**: keep serious/professional, private/vulnerable, and comic-break states connected by stable silhouette anchors.

For original retro urban action prompts, use this pattern:

```text
Original retro 1980s-1990s urban action manga panel, [shot size and angle],
[fictional city location and function], [original character description],
[specific action with cause and consequence], cinematic paneling,
realistic city background detail, expressive but non-franchise character design,
[black-and-white ink / limited color / screentone], [lighting and mood].
Negative: living artist imitation, franchise characters, recognizable City Hunter scene,
exact copied panel layout, logo, watermark.
```

## Workflow

1. **Intake and scope**: collect source text, rights boundary, chapter boundaries, output mode, language, visual style, and publishing constraints.
2. **Adaptation**: extract beats, compress scenes, choose panel/page count, rewrite narration into visual action, plan panel-to-panel transitions, and keep dialogue short.
   - For `finished-comic-pages`, a text-only name pass is mandatory before image prompts. It must confirm panel beats, page blocks, entry/exit hook, reading path, and text-image binding for every page.
3. **Visual bible**: define recurring character anchors, locations, props, palette, lighting, shot language, continuity rules, and style-reference boundaries.
4. **Image plan**: write prompts with character anchors, page composition, mood, negative constraints, aspect ratio, and exact output path. Prompts must follow the clean-art rule in the Overview.
   - For `finished-comic-pages`, do a thumbnail gate before full-resolution art: confirm panel block grouping, dominant panel, entry hook, exit hook, and reading path.
5. **Artwork production**: for final art, generate one style sample or first comic page before a large batch when the task allows iteration; copy selected outputs from `~/.codex/generated_images/...` into `public/panels/` and keep originals in place.
6. **Lettering layer**: add captions/dialogue after artwork generation by drawing white-backed text boxes in HTML/SVG/CSS. Position Chinese text inside those boxes; do not rely on image-generated blank areas. Match every text box to the panel content it describes or the character/object that speaks.
7. **Web build**: use an existing frontend if present; otherwise copy `assets/vite-webcomic-template/` into the project and populate `public/asset-manifest.json` and assets.
8. **QA**: run manifest validation, build the app, verify desktop/mobile rendering, confirm source links and controls work, check assets load, and visually inspect that dialogue quotation, panel layout variety, and text-image matching all pass.

Read [adaptation workflow](references/adaptation-workflow.md) when planning story adaptation, output mode, comic scripts, or image prompts. Read [urban action style](references/urban-action-style.md) when the user asks for City Hunter-like, 80s urban action, hardboiled comedy, private-justice, or stylish city suspense influence. Read [City Hunter technique notes](references/city-hunter-technique-notes.md) when the user asks specifically for City Hunter, Tsukasa Hojo, technique analysis, source-backed notes, or style constraints. Read [webcomic app notes](references/webcomic-app.md) when building or modifying the React/Vite reader. Use [manifest validation](scripts/validate_manifest.py) before final delivery and [the Vite webcomic template](assets/vite-webcomic-template/package.json) when no existing app is available.

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
- Each panel should carry one visible action, reaction, reveal, or mood turn; if a prose sentence does not change what the reader can see or infer, merge it into a nearby panel or cut it.
- Page plans should be built around page-turn beats: establish, escalate, reveal, reverse, or cliffhanger. Avoid even, mechanical paragraph-to-panel mapping.
- Finished-page plans must pass a name pass and thumbnail gate before full artwork unless the user explicitly asks for a rough single-page experiment.
- Before writing image prompts or lettering coordinates, bind every caption/dialogue/SFX line to a target page panel and visible subject: speaker, reaction, prop, location, wound, phone, or action. If no suitable visual subject exists, rewrite the beat or regenerate/recompose the page.
- Final visible Chinese dialogue must use Chinese quotation marks, e.g. `“能治吗？”`. Captions and pure descriptions must not use quotation marks. If the data model stores dialogue without quotes, the lettering renderer must add them automatically before output.
- Finished page layouts should vary panel scale and direction according to emotion and story function: wide panels for location/pressure, vertical panels for isolation or pursuit, small inserts for phone/props/injury details, side-by-side panels for contrast or call-and-response, and large dominant panels for the page's emotional or action peak. Reject simple equal-height top-to-bottom strips unless that monotony is intentionally serving the scene and is stated in the page plan.
- Text-image matching is mandatory: a dialogue line must sit on the same panel as the speaker or the immediate reaction to that line; a caption must describe the exact visible beat under it. Do not place a line next to an unrelated action just because there is empty space.
- Finished pages should be real comic artwork, not wireframe-like SVG placeholders, unless the user asked for rough structure.
- Base art must follow the clean-art rule in the Overview: no placeholder lettering areas, fake balloons, fake text, or generated labels.
- Character descriptions and generated artwork must stay consistent enough for chapter continuity.
- The webpage must be responsive, readable on mobile, keyboard accessible for key controls, and free of text/panel overlap.
- Run `scripts/validate_manifest.py` against the generated project before final delivery.
- Final answers should mention output mode, created assets, validation/build/browser checks, and any remaining placeholder or ungenerated art.
