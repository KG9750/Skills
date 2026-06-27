---
name: xhs-post-packager
description: 'Create Xiaohongshu/XHS image-post packages from a topic: 5-10 portrait cards, cover background, humanized Chinese copy, caption, hashtags, alt text, checklist, publish payload, and zip. Use for 小红书 note/post, carousel cards, ready-to-upload manual packages, or publish-assist draft filling; never automate login, captcha, final publish, or private API bypass.'
---

# XHS Post Packager

## Outcome

Turn a topic into a hand-publishable Xiaohongshu package:

- 5-10 portrait PNG cards, 1080x1440 by default
- cover-first carousel structure with a clear hook and one idea per card
- `caption.md` with a substantive post body, 10+ search-oriented hashtags, alt text, and a manual publishing checklist
- `manifest.json`, `publish-payload.json`, and a `.zip` containing all publish assets

Do not automate Xiaohongshu login, session reuse, captcha handling, anti-bot workarounds, or any action that may bypass platform controls. Treat "publish" as "package for manual publishing" unless the user explicitly asks for publish assistance and accepts the account/session constraints.

Optional `publish-assist` mode means: open the official creator page in the user's browser, use the generated local files to fill a draft, and stop before the final publish/submit button. Never click the final publish button, schedule a live post, solve a captcha, scrape private platform APIs, or claim the post was published unless the user personally confirms it.

## Workflow

1. Define the brief.
   - Use the user's topic as the source of truth.
   - If missing and not risky, assume: general audience, practical tone, 6-8 cards, portrait card layout, no external claims.
   - Ask only when the topic has high-stakes claims, regulated advice, a named brand/person, a time-sensitive trend, or a required visual identity.

2. Validate factual risk.
   - Browse or verify when claims are current, medical, legal, financial, political, product-specific, or otherwise likely to have changed.
   - Do not invent citations, screenshots, user testimonials, prices, rankings, or platform rules.
   - Flag uncertain claims in the draft or rewrite them as opinion/experience.
   - For GitHub high-star project posts, verify the repository metadata at generation time: current star count, latest pushed/updated date, license when relevant, and the README/AGENTS or docs facts used in the post.

3. Write the post plan.
   - Create 5-10 cards. Prefer 6-8 unless the user specified a count.
   - Card 1: strong cover hook, concrete promise, no dense body text.
   - Make the cover structurally different from content pages: the title should be the main visual object, often occupying much of the upper half. Use a short, punchy headline that can be rendered very large.
   - For GitHub high-star project posts, use a unified cover badge: set slide 1 `kicker` to `Github高星好活儿`. Do not put the project URL or `owner/repo` path on the cover. Put cover metadata in 2 short bullets: one concrete applicable-scenario sentence, and one compact metadata line formatted as `Last Update：YYYY-MM-DD · <stars> ★`. Let the scenario wrap to a second line when needed; do not compress it into vague slash-separated keywords. The renderer draws the `★` icon in gold on the final cover.
   - Middle cards: one point per card, with enough concrete explanation to stand alone. Prefer a specific subhead plus 3-5 substantial bullets; avoid pages that are only labels, slogans, or two-line summaries.
   - Final card: summary, checklist, decision rule, or soft call to action.
   - Keep each card scannable on mobile: short headline, 3-5 bullets for content pages, no paragraph walls.
   - Keep inner pages text-only by default. Add line-art only when the user explicitly asks for inner-page illustrations or when a specific slide has a controlled `sketch` field.
   - Plan the caption as part of the post, not as an afterthought. The caption body may be more specific than the images: add context, concrete examples, use cases, limits, source notes, or a practical next step that would overcrowd the cards.
   - After the caption body is drafted, generate a separate hashtag set from the actual topic and wording. Include at least 10 tags to improve Xiaohongshu search discovery, mixing exact-topic tags, broader category tags, audience/use-case tags, and problem/intent tags.

4. Run a humanized copy pass.
   - Apply the anti-AI-writing rules in `references/post-spec.md` before writing `post_spec.json`.
   - Keep the post specific, source-honest, and human-sounding without faking personal experience, data, or certainty.
   - Recheck the cover title, slide bullets, caption body, hashtags, and alt text after this pass.
   - Treat `caption.body` as a first-class target of the humanized pass. It must not sound like generic AI-generated companion copy or a polite summary of the slides.

5. Generate a cover background when useful.
   - Use the built-in imagegen path to create one minimalist raster background from the cover headline, subhead, and topic.
   - Hard rule: never deliver the raw imagegen output as the cover. Treat it as a background asset only. The final cover must be rendered by `render_xhs_package.py`, which combines the imagegen background with the Kami-typed cover headline, subhead, bullets, page marker, and footer.
   - Before prompting imagegen, create a fresh art direction for this specific title. Define: topic category, subject metaphor, setting, visual material, composition, and palette. Do not reuse a prior cover's scene or palette unless the topic truly calls for it.
   - Use the visual direction routes in `references/post-spec.md` instead of a single reusable cover prompt.
   - Extract 2-4 concrete semantic anchors from the cover and bullets before prompting, such as objects, places, actions, states, data shapes, tools, or domain-specific artifacts. The generated image must visibly include at least one anchor.
   - Make it quiet but not empty: one clear supporting subject or scene layer, visible mostly in the lower-right or right half, with a clean text-safe area in the upper-left.
   - Choose a coherent palette from the topic, not from habit. It may be warm, cool, high-key, technical, natural, cultural, or product-like as long as it harmonizes with Kami typography. Avoid muddy gray, arbitrary mismatched colors, and defaulting to parchment/desk/window-light scenes.
   - Keep it refined and minimalist, not a busy illustration. Avoid readable text, logos, watermarks, fake UI labels, and repeated generic props such as notebook/desk/plant/window unless they are semantically necessary.
   - Inspect the generated image. Reject and regenerate if it is abstract filler, unrelated to the title, too dull, visibly low quality, contains text, repeats a previous cover style without reason, or conflicts with the card palette.
   - Save the selected image next to `post_spec.json`, for example `assets/cover-background.png`.
   - Put the relative path in `cover_background.path`. Add `cover_background.prompt`, `cover_background.art_direction`, and any rejected assets/reasons when available so the manifest preserves how the cover was made.
   - Skip imagegen for sober factual/high-stakes topics or when the user asks for text-only cards.

6. Create a post spec JSON.
   - Follow `references/post-spec.md`.
   - Save it in the task output directory as `post_spec.json`.
   - Prefer plain language and avoid exaggerated Xiaohongshu cliches unless the user's brand voice calls for them.
   - Write `caption.body` as publish-ready post text, usually 180-450 Chinese characters unless the user asks for a shorter note. It should add meaningful detail beyond the image cards while staying easy to paste into Xiaohongshu, then run the same anti-AI rewrite gate on the final caption text.
   - Write `caption.hashtags` as at least 10 relevant search tags, without `#` prefixes. Derive them from the title, topic, audience, tool/category, concrete use cases, and likely search phrases. Do not pad with unrelated broad tags.
   - Add `sources` when external facts, current claims, project metadata, or quoted source material were used.
   - Use `cover_background` only for the cover imagegen asset. Omit `illustrations` for text-only inner pages, use `illustrations.mode: "auto"` only when inner-page line art is desired, or per-slide `sketch` fields when the visual metaphor must be controlled.

7. Render and package.
   - Run:

```bash
python3 /Users/leo/.codex/skills/xhs-post-packager/scripts/render_xhs_package.py post_spec.json --out ./xhs-package
```

   - The script writes PNGs, caption/checklist files, `manifest.json`, `publish-payload.json`, and a zip archive.

8. Verify the package.
   - Confirm the image count is 5-10.
   - Open `slide-01.png`, not only the raw imagegen asset. Verify the rendered cover combines the background and Kami text into one coherent poster: readable title, aligned text block, visible but secondary background, and no conflict between image and copy. If `slide-01.png` has not been rendered, the cover is unfinished.
   - Confirm the cover grabs attention at phone-feed size: the headline should dominate the composition and remain readable at a glance.
   - For GitHub high-star project posts, confirm the cover badge reads `Github高星好活儿`, the cover does not show a URL or `owner/repo` path, the applicable scenario is concrete rather than a compressed keyword list, the metadata line uses `Last Update：YYYY-MM-DD · <stars> ★`, and the `★` icon renders in gold.
   - Confirm `caption.md` includes title, a concrete publish-ready body, and at least 10 relevant hashtags.
   - Confirm the caption has information gain over the images: context, examples, caveats, action advice, or source-backed detail. If it merely repeats slide headlines, rewrite `caption.body` and rerender.
   - Confirm the caption passes the humanized copy gate: no assistant residue, no formulaic contrast sentences, no generic filler ending, and no over-polished "AI summary" rhythm.
   - Confirm hashtags are search-oriented and topic-specific: include exact names/keywords, category labels, audience labels, and use-case phrases; remove duplicates and unrelated traffic tags.
   - Confirm inner pages contain concrete explanation, examples, conditions, or boundaries rather than only a few generic bullet labels.
   - Read the cover, two inner pages, and `caption.md` aloud or line-by-line. If they contain AI-ish filler, vague claims, forced slogans, or same-length sentence rhythm, revise `post_spec.json` and rerender.
   - Open `manifest.json` and check `warnings`. If layout warnings exist, inspect and rerender before handoff unless the warning is visibly harmless.
   - Confirm `publish-payload.json` exists and lists the title, body, hashtags, and slide image paths.
   - Report the final package directory and zip path.

## Publish Assist Mode

Use this only when the user explicitly asks to assist posting an already generated package.

1. Read `publish-payload.json` from the package directory.
2. Prefer the user's normal Chrome session when login state matters. If no logged-in session is available, ask the user to log in manually.
3. Navigate only to the official creator surface, usually `https://creator.xiaohongshu.com/`.
4. Upload the slide PNGs in filename order and fill title/body/hashtags from the payload.
5. Pause for the user to review all images, crop/order, visibility, location, permissions, and platform warnings.
6. Stop before any final publish, submit, schedule, or confirmation action. Tell the user the draft is filled and needs manual review/publish.
7. If the page asks for captcha, QR login, SMS, device verification, or unexpected permissions, stop and hand control back to the user.

## Visual Rules

- Use 1080x1440 portrait cards unless the user asks for another size.
- Keep text inside safe margins; do not let headlines or bullets overflow.
- Use contrast that survives phone screenshots and Xiaohongshu compression.
- Prefer Kami-style editorial cards: warm parchment, ivory panels, ink-blue accent, warm grays, and no hard shadows.
- The cover must be visually stronger than inner pages: oversized title, clear hook, and a distinct cover composition. It should not share the inner-page tag, vertical title rail, bullet layout, or footer-line structure.
- Avoid awkward line breaks. Do not split English words, code-like tokens, version numbers, formulas, or sentence-ending punctuation across lines.
- Use the imagegen cover background as a topic-specific atmosphere with one supporting subject, not as the main message.
- Judge the cover as a composite artifact. A good background alone is not enough; the background and Kami typography must look intentionally designed together.
- Keep inner pages text-first and image-free by default. Do not put generated raster backgrounds on inner pages; `cover_background` is for slide 1 only.
- Use line art as marginal annotation only when intentionally enabled. Keep it single-color, low contrast, and secondary to the headline.
- Choose simple visual metaphors: checklist, clock, book, bulb, chart, home, or leaf. If no metaphor is clear, use no sketch or a leaf.
- Do not place generated image assets on content pages unless the user explicitly asks; this skill's default generated-image path is cover background only.

## Resource Use

- Read [the post spec reference](references/post-spec.md) before writing the JSON spec.
- Use [the renderer script](scripts/render_xhs_package.py) for deterministic packaging.
- If the user supplies brand colors, fonts, images, or examples, adapt the spec while keeping the script's schema.
