---
name: bagua
description: AI social gossip radar for finding, clustering, scoring, and reporting high-heat AI industry gossip from social platforms. Use when Codex needs to search X.com, Reddit, Telegram, or web-indexed social discussion for AI founder drama, public disputes, product failures, benchmark controversies, funding rumors, open-source conflicts, or other fast-moving social news, then produce a Chinese report with evidence links, heat scores, credibility labels, and follow-up suggestions.
---

# Bagua

## Purpose

Use this skill to run an on-demand AI gossip radar. Focus v1 on AI-related social signals from X, Reddit, and Telegram, then produce a Chinese report that separates confirmed events from early signals.

Keep the output lively but careful: write readable "eat-melon" titles, but do not present rumors as facts.

## Workflow

1. Load `references/platforms.md` before changing or extending platform collection.
2. Load `references/scoring.md` before changing heat, credibility, clustering, or ranking behavior.
3. Load `references/ai-gossip-taxonomy.md` before adding categories, watchlist entities, or controversy keywords.
4. Load `references/report-format.md` before changing report structure or language.
5. Run the CLI from the skill root:

```bash
python3 scripts/collect.py --demo
```

For real collection, create a local config from `assets/config.example.toml`, then run:

```bash
python3 scripts/collect.py --config ~/.bagua/config.toml
```

Install the local runtime dependencies before real collection:

```bash
python3 -m pip install -r requirements.txt
```

The CLI writes each run to a timestamped directory under `~/.bagua/runs/` by default and also updates `latest.md`, `latest-items.jsonl`, and `latest-events.jsonl`.

Use `--platform x,reddit,telegram,brave` to debug a subset. Use `--dry-run` to write the timestamped run without updating `latest-*` files or SQLite history.

Live collection runs preflight checks and skips platforms without usable credentials or seeds. Use `--force-live` only when intentionally testing best-effort public endpoints such as Reddit public JSON.

Check runtime readiness and run credentialed smoke tests with:

```bash
python3 scripts/smoke_check.py --config ~/.bagua/config.toml --live
```

## Boundaries

- Collect public, authorized, or web-indexed content only.
- Do not bypass logins, paywalls, CAPTCHAs, rate limits, private groups, private Discord servers, or platform access controls.
- Do not output doxxing, private contact details, location data, private chat leaks, or minors-related gossip.
- Public screenshots, deleted-post caches, and secondhand claims may enter evidence chains, but score them lower than accessible first-party links.
- Default to tolerant platform failure: record warnings and continue. Use strict mode only for debugging.

## Defaults

- Domain: AI only in v1.
- Time windows: keep only items inside `heating_days`, mark items inside `fresh_hours` as fresh, and down-rank unknown timestamps.
- Content gate: require a gossip or controversy signal by default, so ordinary launches, papers, and product updates do not enter the board.
- Platforms: X official API plus public-web best effort, Reddit OAuth plus forced public-JSON best effort, Telegram Bot API plus public channel pages.
- Search fallback: Brave Search when `brave.api_key` is configured.
- Storage: timestamped JSONL/Markdown outputs plus optional SQLite history for real runs.
- Collection size: `collection.results_per_query` controls platform result limits; `collection.max_pages` controls X/Reddit pagination.
- Watchlist: configured in local TOML only; no ad hoc CLI watchlist in v1.
- Output: Chinese report summaries and follow-ups, with English sources preserved only as links, handles, and short verification snippets.
- Ranking: Main Board top 10 and Early Signals top 10.
- Heat priority: cross-platform spread first.
- Credibility priority: first-party sources first, then verifiable evidence, independent source domains, and source reputation.

## Scripts

- `scripts/collect.py`: CLI entrypoint and run orchestration.
- `scripts/adapters/`: platform adapter contracts and collectors.
- `scripts/adapters/brave_search.py`: Brave Web Search fallback and X search supplement.
- `scripts/storage.py`: SQLite history and cross-run dedupe cache.
- `scripts/llm_enhance.py`: optional OpenAI-compatible title, summary, and follow-up generation.
- `scripts/smoke_check.py`: dependency, credential, and live-smoke readiness checker.
- `scripts/normalize_items.py`: item normalization, blacklist filtering, and item-level dedupe.
- `scripts/event_cluster.py`: event clustering from normalized posts.
- `scripts/score_heat.py`: heat and credibility scoring.
- `scripts/render_report.py`: Markdown report generation.

## Configuration

Use `assets/config.example.toml` as the template. Real secrets should live in `~/.bagua/config.toml` or another local file outside git. Never print tokens in reports, warnings, or tracebacks.
