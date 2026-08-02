#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("render_document.py")
SPEC = importlib.util.spec_from_file_location("doc_style_ch_renderer", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load renderer")
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class RendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = RENDERER.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.document = {
            "title": "示例项目说明",
            "subtitle": "用于验证中文长文样式",
            "kicker": "PROJECT NOTE",
            "meta": ["版本 1.0", "内部文档"],
            "lead": "先说结论，再展开证据。",
            "sections": [
                {
                    "title": "核心判断",
                    "eyebrow": "SUMMARY",
                    "blocks": [
                        {"type": "paragraph", "text": "这是 **关键结论**，包含 `code`。"},
                        {"type": "bullets", "items": ["第一项", "第二项"]},
                        {"type": "callout", "tone": "success", "title": "已确认", "text": "验证通过。"},
                    ],
                },
                {
                    "title": "数据对照",
                    "blocks": [
                        {"type": "table", "headers": ["项目", "结果"], "rows": [["结构", "通过"]]},
                        {"type": "quote", "text": "克制比装饰更重要。", "cite": "设计原则"},
                    ],
                },
            ],
            "footer": "由 doc-style-CH 生成。",
        }

    def test_renders_complete_document(self) -> None:
        result = RENDERER.render_document(self.document, self.template)
        self.assertIn('data-output-profile="document"', result)
        self.assertIn("示例项目说明", result)
        self.assertIn('id="section-01"', result)
        self.assertIn('href="#section-02"', result)
        self.assertIn("<strong>关键结论</strong>", result)
        self.assertNotRegex(result, r"\{\{[A-Z_]+\}\}")
        for forbidden in ("候选 A", "答案键", "评分进度"):
            self.assertNotIn(forbidden, result)

    def test_template_keeps_screen_navigation_and_print_contracts(self) -> None:
        result = RENDERER.render_document(self.document, self.template)
        for expected in (
            '--reading: clamp(48rem, 78vw, 76rem);',
            'background: rgba(45,39,34,.60);',
            'class="nav-overview"',
            'html[data-output-profile="document"] .nav-overview',
            'content: counter(page) " / " counter(pages);',
            '.rail-title { max-width: none; font-size: 33pt; line-height: 1.16; letter-spacing: 0; }',
            'html[data-output-profile="image"] .document {',
            'html[data-output-profile="image"] .footer { max-width: none; }',
            'font-size: clamp(3rem, 4.1vw, 4.4rem);',
            '.code-toolbar {',
            'background: transparent;',
            'background: rgba(234,234,230,.90);',
            '.blocks blockquote p { margin: 0; font-size: inherit; }',
            'font-size: .9rem;',
            'html[data-output-profile="image"] .blocks .callout { font-size: .94rem; }',
            'height: auto;',
            'border-radius: .45rem;',
            'overflow: hidden;',
            'background: none;',
            'html[data-output-profile="image"] .code-copy { display: none; }',
            '.code-copy { display: none; }',
        ):
            self.assertIn(expected, result)
        self.assertNotIn('class="rail-foot"', result)
        meta_css = result.split('.meta span {', 1)[1].split('}', 1)[0]
        self.assertIn('display: block;', meta_css)
        for selector in ('.rail-title', '.hero h1', '.section-number', '.section h2'):
            title_css = result.split(f'{selector} {{', 1)[1].split('}', 1)[0]
            self.assertIn('font-weight: 600;', title_css)
        for selector in ('blockquote', '.callout'):
            note_css = result.split(f'{selector} {{', 1)[1].split('}', 1)[0]
            self.assertIn('width: 100%;', note_css)
            self.assertIn('height: auto;', note_css)
        code_css = result.split('.code-block {', 1)[1].split('}', 1)[0]
        self.assertIn('border: 0;', code_css)

    def test_preserves_template_like_text_in_document_content(self) -> None:
        self.document["title"] = "标题 {{CONTENT_HTML}}"
        self.document["sections"][0]["blocks"][0]["text"] = (
            "保留 {{FOOTER_HTML}} 与 {{DOCUMENT_TITLE}}。"
        )
        result = RENDERER.render_document(self.document, self.template)
        self.assertIn("标题 {{CONTENT_HTML}}", result)
        self.assertIn("保留 {{FOOTER_HTML}} 与 {{DOCUMENT_TITLE}}。", result)

    def test_rejects_unknown_placeholders_in_template(self) -> None:
        template = self.template.replace("</body>", "{{UNKNOWN_SLOT}}</body>")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SLOT"):
            RENDERER.render_document(self.document, template)

    def test_renders_image_profile(self) -> None:
        result = RENDERER.render_document(
            self.document,
            self.template,
            output_profile="image",
        )
        self.assertIn('data-output-profile="image"', result)
        self.assertIn('html[data-output-profile="image"]', result)

    def test_rejects_unknown_output_profile(self) -> None:
        with self.assertRaisesRegex(ValueError, "output_profile"):
            RENDERER.render_document(
                self.document,
                self.template,
                output_profile="slides",
            )

    def test_rejects_null_optional_text_fields(self) -> None:
        documents = [
            ({**self.document, "subtitle": None}, "subtitle"),
            ({**self.document, "kicker": None}, "kicker"),
            ({**self.document, "lead": None}, "lead"),
            ({**self.document, "footer": None}, "footer"),
            ({**self.document, "meta": None}, "meta"),
            (
                {
                    **self.document,
                    "sections": [
                        {**self.document["sections"][0], "eyebrow": None},
                        self.document["sections"][1],
                    ],
                },
                "eyebrow",
            ),
            (
                {
                    **self.document,
                    "sections": [
                        {
                            **self.document["sections"][0],
                            "blocks": [{"type": "quote", "text": "引文", "cite": None}],
                        },
                        self.document["sections"][1],
                    ],
                },
                "cite",
            ),
            (
                {
                    **self.document,
                    "sections": [
                        {
                            **self.document["sections"][0],
                            "blocks": [
                                {
                                    "type": "image",
                                    "src": "images/a.png",
                                    "alt": "图",
                                    "caption": None,
                                }
                            ],
                        },
                        self.document["sections"][1],
                    ],
                },
                "caption",
            ),
        ]
        for document, field in documents:
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    ValueError,
                    rf"{field} must be (?:a string|an array of strings)",
                ):
                    RENDERER.render_document(document, self.template)

    def test_rejects_null_code_language(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "code", "language": None, "text": "print('ok')"}
        ]
        with self.assertRaisesRegex(ValueError, "language must be a string"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_null_characters_in_text(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "paragraph", "text": "原文 \x00CODE0\x00 与 `真实代码`"}
        ]
        with self.assertRaisesRegex(ValueError, "null character"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_unsafe_image_url(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "image", "src": "javascript:alert(1)", "alt": "坏链接"}
        ]
        with self.assertRaisesRegex(ValueError, "unsupported URL scheme|unsafe URL"):
            RENDERER.render_document(self.document, self.template)

    def test_image_sources_must_be_relative_local_paths(self) -> None:
        for src in (
            "http://example.com/image.png",
            "https://example.com/image.png",
            "//example.com/image.png",
            "/images/example.png",
        ):
            with self.subTest(src=src):
                self.document["sections"][0]["blocks"] = [
                    {"type": "image", "src": src, "alt": "远程图片"}
                ]
                with self.assertRaisesRegex(ValueError, "delivery directory|unsupported URL"):
                    RENDERER.render_document(self.document, self.template)

    def test_image_sources_cannot_escape_delivery_directory(self) -> None:
        for src in (
            "../secret.png",
            "images/../../secret.png",
            "images\\..\\secret.png",
            "%2e%2e/secret.png",
        ):
            with self.subTest(src=src):
                self.document["sections"][0]["blocks"] = [
                    {"type": "image", "src": src, "alt": "越界图片"}
                ]
                with self.assertRaisesRegex(ValueError, "delivery directory"):
                    RENDERER.render_document(self.document, self.template)

    def test_rejects_protocol_relative_inline_links(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "paragraph", "text": "[外部链接](//example.com/path)"}
        ]
        with self.assertRaisesRegex(ValueError, "unsupported URL"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_newlines_in_image_paths(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "image", "src": "images/example\n.png", "alt": "坏路径"}
        ]
        with self.assertRaisesRegex(ValueError, "line breaks"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_unsafe_inline_links(self) -> None:
        for url in ("javascript:alert(1)", "data:text/html,bad"):
            with self.subTest(url=url):
                self.document["sections"][0]["blocks"] = [
                    {"type": "paragraph", "text": f"[坏链接]({url})"}
                ]
                with self.assertRaisesRegex(ValueError, "unsupported URL scheme|unsafe URL"):
                    RENDERER.render_document(self.document, self.template)

    def test_keeps_percent_encoded_colons_as_relative_links(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {
                "type": "paragraph",
                "text": "[编码路径](javascript%3Aexample.html)",
            }
        ]
        result = RENDERER.render_document(self.document, self.template)
        self.assertIn('href="javascript%3Aexample.html"', result)
        self.assertNotIn('href="javascript:', result)

    def test_rejects_bad_table_width(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "table", "headers": ["A", "B"], "rows": [["only one"]]}
        ]
        with self.assertRaisesRegex(ValueError, "header width"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_tables_without_data_rows(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "table", "headers": ["项目", "结果"], "rows": []}
        ]
        with self.assertRaisesRegex(ValueError, "non-empty array"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_sections_without_content_blocks(self) -> None:
        self.document["sections"][0]["blocks"] = []
        with self.assertRaisesRegex(ValueError, "non-empty array"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_missing_required_fields(self) -> None:
        invalid_documents = [
            ({"title": "文档"}, "sections"),
            ({"title": "文档", "sections": None}, "sections"),
            ({"title": "文档", "sections": "第一节"}, "sections"),
            (
                {
                    "title": "文档",
                    "sections": [
                        {"blocks": [{"type": "paragraph", "text": "正文"}]}
                    ],
                },
                "title",
            ),
            ({"title": "文档", "sections": [{"title": "第一节"}]}, "blocks"),
            (
                {
                    "title": "文档",
                    "sections": [
                        {"title": "第一节", "blocks": [{"type": "image", "alt": "图"}]}
                    ],
                },
                "src",
            ),
            (
                {
                    "title": "文档",
                    "sections": [
                        {
                            "title": "第一节",
                            "blocks": [{"type": "image", "src": "images/a.png"}],
                        }
                    ],
                },
                "alt",
            ),
            (
                {
                    "title": "文档",
                    "sections": [
                        {"title": "第一节", "blocks": [{"type": "callout"}]}
                    ],
                },
                "text",
            ),
        ]
        for document, field in invalid_documents:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    RENDERER.render_document(document, self.template)

    def test_callout_defaults_to_note_tone_and_title(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "callout", "text": "默认提示。"}
        ]
        result = RENDERER.render_document(self.document, self.template)
        self.assertIn('<aside class="callout note">', result)
        self.assertIn('<h3 class="callout-title">提示</h3>', result)

    def test_rejects_invalid_callout_tone(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "callout", "tone": "danger", "text": "错误提示。"}
        ]
        with self.assertRaisesRegex(ValueError, "tone must be note, warning, or success"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_unknown_block_type(self) -> None:
        self.document["sections"][0]["blocks"] = [{"type": "unknown"}]
        with self.assertRaisesRegex(ValueError, "type is unsupported"):
            RENDERER.render_document(self.document, self.template)

    def test_renders_supported_blocks_and_inline_markup(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {
                "type": "paragraph",
                "text": "*强调*与[链接](https://example.com)\n下一行",
            },
            {"type": "steps", "items": ["第一步", "第二步"]},
            {"type": "code", "language": "python", "text": "print('ok')"},
            {"type": "divider"},
            {
                "type": "image",
                "src": "images/example.png",
                "alt": "示例图",
                "caption": "图片说明",
            },
            {"type": "callout", "tone": "warning", "text": "请注意。"},
        ]
        result = RENDERER.render_document(self.document, self.template)
        for expected in (
            "<em>强调</em>",
            '<a href="https://example.com">链接</a>',
            "<br>",
            "<ol>",
            '<div class="code-block">',
            '<span class="code-language">&lt;python&gt;</span>',
            '<button class="code-copy" type="button">复制</button>',
            '<code class="language-python">',
            '<hr class="divider">',
            '<img src="images/example.png" alt="示例图"',
            '<aside class="callout warning">',
            '<h3 class="callout-title">提示</h3>',
        ):
            self.assertIn(expected, result)

    def test_uses_consistent_language_tags_for_shells(self) -> None:
        for language in ("bash", "zsh", "fish"):
            with self.subTest(language=language):
                self.document["sections"][0]["blocks"] = [
                    {"type": "code", "language": language, "text": "echo ok"}
                ]
                result = RENDERER.render_document(self.document, self.template)
                self.assertIn(
                    f'<span class="code-language">&lt;{language}&gt;</span>',
                    result,
                )

    def test_renders_document_defaults_and_optional_omissions(self) -> None:
        section = {
            "title": "默认行为",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": (
                        "[**相对链接**](docs/file.html)、[邮件](mailto:test@example.com)，"
                        "以及 **包含 `代码一`** 和 `代码二`。"
                    ),
                },
                {"type": "quote", "text": "无出处引文。"},
                {"type": "image", "src": "images/example.png", "alt": "无说明图片"},
                {"type": "code", "text": "plain text"},
            ],
        }
        document = {"title": "最小默认文档", "meta": [], "sections": [section]}
        result = RENDERER.render_document(document, self.template)
        for expected in (
            '<p class="section-eyebrow">SECTION</p>',
            '<a href="docs/file.html"><strong>相对链接</strong></a>',
            '<a href="mailto:test@example.com">邮件</a>',
            '<strong>包含 <code>代码一</code></strong>',
            '<code>代码二</code>',
            '<code class="language-text">',
            '<div class="meta"></div>',
        ):
            self.assertIn(expected, result)
        self.assertNotIn("<cite>", result)
        self.assertNotIn("<figcaption>", result)

    def test_cli_output_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output = Path(directory) / "nested" / "document.html"
            input_path.write_text(
                json.dumps(self.document, ensure_ascii=False),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(input_path), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            text = output.read_text(encoding="utf-8")
            self.assertIn(f"Rendered {output}", completed.stdout)
            self.assertIn("<style>", text)
            self.assertNotIn("https://fonts", text)

    def test_cli_selects_image_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output = Path(directory) / "image.html"
            input_path.write_text(
                json.dumps(self.document, ensure_ascii=False),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(input_path),
                    str(output),
                    "--profile",
                    "image",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(
                'data-output-profile="image"',
                output.read_text(encoding="utf-8"),
            )

    def test_template_hides_empty_subtitles_and_uses_compatible_line_color(self) -> None:
        self.assertIn(".rail-subtitle:empty", self.template)
        self.assertIn(".hero-subtitle:empty", self.template)
        self.assertNotIn("color-mix(", self.template)
        self.assertRegex(self.template, r"@page\s*\{\s*size: A4 portrait;")

    def test_template_has_adaptive_accessible_navigation(self) -> None:
        for expected in (
            'class="nav-trigger"',
            'aria-controls="document-navigation"',
            'aria-expanded="false"',
            'class="skip-link"',
            '@media (hover: hover)',
            '.nav-shell:not(.is-hover-suppressed):hover .nav-panel',
            'event.key === "Escape"',
            'trigger.focus({ preventScroll: true })',
            'html[data-output-profile="image"] .nav-trigger { display: none; }',
            '.toc { display: none; }',
        ):
            self.assertIn(expected, self.template)
        self.assertNotIn("grid-template-columns: var(--sidebar)", self.template)


if __name__ == "__main__":
    unittest.main()
