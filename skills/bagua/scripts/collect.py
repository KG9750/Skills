#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from adapters import brave_search, demo, reddit_search, telegram_public, x_search
from config import load_config
from event_cluster import cluster_events
from http_client import HttpClient, HttpSettings
from llm_enhance import enhance_events
from normalize_items import normalize_items
from render_report import render_report
from score_heat import score_events
from storage import connect_storage, persist_run


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def atomic_copy(source: Path, destination: Path) -> None:
    temp = destination.with_name(destination.name + ".tmp-" + uuid4().hex[:8])
    shutil.copyfile(source, temp)
    os.replace(temp, destination)


def run(args: argparse.Namespace) -> Path:
    skill_root = Path(__file__).resolve().parents[1]
    config = load_config(args.config)
    warnings = []
    suggested_sources = []
    client = None

    if args.demo:
        result = demo.collect(config, skill_root)
        raw_items = result.items
        warnings.extend(result.warnings)
        suggested_sources.extend(result.suggested_sources)
    else:
        collection = config.get("collection", {})
        client = HttpClient(HttpSettings(
            timeout=float(collection.get("request_timeout", 20)),
            retry_count=int(collection.get("retry_count", 2)),
            user_agent=config.get("reddit", {}).get("user_agent", "bagua/0.1"),
        ))
        raw_items = []
        try:
            adapters = selected_adapters(args.platform)
            warnings.extend(live_preflight_warnings(config, [name for name, _ in adapters]))
            if not getattr(args, "force_live", False):
                adapters = [(name, adapter) for name, adapter in adapters if platform_ready(config, name)]
            for name, adapter in adapters:
                result = adapter.collect(config, client)
                raw_items.extend(result.items)
                warnings.extend(result.warnings)
                suggested_sources.extend(result.suggested_sources)
                if result.warnings and config.get("general", {}).get("strict"):
                    raise RuntimeError(f"{name} adapter failed in strict mode: {'; '.join(result.warnings)}")
        finally:
            client.close()

    items = normalize_items(raw_items, config)
    events = score_events(cluster_events(items), config)
    events, llm_warnings = enhance_events(events, config)
    warnings.extend(llm_warnings)
    report = render_report(events, warnings, suggested_sources, config)

    output_root = Path(config.get("general", {}).get("output_dir", "~/.bagua/runs")).expanduser()
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S_%f") + "-" + uuid4().hex[:6]
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(run_dir / "items.jsonl", items)
    write_jsonl(run_dir / "events.jsonl", events)
    (run_dir / "report.md").write_text(report, encoding="utf-8")

    output_root.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        atomic_copy(run_dir / "items.jsonl", output_root / "latest-items.jsonl")
        atomic_copy(run_dir / "events.jsonl", output_root / "latest-events.jsonl")
        atomic_copy(run_dir / "report.md", output_root / "latest.md")
        if not args.demo:
            with connect_storage(config) as connection:
                persist_run(connection, run_id, items, events, warnings)

    return run_dir


def selected_adapters(platforms: str | None):
    available = {
        "x": x_search,
        "reddit": reddit_search,
        "telegram": telegram_public,
        "brave": brave_search,
    }
    if not platforms:
        names = ["x", "reddit", "telegram", "brave"]
    else:
        names = [name.strip() for name in platforms.split(",") if name.strip()]
    unknown = [name for name in names if name not in available]
    if unknown:
        raise ValueError(f"Unknown platform(s): {', '.join(unknown)}")
    return [(name, available[name]) for name in names]


def live_preflight_warnings(config: dict, platforms: list[str]) -> list[str]:
    warnings = []
    for name in platforms:
        if not platform_ready(config, name):
            warnings.append(f"preflight: {name} not ready; {platform_reason(config, name)}")
    return warnings


def platform_ready(config: dict, name: str) -> bool:
    if name == "brave":
        return bool(config.get("brave", {}).get("api_key"))
    if name == "x":
        x_config = config.get("x", {})
        return bool(x_config.get("bearer_token") or (x_config.get("public_web_best_effort", True) and config.get("brave", {}).get("api_key")))
    if name == "reddit":
        reddit = config.get("reddit", {})
        return bool(reddit.get("client_id") and reddit.get("client_secret"))
    if name == "telegram":
        telegram = config.get("telegram", {})
        return bool(telegram.get("bot_token") or telegram.get("seed_channels"))
    return False


def platform_reason(config: dict, name: str) -> str:
    if name == "brave":
        return "missing brave.api_key or BRAVE_API_KEY"
    if name == "x":
        return "missing x.bearer_token/X_BEARER_TOKEN and Brave supplement"
    if name == "reddit":
        return "Reddit public JSON is best-effort and often blocked; configure OAuth or rerun with --force-live"
    if name == "telegram":
        return "missing telegram.bot_token/TELEGRAM_BOT_TOKEN or seed_channels"
    return "unknown platform"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and report AI social gossip signals.")
    parser.add_argument("--config", help="Path to local bagua TOML config. Defaults to ~/.bagua/config.toml if present.")
    parser.add_argument("--demo", action="store_true", help="Run against bundled sample data instead of live adapters.")
    parser.add_argument("--platform", help="Comma-separated platform subset: x,reddit,telegram,brave.")
    parser.add_argument("--dry-run", action="store_true", help="Write the timestamped run but do not update latest files or SQLite storage.")
    parser.add_argument("--force-live", action="store_true", help="Attempt selected live adapters even when preflight says they are not ready.")
    return parser.parse_args()


if __name__ == "__main__":
    output = run(parse_args())
    print(f"Bagua report written to {output / 'report.md'}")
