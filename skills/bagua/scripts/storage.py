from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def connect_storage(config: dict) -> sqlite3.Connection:
    storage = config.get("storage", {})
    path = Path(storage.get("sqlite_path", "~/.bagua/bagua.sqlite3")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    ensure_schema(connection)
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            item_count INTEGER NOT NULL,
            event_count INTEGER NOT NULL,
            warnings_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS items (
            canonical_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            url TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL,
            text TEXT NOT NULL,
            first_seen_run_id TEXT NOT NULL,
            last_seen_run_id TEXT NOT NULL,
            seen_count INTEGER NOT NULL DEFAULT 1,
            item_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            latest_run_id TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            category TEXT NOT NULL,
            heat INTEGER NOT NULL,
            credibility INTEGER NOT NULL,
            event_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_items (
            event_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            PRIMARY KEY (event_id, canonical_id)
        );
        """
    )
    connection.commit()


def persist_run(connection: sqlite3.Connection, run_id: str, items: list[dict], events: list[dict], warnings: list[str]) -> None:
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO runs(run_id, created_at, item_count, event_count, warnings_json) VALUES (?, ?, ?, ?, ?)",
            (run_id, created_at, len(items), len(events), json.dumps(warnings, ensure_ascii=False)),
        )
        for item in items:
            existing = connection.execute(
                "SELECT seen_count FROM items WHERE canonical_id = ?",
                (item["canonical_id"],),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE items
                    SET last_seen_run_id = ?, seen_count = ?, item_json = ?
                    WHERE canonical_id = ?
                    """,
                    (run_id, existing[0] + 1, json.dumps(item, ensure_ascii=False), item["canonical_id"]),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO items(canonical_id, platform, url, author, created_at, text, first_seen_run_id, last_seen_run_id, seen_count, item_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["canonical_id"],
                        item.get("platform", ""),
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("created_at", ""),
                        item.get("text", ""),
                        run_id,
                        run_id,
                        1,
                        json.dumps(item, ensure_ascii=False),
                    ),
                )
        for event in events:
            scores = event.get("scores", {})
            connection.execute(
                """
                INSERT OR REPLACE INTO events(event_id, latest_run_id, entity_key, category, heat, credibility, event_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    run_id,
                    event.get("entity_key", ""),
                    event.get("category", ""),
                    int(scores.get("heat", 0)),
                    int(scores.get("credibility", 0)),
                    json.dumps(event, ensure_ascii=False),
                ),
            )
            for item in event.get("items", []):
                canonical_id = item.get("canonical_id")
                if canonical_id:
                    connection.execute(
                        "INSERT OR IGNORE INTO event_items(event_id, canonical_id) VALUES (?, ?)",
                        (event["event_id"], canonical_id),
                    )
