#!/usr/bin/env python3
"""Render structured JSON into a self-contained doc-style-CH HTML document."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = SKILL_ROOT / "assets" / "document-shell.html"
BLOCK_TYPES = {
    "paragraph",
    "bullets",
    "steps",
    "quote",
    "callout",
    "table",
    "code",
    "divider",
    "image",
}
PLACEHOLDERS = {
    "DOCUMENT_TITLE",
    "DOCUMENT_SUBTITLE",
    "KICKER",
    "META_HTML",
    "TOC_HTML",
    "LEAD_HTML",
    "CONTENT_HTML",
    "FOOTER_HTML",
}
PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z_]+)\}\}")


def require_string(value: object, label: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if "\x00" in value:
        raise ValueError(f"{label} contains an unsupported null character")
    if not allow_empty and not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def validated_url(value: object, label: str) -> str:
    url = require_string(value, label)
    if "\n" in url or "\r" in url:
        raise ValueError(f"{label} must not contain line breaks")
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in {"http", "https", "mailto"}:
        raise ValueError(f"{label} uses an unsupported URL scheme")
    if parsed.netloc and not parsed.scheme:
        raise ValueError(f"{label} uses an unsupported URL form")
    if url.lstrip().lower().startswith(("javascript:", "data:")):
        raise ValueError(f"{label} uses an unsafe URL")
    return url


def safe_url(value: object, label: str) -> str:
    return html.escape(validated_url(value, label), quote=True)


def safe_image_url(value: object, label: str) -> str:
    url = validated_url(value, label)
    parsed = urlparse(url)
    if (
        parsed.scheme in {"http", "https", "mailto"}
        or parsed.netloc
        or url.startswith(("/", "\\"))
    ):
        raise ValueError(f"{label} must use a relative local path")
    return html.escape(url, quote=True)


def inline_markup(value: object, label: str) -> str:
    text = require_string(value, label, allow_empty=True)
    escaped = html.escape(text, quote=True)
    code_tokens: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_tokens.append(f"<code>{match.group(1)}</code>")
        return f"\x00CODE{len(code_tokens) - 1}\x00"

    escaped = re.sub(r"`([^`\n]+)`", stash_code, escaped)

    def link(match: re.Match[str]) -> str:
        label_text, raw_url = match.groups()
        return f'<a href="{safe_url(html.unescape(raw_url), "inline link")}">{label_text}</a>'

    escaped = re.sub(r"\[([^\]\n]+)\]\(([^)\s]+)\)", link, escaped)
    escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", escaped)
    for index, token in enumerate(code_tokens):
        escaped = escaped.replace(f"\x00CODE{index}\x00", token)
    return escaped.replace("\n", "<br>\n")


def render_block(block: object, section_index: int, block_index: int) -> str:
    label = f"sections[{section_index}].blocks[{block_index}]"
    if not isinstance(block, dict):
        raise ValueError(f"{label} must be an object")
    block_type = block.get("type")
    if block_type not in BLOCK_TYPES:
        raise ValueError(f"{label}.type is unsupported: {block_type!r}")

    if block_type == "paragraph":
        return f'<p>{inline_markup(block.get("text"), label + ".text")}</p>'
    if block_type in {"bullets", "steps"}:
        items = block.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError(f"{label}.items must be a non-empty array")
        tag = "ul" if block_type == "bullets" else "ol"
        rendered = "".join(
            f"<li>{inline_markup(item, label + '.items[]')}</li>" for item in items
        )
        return f"<{tag}>{rendered}</{tag}>"
    if block_type == "quote":
        quote = inline_markup(block.get("text"), label + ".text")
        cite = (
            require_string(block["cite"], label + ".cite", allow_empty=True)
            if "cite" in block
            else None
        )
        cite_html = (
            f"<cite>{inline_markup(cite, label + '.cite')}</cite>"
            if cite is not None
            else ""
        )
        return f"<blockquote><p>{quote}</p>{cite_html}</blockquote>"
    if block_type == "callout":
        tone = block.get("tone", "note")
        if tone not in {"note", "warning", "success"}:
            raise ValueError(f"{label}.tone must be note, warning, or success")
        title = inline_markup(block.get("title", "提示"), label + ".title")
        text = inline_markup(block.get("text"), label + ".text")
        return (
            f'<aside class="callout {tone}"><h3 class="callout-title">{title}</h3>'
            f"<p>{text}</p></aside>"
        )
    if block_type == "table":
        headers = block.get("headers")
        rows = block.get("rows")
        if not isinstance(headers, list) or not headers:
            raise ValueError(f"{label}.headers must be a non-empty array")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{label}.rows must be a non-empty array")
        width = len(headers)
        if any(not isinstance(row, list) or len(row) != width for row in rows):
            raise ValueError(f"{label}.rows must match the header width")
        head = "".join(f"<th>{inline_markup(cell, label + '.headers[]')}</th>" for cell in headers)
        body = "".join(
            "<tr>" + "".join(
                f"<td>{inline_markup(cell, label + '.rows[][]')}</td>" for cell in row
            ) + "</tr>"
            for row in rows
        )
        return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    if block_type == "code":
        code = html.escape(require_string(block.get("text"), label + ".text"))
        language = html.escape(
            require_string(block.get("language", "text"), label + ".language"),
            quote=True,
        )
        return f'<pre><code class="language-{language}">{code}</code></pre>'
    if block_type == "divider":
        return '<hr class="divider">'
    if block_type == "image":
        src = safe_image_url(block.get("src"), label + ".src")
        alt = html.escape(require_string(block.get("alt"), label + ".alt"), quote=True)
        caption = (
            require_string(block["caption"], label + ".caption", allow_empty=True)
            if "caption" in block
            else None
        )
        caption_html = (
            f"<figcaption>{inline_markup(caption, label + '.caption')}</figcaption>"
            if caption is not None
            else ""
        )
        return f'<figure><img src="{src}" alt="{alt}" loading="lazy">{caption_html}</figure>'
    raise AssertionError(f"unhandled block type: {block_type}")


def render_document(document: object, template: str) -> str:
    if not isinstance(document, dict):
        raise ValueError("document must be a JSON object")
    title = require_string(document.get("title"), "title")
    subtitle = require_string(document.get("subtitle", ""), "subtitle", allow_empty=True)
    kicker = require_string(
        document.get("kicker", "DOC STYLE · CH"),
        "kicker",
        allow_empty=True,
    )
    meta = document.get("meta", [])
    if not isinstance(meta, list):
        raise ValueError("meta must be an array of strings")
    meta = [
        require_string(item, "meta[]", allow_empty=True)
        for item in meta
    ]
    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("sections must be a non-empty array")

    toc_items: list[str] = []
    section_items: list[str] = []
    for section_index, section in enumerate(sections, 1):
        label = f"sections[{section_index - 1}]"
        if not isinstance(section, dict):
            raise ValueError(f"{label} must be an object")
        section_title = require_string(section.get("title"), label + ".title")
        eyebrow = require_string(
            section.get("eyebrow", "SECTION"),
            label + ".eyebrow",
            allow_empty=True,
        )
        blocks = section.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            raise ValueError(f"{label}.blocks must be a non-empty array")
        section_id = f"section-{section_index:02d}"
        toc_items.append(
            f'<a href="#{section_id}"><span class="toc-number">{section_index:02d}</span>'
            f"<span>{html.escape(section_title)}</span></a>"
        )
        block_html = "\n".join(
            render_block(block, section_index - 1, block_index)
            for block_index, block in enumerate(blocks)
        )
        section_items.append(
            f'<section class="section" id="{section_id}">'
            f'<header class="section-head"><span class="section-number">{section_index:02d}</span>'
            f'<div><p class="section-eyebrow">{html.escape(eyebrow)}</p>'
            f"<h2>{html.escape(section_title)}</h2></div></header>"
            f'<div class="blocks">{block_html}</div></section>'
        )

    lead = (
        require_string(document["lead"], "lead", allow_empty=True)
        if "lead" in document
        else None
    )
    replacements = {
        "DOCUMENT_TITLE": html.escape(title),
        "DOCUMENT_SUBTITLE": html.escape(subtitle),
        "KICKER": html.escape(kicker),
        "META_HTML": "".join(f"<span>{html.escape(item)}</span>" for item in meta),
        "TOC_HTML": "".join(toc_items),
        "LEAD_HTML": (
            f'<p class="lead">{inline_markup(lead, "lead")}</p>' if lead is not None else ""
        ),
        "CONTENT_HTML": "\n".join(section_items),
        "FOOTER_HTML": inline_markup(document.get("footer", ""), "footer"),
    }
    unknown = set(PLACEHOLDER_PATTERN.findall(template)) - PLACEHOLDERS
    if unknown:
        raise ValueError(f"template contains unresolved placeholders: {sorted(unknown)}")
    return PLACEHOLDER_PATTERN.sub(
        lambda match: replacements[match.group(1)],
        template,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    template = args.template.read_text(encoding="utf-8")
    result = render_document(document, template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    print(f"Rendered {args.output}")


if __name__ == "__main__":
    main()
