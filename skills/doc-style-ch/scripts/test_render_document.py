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

    def test_rejects_unsafe_image_url(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "image", "src": "javascript:alert(1)", "alt": "坏链接"}
        ]
        with self.assertRaisesRegex(ValueError, "unsupported URL scheme|unsafe URL"):
            RENDERER.render_document(self.document, self.template)

    def test_rejects_bad_table_width(self) -> None:
        self.document["sections"][0]["blocks"] = [
            {"type": "table", "headers": ["A", "B"], "rows": [["only one"]]}
        ]
        with self.assertRaisesRegex(ValueError, "header width"):
            RENDERER.render_document(self.document, self.template)

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
