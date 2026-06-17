from __future__ import annotations

from datetime import datetime, timezone
from base64 import b64encode

from adapters.base import AdapterResult, warning
from models import BaguaItem
from query_builder import generated_queries, infer_category, merge_entities


REDDIT_BASE = "https://www.reddit.com"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"


def collect(config: dict, client=None) -> AdapterResult:
    reddit_config = config.get("reddit", {})
    if not reddit_config.get("enabled", True):
        return AdapterResult()

    subreddits = reddit_config.get("subreddits") or ["singularity", "MachineLearning", "LocalLLaMA", "OpenAI", "artificial"]
    token = None
    if reddit_config.get("client_id") and reddit_config.get("client_secret"):
        try:
            token = oauth_token(config, client)
        except Exception as error:  # noqa: BLE001
            token = None
            oauth_warning = warning("reddit", f"OAuth token failed, falling back to public JSON: {error}")
        else:
            oauth_warning = ""
    else:
        oauth_warning = ""
    items = []
    warnings = []
    if oauth_warning:
        warnings.append(oauth_warning)
    for query in generated_queries(config):
        for subreddit in subreddits:
            try:
                items.extend(search_subreddit(config, client, subreddit, query["reddit"], query["entity"], token))
            except Exception as error:  # noqa: BLE001
                if not token and public_json_blocked(error):
                    warnings.append(warning("reddit", f"public JSON blocked; configure OAuth or rerun later: {error}"))
                    return AdapterResult(items=items, warnings=warnings)
                warnings.append(warning("reddit", f"search failed for r/{subreddit} {query['entity']}: {error}"))
    return AdapterResult(items=items, warnings=warnings)


def public_json_blocked(error: Exception) -> bool:
    message = str(error).lower()
    return "403" in message or "blocked" in message or "forbidden" in message


def oauth_token(config: dict, client) -> str:
    reddit_config = config.get("reddit", {})
    credentials = f"{reddit_config['client_id']}:{reddit_config['client_secret']}".encode("utf-8")
    data = client.post_json(
        f"{REDDIT_BASE}/api/v1/access_token",
        headers={
            "Authorization": "Basic " + b64encode(credentials).decode("ascii"),
            "User-Agent": reddit_config.get("user_agent", "bagua/0.1"),
        },
        data={"grant_type": "client_credentials"},
    )
    return data["access_token"]


def search_subreddit(config: dict, client, subreddit: str, query: str, entity: str, token: str | None = None) -> list[dict]:
    reddit_config = config.get("reddit", {})
    collection = config.get("collection", {})
    base = REDDIT_OAUTH_BASE if token else REDDIT_BASE
    path = f"/r/{subreddit}/search" if token else f"/r/{subreddit}/search.json"
    headers = {"User-Agent": reddit_config.get("user_agent", "bagua/0.1")}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {
            "q": query,
            "restrict_sr": "1",
            "sort": "hot",
            "t": "week",
            "limit": min(100, int(collection.get("results_per_query", 10))),
    }
    items = []
    for _ in range(max(1, int(collection.get("max_pages", 2)))):
        data = client.get_json(f"{base}{path}", headers=headers, params=params)
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            text = "\n".join(part for part in (post.get("title"), post.get("selftext")) if part)
            post_id = post.get("name") or post.get("id", "")
            created = datetime.fromtimestamp(float(post.get("created_utc", 0)), timezone.utc).replace(microsecond=0)
            items.append(BaguaItem(
                platform="reddit",
                post_id=post_id,
                url=f"https://www.reddit.com{post.get('permalink', '')}",
                author=f"u/{post.get('author', 'unknown')}",
                source_type="community",
                evidence_type="discussion_with_links" if "http" in text else "discussion",
                created_at=created.isoformat().replace("+00:00", "Z"),
                text=text,
                entities=merge_entities(entity, text, config),
                category=infer_category(text),
                engagement={
                    "score": int(post.get("score", 0)),
                    "comments": int(post.get("num_comments", 0)),
                },
                raw={"subreddit": subreddit, "query": query},
            ).to_dict())
        after = data.get("data", {}).get("after")
        if not after:
            break
        params["after"] = after
    return items
