from __future__ import annotations

from adapters import brave_search
from adapters.base import AdapterResult, warning
from models import BaguaItem
from query_builder import generated_queries, merge_entities


X_RECENT_SEARCH_ENDPOINT = "https://api.x.com/2/tweets/search/recent"


def collect(config: dict, client=None) -> AdapterResult:
    x_config = config.get("x", {})
    if not x_config.get("enabled", True):
        return AdapterResult()

    if not x_config.get("bearer_token"):
        if x_config.get("public_web_best_effort", True) and client:
            return brave_search.collect_x_supplement(config, client)
        return AdapterResult(warnings=[warning("x", "skipped: x.bearer_token is not configured")])

    items = []
    warnings = []
    for query in generated_queries(config):
        try:
            items.extend(search_recent(config, client, query["x"], query["entity"]))
        except Exception as error:  # noqa: BLE001
            warnings.append(warning("x", f"recent search failed for {query['entity']}: {error}"))
    return AdapterResult(items=items, warnings=warnings)


def search_recent(config: dict, client, query: str, entity: str) -> list[dict]:
    x_config = config.get("x", {})
    collection = config.get("collection", {})
    max_pages = max(1, int(collection.get("max_pages", 2)))
    params = {
            "query": query,
            "max_results": max(10, min(100, int(collection.get("results_per_query", 10)))),
            "tweet.fields": "created_at,public_metrics,author_id,conversation_id,referenced_tweets",
            "expansions": "author_id",
            "user.fields": "username,name,verified,description",
    }
    items = []
    for _ in range(max_pages):
        data = client.get_json(
            X_RECENT_SEARCH_ENDPOINT,
            headers={"Authorization": f"Bearer {x_config['bearer_token']}"},
            params=params,
        )
        users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
        for tweet in data.get("data", []):
            user = users.get(tweet.get("author_id"), {})
            username = user.get("username") or tweet.get("author_id") or "unknown"
            metrics = tweet.get("public_metrics", {})
            text = tweet.get("text", "")
            items.append(BaguaItem(
                platform="x",
                post_id=tweet.get("id", ""),
                url=f"https://x.com/{username}/status/{tweet.get('id', '')}",
                author=f"@{username}",
                source_type="first_party" if user.get("verified") else "community",
                evidence_type="public_post",
                created_at=tweet.get("created_at", ""),
                text=text,
                entities=merge_entities(entity, text, config),
                engagement={
                    "likes": int(metrics.get("like_count", 0)),
                    "reposts": int(metrics.get("retweet_count", 0)) + int(metrics.get("quote_count", 0)),
                    "comments": int(metrics.get("reply_count", 0)),
                },
                raw={"query": query},
            ).to_dict())
        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
        params["next_token"] = next_token
    return items
