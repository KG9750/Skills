# Platform Strategy

## Scope

v1 focuses on X, Reddit, and Telegram. Chinese social platforms are intentionally out of scope for v1. Web search may be used by Codex as a fallback when platform APIs or public pages are unavailable, but the script should keep its own adapter boundaries clear.

## X

- Prefer the official recent search API when `x.bearer_token` is configured.
- Fall back to public-web or search-index results only when accessible without bypassing access controls.
- Use `collection.results_per_query` for `max_results` and follow `next_token` up to `collection.max_pages`.
- Good signals: original posts by founders, employees, researchers, investors, AI journalists, and project maintainers; quote-post chains; public replies; sudden deletion or apology references.
- Expected v1 adapter behavior: return structured items when credentials are available, otherwise emit a warning and continue.

## Reddit

- Prefer public JSON endpoints for public subreddit/search pages.
- Use OAuth only as an enhancement when credentials are configured.
- Use `collection.results_per_query` for listing limits and follow `after` up to `collection.max_pages`.
- Default live preflight treats Reddit as ready only when OAuth is configured. Use `--force-live` to intentionally try public JSON.
- Expect public JSON to be blocked in some network environments; after a 403/blocked response, stop the Reddit adapter for that run and report one warning instead of retrying every subreddit.
- Good signals: highly upvoted threads in AI, ML, startup, programming, and product communities; comments with primary links; crossposts.
- Treat anonymous claims as early signals unless linked to first-party evidence.

## Telegram

- Use configured seed channels first.
- Support Telegram Bot API only for channels or groups the bot is authorized to see.
- Support public `t.me/s/<channel>` pages for public channel seeds.
- Pass Telegram `allowed_updates` as JSON. If a bot-visible update has no timestamp, use collection time and mark it through normal time confidence handling.
- Automatically discovered channels should go to suggested-source output and must not be trusted by default.
- Telegram is not a full-web search source; avoid implying complete coverage.

## Web Search Fallback

When `brave.api_key` is configured, the Brave adapter searches web-indexed AI gossip signals and X-indexed supplement results. When no search API is configured, the skill may guide Codex to use available web search tools and then pass results into the same JSONL shape.

Brave is single-page in this implementation: tune `brave.count` for result count. `collection.max_pages` applies to X and Reddit.

## Failure Policy

Default to tolerant failure. If one platform fails, continue the run, include a warning, and list missing platforms in the report. If `general.strict = true`, fail fast.

Live collection skips platforms that fail preflight unless `--force-live` is set. This avoids long hangs in no-credential environments.

Use `scripts/smoke_check.py --live` after configuring credentials or seed channels. Missing credentials should be reported as readiness gaps, not hidden failures.
