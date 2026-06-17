from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
import re

from time_utils import date_bucket


def cluster_key(item: dict) -> tuple:
    entities = item.get("entities") or ["unknown"]
    entity = sorted(str(entity).lower() for entity in entities)[0]
    return (entity, item.get("category", "community-backlash"), date_bucket(item.get("created_at")), topic_signature(item.get("text", "")))


def topic_signature(text: str) -> str:
    lowered = text.lower()
    topics = []
    for term in (
        "plagiarism",
        "harness",
        "eval",
        "benchmark",
        "funding",
        "valuation",
        "rollback",
        "outage",
        "license",
        "fork",
        "lawsuit",
        "resigned",
        "fired",
    ):
        if term in lowered:
            topics.append(term)
    if topics:
        return "-".join(topics[:2])
    words = [word for word in re.findall(r"[a-z0-9]+", lowered) if len(word) > 3]
    return sha1(" ".join(words[:8]).encode("utf-8")).hexdigest()[:8]


def cluster_events(items: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for item in items:
        groups[cluster_key(item)].append(item)

    events = []
    for entity, category, bucket, signature in sorted(groups):
        grouped_items = groups[(entity, category, bucket, signature)]
        entities = sorted({entity for item in grouped_items for entity in item.get("entities", [])})
        platforms = sorted({item.get("platform", "unknown") for item in grouped_items})
        event_id = "event-" + sha1(f"{entity}:{category}:{bucket}:{signature}".encode("utf-8")).hexdigest()[:12]
        events.append({
            "event_id": event_id,
            "entity_key": entity,
            "category": category,
            "time_bucket": bucket,
            "topic_signature": signature,
            "entities": entities,
            "platforms": platforms,
            "items": grouped_items,
        })
    return events
