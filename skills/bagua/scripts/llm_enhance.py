from __future__ import annotations

import json
import urllib.error
import urllib.request

from redact import redact_text


def enhance_events(events: list[dict], config: dict) -> tuple[list[dict], list[str]]:
    llm_config = config.get("llm", {})
    if not llm_config.get("enabled"):
        return events, []
    api_key = llm_config.get("api_key")
    if not api_key:
        return events, ["llm: skipped: llm.api_key is not configured"]

    warnings = []
    enhanced = []
    for event in events:
        try:
            enhanced.append(enhance_event(event, llm_config))
        except Exception as error:  # noqa: BLE001
            warnings.append(redact_text(f"llm: enhancement failed for {event.get('event_id')}: {error}"))
            enhanced.append(event)
    return enhanced, warnings


def enhance_event(event: dict, llm_config: dict) -> dict:
    snippets = []
    for item in event.get("items", [])[:5]:
        snippets.append({
            "platform": item.get("platform"),
            "author": item.get("author"),
            "text": (item.get("text") or "")[:500],
            "url": item.get("url"),
            "evidence_type": item.get("evidence_type"),
        })
    prompt = {
        "category": event.get("category"),
        "entities": event.get("entities"),
        "label": event.get("scores", {}).get("label"),
        "snippets": snippets,
    }
    body = {
        "model": llm_config.get("model", "gpt-4.1-mini"),
        "messages": [
            {"role": "system", "content": "你是谨慎的中文 AI 八卦情报编辑。只基于输入证据写，不要把传闻写成事实。输出 JSON。"},
            {"role": "user", "content": "为这个事件生成 title, summary, follow_up 三个中文字段：\n" + json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        llm_config.get("base_url", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {llm_config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail[:200]}") from error
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("unexpected response shape: " + redact_text(json.dumps(data, ensure_ascii=False)[:240])) from error
    try:
        event["llm"] = json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError("malformed JSON response: " + redact_text(content[:240])) from error
    return event
