from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, time as dt_time
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("run_biweekly_report", SCRIPTS_DIR / "run_biweekly_report.py")
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class SecureOutputTests(unittest.TestCase):
    def test_secure_write_text_creates_owner_only_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "collected.raw.json"

            runner.secure_write_text(path, "{}")

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_cleanup_removes_only_expired_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            expired = output_dir / "collected.raw.json"
            unrelated = output_dir / "notes.txt"
            runner.secure_write_text(expired, "{}")
            unrelated.write_text("keep", encoding="utf-8")
            old = datetime.now().timestamp() - 7200
            os.utime(expired, (old, old))

            runner.cleanup_sensitive_outputs(output_dir, retention_hours=1)

            self.assertFalse(expired.exists())
            self.assertTrue(unrelated.exists())


class DocumentDeliveryTests(unittest.TestCase):
    def test_existing_period_marker_prevents_duplicate_append(self) -> None:
        config = {"department": "销售部", "feishu": {"target_document_id": "docx_real"}}
        marker = runner.report_marker(config, date(2026, 7, 1), date(2026, 7, 14))
        with tempfile.TemporaryDirectory() as tmp:
            markdown_path = Path(tmp) / "report.md"
            runner.secure_write_text(markdown_path, f"{marker}\n\n# 双周报\n")
            fetch_response = {"data": {"content": f"旧内容\n{marker}\n"}}

            with mock.patch.object(runner, "run_lark_cli_json", return_value=fetch_response) as call:
                status = runner.append_to_feishu_doc(
                    config,
                    markdown_path,
                    date(2026, 7, 1),
                    date(2026, 7, 14),
                )

        self.assertEqual(status, "already_exists")
        self.assertEqual(call.call_count, 1)

    def test_append_uses_lark_docs_update(self) -> None:
        config = {"department": "销售部", "feishu": {"target_document_id": "docx_real"}}
        with tempfile.TemporaryDirectory() as tmp:
            markdown_path = Path(tmp) / "report.md"
            runner.secure_write_text(markdown_path, "# 双周报\n")
            with mock.patch.object(
                runner,
                "run_lark_cli_json",
                side_effect=[{"data": {"content": "旧内容"}}, {"code": 0}],
            ) as call:
                status = runner.append_to_feishu_doc(
                    config,
                    markdown_path,
                    date(2026, 7, 1),
                    date(2026, 7, 14),
                )

        self.assertEqual(status, "appended")
        update_arguments = call.call_args_list[1].args[0]
        self.assertEqual(update_arguments[:2], ["docs", "+update"])
        self.assertIn("--mode", update_arguments)
        self.assertIn("append", update_arguments)


class ConfigValidationTests(unittest.TestCase):
    def test_write_mode_rejects_placeholder_document_id(self) -> None:
        config = {
            "department": "销售部",
            "timezone": "Asia/Shanghai",
            "feishu": {
                "report_rule_id": "rule-1",
                "members": [{"name": "张三", "user_id": "ou_1"}],
                "target_document_id": "docx_xxx",
            },
            "llm": {"provider": "openai", "model": "gpt-5.6"},
        }

        with self.assertRaisesRegex(runner.SafeBlocker, "placeholder"):
            runner.validate_config(config, write_requested=True)

    def test_unix_seconds_uses_configured_timezone(self) -> None:
        timezone = ZoneInfo("Asia/Shanghai")

        actual = runner.unix_seconds(date(2026, 7, 16), timezone)

        expected = int(datetime.combine(date(2026, 7, 16), dt_time.min, tzinfo=timezone).timestamp())
        self.assertEqual(actual, expected)

    def test_preflight_requires_configured_model_key(self) -> None:
        config = {
            "department": "销售部",
            "timezone": "Asia/Shanghai",
            "feishu": {
                "auth_source": "env",
                "report_rule_id": "rule-1",
                "members": [{"name": "张三", "user_id": "ou_1"}],
            },
            "llm": {"provider": "openai", "model": "gpt-5.6"},
        }

        with mock.patch.dict(runner.os.environ, {}, clear=True):
            with self.assertRaisesRegex(runner.SafeBlocker, "OPENAI_API_KEY"):
                runner.run_preflight(config, skip_ai=False, write_requested=False)

    def test_preflight_checks_message_scopes_for_configured_chats(self) -> None:
        config = {
            "department": "销售部",
            "timezone": "Asia/Shanghai",
            "feishu": {
                "auth_source": "lark_cli",
                "report_rule_id": "rule-1",
                "members": [{"name": "张三", "user_id": "ou_1"}],
                "chats": [{"chat_id": "oc_1"}],
            },
            "llm": {"provider": "openai", "model": "gpt-5.6"},
        }

        with mock.patch.object(runner, "run_lark_cli_json", return_value={"ok": True}) as call:
            runner.run_preflight(config, skip_ai=True, write_requested=False)

        self.assertEqual(call.call_args.args[0][:2], ["auth", "check"])


class FailureSurfaceTests(unittest.TestCase):
    def test_lark_cli_timeout_is_reported_as_safe_blocker(self) -> None:
        with mock.patch.object(
            runner.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["lark-cli"], timeout=120),
        ):
            with self.assertRaisesRegex(runner.SafeBlocker, "timed out"):
                runner.run_lark_cli_json(["config", "show"], "config preflight")


class ReportCollectionTests(unittest.TestCase):
    def test_report_identity_mismatch_stops_collection(self) -> None:
        config = {
            "timezone": "Asia/Shanghai",
            "feishu": {
                "auth_source": "lark_cli",
                "report_rule_id": "rule-1",
                "members": [{"name": "张三", "user_id": "ou_expected"}],
            },
        }
        response = {
            "code": 0,
            "data": {
                "has_more": False,
                "items": [{"from_user_id": "ou_other", "from_user_name": "李四", "task_id": "task-1"}],
            },
        }

        with mock.patch.object(runner, "run_lark_cli_json", return_value=response):
            with self.assertRaisesRegex(runner.SafeBlocker, "identity mismatch"):
                runner.collect_reports_from_api(config, date(2026, 7, 1), date(2026, 7, 14), None)


class MessageCollectionTests(unittest.TestCase):
    def test_message_overflow_splits_time_window_instead_of_aborting(self) -> None:
        config = {
            "timezone": "Asia/Shanghai",
            "feishu": {"messages": {"include": ["group", "p2p"], "page_size": 50, "max_pages": 1}},
        }
        calls: list[tuple[str, str]] = []

        def fake_search(arguments: list[str], _command: str) -> dict:
            start = arguments[arguments.index("--start") + 1]
            end = arguments[arguments.index("--end") + 1]
            calls.append((start, end))
            if len(calls) == 1:
                return {"data": {"messages": [], "has_more": True, "page_token": "more"}}
            return {
                "data": {
                    "messages": [{"message_id": f"om_{len(calls)}", "chat_type": "group", "content": "ok"}],
                    "has_more": False,
                }
            }

        with mock.patch.object(runner, "run_lark_cli_json", side_effect=fake_search):
            messages = runner.collect_user_messages(config, date(2026, 7, 1), date(2026, 7, 2))

        self.assertEqual(len(messages), 2)
        self.assertEqual(len(calls), 3)

    def test_configured_chats_use_lark_message_search_path(self) -> None:
        config = {
            "timezone": "Asia/Shanghai",
            "feishu": {"chats": [{"chat_id": "oc_1", "name": "项目群"}]},
            "fallback": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(runner, "collect_user_messages", return_value=[]) as collect:
                runner.collect_chats(config, date(2026, 7, 1), date(2026, 7, 14), Path(tmp))

        scoped_config = collect.call_args.args[0]
        self.assertEqual(scoped_config["feishu"]["messages"]["chat_ids"], ["oc_1"])

    def test_message_search_scopes_configured_chat_ids(self) -> None:
        config = {
            "timezone": "Asia/Shanghai",
            "feishu": {"messages": {"chat_ids": ["oc_1", "oc_2"]}},
        }

        with mock.patch.object(
            runner,
            "run_lark_cli_json",
            return_value={"data": {"messages": [], "has_more": False}},
        ) as search:
            runner.collect_user_messages(config, date(2026, 7, 1), date(2026, 7, 14))

        arguments = search.call_args.args[0]
        self.assertEqual(arguments[arguments.index("--chat-id") + 1], "oc_1,oc_2")


class ModelInputSafetyTests(unittest.TestCase):
    def test_chat_evidence_redacts_credentials_and_marks_content_untrusted(self) -> None:
        config = {"privacy": {}}
        chats = [{"message_id": "om_1", "content": "Authorization: Bearer secret-token"}]

        prepared = runner.prepare_chat_evidence(config, chats)
        messages = runner.generation_messages(config, date(2026, 7, 1), date(2026, 7, 14), [], prepared)

        self.assertNotIn("secret-token", messages[1]["content"])
        self.assertIn("不可信证据", messages[0]["content"])

    def test_generated_report_rejects_wrong_field_types(self) -> None:
        generated = {
            "highlights": "not-a-list",
            "chat_items": [],
            "decisions": [],
            "risks": [],
            "next_actions": [],
            "evidence": [],
        }

        with self.assertRaisesRegex(runner.SafeBlocker, "highlights"):
            runner.validate_generated_report(generated)

    def test_large_chat_input_is_summarized_in_chunks_before_final_generation(self) -> None:
        config = {"llm": {"provider": "openai", "model": "gpt-5.6", "chunk_size": 2}}
        chats = [{"message_id": f"om_{index}", "content": f"message {index}"} for index in range(5)]
        valid_summary = {
            "highlights": [],
            "chat_items": [],
            "decisions": [],
            "risks": [],
            "next_actions": [],
            "evidence": [],
        }

        with mock.patch.object(runner, "call_llm_json", return_value=valid_summary) as call:
            runner.generate_with_llm(config, date(2026, 7, 1), date(2026, 7, 14), [], chats)

        self.assertEqual(call.call_count, 4)


if __name__ == "__main__":
    unittest.main()
