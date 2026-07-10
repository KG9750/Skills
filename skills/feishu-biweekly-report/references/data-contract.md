# Data Contract

Normalize collected Feishu evidence into a single UTF-8 JSON file before rendering.

## Minimal Input

```json
{
  "department": "部门名称",
  "period": {
    "start": "2026-06-26",
    "end": "2026-07-09"
  },
  "members": [],
  "highlights": [],
  "chat_items": []
}
```

## Full Input Shape

```json
{
  "department": "部门名称",
  "period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "generated_at": "YYYY-MM-DD HH:MM",
  "members": [
    {
      "name": "成员姓名",
      "role": "岗位或小组",
      "reports": [
        {
          "week": "2026-W27",
          "done": ["已完成事项"],
          "next": ["后续计划"],
          "risks": ["风险或阻塞"],
          "support_needed": ["需要协调"],
          "links": [
            {
              "label": "周报链接或标题",
              "url": "https://..."
            }
          ]
        }
      ]
    }
  ],
  "highlights": [
    {
      "title": "管理层重点进展",
      "summary": "归纳说明",
      "owner": "负责人或团队",
      "source": "周报链接 / message_id / task_id"
    }
  ],
  "chat_items": [
    {
      "title": "事项标题",
      "summary": "一句话说明",
      "owner": "负责人",
      "status": "推进中",
      "priority": "P1",
      "date": "YYYY-MM-DD",
      "source": "群名 / 消息链接 / message_id"
    }
  ],
  "decisions": ["已确认决策"],
  "risks": ["跨成员风险或待确认风险"],
  "next_actions": [
    {
      "item": "下两周动作",
      "owner": "负责人",
      "due": "YYYY-MM-DD"
    }
  ],
  "evidence": ["补充证据索引"]
}
```

## Normalization Rules

- Keep user-facing report text in Chinese.
- Preserve original Feishu URLs, message IDs, document tokens, and report titles in evidence fields.
- Deduplicate by normalized title plus owner plus source date.
- Prefer management-level outcomes over activity logs.
- Keep per-member weekly report details in the appendix, not the main body.
- Mark uncertain AI inferences as `待确认`.
- Convert empty arrays and missing optional fields to "无" during rendering.
- Do not include raw secrets, access tokens, local file paths, or private config values in the final report.
