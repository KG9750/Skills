---
name: feishu-biweekly-report
description: Production-oriented Feishu biweekly report generator. Use when the user wants a "飞书双周报生成助手" that uses Feishu self-built app credentials, a configured Feishu built-in Report rule ID, a fixed member list, configured chats or user-authorized all-conversation search, DeepSeek V4-Pro management-summary generation, and append-only writing to a target Feishu document. Also use for dry runs, config preflight, Feishu Report API blockers, or exported JSON fallbacks for the same workflow.
---

# Feishu Biweekly Report

Generate a Chinese management-level biweekly report from Feishu built-in Report submissions and full Feishu chat histories, then append it to a target Feishu doc.

## Product Contract

- Use Feishu self-built app credentials from `FEISHU_APP_ID` and `FEISHU_APP_SECRET`, or the active secure `lark-cli` profile when `feishu.auth_source: lark_cli`.
- Use a configured Feishu built-in Report `report_rule_id`; do not infer weekly reports by title.
- Use an explicit configured member list; do not enumerate the department automatically.
- Pull full messages from configured chat IDs, or search every group and P2P conversation visible to an explicitly authorized user, for the two-week window; then let DeepSeek judge importance.
- Generate a management summary, not a per-person activity log.
- Allow DeepSeek to merge, deduplicate, and rewrite, but preserve evidence and mark uncertain items as `待确认`.
- Append to the target document tail only. Do not replace or overwrite.
- Prefer official Feishu Report OpenAPI. If blocked or unavailable, use exported JSON fallback rather than private endpoints.

## Quick Start

1. Copy `assets/config.example.yaml` outside the skill directory and fill in department, `report_rule_id`, members, a chat collection mode, and `target_document_id`.
2. Export secrets in the shell:

   ```bash
   export FEISHU_APP_ID=cli_xxx
   export FEISHU_APP_SECRET=xxx
   export DEEPSEEK_API_KEY=sk-xxx
   export DEEPSEEK_MODEL=deepseek-v4-pro
   ```

3. Run without writing first:

   ```bash
   python3 ~/.codex/skills/feishu-biweekly-report/scripts/run_biweekly_report.py \
     --config config/feishu-biweekly-report.yaml
   ```

4. Append only after reviewing the generated Markdown:

   ```bash
   python3 ~/.codex/skills/feishu-biweekly-report/scripts/run_biweekly_report.py \
     --config config/feishu-biweekly-report.yaml \
     --write
   ```

Use `--skip-ai` to produce a deterministic evidence summary when `DEEPSEEK_API_KEY` is not available.

## Workflow

1. Read `references/feishu-collection.md` before live collection.
2. Read `references/data-contract.md` before changing adapters or rendered fields.
3. Run the main script with external YAML config.
4. If Feishu Report API fails, report the exact safe blocker. Use `fallback.reports_json` only when the user has an export.
5. If chat collection fails because `feishu-cli` is unavailable, report the blocker. Use `fallback.chats_json` for development.
6. Inspect `collected.raw.json`, `normalized.json`, and `biweekly-report.md` in the output dir.
7. Append with `--write` only when the user wants live delivery.

## Files

- `scripts/run_biweekly_report.py`: product runner for collect, generate, render, and optional append.
- `scripts/render_biweekly_report.py`: deterministic Markdown renderer.
- `assets/config.example.yaml`: external config template.
- `references/feishu-collection.md`: live collection and permissions guide.
- `references/data-contract.md`: normalized JSON contract.

## Failure Handling

- Missing config or secrets: stop with a JSON error, not a partial report.
- Missing `PyYAML`: install it or run in an environment that provides it.
- Missing `DEEPSEEK_API_KEY`: rerun with valid DeepSeek env or `--skip-ai`.
- Missing `feishu-cli` for chat/write paths: provide chat fallback JSON or install/configure `feishu-cli`.
- Feishu Report API returns non-zero `code`: show `code` and `msg`; do not switch to guessed endpoints.
