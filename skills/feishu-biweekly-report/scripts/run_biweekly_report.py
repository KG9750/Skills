#!/usr/bin/env python3
"""Collect Feishu reports/chats, generate a management summary, and optionally append it."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any

from render_biweekly_report import render


class SafeBlocker(RuntimeError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise SafeBlocker("missing dependency: install PyYAML to read YAML config, e.g. python3 -m pip install PyYAML") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SafeBlocker("config must be a YAML object")
    return data


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def parse_period(config: dict[str, Any]) -> tuple[date, date]:
    period = config.get("period") or {}
    end_value = text(period.get("end"))
    start_value = text(period.get("start"))
    end = datetime.strptime(end_value, "%Y-%m-%d").date() if end_value else date.today()
    start = datetime.strptime(start_value, "%Y-%m-%d").date() if start_value else end - timedelta(days=13)
    if start > end:
        raise SafeBlocker("invalid period: start must be earlier than or equal to end")
    return start, end


def unix_seconds(day: date, end_of_day: bool = False) -> int:
    value = datetime.combine(day, dt_time.max if end_of_day else dt_time.min)
    return int(value.timestamp())


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SafeBlocker(f"http request failed safely: {exc.code} {url} {detail}") from exc
    except urllib.error.URLError as exc:
        raise SafeBlocker(f"http request failed safely: {exc.reason}") from exc
    if not isinstance(data, dict):
        raise SafeBlocker(f"http response is not a JSON object: {url}")
    return data


def get_tenant_access_token(base_url: str) -> str:
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SafeBlocker("missing env: FEISHU_APP_ID and FEISHU_APP_SECRET are required for live Feishu collection")
    data = http_json(
        "POST",
        f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
    )
    if data.get("code") != 0:
        raise SafeBlocker(f"tenant token failed safely: code={data.get('code')} msg={data.get('msg')}")
    token = text(data.get("tenant_access_token"))
    if not token:
        raise SafeBlocker("tenant token failed safely: tenant_access_token missing")
    return token


def normalize_report_task(member: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    done: list[str] = []
    next_items: list[str] = []
    risks: list[str] = []
    support_needed: list[str] = []
    form_contents = [item for item in as_list(task.get("form_contents")) if isinstance(item, dict)]
    for item in form_contents:
        field_name = text(item.get("field_name"))
        field_value = text(item.get("field_value"))
        if not field_value:
            continue
        if "下周" in field_name or "计划" in field_name:
            next_items.append(field_value)
        elif "风险" in field_name or "问题" in field_name or "阻塞" in field_name:
            risks.append(field_value)
        elif "协调" in field_name or "帮助" in field_name or "支持" in field_name:
            support_needed.append(field_value)
        else:
            done.append(field_value)

    if not form_contents:
        content = task.get("content") or task.get("report_content") or task.get("summary") or task.get("answers") or task
        content_text = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else text(content)
        if content_text:
            done.append(content_text)

    title = text(task.get("rule_name")) or text(task.get("title")) or text(task.get("task_title")) or "飞书汇报"
    commit_time = task.get("commit_time") or task.get("update_time") or task.get("create_time")
    week = text(task.get("week")) or (datetime.fromtimestamp(int(commit_time)).strftime("%G-W%V") if str(commit_time).isdigit() else "未标注周期")
    return {
        "week": week,
        "done": done,
        "next": next_items,
        "risks": risks,
        "support_needed": support_needed,
        "links": [{"label": title, "url": text(task.get("url"))}] if text(task.get("url")) else [{"label": title}],
        "raw_task_id": text(task.get("task_id")) or text(task.get("id")),
    }


def parse_cli_json(output: str, command: str) -> dict[str, Any]:
    json_start = output.find("{")
    if json_start < 0:
        raise SafeBlocker(f"{command} failed safely: JSON output missing")
    try:
        data = json.loads(output[json_start:])
    except json.JSONDecodeError as exc:
        raise SafeBlocker(f"{command} failed safely: invalid JSON output: {exc}") from exc
    if not isinstance(data, dict):
        raise SafeBlocker(f"{command} failed safely: output must be a JSON object")
    return data


def run_lark_cli_json(arguments: list[str], command: str) -> dict[str, Any]:
    cli = shutil.which("lark-cli")
    if not cli:
        raise SafeBlocker(f"{command} blocked: lark-cli is unavailable")
    process = subprocess.run([cli, *arguments], capture_output=True, text=True)
    output = process.stdout.strip()
    if process.returncode != 0:
        if output:
            try:
                error_data = parse_cli_json(output, command)
                error = error_data.get("error") or error_data
                raise SafeBlocker(f"{command} failed safely: {json.dumps(error, ensure_ascii=False)}")
            except SafeBlocker:
                raise
        detail = process.stderr.strip() or f"exit={process.returncode}"
        raise SafeBlocker(f"{command} failed safely: {detail}")
    return parse_cli_json(output, command)


def verify_lark_cli_app(expected_app_id: str) -> None:
    if not expected_app_id:
        return
    data = run_lark_cli_json(["config", "show"], "lark-cli config preflight")
    actual_app_id = text(data.get("appId"))
    if actual_app_id != expected_app_id:
        raise SafeBlocker(f"lark-cli app mismatch: expected={expected_app_id} actual={actual_app_id or 'missing'}")


def collect_reports_from_api(config: dict[str, Any], start: date, end: date, token: str | None) -> list[dict[str, Any]]:
    feishu = config.get("feishu") or {}
    base_url = text(feishu.get("base_url")) or "https://open.feishu.cn"
    rule_id = text(feishu.get("report_rule_id"))
    members = [item for item in as_list(feishu.get("members")) if isinstance(item, dict)]
    if not rule_id:
        raise SafeBlocker("config missing: feishu.report_rule_id")
    if not members:
        raise SafeBlocker("config missing: feishu.members")

    result: list[dict[str, Any]] = []
    auth_source = text(feishu.get("auth_source")) or "env"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    user_id_type = text(feishu.get("user_id_type")) or "open_id"
    for member in members:
        reports: list[dict[str, Any]] = []
        page_token = ""
        while True:
            payload = {
                "commit_start_time": unix_seconds(start),
                "commit_end_time": unix_seconds(end, end_of_day=True),
                "rule_id": rule_id,
                "user_id": text(member.get("user_id")),
                "page_size": 20,
                "page_token": page_token,
            }
            if auth_source == "lark_cli":
                data = run_lark_cli_json(
                    [
                        "api",
                        "POST",
                        "/open-apis/report/v1/tasks/query",
                        "--as",
                        "bot",
                        "--params",
                        json.dumps({"user_id_type": user_id_type}, ensure_ascii=False),
                        "--data",
                        json.dumps(payload, ensure_ascii=False),
                        "--format",
                        "json",
                    ],
                    "report task query",
                )
            else:
                data = http_json(
                    "POST",
                    f"{base_url}/open-apis/report/v1/tasks/query?user_id_type={user_id_type}",
                    payload,
                    headers,
                )
            if data.get("code") != 0:
                raise SafeBlocker(f"report task query failed safely: code={data.get('code')} msg={data.get('msg')}")
            body = data.get("data") or {}
            items = body.get("items") or body.get("tasks") or []
            reports.extend(normalize_report_task(member, item) for item in items if isinstance(item, dict))
            page_token = text(body.get("page_token"))
            if not body.get("has_more") or not page_token:
                break
        result.append({"name": text(member.get("name")) or text(member.get("user_id")), "role": text(member.get("role")), "reports": reports})
    return result


def load_fallback_reports(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("members"), list):
        return data["members"]
    if isinstance(data, list):
        return data
    raise SafeBlocker("fallback reports JSON must be a list or an object with members[]")


def local_period_time(day: date, end_of_day: bool = False) -> str:
    local_tz = datetime.now().astimezone().tzinfo
    value = datetime.combine(day, dt_time.max if end_of_day else dt_time.min, tzinfo=local_tz)
    return value.isoformat(timespec="seconds")


def collect_user_messages(config: dict[str, Any], start: date, end: date) -> list[dict[str, Any]]:
    feishu = config.get("feishu") or {}
    message_config = feishu.get("messages") or {}
    page_size = int(message_config.get("page_size") or 50)
    max_pages = int(message_config.get("max_pages") or 40)
    include_types = {text(item) for item in as_list(message_config.get("include")) if text(item)}
    if page_size < 1 or page_size > 50:
        raise SafeBlocker("config invalid: feishu.messages.page_size must be between 1 and 50")

    page_token = ""
    page_count = 0
    seen: set[str] = set()
    messages: list[dict[str, Any]] = []
    while True:
        arguments = [
            "im",
            "+messages-search",
            "--as",
            "user",
            "--query",
            "",
            "--start",
            local_period_time(start),
            "--end",
            local_period_time(end, end_of_day=True),
            "--page-size",
            str(page_size),
            "--format",
            "json",
        ]
        if include_types == {"group"}:
            arguments.extend(["--chat-type", "group"])
        elif include_types == {"p2p"}:
            arguments.extend(["--chat-type", "p2p"])
        if page_token:
            arguments.extend(["--page-token", page_token])

        response = run_lark_cli_json(arguments, "message search")
        body = response.get("data") or {}
        for item in as_list(body.get("messages")):
            if not isinstance(item, dict) or item.get("deleted"):
                continue
            message_id = text(item.get("message_id"))
            if message_id and message_id in seen:
                continue
            if message_id:
                seen.add(message_id)
            sender = item.get("sender") if isinstance(item.get("sender"), dict) else {}
            messages.append(
                {
                    "message_id": message_id,
                    "chat_id": text(item.get("chat_id")),
                    "chat_name": text(item.get("chat_name")),
                    "chat_type": text(item.get("chat_type")),
                    "create_time": text(item.get("create_time")),
                    "sender": {"id": text(sender.get("id")), "name": text(sender.get("name")), "type": text(sender.get("sender_type"))},
                    "msg_type": text(item.get("msg_type")),
                    "content": text(item.get("content")),
                    "mentions": as_list(item.get("mentions")),
                    "thread_id": text(item.get("thread_id")),
                    "reply_to": text(item.get("reply_to")),
                    "source": message_id,
                }
            )
        page_count += 1
        page_token = text(body.get("page_token"))
        if not body.get("has_more") or not page_token:
            break
        if page_count >= max_pages:
            raise SafeBlocker(f"message search stopped safely: reached max_pages={max_pages} with more results remaining")
    return messages


def collect_chats(config: dict[str, Any], start: date, end: date, output_dir: Path) -> list[dict[str, Any]]:
    fallback = config.get("fallback") or {}
    fallback_path = text(fallback.get("chats_json"))
    if fallback_path:
        data = json.loads(Path(fallback_path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("chat_items"), list):
            return data["chat_items"]
        if isinstance(data, list):
            return data
        raise SafeBlocker("fallback chats JSON must be a list or an object with chat_items[]")

    feishu = config.get("feishu") or {}
    message_config = feishu.get("messages") or {}
    if text(message_config.get("mode")) == "user_search":
        return collect_user_messages(config, start, end)

    chats = [item for item in as_list(feishu.get("chats")) if isinstance(item, dict)]
    if not chats:
        return []

    helper = Path.home() / ".codex/skills/feishu-cli-chat/scripts/fetch_chat_history.py"
    if not helper.exists() or shutil.which("feishu-cli") is None:
        raise SafeBlocker("chat collection blocked: feishu-cli or feishu-cli-chat helper is unavailable; set fallback.chats_json for dry development")

    collected: list[dict[str, Any]] = []
    for chat in chats:
        chat_dir = output_dir / "chat" / text(chat.get("chat_id"))
        chat_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                str(helper),
                text(chat.get("chat_id")),
                "--start",
                f"{start.isoformat()}T00:00:00",
                "--end",
                f"{(end + timedelta(days=1)).isoformat()}T00:00:00",
                "--output-dir",
                str(chat_dir),
            ],
            check=True,
        )
        timeline = chat_dir / "timeline.txt"
        if timeline.exists():
            collected.append({"title": text(chat.get("name")) or text(chat.get("chat_id")), "summary": timeline.read_text(encoding="utf-8"), "source": text(chat.get("chat_id"))})
    return collected


def deterministic_summary(config: dict[str, Any], start: date, end: date, members: list[dict[str, Any]], chat_items_raw: list[dict[str, Any]]) -> dict[str, Any]:
    highlights: list[dict[str, Any]] = []
    for member in members:
        for report in as_list(member.get("reports")):
            if isinstance(report, dict):
                done = as_list(report.get("done"))
                if done:
                    highlights.append({"title": text(done[0])[:80], "owner": text(member.get("name")), "source": text(report.get("raw_task_id"))})

    return {
        "department": text(config.get("department")) or "部门",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "highlights": highlights[:10],
        "chat_items": chat_items_raw[:20],
        "decisions": [],
        "risks": [],
        "next_actions": [],
        "members": members,
        "evidence": [],
    }


def extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts: list[str] = []
    for item in as_list(response.get("output")):
        if not isinstance(item, dict):
            continue
        for content in as_list(item.get("content")):
            if isinstance(content, dict) and content.get("type") == "output_text":
                parts.append(text(content.get("text")))
    return "\n".join(part for part in parts if part)


def generation_messages(config: dict[str, Any], start: date, end: date, members: list[dict[str, Any]], chat_items_raw: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "你是飞书双周报生成助手。请基于证据生成管理层摘要，只输出符合要求的 JSON，不要输出 Markdown。",
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "要求": {
                        "语言": "中文",
                        "风格": "管理层摘要",
                        "边界": "允许归纳、去重、合并、改写，但重点事项、风险、决策必须保留来源；不确定项标记待确认。忽略与部门工作无关的私人对话、系统通知和审批提醒，只保留与配置成员、客户、项目或部门经营相关的信息。",
                        "输出字段": ["department", "period", "generated_at", "highlights", "chat_items", "decisions", "risks", "next_actions", "members", "evidence"],
                    },
                    "department": text(config.get("department")) or "部门",
                    "period": {"start": start.isoformat(), "end": end.isoformat()},
                    "members": members,
                    "raw_chat_items": chat_items_raw,
                },
                ensure_ascii=False,
            ),
        },
    ]


def extract_chat_completion_text(response: dict[str, Any]) -> str:
    choices = as_list(response.get("choices"))
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    return text(message.get("content"))


def generate_with_llm(config: dict[str, Any], start: date, end: date, members: list[dict[str, Any]], chat_items_raw: list[dict[str, Any]]) -> dict[str, Any]:
    llm_cfg = config.get("llm") or config.get("openai") or {}
    provider = (os.getenv("BIWEEKLY_LLM_PROVIDER") or text(llm_cfg.get("provider")) or "deepseek").lower()
    messages = generation_messages(config, start, end, members, chat_items_raw)

    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise SafeBlocker("missing env: DEEPSEEK_API_KEY is required for DeepSeek generation; rerun with --skip-ai to produce a deterministic素材包")
        model = os.getenv("DEEPSEEK_MODEL") or text(llm_cfg.get("model")) or "deepseek-v4-pro"
        response = http_json(
            "POST",
            "https://api.deepseek.com/chat/completions",
            {"model": model, "messages": messages, "response_format": {"type": "json_object"}},
            {"Authorization": f"Bearer {api_key}"},
            timeout=300,
        )
        output_text = extract_chat_completion_text(response)
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SafeBlocker("missing env: OPENAI_API_KEY is required for OpenAI generation; rerun with --skip-ai to produce a deterministic素材包")
        model = os.getenv("OPENAI_MODEL") or text(llm_cfg.get("model")) or "gpt-5-mini"
        response = http_json(
            "POST",
            "https://api.openai.com/v1/responses",
            {"model": model, "input": messages},
            {"Authorization": f"Bearer {api_key}"},
        )
        output_text = extract_output_text(response)
    else:
        raise SafeBlocker(f"unsupported llm.provider: {provider}")

    if not output_text:
        raise SafeBlocker(f"{provider} generation failed safely: empty output")
    try:
        generated = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise SafeBlocker(f"{provider} generation failed safely: output was not JSON: {exc}") from exc
    if not isinstance(generated, dict):
        raise SafeBlocker(f"{provider} generation failed safely: output JSON must be an object")
    generated["department"] = text(config.get("department")) or "部门"
    generated["period"] = {"start": start.isoformat(), "end": end.isoformat()}
    generated["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    generated["members"] = members
    return generated


def append_to_feishu_doc(config: dict[str, Any], markdown_path: Path) -> None:
    feishu = config.get("feishu") or {}
    document_id = text(feishu.get("target_document_id"))
    if not document_id:
        raise SafeBlocker("write blocked: config missing feishu.target_document_id")
    cli = shutil.which("feishu-cli")
    if not cli:
        raise SafeBlocker("write blocked: feishu-cli is not available in PATH")
    subprocess.run([cli, "doc", "content-update", document_id, "--mode", "append", "--markdown-file", str(markdown_path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Feishu biweekly report generation.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--output-dir", help="Override output directory.")
    parser.add_argument("--write", action="store_true", help="Append the generated Markdown to the target Feishu document.")
    parser.add_argument("--skip-ai", action="store_true", help="Skip LLM generation and render a deterministic evidence summary.")
    args = parser.parse_args()

    try:
        config = load_yaml(Path(args.config))
        start, end = parse_period(config)
        output_dir = Path(args.output_dir or text((config.get("output") or {}).get("dir")) or f"/tmp/feishu-biweekly-report-{int(time.time())}")
        output_dir.mkdir(parents=True, exist_ok=True)

        fallback_reports = text((config.get("fallback") or {}).get("reports_json"))
        if fallback_reports:
            members = load_fallback_reports(fallback_reports)
        else:
            feishu = config.get("feishu") or {}
            auth_source = text(feishu.get("auth_source")) or "env"
            if auth_source == "lark_cli":
                verify_lark_cli_app(text(feishu.get("expected_app_id")))
                token = None
            elif auth_source == "env":
                token = get_tenant_access_token(text(feishu.get("base_url")) or "https://open.feishu.cn")
            else:
                raise SafeBlocker(f"unsupported feishu.auth_source: {auth_source}")
            members = collect_reports_from_api(config, start, end, token)

        chat_items_raw = collect_chats(config, start, end, output_dir)
        raw_path = output_dir / "collected.raw.json"
        raw_path.write_text(json.dumps({"members": members, "chat_items": chat_items_raw}, ensure_ascii=False, indent=2), encoding="utf-8")

        normalized = deterministic_summary(config, start, end, members, chat_items_raw) if args.skip_ai else generate_with_llm(config, start, end, members, chat_items_raw)
        normalized_path = output_dir / "normalized.json"
        markdown_path = output_dir / "biweekly-report.md"
        normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(render(normalized), encoding="utf-8")

        if args.write:
            append_to_feishu_doc(config, markdown_path)

        print(json.dumps({"ok": True, "raw": str(raw_path), "normalized": str(normalized_path), "markdown": str(markdown_path), "written": bool(args.write)}, ensure_ascii=False))
        return 0
    except SafeBlocker as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
