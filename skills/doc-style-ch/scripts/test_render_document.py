#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
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
        self.assertIn("示例项目说明", result)
        self.assertIn('id="section-01"', result)
        self.assertIn('href="#section-02"', result)
        self.assertIn("<strong>关键结论</strong>", result)
        self.assertNotRegex(result, r"\{\{[A-Z_]+\}\}")
        for forbidden in ("候选 A", "答案键", "评分进度"):
            self.assertNotIn(forbidden, result)

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

    def test_rejects_null_optional_text_fields(self) -> None:
        documents = [
            ({**self.document, "subtitle": None}, "subtitle"),
            ({**self.document, "kicker": None}, "kicker"),
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
        ]
        for document, field in documents:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, rf"{field} must be a string"):
                    RENDERER.render_document(document, self.template)

    def test_rejects_null_code_language(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "code", "language": None, "text": "print('ok')"}
        ]
        with self.assertRaisesRegex(ValueError, "language must be a string"):
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
                with self.assertRaisesRegex(ValueError, "relative local path"):
                    RENDERER.render_document(self.document, self.template)

    def test_rejects_protocol_relative_inline_links(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "paragraph", "text": "[外部链接](//example.com/path)"}
        ]
        with self.assertRaisesRegex(ValueError, "unsupported URL"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_bad_table_width(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "table", "headers": ["A", "B"], "rows": [["only one"]]}
        ]
        with self.assertRaisesRegex(ValueError, "header width"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_sections_without_content_blocks(self) -> None:
        self.document["sections"][0]["blocks"] = []
        with self.assertRaisesRegex(ValueError, "non-empty array"):
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
            '<code class="language-python">',
            '<hr class="divider">',
            '<img src="images/example.png" alt="示例图"',
            '<aside class="callout warning">',
            '<h3 class="callout-title">提示</h3>',
        ):
            self.assertIn(expected, result)

    def test_cli_output_is_self_contained(self) -> None:
        result = RENDERER.render_document(self.document, self.template)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "document.html"
            output.write_text(result, encoding="utf-8")
            text = output.read_text(encoding="utf-8")
            self.assertIn("<style>", text)
            self.assertNotIn("https://fonts", text)


if __name__ == "__main__":
    unittest.main()
