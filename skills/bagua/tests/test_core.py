from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from argparse import Namespace

from adapters import brave_search, reddit_search, telegram_public, x_search  # noqa: E402
from collect import run as collect_run, live_preflight_warnings  # noqa: E402
from config import DEFAULT_CONFIG, deep_merge, load_config  # noqa: E402
from event_cluster import cluster_events  # noqa: E402
from llm_enhance import enhance_events  # noqa: E402
from models import BaguaItem  # noqa: E402
from normalize_items import normalize_items  # noqa: E402
from query_builder import generated_queries  # noqa: E402
from render_report import render_report  # noqa: E402
from score_heat import score_events  # noqa: E402
from smoke_check import live_platforms, platform_status, readiness_report  # noqa: E402
from storage import connect_storage, persist_run  # noqa: E402


class FakeClient:
    def __init__(self, json_data=None, text_data=""):
        self.json_data = json_data or {}
        self.text_data = text_data
        self.requests = []

    def get_json(self, url, **kwargs):
        self.requests.append((url, kwargs))
        if callable(self.json_data):
            return self.json_data(url, **kwargs)
        return self.json_data

    def get_text(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.text_data

    def post_json(self, url, **kwargs):
        self.requests.append((url, kwargs))
        if callable(self.json_data):
            return self.json_data(url, **kwargs)
        return self.json_data


def iso_hours_ago(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_load_config_without_file_works_without_toml_dependency():
    config = load_config(None)
    assert config["general"]["main_limit"] == 10
    assert "OpenAI" in config["watchlist"]["companies"]


def test_deep_merge_keeps_defaults():
    merged = deep_merge(DEFAULT_CONFIG, {"general": {"strict": True}})
    assert merged["general"]["strict"] is True
    assert merged["general"]["main_limit"] == 10


def test_generated_queries_use_watchlist_and_limits():
    config = deep_merge(DEFAULT_CONFIG, {"collection": {"per_query_limit": 1}, "watchlist": {"companies": ["DemoAI"]}})
    queries = generated_queries(config)
    assert len(queries) == 1
    assert "DemoAI" in queries[0]["x"]


def test_normalize_cluster_score_pipeline():
    items = normalize_items([
        {
            "platform": "x",
            "post_id": "1",
            "url": "https://x.com/demo/status/1",
            "author": "@demo",
            "source_type": "first_party",
            "evidence_type": "public_post",
            "created_at": "2026-06-16T00:00:00Z",
            "text": "DemoAI benchmark dispute and fake benchmark accusation",
            "entities": ["DemoAI"],
            "engagement": {"likes": 100},
        },
        {
            "platform": "x",
            "post_id": "1",
            "url": "https://x.com/demo/status/1",
            "author": "@demo",
            "text": "duplicate",
        },
    ], DEFAULT_CONFIG)
    assert len(items) == 1
    events = score_events(cluster_events(items), DEFAULT_CONFIG)
    assert events[0]["scores"]["heat"] > 0
    assert events[0]["scores"]["credibility"] >= 60


def test_time_window_filters_old_items_and_marks_fresh():
    config = deep_merge(DEFAULT_CONFIG, {"general": {"fresh_hours": 24, "heating_days": 7}})
    items = normalize_items([
        {
            "platform": "x",
            "post_id": "fresh",
            "url": "https://x.com/demo/status/fresh",
            "author": "@demo",
            "source_type": "first_party",
            "evidence_type": "public_post",
            "created_at": iso_hours_ago(2),
            "text": "DemoAI benchmark dispute fresh",
            "entities": ["DemoAI"],
        },
        {
            "platform": "x",
            "post_id": "old",
            "url": "https://x.com/demo/status/old",
            "author": "@demo",
            "created_at": iso_hours_ago(24 * 9),
            "text": "DemoAI benchmark dispute stale",
            "entities": ["DemoAI"],
        },
    ], config)
    assert [item["post_id"] for item in items] == ["fresh"]
    assert items[0]["fresh"] is True
    assert items[0]["time_confidence"] == "known"


def test_gossip_gate_filters_plain_ai_updates():
    config = deep_merge(DEFAULT_CONFIG, {"watchlist": {"companies": ["Hugging Face"]}})
    items = normalize_items([
        {
            "platform": "telegram",
            "post_id": "huggingface:2300",
            "url": "https://t.me/s/huggingface/2300",
            "author": "huggingface",
            "source_type": "aggregator",
            "evidence_type": "public_channel_post",
            "created_at": iso_hours_ago(1),
            "text": "Hugging Face RT Introducing Tiny Aya, a multilingual small language model for local devices.",
            "entities": ["Hugging Face"],
        }
    ], config)
    assert items == []


def test_gossip_gate_filters_uncategorized_keyword_noise():
    config = deep_merge(DEFAULT_CONFIG, {"watchlist": {"companies": ["OpenAI"]}})
    items = normalize_items([
        {
            "platform": "x",
            "post_id": "noise",
            "url": "https://x.com/example/status/1",
            "author": "x.com",
            "source_type": "search_result",
            "evidence_type": "search_snippet",
            "created_at": iso_hours_ago(1),
            "text": "OpenAI published a report on how bad actors used AI-generated scripts for romance scams and fraud.",
            "entities": ["OpenAI"],
        }
    ], config)
    assert items == []


def test_gossip_gate_keeps_controversy_signals():
    config = deep_merge(DEFAULT_CONFIG, {"watchlist": {"companies": ["DemoAI"]}})
    items = normalize_items([
        {
            "platform": "x",
            "post_id": "dispute",
            "url": "https://x.com/demo/status/1",
            "author": "@demo",
            "source_type": "first_party",
            "evidence_type": "public_post",
            "created_at": iso_hours_ago(1),
            "text": "DemoAI founder accused BenchArena of a fake benchmark after an eval harness dispute.",
            "entities": ["DemoAI"],
        }
    ], config)
    assert len(items) == 1
    assert items[0]["gossip_signal"] is True


def test_recency_score_drops_for_still_heating_items():
    config = deep_merge(DEFAULT_CONFIG, {"general": {"fresh_hours": 24, "heating_days": 7}})
    fresh_event = score_events(cluster_events(normalize_items([{
        "platform": "x",
        "post_id": "fresh",
        "url": "https://x.com/demo/status/fresh",
        "author": "@demo",
        "source_type": "first_party",
        "evidence_type": "public_post",
        "created_at": iso_hours_ago(1),
        "text": "DemoAI benchmark dispute",
        "entities": ["DemoAI"],
    }], config)), config)[0]
    heating_event = score_events(cluster_events(normalize_items([{
        "platform": "x",
        "post_id": "heating",
        "url": "https://x.com/demo/status/heating",
        "author": "@demo",
        "source_type": "first_party",
        "evidence_type": "public_post",
        "created_at": iso_hours_ago(24 * 4),
        "text": "DemoAI benchmark dispute",
        "entities": ["DemoAI"],
    }], config)), config)[0]
    assert fresh_event["scores"]["components"]["recency"] > heating_event["scores"]["components"]["recency"]
    assert fresh_event["fresh_count"] == 1
    assert heating_event["fresh_count"] == 0


def test_report_uses_chinese_summary_for_events():
    config = deep_merge(DEFAULT_CONFIG, {"watchlist": {"companies": ["Anthropic"]}})
    items = normalize_items([
        {
            "platform": "web",
            "post_id": "story",
            "url": "https://gizmodo.com/anthropic-lawsuit",
            "author": "gizmodo.com",
            "source_type": "search_result",
            "evidence_type": "search_snippet",
            "created_at": iso_hours_ago(1),
            "text": "Anthropic accused of misleading users in a new lawsuit over usage limits.",
            "entities": ["Anthropic"],
        }
    ], config)
    events = score_events(cluster_events(items), config)
    report = render_report(events, [], [], config)
    assert "法律争议" in report
    assert "legal-dispute" not in report.split("- What happened:", 1)[1].split("\n", 1)[0]
    assert "来源提到起诉、诉讼或法律指控" in report
    assert "Anthropic出现" not in report


def test_reputable_search_sources_can_upgrade_to_rumor():
    config = deep_merge(DEFAULT_CONFIG, {"watchlist": {"companies": ["Anthropic"]}})
    created_at = iso_hours_ago(1)
    items = normalize_items([
        {
            "platform": "web",
            "post_id": "gizmodo",
            "url": "https://gizmodo.com/anthropic-lawsuit",
            "author": "gizmodo.com",
            "source_type": "search_result",
            "evidence_type": "search_snippet",
            "created_at": created_at,
            "text": "Anthropic accused of misleading users in a new lawsuit over usage limits.",
            "entities": ["Anthropic"],
        },
        {
            "platform": "web",
            "post_id": "seekingalpha",
            "url": "https://seekingalpha.com/news/anthropic-lawsuit",
            "author": "seekingalpha.com",
            "source_type": "search_result",
            "evidence_type": "search_snippet",
            "created_at": created_at,
            "text": "Anthropic faces lawsuit alleging misrepresented usage limits and potential fraud.",
            "entities": ["Anthropic"],
        },
    ], config)
    event = score_events(cluster_events(items), config)[0]
    assert event["scores"]["label"] == "rumor"
    assert event["scores"]["credibility"] >= 35
    assert event["scores"]["components"]["independent_sources"] > 0


def test_brave_search_maps_results_to_items():
    config = deep_merge(DEFAULT_CONFIG, {"brave": {"api_key": "test"}, "watchlist": {"companies": ["DemoAI"]}, "collection": {"per_query_limit": 1}})
    client = FakeClient(json_data={
        "web": {
            "results": [
                {
                    "url": "https://x.com/demo/status/1",
                    "title": "DemoAI founder dispute",
                    "description": "benchmark controversy",
                }
            ]
        }
    })
    result = brave_search.collect(config, client)
    assert result.items[0]["platform"] == "x"
    assert result.items[0]["entities"] == ["DemoAI"]


def test_brave_search_skips_results_without_actual_entity_match():
    config = deep_merge(DEFAULT_CONFIG, {"brave": {"api_key": "test"}, "watchlist": {"companies": ["Google DeepMind"]}, "collection": {"per_query_limit": 1}})
    client = FakeClient(json_data={
        "web": {
            "results": [
                {
                    "url": "https://x.com/demo/status/1",
                    "title": "Delve accused of faking compliance reports",
                    "description": "A YC startup raised money and faces backlash.",
                }
            ]
        }
    })
    result = brave_search.collect(config, client)
    assert result.items == []


def test_infer_category_avoids_broad_raise_and_deepfake_noise():
    from query_builder import infer_category  # noqa: E402

    assert infer_category("Anthropic dispute raises questions about AI readiness") == "uncategorized"
    assert infer_category("Deepfake detection benchmark is #1 on Hugging Face") == "uncategorized"
    assert infer_category("Fraud Detection Benchmark dataset on Hugging Face") == "uncategorized"
    assert infer_category("Anthropic faces lawsuit over usage limits") == "legal-dispute"


def test_x_recent_search_maps_tweets_to_items():
    config = deep_merge(DEFAULT_CONFIG, {
        "x": {"bearer_token": "token"},
        "watchlist": {"companies": ["DemoAI"]},
        "collection": {"per_query_limit": 1},
    })
    client = FakeClient(json_data={
        "data": [
            {
                "id": "123",
                "text": "DemoAI benchmark dispute is heating up",
                "author_id": "u1",
                "created_at": "2026-06-16T00:00:00Z",
                "public_metrics": {"like_count": 10, "retweet_count": 2, "quote_count": 1, "reply_count": 3},
            }
        ],
        "includes": {"users": [{"id": "u1", "username": "demo", "verified": True}]},
    })
    result = x_search.collect(config, client)
    assert result.items[0]["url"] == "https://x.com/demo/status/123"
    assert result.items[0]["engagement"]["reposts"] == 3
    assert result.items[0]["source_type"] == "first_party"
    assert client.requests[0][1]["params"]["max_results"] == DEFAULT_CONFIG["collection"]["results_per_query"]


def test_x_recent_search_extracts_cross_entities_and_paginates():
    responses = [
        {
            "data": [{"id": "1", "text": "DemoAI and Claude benchmark fight", "author_id": "u1", "created_at": iso_hours_ago(1), "public_metrics": {}}],
            "includes": {"users": [{"id": "u1", "username": "demo"}]},
            "meta": {"next_token": "next"},
        },
        {
            "data": [{"id": "2", "text": "DemoAI follow up", "author_id": "u1", "created_at": iso_hours_ago(1), "public_metrics": {}}],
            "includes": {"users": [{"id": "u1", "username": "demo"}]},
        },
    ]

    def router(url, **kwargs):
        return responses.pop(0)

    config = deep_merge(DEFAULT_CONFIG, {
        "x": {"bearer_token": "token"},
        "watchlist": {"companies": ["DemoAI"], "products": ["Claude"]},
        "collection": {"per_query_limit": 1, "max_pages": 2, "results_per_query": 10},
    })
    result = x_search.collect(config, FakeClient(json_data=router))
    assert len(result.items) == 2
    assert set(result.items[0]["entities"]) == {"DemoAI", "Claude"}


def test_x_without_token_uses_brave_supplement():
    config = deep_merge(DEFAULT_CONFIG, {
        "brave": {"api_key": "brave"},
        "watchlist": {"companies": ["DemoAI"]},
        "collection": {"per_query_limit": 1},
    })
    client = FakeClient(json_data={"web": {"results": [{"url": "https://x.com/demo/status/1", "title": "DemoAI dispute", "description": "AI drama"}]}})
    result = x_search.collect(config, client)
    assert result.items[0]["platform"] == "x"


def test_reddit_public_search_maps_listing_to_items():
    config = deep_merge(DEFAULT_CONFIG, {
        "watchlist": {"companies": ["DemoAI"]},
        "collection": {"per_query_limit": 1},
        "reddit": {"subreddits": ["OpenAI"]},
    })
    client = FakeClient(json_data={
        "data": {
            "children": [
                {"data": {
                    "name": "t3_demo",
                    "id": "demo",
                    "title": "DemoAI launch rollback",
                    "selftext": "Users are discussing the product fail",
                    "permalink": "/r/OpenAI/comments/demo",
                    "author": "tester",
                    "created_utc": 1781568000,
                    "score": 42,
                    "num_comments": 7,
                }}
            ]
        }
    })
    result = reddit_search.collect(config, client)
    assert result.items[0]["platform"] == "reddit"
    assert result.items[0]["engagement"]["comments"] == 7
    assert "/r/OpenAI/comments/demo" in result.items[0]["url"]
    assert client.requests[0][1]["params"]["limit"] == DEFAULT_CONFIG["collection"]["results_per_query"]


def test_reddit_search_extracts_cross_entities_and_paginates():
    responses = [
        {"data": {"after": "after-1", "children": [{"data": {
            "name": "t3_1",
            "title": "DemoAI and Claude launch rollback",
            "selftext": "",
            "permalink": "/r/OpenAI/comments/1",
            "author": "tester",
            "created_utc": datetime.now(timezone.utc).timestamp(),
            "score": 1,
            "num_comments": 1,
        }}]}},
        {"data": {"after": None, "children": [{"data": {
            "name": "t3_2",
            "title": "DemoAI follow up",
            "selftext": "",
            "permalink": "/r/OpenAI/comments/2",
            "author": "tester",
            "created_utc": datetime.now(timezone.utc).timestamp(),
            "score": 1,
            "num_comments": 1,
        }}]}},
    ]

    def router(url, **kwargs):
        return responses.pop(0)

    config = deep_merge(DEFAULT_CONFIG, {
        "watchlist": {"companies": ["DemoAI"], "products": ["Claude"]},
        "collection": {"per_query_limit": 1, "max_pages": 2, "results_per_query": 10},
        "reddit": {"subreddits": ["OpenAI"]},
    })
    result = reddit_search.collect(config, FakeClient(json_data=router))
    assert len(result.items) == 2
    assert set(result.items[0]["entities"]) == {"DemoAI", "Claude"}


def test_reddit_oauth_path_requests_token_then_oauth_search():
    def json_router(url, **kwargs):
        if url.endswith("/api/v1/access_token"):
            return {"access_token": "oauth-token"}
        assert url.startswith("https://oauth.reddit.com/")
        assert kwargs["headers"]["Authorization"] == "Bearer oauth-token"
        return {"data": {"children": []}}

    config = deep_merge(DEFAULT_CONFIG, {
        "watchlist": {"companies": ["DemoAI"]},
        "collection": {"per_query_limit": 1},
        "reddit": {"client_id": "id", "client_secret": "secret", "subreddits": ["OpenAI"]},
    })
    result = reddit_search.collect(config, FakeClient(json_data=json_router))
    assert result.warnings == []


def test_reddit_public_403_fast_fails_remaining_queries():
    class RedditBlocked(Exception):
        def __str__(self):
            return "Client error '403 Blocked'"

    config = deep_merge(DEFAULT_CONFIG, {
        "watchlist": {"companies": ["DemoAI"]},
        "collection": {"per_query_limit": 1},
        "reddit": {"subreddits": ["OpenAI", "MachineLearning"]},
    })
    client = FakeClient(json_data=lambda url, **kwargs: (_ for _ in ()).throw(RedditBlocked()))
    result = reddit_search.collect(config, client)
    assert len(client.requests) == 1
    assert any("public JSON blocked" in entry for entry in result.warnings)


def test_telegram_bot_updates_parser():
    config = deep_merge(DEFAULT_CONFIG, {"telegram": {"bot_token": "token"}, "watchlist": {"companies": ["DemoAI"]}})
    client = FakeClient(json_data={
        "result": [
            {
                "update_id": 1,
                "channel_post": {
                    "message_id": 55,
                    "date": 1781568000,
                    "text": "DemoAI founder drama update",
                    "chat": {"username": "ai_channel"},
                },
            }
        ]
    })
    items = telegram_public.collect_bot_updates(config, client)
    assert items[0]["url"] == "https://t.me/ai_channel/55"
    assert items[0]["entities"] == ["DemoAI"]
    assert isinstance(client.requests[0][1]["params"]["allowed_updates"], str)


def test_telegram_bot_missing_date_uses_current_time():
    config = deep_merge(DEFAULT_CONFIG, {"telegram": {"bot_token": "token"}, "watchlist": {"companies": ["DemoAI"]}})
    client = FakeClient(json_data={"result": [{"channel_post": {"message_id": 1, "text": "DemoAI update", "chat": {"username": "ai_channel"}}}]})
    items = telegram_public.collect_bot_updates(config, client)
    assert not items[0]["created_at"].startswith("1970-")


def test_telegram_public_channel_parser():
    html = """
    <div class="tgme_widget_message" data-post="demo/123">
      <div class="tgme_widget_message_text">DemoAI benchmark dispute keeps spreading</div>
      <time datetime="2026-06-16T01:02:03+00:00"></time>
      <span class="tgme_widget_message_views">1.2K</span>
    </div>
    """
    config = deep_merge(DEFAULT_CONFIG, {"watchlist": {"companies": ["DemoAI"]}})
    items = telegram_public.collect_public_channel(config, FakeClient(text_data=html), "demo")
    assert items[0]["post_id"] == "demo:123"
    assert items[0]["engagement"]["views"] == 1200
    assert items[0]["entities"] == ["DemoAI"]


def test_sqlite_persist_run(tmp_path):
    config = deep_merge(DEFAULT_CONFIG, {"storage": {"sqlite_path": str(tmp_path / "bagua.sqlite3")}})
    item = normalize_items([
        {
            "platform": "reddit",
            "post_id": "t3_demo",
            "url": "https://reddit.com/r/demo/comments/1",
            "author": "u/demo",
            "source_type": "community",
            "evidence_type": "discussion",
            "created_at": "2026-06-16T00:00:00Z",
            "text": "DemoAI launch rollback discussion",
            "entities": ["DemoAI"],
        }
    ], config)
    events = score_events(cluster_events(item), config)
    with connect_storage(config) as connection:
        persist_run(connection, "run-1", item, events, [])
        persist_run(connection, "run-2", item, events, [])
        seen_count = connection.execute("SELECT seen_count FROM items WHERE canonical_id = ?", (item[0]["canonical_id"],)).fetchone()[0]
    assert seen_count == 2


def test_event_id_distinguishes_same_entity_category_different_text():
    config = DEFAULT_CONFIG
    items = normalize_items([
        {
            "platform": "x",
            "post_id": "1",
            "url": "https://x.com/demo/status/1",
            "author": "@demo",
            "created_at": iso_hours_ago(1),
            "text": "DemoAI benchmark dispute about eval harness",
            "entities": ["DemoAI"],
            "category": "benchmark-dispute",
        },
        {
            "platform": "x",
            "post_id": "2",
            "url": "https://x.com/demo/status/2",
            "author": "@demo",
            "created_at": iso_hours_ago(1),
            "text": "DemoAI benchmark dispute about plagiarism claims",
            "entities": ["DemoAI"],
            "category": "benchmark-dispute",
        },
    ], config)
    events = cluster_events(items)
    assert len(events) == 2
    assert len({event["event_id"] for event in events}) == 2


def test_collect_real_warning_run_updates_sqlite_when_not_dry_run(tmp_path):
    config_path = tmp_path / "config.toml"
    output_dir = tmp_path / "runs"
    sqlite_path = tmp_path / "bagua.sqlite3"
    config_path.write_text(
        f"""
[general]
output_dir = "{output_dir}"

[storage]
sqlite_path = "{sqlite_path}"
""",
        encoding="utf-8",
    )
    run_dir = collect_run(Namespace(config=str(config_path), demo=False, platform="x", dry_run=False))
    assert (run_dir / "items.jsonl").exists()
    assert (output_dir / "latest.md").exists()
    assert sqlite_path.exists()


def test_live_preflight_warns_when_selected_platforms_are_not_ready():
    config = deep_merge(DEFAULT_CONFIG, {
        "brave": {"api_key": ""},
        "x": {"bearer_token": ""},
        "telegram": {"seed_channels": [], "bot_token": ""},
    })
    warnings = live_preflight_warnings(config, ["x", "telegram", "brave"])
    assert any("preflight" in entry for entry in warnings)
    assert any("x not ready" in entry for entry in warnings)


def test_collect_run_ids_do_not_collide_within_same_second(tmp_path):
    config_path = tmp_path / "config.toml"
    output_dir = tmp_path / "runs"
    config_path.write_text(f"[general]\noutput_dir = \"{output_dir}\"\n", encoding="utf-8")
    first = collect_run(Namespace(config=str(config_path), demo=True, platform=None, dry_run=True))
    second = collect_run(Namespace(config=str(config_path), demo=True, platform=None, dry_run=True))
    assert first != second
    assert first.exists()
    assert second.exists()


def test_blacklist_filters_accounts_keywords_channels_subreddits_domains():
    config = deep_merge(DEFAULT_CONFIG, {
        "blacklist": {
            "accounts": ["@blocked"],
            "keywords": ["ignoreme"],
            "channels": ["badchannel"],
            "subreddits": ["OpenAI"],
            "domains": ["blocked.example"],
        }
    })
    rows = [
        {"platform": "x", "post_id": "a", "author": "@blocked", "text": "DemoAI", "url": "https://x.com/a", "entities": ["DemoAI"]},
        {"platform": "x", "post_id": "b", "author": "@ok", "text": "ignoreme DemoAI", "url": "https://x.com/b", "entities": ["DemoAI"]},
        {"platform": "telegram", "post_id": "c", "author": "badchannel", "text": "DemoAI", "url": "https://t.me/s/badchannel/1", "entities": ["DemoAI"], "raw": {"channel": "badchannel"}},
        {"platform": "reddit", "post_id": "d", "author": "u/ok", "text": "DemoAI", "url": "https://reddit.com/r/OpenAI/comments/1", "entities": ["DemoAI"], "raw": {"subreddit": "OpenAI"}},
        {"platform": "web", "post_id": "e", "author": "ok", "text": "DemoAI", "url": "https://blocked.example/story", "entities": ["DemoAI"]},
        {"platform": "x", "post_id": "f", "author": "@ok", "text": "DemoAI benchmark dispute", "url": "https://x.com/f", "entities": ["DemoAI"]},
    ]
    assert [item["post_id"] for item in normalize_items(rows, config)] == ["f"]


def test_engagement_parses_numeric_strings_and_suffixes_but_not_bool():
    item = BaguaItem.from_dict({
        "platform": "x",
        "post_id": "1",
        "url": "https://x.com/demo/status/1",
        "author": "@demo",
        "source_type": "community",
        "evidence_type": "public_post",
        "created_at": iso_hours_ago(1),
        "text": "DemoAI",
        "engagement": {"likes": "4,200", "views": "1.2K", "bad": True},
    }).to_dict()
    assert item["engagement"] == {"likes": 4200, "views": 1200}


def test_sample_items_jsonl_is_valid():
    sample_path = ROOT / "assets" / "sample_items.jsonl"
    rows = [json.loads(line) for line in sample_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) >= 3


def test_smoke_platform_status_reports_ready_inputs():
    config = deep_merge(DEFAULT_CONFIG, {
        "brave": {"api_key": "brave"},
        "telegram": {"seed_channels": ["demo_channel"]},
    })
    status = platform_status(config)
    assert status["brave"]["ready"] is True
    assert status["telegram"]["ready"] is True
    assert status["x"]["ready"] is True
    assert "brave" in live_platforms(status)


def test_reddit_public_without_oauth_is_not_live_ready():
    status = platform_status(DEFAULT_CONFIG)
    assert status["reddit"]["enabled"] is True
    assert status["reddit"]["ready"] is False
    assert live_platforms(status) == []


def test_smoke_readiness_without_config_is_machine_readable():
    report = readiness_report(None)
    assert "dependencies" in report
    assert "platforms" in report
    assert "ready_platforms" in report


def test_llm_malformed_response_warning_is_redacted(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "not json sk-test-secret"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    events, warnings = enhance_events([{
        "event_id": "event-1",
        "category": "benchmark-dispute",
        "entities": ["DemoAI"],
        "scores": {"label": "rumor"},
        "items": [{"platform": "x", "author": "@demo", "text": "DemoAI", "url": "https://x.com/1", "evidence_type": "public_post"}],
    }], {"llm": {"enabled": True, "api_key": "sk-live-secret", "base_url": "https://example.test/v1", "model": "demo"}})
    assert events[0].get("llm") is None
    assert warnings
    assert "sk-live-secret" not in warnings[0]
    assert "sk-test-secret" not in warnings[0]
