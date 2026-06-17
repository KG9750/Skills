from __future__ import annotations

from datetime import datetime, timezone


CATEGORY_LABELS = {
    "benchmark-dispute": "评测争议",
    "funding-rumor": "融资传闻",
    "open-source-conflict": "开源冲突",
    "product-fail": "产品翻车",
    "founder-drama": "创始人风波",
    "legal-dispute": "法律争议",
    "paper-attribution": "论文署名争议",
    "employee-leak": "员工爆料",
    "safety-ethics": "安全伦理争议",
    "platform-policy": "平台政策争议",
    "community-backlash": "社区反弹",
    "uncategorized": "待分类线索",
}


def event_title(event: dict) -> str:
    if event.get("llm", {}).get("title"):
        return event["llm"]["title"]
    entities = ", ".join(event.get("entities") or [event.get("entity_key", "Unknown")])
    category = category_label(event.get("category", "community-backlash"))
    label = event.get("scores", {}).get("label", "weak signal")
    if label in {"confirmed", "likely"}:
        return f"{entities} 的{category}正在发酵"
    if label == "rumor":
        return f"{entities} 相关{category}传闻待核实"
    return f"{entities} 相关{category}线索待核实"


def source_line(item: dict) -> str:
    platform = item.get("platform", "unknown")
    author = item.get("author", "unknown")
    evidence = item.get("evidence_type", "unknown")
    url = item.get("url", "")
    return f"  - {platform}: {author} | {evidence} | {url}"


def render_report(events: list[dict], warnings: list[str], suggested_sources: list[dict], config: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    general = config.get("general", {})
    main_limit = int(general.get("main_limit", 10))
    early_limit = int(general.get("early_limit", 10))

    main = [event for event in events if event["scores"]["board"] == "main"][:main_limit]
    early = [event for event in events if event["scores"]["board"] == "early"][:early_limit]

    lines = [
        f"# Bagua AI Radar - {now}",
        "",
        "## Run Notes",
        "",
        f"- Time windows: last {general.get('fresh_hours', 24)}h fresh, last {general.get('heating_days', 7)}d still heating.",
        f"- Platforms observed in results: {', '.join(sorted({platform for event in events for platform in event.get('platforms', [])})) or 'none'}",
    ]

    if warnings:
        lines.append("- Warnings: " + " | ".join(warnings))
    else:
        lines.append("- Warnings: none")

    lines.extend(["", "## Main Board", ""])
    if not main:
        lines.append("_No main-board events found in this run._")
    for index, event in enumerate(main, start=1):
        lines.extend(render_event(index, event))

    lines.extend(["", "## Early Signals", ""])
    if not early:
        lines.append("_No early signals found in this run._")
    for index, event in enumerate(early, start=1):
        lines.extend(render_event(index, event))

    lines.extend(["", "## Suggested Source Leads", ""])
    if not suggested_sources:
        lines.append("_No suggested sources in this run._")
    for source in suggested_sources:
        lines.append(f"- {source}")

    return "\n".join(lines) + "\n"


def render_event(index: int, event: dict) -> list[str]:
    scores = event["scores"]
    components = scores["components"]
    evidence_lines = [source_line(item) for item in event.get("items", [])[:5]]
    summary_item = event.get("items", [{}])[0]
    source_text = summary_item.get("text", "").strip()
    if len(source_text) > 220:
        source_text = source_text[:217] + "..."
    entities = "、".join(event.get("entities") or [event.get("entity_key", "Unknown")])
    summary = event.get("llm", {}).get("summary") or event_summary_zh(event)
    follow_up = event.get("llm", {}).get("follow_up") or follow_up_zh(event)

    return [
        f"### {index}. [{scores['label']}] {event_title(event)}",
        "",
        f"- Heat: {scores['heat']}/100 | Credibility: {scores['credibility']}/100 | Category: {category_label(event.get('category'))}",
        f"- Why included: cross-platform {components['cross_platform']}, engagement {components['engagement']}, source {components['source_prominence']}, controversy {components['controversy']}, recency {components['recency']}.",
        f"- Time signal: fresh items {event.get('fresh_count', 0)} | confidence {event.get('time_confidence', 'unknown')}.",
        f"- What happened: {summary}",
        f"- 原文线索: {source_text}",
        "- Evidence chain:",
        *evidence_lines,
        f"- Follow-up: {follow_up}",
        "",
    ]


def category_label(category: str | None) -> str:
    return CATEGORY_LABELS.get(category or "", category or "未知类别")


def event_summary_zh(event: dict) -> str:
    entities = "、".join(event.get("entities") or [event.get("entity_key", "Unknown")])
    category = event.get("category")
    platforms = "、".join(platform_label(platform) for platform in event.get("platforms") or ["unknown"])
    item_count = len(event.get("items", []))
    source_count = len({item.get("author") or item.get("platform") for item in event.get("items", [])})
    label = event.get("scores", {}).get("label", "weak signal")
    credibility = event.get("scores", {}).get("credibility", 0)
    lead = category_summary_lead(category)
    strength = evidence_strength(label, credibility, source_count)
    return f"{entities} 相关{category_label(category)}正在被捕捉：{lead}；目前在{platforms}捕捉到 {item_count} 条线索、约 {source_count} 个来源；证据等级为 {label}，建议先按{strength}处理。"


def category_summary_lead(category: str | None) -> str:
    if category == "legal-dispute":
        return "来源提到起诉、诉讼或法律指控"
    if category == "benchmark-dispute":
        return "重点是 benchmark、eval 或复现口径是否被质疑"
    if category == "funding-rumor":
        return "涉及融资动作、估值或投资人信号"
    if category == "product-fail":
        return "可能涉及回滚、故障、定价争议或用户反弹"
    if category == "founder-drama":
        return "可能涉及创始人、高管的公开争吵、否认或指控"
    if category == "open-source-conflict":
        return "可能涉及维护者、许可、fork 或贡献归属"
    return "属于待核实的 AI 行业争议线索"


def evidence_strength(label: str, credibility: int, source_count: int) -> str:
    if label in {"confirmed", "likely"} or credibility >= 60:
        return "较强公开证据"
    if label == "rumor" or source_count >= 2:
        return "可追踪传闻"
    return "早期弱信号"


def platform_label(platform: str) -> str:
    return {
        "x": "X",
        "reddit": "Reddit",
        "telegram": "Telegram",
        "web": "网页",
    }.get(platform, platform)


def follow_up_zh(event: dict) -> str:
    category = event.get("category")
    if category == "legal-dispute":
        return "继续找法院文件、公司回应、当事人原帖和至少一个独立媒体来源。"
    if category == "benchmark-dispute":
        return "继续找复现脚本、repo issue、维护者回应和当事人的完整 thread。"
    return "关注当事人后续回应、官方声明、repo issue、quote/reply 链是否继续升级。"
