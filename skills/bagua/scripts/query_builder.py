from __future__ import annotations

import re


CONTROVERSY_TERMS = [
    "drama",
    "beef",
    "dispute",
    "accused",
    "accusation",
    "fraud",
    "fake",
    "fake benchmark",
    "benchmark gaming",
    "misleading",
    "plagiarism",
    "leaked",
    "meltdown",
    "apology",
    "deleted",
    "called out",
    "exposed",
    "rollback",
    "outage",
    "lawsuit",
    "fired",
    "resigned",
    "denies",
    "rumor",
    "unconfirmed",
    "complaint",
    "complaints",
]

CONFLICT_CATEGORIES = {
    "benchmark-dispute",
    "funding-rumor",
    "open-source-conflict",
    "product-fail",
    "founder-drama",
    "legal-dispute",
}


def merge_entities(primary: str | None, text: str, config: dict) -> list[str]:
    entities = []
    if primary:
        entities.append(primary)
    entities.extend(infer_entities(text, config))
    deduped = []
    seen = set()
    for entity in entities:
        key = entity.lower()
        if key not in seen:
            deduped.append(entity)
            seen.add(key)
    return deduped


def watch_entities(config: dict) -> list[str]:
    watchlist = config.get("watchlist", {})
    entities = []
    for key in ("companies", "products", "projects", "public_figures"):
        entities.extend(str(value) for value in watchlist.get(key, []) if str(value).strip())
    deduped = []
    seen = set()
    for entity in entities:
        normalized = entity.lower()
        if normalized not in seen:
            deduped.append(entity)
            seen.add(normalized)
    return deduped


def per_query_limit(config: dict) -> int:
    return int(config.get("collection", {}).get("per_query_limit", 8))


def generated_queries(config: dict) -> list[dict[str, str]]:
    terms = " OR ".join(f'"{term}"' if " " in term else term for term in CONTROVERSY_TERMS[:8])
    queries = []
    for entity in watch_entities(config)[:per_query_limit(config)]:
        queries.append({
            "entity": entity,
            "general": f'"{entity}" ({terms}) AI',
            "x": f'"{entity}" ({terms}) lang:en -is:retweet',
            "brave_x": f'site:x.com "{entity}" ({terms}) AI',
            "reddit": f'"{entity}" ({terms})',
        })
    return queries


def infer_entities(text: str, config: dict) -> list[str]:
    lowered = text.lower()
    return [entity for entity in watch_entities(config) if entity.lower() in lowered]


def infer_category(text: str) -> str:
    lowered = text.lower()
    if ("benchmark" in lowered or "eval" in lowered) and has_any(lowered, ("dispute", "fake benchmark", "accused", "accusation", "gaming", "misleading", "harness")):
        return "benchmark-dispute"
    if has_any(lowered, ("lawsuit", "sued", "sues", "legal dispute", "court filing")):
        return "legal-dispute"
    if "funding" in lowered or "valuation" in lowered or re.search(r"\brais(?:e|ed|ing)\b", lowered):
        return "funding-rumor"
    if has_any(lowered, ("license", "fork", "maintainer")) and has_any(lowered, ("dispute", "fight", "called out", "accused", "backlash", "drama")):
        return "open-source-conflict"
    if "rollback" in lowered or "outage" in lowered or "broken" in lowered or "product fail" in lowered or ("pricing" in lowered and has_any(lowered, ("complaint", "backlash", "angry"))):
        return "product-fail"
    if has_any(lowered, ("founder", "ceo", "investor")) and has_any(lowered, ("drama", "beef", "arguing", "fight", "accused", "denies", "lawsuit", "fired", "resigned")):
        return "founder-drama"
    if has_any(lowered, ("backlash", "called out", "exposed", "meltdown")):
        return "community-backlash"
    return "uncategorized"


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def is_gossip_signal(text: str, category: str | None = None) -> bool:
    return bool(category and category in CONFLICT_CATEGORIES)
