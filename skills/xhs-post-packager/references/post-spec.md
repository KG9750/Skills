# XHS post package spec

Use this reference when creating `post_spec.json` for `render_xhs_package.py`.

## Contents

- JSON shape and field rules
- Imagegen cover background
- Line-art sketches
- Content standards, caption quality, and humanized copy gate
- Default carousel structures

## JSON shape

```json
{
  "title": "Post title for caption and manifest",
  "subtitle": "Optional short positioning line",
  "author": "Optional account or brand name",
  "sources": [
    {
      "name": "Source name",
      "url": "https://example.com",
      "checked_at": "2026-06-14",
      "note": "What fact this source supports"
    }
  ],
  "cover_background": {
    "path": "assets/cover-background.png",
    "prompt": "Final imagegen prompt used for the accepted background",
    "art_direction": "tech-project: abstract document blocks into data nodes",
    "accepted_asset": "assets/cover-background.png",
    "rejected_assets": [
      {
        "path": "assets/cover-background-rejected.png",
        "reason": "contained readable symbols"
      }
    ],
    "opacity": 0.58,
    "wash": 72,
    "text_wash": 136,
    "blur": 0
  },
  "illustrations": {
    "mode": "off"
  },
  "theme": {
    "name": "kami-paper",
    "background": "#f5f4ed",
    "card": "#faf9f5",
    "accent": "#1B365D",
    "tag_bg": "#EEF2F7",
    "text": "#141413",
    "muted": "#504e49",
    "stone": "#6b6a64",
    "border": "#e8e6dc",
    "border_soft": "#e5e3d8"
  },
  "caption": {
    "body": "发布正文，可包含换行；应比图片内容更具体，补充背景、例子、边界或行动建议。",
    "hashtags": ["小红书", "学习方法", "自我提升"]
  },
  "slides": [
    {
      "kicker": "01",
      "headline": "封面钩子",
      "subhead": "可选副标题",
      "bullets": ["短句 1", "短句 2"],
      "footer": "可选页脚",
      "alt": "给图片的替代文本"
    }
  ]
}
```

## Required fields

- `title`: required string.
- `caption.body`: required publish-ready post text.
- `slides`: required list of 5-10 cards.
- Each slide requires `headline`; `bullets` should be 0-5 short strings.
- Slide 1 is treated as the cover by the renderer. Write it as a cover hook: short, sharp, and visually dominant. The cover title should be able to occupy much of the upper half; keep bullets fewer than content pages.

## Optional fields

- `subtitle`, `author`
- `sources`: optional list for external facts, current project metadata, citations, or source-backed claims. Include `name`, `url`, `checked_at`, and a short `note`.
- `cover_background.path`: optional imagegen-generated minimalist background path for the cover card, relative to `post_spec.json`.
- `cover_background.prompt`: final prompt used for the accepted background.
- `cover_background.art_direction`: short category and visual direction chosen before prompting.
- `cover_background.accepted_asset`: accepted background path when different from `path` or when preserving provenance.
- `cover_background.rejected_assets`: optional list of generated-but-rejected assets with reasons.
- `cover_background.opacity`: background image opacity. Default is `0.58`.
- `cover_background.wash`: full-panel ivory wash alpha `0-255`. Default is `72`.
- `cover_background.text_wash`: extra ivory wash behind the title and bullets. Default is `136`.
- `cover_background.blur`: optional Gaussian blur radius. Default is `0`.
- `illustrations.mode`: `off` (default), `auto`, or `cover-only`.
- `illustrations.max_slides`: maximum number of cards with line-art sketches. Default is `0`; set it explicitly when enabling `auto`.
- `theme.background`, `theme.card`, `theme.accent`, `theme.tag_bg`, `theme.text`, `theme.muted`, `theme.stone`, `theme.border`, `theme.border_soft`
- slide `kicker`, `subhead`, `footer`, `alt`, `sketch`

## Imagegen cover background

When a cover would benefit from a visual base, generate one minimalist raster image with imagegen and save it next to `post_spec.json`, usually as `assets/cover-background.png`. The background should be quiet but not empty: include one clear visual subject or scene layer that supports the cover idea. The raw imagegen file is not the cover and must not be delivered as the cover; it is only a background layer. The final cover is `slide-01.png` after the renderer overlays Kami typography and card chrome.

Before prompting, create a fresh art direction for this title. Do not start from a reusable "warm paper desk by a window" prompt. Choose one route, then define:

- Subject metaphor: what object, scene, or abstraction expresses this title?
- Setting/material: workspace, landscape, product surface, data field, ritual object, architecture, screen glow, fabric, water, paper, etc.
- Composition: where the subject sits and where text-safe space lives.
- Palette: derived from the topic and still compatible with Kami text.

Visual direction routes:

- `tech-project`: abstract data space, product surface, code-free system blocks, network nodes, translucent UI-free panels, device silhouettes.
- `philosophy`: symbolic object, landscape, light/shadow, water, stone, fabric, architecture, negative space; avoid religious cliches unless requested.
- `lifestyle`: actual room/activity/object state, before-after trace, practical tools; use home/desk/window only if the topic demands it.
- `product-tool`: real product category, material close-up, workflow scene, interface-inspired abstract blocks without fake UI labels.
- `travel-place`: recognizable place cues, map-like forms, local texture, weather/light, route or architectural geometry.
- `personal-growth`: body-free ritual scene, threshold, path, mirror/reflection, calendar/time object, quiet symbolic motion.

Then extract concrete semantic anchors from the cover and slide plan:

- Objects: domain artifacts such as document planes, table grids, API blocks, storage objects, ritual objects, route markers, product materials.
- Places: only use locations that belong to the topic, such as abstract data space, library archive, kitchen counter, temple corridor, train platform, or workspace.
- Actions/states: parsed, transformed, compared, sorted, calm, focused, lightweight, before/after, threshold, return, reset.
- Avoid abstract-only prompts such as "soft shapes about productivity"; they usually produce irrelevant filler.
- Avoid habit prompts that always produce the same desk, notebook, plant, parchment wall, or window light unless those anchors are actually part of the topic.

Prompt imagegen from the cover content:

```text
Use case: stylized-concept
Asset type: Xiaohongshu cover background
Primary request: minimalist background inspired by "<cover headline>" and "<subhead>"
Art direction route: <tech-project | philosophy | lifestyle | product-tool | travel-place | personal-growth>
Style/medium: refined minimalist editorial image, topic-specific materials and depth, not icon-like
Scene/backdrop: include these semantic anchors from the post: <2-4 concrete anchors tied to this title>
Composition/framing: portrait cover background, visible subject in the lower-right or right half, large clean text-safe area in the upper-left, no central clutter
Color palette: one coherent palette chosen from the topic, compatible with Kami text; do not reuse the same warm parchment/sage/terracotta palette by default; avoid muddy gray and mismatched accents
Constraints: no readable text, no logo, no watermark, no border frame, no busy scene, no high contrast behind title area, no repeated default props unless semantically required
```

Quality gate:

- Relevant: at least one concrete anchor from the title or bullets is visible.
- Cohesive: palette is intentional, topic-specific, and coordinated with the card theme.
- Useful: upper-left text area stays clean; the subject lives mostly in the right/lower-right.
- Clean: no text, fake logo, watermark, random object, or noisy clutter.
- Provenance: record the accepted prompt and any rejected generated assets/reasons in `cover_background`.
- If any gate fails, regenerate before packaging.

Composite cover gate:

- Render the package and inspect `slide-01.png`, not just the background asset.
- The title, subhead, bullets, page marker, and footer must sit on top of the background with Kami spacing and hierarchy.
- If `slide-01.png` has not been rendered, the cover is unfinished even if the imagegen background exists.
- The cover must not look like a normal inner page with a picture behind it. It should have a larger, more attention-grabbing headline, fewer supporting lines, and a different structure from the inner-page tag/rail/footer layout.
- The background should support the copy and remain visibly connected to the topic, but it must not compete with the title block.
- If the composite feels like text pasted over an unrelated image, regenerate the background or adjust `opacity`, `wash`, and `text_wash`.

Then set:

```json
{
  "cover_background": {
    "path": "assets/cover-background.png",
    "prompt": "<final imagegen prompt>",
    "art_direction": "<route>: <specific visual idea>",
    "opacity": 0.58,
    "wash": 72,
    "text_wash": 136
  }
}
```

The renderer only uses `cover_background` on slide 1. It crops the image into the cover panel, applies opacity, adds a light full-panel wash, adds stronger ivory wash only behind the title and bullets, then draws the Kami cover text and chrome on top. Inner pages must stay text-first and must not use generated raster backgrounds.

## Line-art sketches

Use sketches sparingly. They are small hand-drawn line-art accents placed in the lower-right blank area when space allows.

- Default: omit `illustrations`; the renderer uses `off` and draws no inner-page sketches.
- Disable globally: `"illustrations": {"mode": "off"}`.
- Enable sparse auto sketches: `"illustrations": {"mode": "auto", "max_slides": 1}`.
- Cover only: `"illustrations": {"mode": "cover-only", "max_slides": 1}`.
- Disable one slide: `"sketch": "none"`.
- Force one slide: `"sketch": "checklist"` or `{"type": "clock"}`.

Supported sketch types: `auto`, `leaf`, `checklist`, `clock`, `book`, `bulb`, `chart`, `home`.

Auto selection uses content keywords:

- Room, storage, desk, home: `home`
- Checklist, steps, save, action: `checklist`
- Time, hours, schedule, efficiency: `clock`
- Study, reading, notes, knowledge: `book`
- Ideas, principles, methods: `bulb`
- Trends, data, growth, comparison: `chart`

Skip sketches when a page already feels dense, when the metaphor is unclear, or when the topic requires sober factual presentation.

## Content standards

- Write for mobile scanning. Prefer short phrases over complete essays.
- Put only one job on each card: hook, contrast, step, example, checklist, summary, or CTA.
- Make the cover specific and eye-catching: target reader + pain point + promise, with the shortest headline that still has force.
- Write the caption body as real post copy, usually 180-450 Chinese characters unless the user asks otherwise. It should add useful detail that cannot fit on the image cards.
- Give the caption information gain: background context, concrete examples, reader scenarios, caveats, source notes, setup steps, or a practical next action. Avoid a caption that only restates the slide headlines.
- Run the humanized copy gate on `caption.body` after writing the richer version. The caption often carries the strongest AI smell because it is longer than the cards.
- Use examples, numbers, and conditions where true. Avoid fake precision.
- Do not overuse emoji, exclamation marks, or "姐妹们/家人们/封神" unless requested.
- For educational posts, make the final card a checklist or action plan.
- For opinion posts, separate observation, reasoning, and personal stance.
- For product posts, distinguish facts, experience, and recommendation.

## Caption quality gate

Before rendering, check `caption.body` separately from the slides.

- It should be ready to paste into Xiaohongshu with natural paragraph breaks.
- It should say at least one concrete thing that does not appear verbatim on the images.
- For project/tool posts, include practical detail such as what the tool handles, who should try it, setup cost, limits, or a source-backed version note.
- For philosophy/lifestyle posts, include a small scene, a reflection question, a boundary, or a daily practice rather than generic comfort language.
- It must pass the same anti-AI rules as the slides: no assistant residue, no banned contrast formulas, no vague authority, no decorative conclusion, and no same-length sentence rhythm.
- Keep hashtags focused. Prefer 5-10 relevant tags over broad filler.

## Typography safety gate

Prevent ugly line breaks before writing `post_spec.json` and check them again after rendering.

- Do not split English words, project names, model names, code-like tokens, version numbers, formulas, or LaTeX snippets across lines.
- Avoid placing long English tokens near the end of a bullet. Move them earlier, shorten the line, or replace with a Chinese explanation.
- Do not let sentence-ending punctuation sit alone at the start of a line. Rewrite the sentence if needed.
- Keep cover headlines short enough to render oversized. If a title needs many words, move detail into `subhead` or the first bullet.
- For formulas or code-like text, prefer one compact token per line area, such as `effort=high` or `MinerU2.5-Pro`, instead of a long mixed sentence.

## Content density gate

Inner pages should feel useful after a single screenshot. Do not make them only a headline plus a few thin labels.

- Each non-cover content slide should usually include a `subhead` and 3-5 bullets.
- Make bullets substantial: each bullet should add a concrete detail, example, mechanism, condition, boundary, or next action.
- Avoid bare labels such as "效率更高", "适合新手", "注意风险" unless the same bullet explains why or how.
- Use compact descriptive lines instead of long paragraphs. A good bullet is often 18-38 Chinese characters; split if it carries two ideas.
- For project/tool posts, cover capability, workflow, limits, setup cost, and use cases across the carousel.
- For philosophy/lifestyle posts, use small scenes, relationship moments, emotional triggers, and practical reflection questions.
- If a slide has fewer than 3 bullets, it should be intentionally sparse: cover, transition, quote, summary, or CTA.

## Humanized copy gate

Run this gate before finalizing slide text, caption, hashtags, and alt text. The goal is not to make the post casual; it is to make it sound like a person with a clear point of view wrote it.

- Delete assistant residue: "当然", "希望这对你有帮助", "如果你想了解更多", "下面为你".
- Delete ceremonial openings and generic endings. Start with the point; end with a decision rule, checklist, boundary, or specific takeaway.
- Avoid vague authority: "专家认为", "行业报告显示", "很多人都说". Name the source or rewrite as observation/opinion.
- Avoid inflated words unless evidence supports them: "深刻", "关键", "赋能", "生态", "格局", "革命性", "重塑", "彰显", "体现".
- Ban obvious AI contrast formulas: "不是...而是", "不是...是", "不仅是...而是", "不只是...", "别只...". Say the useful thing directly unless the sentence is genuinely correcting a factual misunderstanding.
- Avoid forced three-part rhythm. Use two points, four points, or one stronger example when that is more natural.
- Vary sentence length. Mix short hooks with slightly longer explanatory lines; do not make every bullet the same shape.
- Prefer concrete nouns and verbs over abstract claims. "把 PDF 拆成文本、表格、公式" is better than "提升文档理解效率".
- Keep uncertainty honest. Use "适合/不适合", "我会这样判断", "边界是..." instead of pretending every point is universal.
- Remove decorative emoji and bold-label list patterns unless the user requested that style.

For project or tool posts:

- Use "能做什么 / 做不到什么 / 适合谁 / 上手成本" as the main frame.
- Mention stars, releases, benchmarks, or comparisons only when verified and listed in `sources`.
- Do not turn README facts into launch-event copy.

For philosophy, Buddhism, lifestyle, or personal-growth posts:

- Keep language warm but plain.
- Avoid fake aphorisms and over-polished "金句".
- Use everyday scenes, choices, and misunderstandings instead of abstract preaching.

## Default carousel structures

### Practical guide

1. Cover: pain point + result
2. Why it matters
3. Mistake 1
4. Better method 1
5. Better method 2
6. Example/template
7. Checklist
8. Save/share CTA

### Trend explanation

1. Cover: what changed
2. One-sentence answer
3. Background
4. Key evidence
5. What people misunderstand
6. What to do next
7. Risks/limits
8. Summary

### Personal experience

1. Cover: before/after or hard-won lesson
2. Context
3. Turning point
4. Specific method
5. Example
6. Result
7. Who it is for/not for
8. Takeaway
