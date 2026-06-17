from __future__ import annotations

import math
from urllib.parse import urlparse

from time_utils import age_hours, utc_now


FIRST_PARTY_TYPES = {"first_party", "official", "employee", "founder", "maintainer"}
VERIFIABLE_TYPES = {"public_post", "official_statement", "repo_issue", "discussion_with_links"}
SECONDHAND_TYPES = {"secondhand_claim", "secondhand_summary", "screenshot", "deleted_cache"}
CONTROVERSY_TERMS = {
    "drama", "beef", "dispute", "accused", "accusation", "fired", "resigned",
    "lawsuit", "fraud", "fake benchmark", "benchmark gaming", "misleading",
    "plagiarism", "copied", "leaked", "meltdown", "apology", "deleted",
    "retracted", "called out", "exposed", "scam", "rollback",
}
REPUTABLE_DOMAINS = {
    "bbc.com",
    "bbc.co.uk",
    "bloomberg.com",
    "businessinsider.com",
    "cnbc.com",
    "decrypt.co",
    "engadget.com",
    "financialtimes.com",
    "ft.com",
    "gizmodo.com",
    "reuters.com",
    "seekingalpha.com",
    "techcrunch.com",
    "theinformation.com",
    "theverge.com",
    "wired.com",
    "wsj.com",
}


def engagement_value(item: dict) -> int:
    engagement = item.get("engagement", {})
    return sum(int(value) for value in engagement.values() if isinstance(value, int))


def clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def score_event(event: dict, config: dict | None = None) -> dict:
    config = config or {}
    heat_weights = config.get("scoring", {}).get("weights", {}).get("heat", {})
    credibility_weights = config.get("scoring", {}).get("weights", {}).get("credibility", {})
    items = event.get("items", [])
    platforms = {item.get("platform") for item in items if item.get("platform")}
    source_types = {item.get("source_type") for item in items if item.get("source_type")}
    evidence_types = {item.get("evidence_type") for item in items if item.get("evidence_type")}
    combined_text = " ".join(item.get("text", "") for item in items).lower()
    total_engagement = sum(engagement_value(item) for item in items)
    now = utc_now()
    ages = [age_hours(item.get("created_at"), now) for item in items]
    known_ages = [age for age in ages if age is not None]
    latest_age = min(known_ages) if known_ages else None
    fresh_count = sum(1 for item in items if item.get("fresh"))

    max_cross_platform = int(heat_weights.get("cross_platform", 35))
    max_engagement = int(heat_weights.get("engagement", 20))
    max_source = int(heat_weights.get("source_prominence", 15))
    max_controversy = int(heat_weights.get("controversy", 15))
    max_recency = int(heat_weights.get("recency", 10))
    max_evidence = int(heat_weights.get("evidence", 5))

    cross_platform = min(max_cross_platform, len(platforms) * (max_cross_platform / 2.5))
    engagement = min(max_engagement, math.log10(total_engagement + 1) * (max_engagement / 4))
    source_prominence = max_source if source_types & FIRST_PARTY_TYPES else max_source * 0.55 if source_types else 0
    controversy = min(max_controversy, sum(max_controversy / 5 for term in CONTROVERSY_TERMS if term in combined_text))
    recency = recency_score(latest_age, config, max_recency)
    evidence = max_evidence if evidence_types else 0
    heat = clamp(cross_platform + engagement + source_prominence + controversy + recency + evidence)

    max_first_party = int(credibility_weights.get("first_party", 35))
    max_verifiable = int(credibility_weights.get("verifiable_evidence", 25))
    max_independent = int(credibility_weights.get("independent_sources", 20))
    max_reputation = int(credibility_weights.get("source_reputation", 10))
    max_specificity = int(credibility_weights.get("claim_specificity", 10))

    first_party = max_first_party if source_types & FIRST_PARTY_TYPES else 0
    verifiable = max_verifiable if evidence_types & VERIFIABLE_TYPES else max_verifiable * 0.4 if evidence_types - SECONDHAND_TYPES else 0
    independent = independent_score(items, platforms, max_independent)
    reputation = source_reputation_score(items, source_types, max_reputation)
    search_snippet = bool(evidence_types == {"search_snippet"} or "search_snippet" in evidence_types)
    if search_snippet and reputation >= max_reputation * 0.8:
        verifiable = max(verifiable, max_verifiable * 0.6)
    specificity = max_specificity if event.get("entities") and event.get("category") else max_specificity * 0.5
    credibility = clamp(first_party + verifiable + independent + reputation + specificity)

    label = "confirmed" if credibility >= 80 else "likely" if credibility >= 60 else "rumor" if credibility >= 35 else "weak signal"
    board = "main" if credibility >= 60 or (first_party and heat >= 55) else "early"

    event["scores"] = {
        "heat": heat,
        "credibility": credibility,
        "components": {
            "cross_platform": round(cross_platform),
            "engagement": round(engagement),
            "source_prominence": round(source_prominence),
            "controversy": round(controversy),
            "recency": recency,
            "evidence": evidence,
            "first_party": first_party,
            "verifiable_evidence": verifiable,
            "independent_sources": independent,
        },
        "label": label,
        "board": board,
    }
    event["fresh_count"] = fresh_count
    event["time_confidence"] = "known" if known_ages else "unknown"
    return event


def score_events(events: list[dict], config: dict | None = None) -> list[dict]:
    return sorted((score_event(event, config) for event in events), key=lambda event: event["scores"]["heat"], reverse=True)


def recency_score(latest_age_hours: float | None, config: dict, max_recency: int) -> float:
    if latest_age_hours is None:
        return max_recency * 0.25
    fresh_hours = float(config.get("general", {}).get("fresh_hours", 24))
    heating_hours = float(config.get("general", {}).get("heating_days", 7)) * 24
    if latest_age_hours <= fresh_hours:
        return max_recency
    if latest_age_hours >= heating_hours:
        return max_recency * 0.1
    remaining = (heating_hours - latest_age_hours) / max(1.0, heating_hours - fresh_hours)
    return max_recency * max(0.1, remaining)


def independent_score(items: list[dict], platforms: set[str], max_independent: int) -> float:
    domains = {source_domain(item) for item in items if source_domain(item)}
    if len(domains) >= 2:
        return min(max_independent, (len(domains) - 1) * (max_independent / 2))
    return min(max_independent, max(0, len(platforms) - 1) * (max_independent / 2))


def source_reputation_score(items: list[dict], source_types: set[str], max_reputation: int) -> float:
    if source_types & {"first_party", "official", "employee", "community"}:
        return max_reputation
    if any(is_reputable_domain(source_domain(item)) for item in items):
        return max_reputation
    return max_reputation * 0.4 if source_types else 0


def source_domain(item: dict) -> str:
    author = str(item.get("author") or "").lower().removeprefix("www.")
    if "." in author and " " not in author:
        return author
    parsed = urlparse(item.get("url") or "")
    return parsed.netloc.lower().removeprefix("www.")


def is_reputable_domain(domain: str) -> bool:
    return any(domain == trusted or domain.endswith("." + trusted) for trusted in REPUTABLE_DOMAINS)
