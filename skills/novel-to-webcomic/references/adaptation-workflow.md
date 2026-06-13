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

When the user supplies a famous manga, artist, studio, or franchise as a reference, convert it into reusable craft terms: type structure, pacing, shot rhythm, lighting mood, emotional mechanics, and action clarity. Do not imitate exact line style, character design, signature gags, lettering, page layouts, or recognizable scenes. For *City Hunter* / 北条司 / 80s urban action comedy references, read `urban-action-style.md`; when the user asks for source-backed technique analysis or constraints, also read `city-hunter-technique-notes.md`.

## Mode Selection

- Use `storyboard-panels` for early pacing, rough layouts, or requests for 分镜.
- Use `finished-comic-pages` when the user asks for 直接出漫画, 成稿, 不要分镜, 完整漫画, or publishable comic pages.
- Use `html-overlay-dialogue` when the artwork should stay free of readable text and captions/dialogue should remain editable in HTML.

Default to `finished-comic-pages` for "make this into a comic webpage" if the user expects final comic art rather than a script.

When `finished-comic-pages` is selected, a text-only name pass is required before image prompts. Here "name pass" means a manga-style ネーム pass: a lightweight page script that assigns every panel beat, text line, and page block to a concrete visual subject before artwork generation. It is not necessarily a user-facing deliverable; it is a quality gate. Skip it only when the user explicitly asks for a rough single-page experiment with no rehearsal.

For all modes that generate artwork, the base image must stay free of empty white
speech balloons, empty caption rectangles, fake lettering areas, and other
dialogue placeholders. Reserve visual breathing room through composition only.
Add actual white-backed dialogue/caption boxes later in a separate lettering
layer, then place Chinese text inside those overlay boxes.

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

## Long Prose to Panel Breakdown

Do not adapt long prose by assigning one paragraph to one panel. First reduce the prose into decisions the reader can see, then rebuild those decisions as page and panel rhythm.

Use this pass before writing storyboard panels or finished pages:

1. **Chapter spine**: write the chapter promise, emotional direction, conflict, midpoint turn, climax, and final hook in 5-7 bullets.
2. **Scene selection**: keep scenes that change information, emotion, location, relationship, danger, or goal. Merge or cut purely explanatory prose.
3. **Visual inventory**: list concrete people, props, locations, body actions, weather, damage, distance, and expressions. Convert internal thought into these external signals first.
4. **Page allocation**: give more space to entrances, choices, reversals, reveals, fights, and quiet emotional beats. Summaries, travel, repeated worry, and exposition get fewer panels or captions.
5. **Panel transitions**: decide what the reader must infer between panels. Use:
   - moment-to-moment only for suspense, hesitation, pain, or micro-comedy;
   - action-to-action for clear physical progression;
   - subject-to-subject for conversations, searches, and cross-cut tension;
   - scene-to-scene for time/location jumps;
   - aspect-to-aspect for atmosphere, city texture, or emotional pause.
     Limit aspect-to-aspect to 1-2 uses per chapter unless the page plan states a clear reason. Use it when emotion needs to settle or location atmosphere must be established without plot movement.
6. **Dialogue compression**: keep dialogue that creates conflict, reveals character, changes the choice, or lands the beat. Replace explanatory dialogue with image information where possible.
7. **Lettering budget**: before final art, confirm every caption or speech line can fit a white-backed overlay box without covering the key face, hand, prop, or action.
8. **Text-image binding**: assign each line to a specific panel and visible object/person before writing image prompts or lettering coordinates. Dialogue belongs with the speaker or the reaction it causes; captions belong with the exact visual beat they summarize. If a line has no visible subject, rewrite the page beat or change the art plan before generation.

Panel beat test:

```markdown
For each panel, answer:
- What visibly changes from the previous panel?
- What must the reader infer in the gutter?
- Which exact story beat would break if this panel were removed?
- Is the text doing something the image cannot already do?
- Is every dialogue/caption line attached to the correct visible panel?
- Would any text still make sense if moved to another panel? If yes, make it more specific or cut it.
- Entry hook: what catches the reader's eye first on this page, and why?
- Exit hook: what pushes the reader to keep reading after the last panel?
```

If a panel fails this test, merge, cut, or rewrite it. If a page has no escalation, reveal, reversal, or emotional punctuation, rebuild the page plan before generating art.

## Page Composition Rhythm

Do not default finished comic pages to uniform horizontal strips. Compose pages around the emotional job of the beat:

### Panel Block Grouping

Before placing individual panels, divide each finished page into 2-4 functional blocks. Then assign panels inside those blocks. A page without block-level intent is usually just a list of equal-weight panels and should be restructured.

| Block type | Function | Typical shape |
| --- | --- | --- |
| Establishing block | Location, time, pressure, spatial layout | 1 wide or large panel |
| Exchange block | Dialogue, call-and-response, confrontation | 2-4 medium or side-by-side panels |
| Action block | Physical movement and cause-effect chain | 2-4 panels with clear direction |
| Reaction block | Close-up, realization, emotional pause | 1-2 close-up or insert panels |
| Payoff block | Reversal, punchline, cliffhanger, afterbeat | 1 dominant or paired panel |

- **Large dominant panel**: use for the page's strongest emotion, location pressure, decisive action, or reveal.
- **Wide panel**: use for city pressure, rain, crowding, pursuit direction, or establishing geography.
- **Vertical panel**: use for isolation, falling/rising distance, doorways, alleys, thresholds, and surveillance.
- **Small insert**: use for phone balance, wound, hand choice, object clue, payment, or tiny reaction.
- **Side-by-side pair**: use for contrast, call-and-response dialogue, before/after choice, or two simultaneous subjects.

Before image generation, write a page layout line such as:

```text
Asymmetrical manga page layout: one large lower-half alley panel, two small phone/face inserts, one narrow vertical reaction panel, one wide top establishing panel; varied panel sizes, not equal horizontal strips.
```

For final art prompts, explicitly say what each major panel shows and why it is large, small, wide, vertical, side-by-side, or dominant. A page with only evenly stacked panels should be rejected unless the user's requested format is a deliberately simple vertical storyboard or the page plan explicitly uses monotony for emotion.

### Thumbnail Gate

Before generating full-resolution finished pages, create a thumbnail plan for each page. It can be text-only layout notation or a low-resolution rough, but it must answer:

1. How many functional panel blocks are on the page, and what job does each block do?
2. What is the entry hook: the first visual anchor the eye should land on?
3. What is the exit hook: the final beat that creates page-turn pressure?
4. What is the intended 2-3 step reading path through the page?
5. Are there competing focal points that would confuse that path?
6. Does the largest panel carry the page's strongest emotional or action beat?

Reject and revise the thumbnail before full artwork if these answers are weak.

### Panel Transition Rhythm

Review adjacent panel transitions before final art. A page that overuses one transition type becomes monotonous or confusing.

- `moment-to-moment`: max 2 consecutive; use for suspense, hesitation, pain, or micro-comedy.
- `action-to-action`: default for clear physical sequences; can chain when direction stays readable.
- `subject-to-subject`: default for conversations, searches, and cross-cut tension.
- `scene-to-scene`: once per page unless the page is an intentional montage.
- `aspect-to-aspect`: 1-2 per chapter; use for atmosphere or emotional pause, not filler.

List the transition chain in the page plan, such as `scene-to-scene -> subject-to-subject x3 -> action-to-action x2 -> aspect-to-aspect`. If all transitions are the same, add variety or state why the monotony is intentional.

## Lettering Distinction

Use separate wording and typography rules for captions, dialogue, phone UI, and SFX:

- **Caption/description**: no quotation marks; concise visual or time/emotion bridge.
- **Dialogue/speech**: final visible Chinese speech must use Chinese quotation marks, e.g. `“能治吗？”`. This applies to speech balloons, white-backed boxes, and phone/chat dialogue that is presented as spoken or messaged dialogue.
- **Phone/message UI**: can use sender labels or UI-style labels, but avoid copying real app branding.
- **SFX**: short sound text; keep it visually distinct but still inside the chosen lettering convention if the project requires white-backed boxes.

When using an HTML/SVG/CSS lettering layer, store the text type so dialogue can automatically receive quotation marks while captions remain unquoted. If source data or `adaptation.md` keeps raw dialogue text, the renderer must add Chinese quotes before the visible final page is exported.

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
  - Mei: “只要送到塔顶，一切就结束了。”
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
- Keep text and image matched: do not attach a line to a panel that depicts an unrelated action.
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
  - 严存: “现实还没发生。”
- Prompt: Finished full-color vertical comic page, contemporary subway thriller...
- Negative prompt: no exact artist/style copy, no copied character design, no readable text, no logo, no watermark
- Asset: public/panels/page-001.png
- Alt: A finished comic page showing the protagonist seeing a red danger trajectory in a crowded subway.
```

For finished pages, prompt the page as a single composed comic sheet rather than separate isolated panels. The prompt should describe a varied page design with large, small, wide, vertical, and insert panels chosen for story purpose. Follow the clean-art rule in Mode Selection; if readable dialogue is needed, create boxes in the later HTML/SVG/CSS lettering layer.

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
2. Inspect the output for character consistency, action clarity, clean gutters, mobile readability, and clean-art compliance from Mode Selection.
3. For project assets, copy selected images from `~/.codex/generated_images/...` into the workspace under `public/panels/`. Preserve the originals in `~/.codex/generated_images/...`.
4. Use `c01-p001.png` names for storyboard panel assets and `page-001.png` names for finished page assets.
5. Update `public/asset-manifest.json` after copying assets.
6. Re-run manifest validation and browser QA.

Do not leave project-referenced artwork only under `~/.codex/generated_images/...`.

## Pre-Delivery Rejection Checklist

Run this checklist on every finished page before delivery. Any `YES` is a rejection and requires revision, regeneration, or re-lettering.

| # | Rejection condition |
| --- | --- |
| 1 | Page reads as rough wireframe/storyboard instead of finished comic art when final art was requested. |
| 2 | Page uses only equal-height horizontal strips without a stated emotional or formal reason. |
| 3 | Finished-page mode skipped the name pass or thumbnail gate without explicit user request for a rough experiment. |
| 4 | Base art contains blank white speech/caption placeholders, fake text, generated labels, logos, or watermarks. |
| 5 | Dialogue sits on a panel that does not contain the speaker or the immediate reaction to that line. |
| 6 | Caption describes a beat that is not visible in its panel. |
| 7 | Visible Chinese dialogue lacks Chinese quotation marks, or captions/descriptions incorrectly use quotation marks. |
| 8 | Page has no clear entry hook, exit hook, escalation, reveal, reversal, or emotional punctuation. |
| 9 | Reading path is unclear because competing focal points fight the intended panel order. |
| 10 | Panel transition chain is all one type without a stated reason. |
| 11 | Character appearance contradicts the visual bible or previously approved reference page. |
| 12 | Text boxes cover key faces, hands, wounds, clues, action contact points, or the emotional focal point. |

## Image Prompt Pattern

Use this prompt base and adapt it per panel/page:

```text
Finished full-color vertical comic page, [character anchor], [story action],
[setting], [composition/page layout], [lighting and palette], expressive comic
storytelling, clean gutters, readable at mobile width, no text, no readable text,
no blank speech balloons, no blank caption boxes, no logo, no watermark,
no exact artist/style copy, no copied character design, aspect ratio 9:16.
```

When a safe urban action influence is requested, use craft language instead of named-style imitation:

```text
urban action comic pacing, clean stylish city suspense, cinematic city framing,
sharp movement diagonals, expressive reaction beats, clear action geography,
focused professional timing, original character designs, no recognizable protected scene
```

Dialogue and captions should stay in HTML/SVG/CSS by default so they remain editable, accessible, and localizable. When producing a lettered final page, draw the white-backed speech/caption boxes in that overlay layer and place the Chinese text inside those boxes; keep the base art clean as defined in Mode Selection.
