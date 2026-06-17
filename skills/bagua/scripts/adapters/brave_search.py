from __future__ import annotations

from hashlib import sha1

from adapters.base import AdapterResult, warning
from models import BaguaItem, utc_now_iso
from query_builder import generated_queries, infer_category, infer_entities


BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def collect(config: dict, client) -> AdapterResult:
    brave_config = config.get("brave", {})
    if not brave_config.get("enabled", True):
        return AdapterResult()
    if not brave_config.get("api_key"):
        return AdapterResult(warnings=[warning("brave", "skipped: brave.api_key is not configured")])

    items = []
    warnings = []
    for query in generated_queries(config):
        try:
            items.extend(search_query(config, client, query["general"], query.get("entity")))
        except Exception as error:  # noqa: BLE001 - warning keeps tolerant mode useful.
            warnings.append(warning("brave", f"query failed for {query['entity']}: {error}"))
    return AdapterResult(items=items, warnings=warnings)


def collect_x_supplement(config: dict, client) -> AdapterResult:
    brave_config = config.get("brave", {})
    if not brave_config.get("enabled", True) or not brave_config.get("api_key"):
        return AdapterResult(warnings=[warning("x", "Brave X supplement skipped: brave.api_key is not configured")])

    items = []
    warnings = []
    for query in generated_queries(config):
        try:
            items.extend(search_query(config, client, query["brave_x"], query.get("entity"), force_platform="x"))
        except Exception as error:  # noqa: BLE001
            warnings.append(warning("x", f"Brave X supplement failed for {query['entity']}: {error}"))
    return AdapterResult(items=items, warnings=warnings)


def search_query(config: dict, client, query: str, entity: str | None = None, force_platform: str | None = None) -> list[dict]:
    brave_config = config.get("brave", {})
    data = client.get_json(
        BRAVE_ENDPOINT,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": brave_config["api_key"],
        },
        params={
            "q": query,
            "count": int(brave_config.get("count", 10)),
            "country": brave_config.get("country", "US"),
            "search_lang": brave_config.get("search_lang", "en"),
        },
    )
    rows = data.get("web", {}).get("results", [])
    items = []
    for row in rows:
        url = row.get("url") or ""
        title = row.get("title") or ""
        description = row.get("description") or ""
        text = " ".join(part for part in (title, description) if part)
        platform = force_platform or platform_from_url(url)
        entities = infer_entities(text, config)
        if entity and entity.lower() in text.lower() and entity not in entities:
            entities.insert(0, entity)
        if not entities:
            continue
        items.append(BaguaItem(
            platform=platform,
            post_id=sha1(url.encode("utf-8")).hexdigest()[:16],
            url=url,
            author=domain_from_url(url),
            source_type="search_result",
            evidence_type="search_snippet",
            created_at=row.get("page_age") or utc_now_iso(),
            text=text,
            entities=entities,
            category=infer_category(text),
            engagement={},
            raw={"source": "brave", "query": query},
        ).to_dict())
    return items


def platform_from_url(url: str) -> str:
    lowered = url.lower()
    if "x.com/" in lowered or "twitter.com/" in lowered:
        return "x"
    if "reddit.com/" in lowered:
        return "reddit"
    if "t.me/" in lowered:
        return "telegram"
    return "web"


def domain_from_url(url: str) -> str:
    return url.split("/")[2] if "://" in url else "unknown"
