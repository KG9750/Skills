# Feishu Collection Guide

Use this guide before collecting live Feishu data for the production biweekly report workflow.

## Required Config

Ask for or infer these values:

- `department`: department name shown in the report title.
- `period`: explicit start/end dates, or blank for the most recent 14 days.
- `feishu.report_rule_id`: Feishu built-in Report rule/template ID for the weekly report.
- `feishu.members`: explicit member list with names and Feishu user IDs.
- `feishu.chats`: chat IDs to pull in full for the period, or `feishu.messages.mode: user_search` to search all group and P2P conversations visible to the authorized user.
- `feishu.target_document_id`: docx document ID for append-only delivery.
- `fallback.reports_json`: optional exported report JSON for development or API blockers.
- `fallback.chats_json`: optional exported chat JSON for development or CLI blockers.

## Weekly Report Sources

Use the official Feishu Report OpenAPI first:

```text
POST /open-apis/report/v1/tasks/query
```

The runner sends `rule_id`, member `user_id`, `commit_start_time`, `commit_end_time`, pagination fields, and `user_id_type`.

Required production assumptions:

- `FEISHU_APP_ID` and `FEISHU_APP_SECRET` are available in the environment.
- The self-built app has Feishu Report read permission such as `report:report`.
- The configured `report_rule_id` is the weekly report rule. Do not use name matching in production.

If the official API is blocked by permissions, tenant settings, or an undocumented response shape, stop with the exact `code`/`msg` and use `fallback.reports_json` only when the user provides an export.

## Chat Sources

Pull full group timelines for the two-week window. Do not keyword-filter first; the AI generation step decides importance.

```bash
python3 ~/.codex/skills/feishu-cli-chat/scripts/fetch_chat_history.py oc_xxx \
  --start 2026-06-26T00:00:00 --end 2026-07-10T00:00:00 \
  --output-dir /tmp/feishu-chat-window
```

When search returns only message IDs, fetch details before summarizing:

```bash
feishu-cli msg mget --message-ids om_xxx,om_yyy
```

If `feishu-cli` is not available, stop with a blocker and use `fallback.chats_json` for development.

For all conversations visible to an authorized user, configure:

```yaml
feishu:
  auth_source: lark_cli
  messages:
    mode: user_search
    include: [group, p2p]
    page_size: 50
    max_pages: 40
```

This mode uses `lark-cli im +messages-search --as user`, paginates until completion, and requires user OAuth scopes including `search:message`, `im:message.group_msg:get_as_user`, `im:message.p2p_msg:get_as_user`, and `im:message:readonly`.

## Auth Preflight

Before live collection, verify the self-built app has the required report and document permissions in Feishu Open Platform. If using `feishu-cli` for chat/write, also check likely user/app scopes:

```bash
feishu-cli auth check --scope "search:message im:message:readonly docx:document:readonly report:report"
```

For writing to the target document, verify document write access:

```bash
feishu-cli doc get <document_id> -o json
```

If auth fails, report the exact missing scope or login command. Do not fall back to fabricated sample data.

## Append Write

Write generated Markdown with `feishu-cli-write` conventions:

```bash
feishu-cli doc content-update <document_id> --mode append \
  --markdown-file /tmp/feishu-biweekly-report.md
```

Verify command success and include the target document ID or URL in the final response.
