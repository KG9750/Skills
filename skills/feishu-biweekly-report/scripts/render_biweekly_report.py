#!/usr/bin/env python3
"""Render a normalized Feishu biweekly-report JSON file to Markdown."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text_or_empty(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def bullet(items: list[Any], empty: str = "无") -> str:
    cleaned = [text_or_empty(item) for item in items if text_or_empty(item)]
    if not cleaned:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in cleaned)


def link_text(link: Any) -> str:
    if isinstance(link, dict):
        label = text_or_empty(link.get("label")) or text_or_empty(link.get("url")) or "来源"
        url = text_or_empty(link.get("url"))
        return f"[{label}]({url})" if url else label
    return text_or_empty(link)


def member_progress(members: list[dict[str, Any]]) -> str:
    if not members:
        return "- 无成员周报数据"

    sections: list[str] = []
    for member in members:
        name = text_or_empty(member.get("name")) or "未命名成员"
        role = text_or_empty(member.get("role"))
        header = f"### {name}" + (f"（{role}）" if role else "")
        parts = [header]

        reports = as_list(member.get("reports"))
        if not reports:
            parts.append("- 无周报数据")
        for report in reports:
            if not isinstance(report, dict):
                continue
            week = text_or_empty(report.get("week")) or "未标注周期"
            parts.append(f"#### {week}")
            parts.append("**已完成**")
            parts.append(bullet(as_list(report.get("done"))))
            parts.append("**下阶段**")
            parts.append(bullet(as_list(report.get("next"))))

            risks = as_list(report.get("risks"))
            support = as_list(report.get("support_needed"))
            if risks or support:
                parts.append("**风险/协同**")
                parts.append(bullet(risks + support))

            links = [link_text(item) for item in as_list(report.get("links")) if link_text(item)]
            if links:
                parts.append("**来源**")
                parts.append(bullet(links))

        sections.append("\n\n".join(parts))
    return "\n\n".join(sections)


def chat_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- 无重要聊天事项"

    rows = ["| 优先级 | 事项 | 负责人 | 状态 | 日期 | 来源 |", "|---|---|---|---|---|---|"]
    for item in items:
        title = text_or_empty(item.get("title")) or text_or_empty(item.get("summary")) or text_or_empty(item.get("content")) or "未命名事项"
        summary = text_or_empty(item.get("summary")) or text_or_empty(item.get("content"))
        title_cell = title if not summary or summary == title else f"{title}<br>{summary}"
        create_time = text_or_empty(item.get("create_time"))
        rows.append(
            "| {priority} | {title} | {owner} | {status} | {date} | {source} |".format(
                priority=text_or_empty(item.get("priority")) or "-",
                title=title_cell.replace("|", "\\|"),
                owner=text_or_empty(item.get("owner")) or text_or_empty(item.get("sender")) or "-",
                status=text_or_empty(item.get("status")) or "-",
                date=text_or_empty(item.get("date")) or create_time[:10] or "-",
                source=text_or_empty(item.get("source")) or text_or_empty(item.get("message_id")) or "-",
            )
        )
    return "\n".join(rows)


def titled_items(items: list[Any], empty: str = "无") -> str:
    if not items:
        return f"- {empty}"

    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            title = (
                text_or_empty(item.get("title"))
                or text_or_empty(item.get("item"))
                or text_or_empty(item.get("decision"))
                or text_or_empty(item.get("risk"))
                or text_or_empty(item.get("action"))
                or text_or_empty(item.get("summary"))
            )
            summary = text_or_empty(item.get("summary"))
            owner = text_or_empty(item.get("owner"))
            evidence_text = text_or_empty(item.get("source")) or text_or_empty(item.get("evidence"))
            suffix = "；".join(part for part in [f"负责人：{owner}" if owner else "", f"来源：{evidence_text}" if evidence_text else ""] if part)
            body = title if not summary or summary == title else f"{title}：{summary}"
            lines.append(f"{body}（{suffix}）" if suffix else body)
        else:
            lines.append(text_or_empty(item))
    return bullet(lines, empty=empty)


def collect_report_risks(data: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    for item in as_list(data.get("risks")):
        if isinstance(item, dict):
            risk = text_or_empty(item.get("risk")) or text_or_empty(item.get("title")) or text_or_empty(item.get("summary"))
            source = text_or_empty(item.get("source")) or text_or_empty(item.get("evidence"))
            if risk:
                risks.append(f"{risk}（来源：{source}）" if source else risk)
        elif text_or_empty(item):
            risks.append(text_or_empty(item))
    for member in as_list(data.get("members")):
        if not isinstance(member, dict):
            continue
        name = text_or_empty(member.get("name")) or "未命名成员"
        for report in as_list(member.get("reports")):
            if not isinstance(report, dict):
                continue
            for value in as_list(report.get("risks")) + as_list(report.get("support_needed")):
                text = text_or_empty(value)
                if text:
                    risks.append(f"{name}: {text}")
    return risks


def next_actions(data: dict[str, Any]) -> str:
    actions = as_list(data.get("next_actions"))
    if not actions:
        return "- 无明确下两周行动项"

    lines: list[str] = []
    for action in actions:
        if isinstance(action, dict):
            item = text_or_empty(action.get("item")) or text_or_empty(action.get("title")) or text_or_empty(action.get("action"))
            owner = text_or_empty(action.get("owner"))
            due = text_or_empty(action.get("due"))
            source = text_or_empty(action.get("source")) or text_or_empty(action.get("evidence"))
            suffix = " ".join(
                part
                for part in [
                    f"负责人：{owner}" if owner else "",
                    f"截止：{due}" if due else "",
                    f"来源：{source}" if source else "",
                ]
                if part
            )
            lines.append(f"{item}（{suffix}）" if suffix else item)
        else:
            lines.append(text_or_empty(action))
    return bullet(lines)


def evidence(data: dict[str, Any]) -> str:
    entries: list[str] = [text_or_empty(item) for item in as_list(data.get("evidence")) if text_or_empty(item)]
    for member in as_list(data.get("members")):
        if not isinstance(member, dict):
            continue
        name = text_or_empty(member.get("name")) or "未命名成员"
        for report in as_list(member.get("reports")):
            if not isinstance(report, dict):
                continue
            week = text_or_empty(report.get("week")) or "未标注周期"
            for link in as_list(report.get("links")):
                rendered = link_text(link)
                if rendered:
                    entries.append(f"{name} {week}: {rendered}")
    for item in as_list(data.get("chat_items")):
        if isinstance(item, dict):
            source = text_or_empty(item.get("source")) or text_or_empty(item.get("message_id"))
            title = text_or_empty(item.get("title")) or text_or_empty(item.get("summary")) or text_or_empty(item.get("content"))
            if source:
                entries.append(f"{title or '聊天事项'}: {source}")
    return bullet(entries, empty="无可展示来源")


def member_appendix(members: list[dict[str, Any]]) -> str:
    return member_progress(members) if members else "- 无成员周报明细"


def render(data: dict[str, Any]) -> str:
    period = data.get("period") or {}
    start = text_or_empty(period.get("start"))
    end = text_or_empty(period.get("end"))
    department = text_or_empty(data.get("department")) or "部门"
    generated_at = text_or_empty(data.get("generated_at")) or datetime.now().strftime("%Y-%m-%d %H:%M")
    members = [item for item in as_list(data.get("members")) if isinstance(item, dict)]
    chats = [item for item in as_list(data.get("chat_items")) if isinstance(item, dict)]
    highlights = as_list(data.get("highlights"))
    decisions = [text_or_empty(item) for item in as_list(data.get("decisions")) if text_or_empty(item)]

    overview_items = [
        f"统计周期：{start or '未填写'} 至 {end or '未填写'}",
        f"覆盖成员：{len(members)} 人",
        f"重要聊天事项：{len(chats)} 项",
        f"已确认决策：{len(decisions)} 项" if decisions else "",
        f"生成时间：{generated_at}",
    ]

    report = [
        f"# {department}双周报（{start or '未填写'} 至 {end or '未填写'}）",
        "## 双周概览",
        bullet(overview_items),
        "## 重点进展",
        titled_items(highlights, empty="无明确重点进展"),
        "## 重要事项",
        chat_items(chats),
        "## 关键决策",
        titled_items(decisions),
        "## 风险与需要协调",
        bullet(collect_report_risks(data)),
        "## 下两周计划",
        next_actions(data),
        "## 附录：证据与来源",
        evidence(data),
        "## 附录：成员周报明细",
        member_appendix(members),
    ]
    return "\n\n".join(report).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Feishu biweekly report from normalized JSON.")
    parser.add_argument("--input", required=True, help="Path to normalized JSON input.")
    parser.add_argument("--output", required=True, help="Path to write Markdown output.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("input JSON must be an object")

    output_path.write_text(render(data), encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
