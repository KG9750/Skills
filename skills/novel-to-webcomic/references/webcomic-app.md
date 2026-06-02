# Webcomic App Reference

Use this reference when creating a standalone React/Vite comic reader or adapting an existing frontend.

## Default Stack

Use React/Vite for a new standalone reader unless the user asks for static HTML or an existing app already has a clear framework.

If no app exists, copy `assets/vite-webcomic-template/` into the target project:

```bash
cp -R novel-to-webcomic/assets/vite-webcomic-template webcomic-reader
cd webcomic-reader
npm install
npm run dev
```

The reader fetches `public/asset-manifest.json` at runtime. Treat that manifest as the single source of truth. Do not hand-write a duplicate `src/data/comic.js`; if a JS module is required by another app, generate it mechanically from the manifest.

## Reader Structure

Minimum user-facing behavior:

- Title/header with chapter selector.
- Vertical panel/page feed optimized for mobile reading.
- Panel captions/dialogue rendered in HTML unless the user explicitly asks for embedded lettering.
- Reading progress indicator.
- Theme toggle or readable color mode.
- Keyboard-friendly controls for previous/next chapter.
- Source link when `source` exists in the manifest.
- Responsive desktop layout that keeps panels/pages centered and not oversized.
- Loading and error states for manifest fetch failures.

Recommended file organization:

```text
webcomic-reader/
  package.json
  index.html
  public/
    asset-manifest.json
    panels/
      page-001.png
  src/
    App.jsx
    main.jsx
    styles.css
```

## Manifest Shape

Use stable English keys so tooling can update assets without rewriting the app:

```json
{
  "title": "Moonlit Courier",
  "subtitle": "Finished comic sample",
  "language": "zh-CN",
  "format": "finished-comic-pages",
  "source": "https://example.com/source-story",
  "chapters": [
    {
      "id": "chapter-01",
      "title": "雨巷里的红信",
      "summary": "A courier accepts a dangerous delivery.",
      "panels": [
        {
          "id": "page-001",
          "image": "/panels/page-001.png",
          "alt": "A finished comic page showing the courier entering a rainy city.",
          "caption": "雨把整座城洗得像一张未干的画。",
          "dialogue": ["只要送到塔顶，一切就结束了。"],
          "sfx": "rain",
          "panelRange": "1-6",
          "prompt": "Finished full-color vertical comic page..."
        }
      ]
    }
  ]
}
```

Supported `format` values:

- `storyboard-panels`: one image per storyboard panel.
- `vertical-webtoon`: one image per webtoon panel.
- `finished-comic-pages`: one image per finished comic page containing multiple internal panels.
- `html-overlay-dialogue`: artwork plus HTML captions/dialogue overlay or adjacent text.

## Visual And Layout Rules

- Keep images in a fixed-width vertical column with `max-width` around 780-920px on desktop.
- Use `aspect-ratio` or explicit image dimensions for placeholders to prevent layout shift.
- For `finished-comic-pages`, reduce decorative card styling so images read as continuous comic pages.
- For storyboard or panel modes, light cards are acceptable for review and captions.
- Use short captions and dialogue blocks with strong contrast and enough line height.
- Avoid text overlap by rendering speech/dialogue beneath or over carefully reserved panel regions.
- Keep first viewport useful: title, current chapter, progress, source link if present, and the first panel/page or cover should be visible.
- Use actual bitmap art for final production. Placeholder SVGs are acceptable for script/layout review only.
- Base artwork should not include empty white speech balloons, caption boxes, or lettering placeholders. If the final reader needs on-image lettering, render white-backed text boxes in the HTML/SVG/CSS layer and place the caption/dialogue text inside those overlay boxes.

## Manifest Validation

Run the bundled validator before final delivery:

```bash
python /path/to/novel-to-webcomic/scripts/validate_manifest.py webcomic-reader
```

It checks JSON validity, supported `format`, non-empty chapters/panels, image file existence, required `id` and `alt`, and optional prompt constraints. Use `--strict-prompts` when final image prompts must enforce no text/no watermark.

## Browser QA

Before final delivery, run:

```bash
npm install
npm run build
npm run dev
```

Verify:

- Manifest validator passes.
- Desktop viewport: header, source link, chapter selector, image column, progress, and captions render correctly.
- Mobile viewport: no horizontal scroll, no text overlap, controls are reachable, images fit the screen.
- Interactions: chapter selector, next/previous chapter, theme toggle, and panel/page focus/progress work.
- Assets: every manifest `image` path returns HTTP 200 and at least the first image loads in-browser.
- Browser console/runtime errors are absent.
- Accessibility: image `alt` text exists, buttons have labels, keyboard focus is visible.
- Temporary QA screenshots or scratch files are removed before handoff.

If using Build Web Apps concept-first implementation for a new custom UI, keep the accepted concept path in notes and compare the running page against it before final handoff.
