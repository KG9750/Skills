from __future__ import annotations

import hashlib
from urllib.parse import urlparse

from models import item_dict
from query_builder import infer_category, is_gossip_signal
from time_utils import age_hours, parse_datetime, utc_now


def canonical_id(item: dict) -> str:
    platform = item.get("platform", "unknown")
    post_id = item.get("post_id") or item.get("id")
    if post_id:
        return f"{platform}:{post_id}"
    url = item.get("url")
    if url:
        return f"url:{url.strip().lower()}"
    digest = hashlib.sha1((item.get("text") or "").encode("utf-8")).hexdigest()[:16]
    return f"text:{digest}"


def blocked(item: dict, blacklist: dict) -> bool:
    text = (item.get("text") or "").lower()
    author = (item.get("author") or "").lower()
    platform = (item.get("platform") or "").lower()
    url = item.get("url") or ""
    domain = urlparse(url).netloc.lower()
    raw = item.get("raw", {}) if isinstance(item.get("raw", {}), dict) else {}

    for account in blacklist.get("accounts", []):
        if author == account.lower():
            return True
    for keyword in blacklist.get("keywords", []):
        if keyword.lower() in text:
            return True
    for blocked_domain in blacklist.get("domains", []):
        if blocked_domain.lower() in domain:
            return True
    if platform == "telegram":
        channel = str(raw.get("channel", item.get("author", ""))).lower()
        for blocked_channel in blacklist.get("channels", []):
            if channel == blocked_channel.lower().removeprefix("@"):
                return True
    if platform == "reddit":
        subreddit = str(raw.get("subreddit", "")).lower()
        for blocked_subreddit in blacklist.get("subreddits", []):
            if subreddit == blocked_subreddit.lower().removeprefix("r/"):
                return True
    return False


def normalize_items(items: list[dict], config: dict) -> list[dict]:
    seen = set()
    normalized = []
    blacklist = config.get("blacklist", {})
    general = config.get("general", {})
    fresh_hours = float(general.get("fresh_hours", 24))
    heating_hours = float(general.get("heating_days", 7)) * 24
    now = utc_now()

    for raw_item in items:
        item = item_dict(raw_item)
        if blocked(item, blacklist):
            continue
        item_age = age_hours(item.get("created_at"), now)
        if item_age is not None and item_age > heating_hours:
            continue
        cid = canonical_id(item)
        if cid in seen:
            continue
        seen.add(cid)
        copy = dict(item)
        copy["canonical_id"] = cid
        copy.setdefault("entities", [])
        copy["time_confidence"] = "known" if parse_datetime(copy.get("created_at")) else "unknown"
        copy["age_hours"] = item_age
        copy["fresh"] = bool(item_age is not None and item_age <= fresh_hours)
        if not copy.get("category") or copy.get("category") in {"community-backlash", "uncategorized"}:
            copy["category"] = infer_category(copy.get("text", ""))
        copy["gossip_signal"] = is_gossip_signal(copy.get("text", ""), copy.get("category"))
        if general.get("require_gossip_signal", True) and not copy["gossip_signal"]:
            continue
        copy.setdefault("engagement", {})
        normalized.append(copy)

    return normalized
