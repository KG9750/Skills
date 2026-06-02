# Adaptation Workflow

Use this reference when converting prose, chapter outlines, or user summaries into a comic/webtoon production plan.

## Intake

Collect only what materially changes the adaptation:

- Source: user-provided text, licensed excerpt, public-domain work, or user-written summary.
- Output mode: `storyboard-panels`, `finished-comic-pages`, or `html-overlay-dialogue`.
- Target: vertical webtoon, finished comic pages, manga/manhua-style page rhythm, or browser reader.
- Scale: panels/pages per chapter, chapters to adapt, image generation now vs prompt-only.
- Tone: genre, age rating, pacing, color mood, visual references supplied by the user.
- Language: write story outputs in the user's language; keep file names and JSON keys in English.

If the source is copyrighted and not provided by the user, request a licensed excerpt or short summary. Do not invent detailed scene-by-scene adaptation from a copyrighted book the user has not supplied.

When the user supplies a famous manga, artist, studio, or franchise as a reference, convert it into reusable craft terms: type structure, pacing, shot rhythm, lighting mood, emotional mechanics, and action clarity. Do not imitate exact line style, character design, signature gags, lettering, page layouts, or recognizable scenes. For *City Hunter* / 北条司 / 80s urban action comedy references, read `urban-action-style.md`.

## Mode Selection

- Use `storyboard-panels` for early pacing, rough layouts, or requests for 分镜.
- Use `finished-comic-pages` when the user asks for 直接出漫画, 成稿, 不要分镜, 完整漫画, or publishable comic pages.
- Use `html-overlay-dialogue` when the artwork should stay free of readable text and captions/dialogue should remain editable in HTML.

Default to `finished-comic-pages` for "make this into a comic webpage" if the user expects final comic art rather than a script.

## Beat Extraction

Convert prose into production beats before writing panels/pages:

```markdown
# adaptation.md

## Logline
One sentence for the chapter's dramatic promise.

## Beat Sheet
1. Setup: location, character state, visual hook.
2. Inciting action: what changes on screen.
3. Escalation: conflict, reveal, or emotional turn.
4. Climax: strongest visual moment.
5. Button: transition, cliffhanger, or quiet afterbeat.

## Scene List
| Scene | Purpose | Location | Characters | Panels/Pages |
| --- | --- | --- | --- | --- |
| S01 | Establish the promise | Subway door | Yan Cun, commuters | page-001 |
```

Compress internal monologue into visible choices, props, expressions, and short captions. Keep only narration that adds meaning the image cannot carry.

For urban action comedy or private-justice chapters, add a craft pass after beat extraction:

- Surface mask: what makes the lead seem weak, unserious, low-status, or unreliable?
- Professional core: what exact timing, observation, or physical choice proves competence?
- Emotional client truth: what wound, secret, or need makes the case matter?
- Comedy release valve: where does tension break for one beat before danger returns?
- City stage: which location detail makes geography, danger, and loneliness readable?
- Afterbeat: does the ending return to humor, restraint, or quiet melancholy?

## Storyboard Panels

Use this format for `storyboard-panels`:

```markdown
### Panel c01-p001
- Beat: Establish the rain-soaked city and the protagonist's problem.
- Shot: Wide vertical establishing shot, high angle.
- Visual: Neon umbrellas crowd a narrow alley; Mei grips a sealed red envelope.
- Characters: Mei, anxious, soaked hair tucked behind one ear.
- Caption: 雨把整座城洗得像一张未干的画。
- Dialogue:
  - Mei: 只要送到塔顶，一切就结束了。
- SFX: drip drip
- Prompt: Vertical webtoon panel, rain-soaked neon alley, young courier...
- Negative prompt: no exact artist/style copy, no copied character design, no readable text, no logo, no watermark
- Asset: public/panels/c01-p001.png
- Alt: Mei stands in a crowded rainy neon alley holding a red envelope.
```

Panel rules:

- One clear action or emotional turn per panel.
- Use varied shots: establishing, medium, close-up, insert, reaction, transition.
- Preserve spatial continuity across consecutive panels.
- Keep dialogue short enough to fit speech balloons.
- Prefer present-tense visual descriptions.
- Avoid camera language that cannot be seen in the generated image.

## Finished Comic Pages

Use this format for `finished-comic-pages`:

```markdown
### Page page-001
- Internal panels: 1-6
- Story range: Cold open, danger detail inserts, protagonist pressure.
- Page composition: One tall 9:16 page sheet with clean gutters and 4-7 internal comic panels.
- Caption: 第一页：危险先于现实亮起。
- Dialogue:
  - 严存: 现实还没发生。
- Prompt: Finished full-color vertical comic page, contemporary subway thriller...
- Negative prompt: no exact artist/style copy, no copied character design, no readable text, no logo, no watermark
- Asset: public/panels/page-001.png
- Alt: A finished comic page showing the protagonist seeing a red danger trajectory in a crowded subway.
```

For finished pages, prompt the page as a single composed comic sheet rather than separate isolated panels. Keep image text out of the art unless the user explicitly requests embedded lettering.

## Chapter Density

- 6-10 panels or 1-2 pages: pitch/sample, one scene, fast proof of concept.
- 20-35 panels or 4-6 pages: short webtoon episode.
- 40-70 panels or 7-12 pages: full webtoon chapter with multiple scenes.

If the user does not specify, choose the smallest count that preserves the emotional arc and say whether it is a sample, short episode, or full chapter.

## Visual Bible

Use `visual-bible.md` to stabilize generation and handoff:

```markdown
# visual-bible.md

## Art Direction
- Format: finished full-color vertical comic pages, mobile-first reading.
- Palette: cold subway blue-gray, emergency red, warm skin reactions.
- Line/Render: clean comic rendering, readable action, expressive faces.
- Style Mechanics: urban action pacing, clean city suspense, pressure-release comedy beats, clear action geography.
- Avoid: exact artist/style copy, copied character designs, readable fake text, logos, watermarks.

## Characters
### Yan Cun
- Role: protagonist, outsourced algorithm tester.
- Face/Hair: short black hair, tired analytical eyes.
- Costume: gray-blue commuter jacket.
- Prompt anchor: "Yan Cun, tired 29-year-old Chinese outsourced algorithm tester..."

## Locations
### Subway Carriage
- Metal doors, crowded commuters, cold fluorescent light, platform gap.
```

Keep prompt anchors consistent across all pages. If image generation produces a final character reference, update prompt anchors to match it.

## Project-Bound Image Generation

When generating final artwork with imagegen:

1. Generate a style sample or first finished page when style consistency is high risk.
2. Inspect the output for character consistency, action clarity, clean gutters, mobile readability, and absence of readable fake text, logo, or watermark.
3. For project assets, copy selected images from `~/.codex/generated_images/...` into the workspace under `public/panels/`. Preserve the originals in `~/.codex/generated_images/...`.
4. Use `c01-p001.png` names for storyboard panel assets and `page-001.png` names for finished page assets.
5. Update `public/asset-manifest.json` after copying assets.
6. Re-run manifest validation and browser QA.

Do not leave project-referenced artwork only under `~/.codex/generated_images/...`.

## Image Prompt Pattern

Use this prompt base and adapt it per panel/page:

```text
Finished full-color vertical comic page, [character anchor], [story action],
[setting], [composition/page layout], [lighting and palette], expressive comic
storytelling, clean gutters, readable at mobile width, no readable text, no logo,
no watermark, no exact artist/style copy, no copied character design, aspect ratio 9:16.
```

When a safe urban action influence is requested, use craft language instead of named-style imitation:

```text
urban action comic pacing, clean stylish city suspense, cinematic city framing,
sharp movement diagonals, expressive reaction beats, clear action geography,
focused professional timing, original character designs, no recognizable protected scene
```

Dialogue and captions should stay in HTML by default so they remain editable, accessible, and localizable.
