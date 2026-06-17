#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from argparse import Namespace
from contextlib import contextmanager

from collect import run as collect_run
from config import load_config


def dependency_status(config_path: str | None) -> dict[str, bool]:
    needs_tomli = sys.version_info < (3, 11) and bool(config_path)
    return {
        "httpx": importlib.util.find_spec("httpx") is not None,
        "beautifulsoup4": importlib.util.find_spec("bs4") is not None,
        "tomli": True if not needs_tomli else importlib.util.find_spec("tomli") is not None,
    }


def platform_status(config: dict) -> dict[str, dict]:
    brave_key = bool(config.get("brave", {}).get("api_key"))
    telegram = config.get("telegram", {})
    reddit = config.get("reddit", {})
    x_config = config.get("x", {})
    return {
        "brave": {
            "enabled": bool(config.get("brave", {}).get("enabled", True)),
            "ready": brave_key,
            "reason": "api key configured" if brave_key else "missing brave.api_key or BRAVE_API_KEY",
        },
        "x": {
            "enabled": bool(x_config.get("enabled", True)),
            "ready": bool(x_config.get("bearer_token") or (x_config.get("public_web_best_effort", True) and brave_key)),
            "reason": "bearer token or Brave supplement configured" if x_config.get("bearer_token") or brave_key else "missing x.bearer_token/X_BEARER_TOKEN and Brave supplement",
        },
        "reddit": {
            "enabled": bool(reddit.get("enabled", True)),
            "ready": bool(reddit.get("enabled", True) and reddit.get("client_id") and reddit.get("client_secret")),
            "reason": "OAuth configured" if reddit.get("client_id") and reddit.get("client_secret") else "public JSON enabled but not live-ready; may be network-blocked",
        },
        "telegram": {
            "enabled": bool(telegram.get("enabled", True)),
            "ready": bool(telegram.get("bot_token") or telegram.get("seed_channels")),
            "reason": "bot token or seed channels configured" if telegram.get("bot_token") or telegram.get("seed_channels") else "missing telegram.bot_token/TELEGRAM_BOT_TOKEN or seed_channels",
        },
    }


def live_platforms(status: dict[str, dict]) -> list[str]:
    return [name for name, value in status.items() if value["enabled"] and value["ready"]]


def readiness_report(config_path: str | None) -> dict:
    config = load_config(config_path)
    deps = dependency_status(config_path)
    platforms = platform_status(config)
    return {
        "dependencies": deps,
        "platforms": platforms,
        "ready_platforms": live_platforms(platforms),
        "ready": all(deps.values()) and bool(live_platforms(platforms)),
    }


def run_live_smoke(config_path: str | None, platforms: list[str]) -> str:
    with smoke_collection_limits():
        run_dir = collect_run(Namespace(
            config=config_path,
            demo=False,
            platform=",".join(platforms),
            dry_run=True,
        ))
    return str(run_dir / "report.md")


@contextmanager
def smoke_collection_limits():
    overrides = {
        "BAGUA_REQUEST_TIMEOUT": "5",
        "BAGUA_RETRY_COUNT": "0",
        "BAGUA_PER_QUERY_LIMIT": "1",
        "BAGUA_RESULTS_PER_QUERY": "10",
    }
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Bagua runtime readiness and optionally run a credentialed live smoke.")
    parser.add_argument("--config", help="Path to local bagua TOML config. Defaults to ~/.bagua/config.toml if present.")
    parser.add_argument("--live", action="store_true", help="Run a dry-run live smoke for ready platforms.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = readiness_report(args.config)
    if args.live and report["ready"]:
        report["live_report"] = run_live_smoke(args.config, report["ready_platforms"])
    elif args.live:
        report["live_report"] = None

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Bagua readiness: " + ("ready" if report["ready"] else "not ready"))
        print("Ready platforms: " + (", ".join(report["ready_platforms"]) or "none"))
        for name, value in report["platforms"].items():
            print(f"- {name}: {'ready' if value['ready'] else 'missing'} ({value['reason']})")
        if report.get("live_report"):
            print("Live smoke report: " + report["live_report"])

    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
