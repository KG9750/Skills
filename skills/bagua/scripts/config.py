from __future__ import annotations

import copy
import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    try:
        import tomli as tomllib
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        tomllib = None


DEFAULT_CONFIG = {
    "general": {
        "output_dir": "~/.bagua/runs",
        "strict": False,
        "main_limit": 10,
        "early_limit": 10,
        "fresh_hours": 24,
        "heating_days": 7,
        "require_gossip_signal": True,
    },
    "watchlist": {
        "companies": ["OpenAI", "Anthropic", "xAI", "Google DeepMind", "Meta AI", "Mistral", "Perplexity", "Hugging Face", "Cursor"],
        "products": ["ChatGPT", "Claude", "Grok", "Gemini", "Llama", "Sora", "Cursor", "Devin"],
        "projects": ["vLLM", "LangChain", "LlamaIndex", "ComfyUI"],
        "public_figures": [],
    },
    "blacklist": {
        "accounts": [],
        "channels": [],
        "subreddits": [],
        "domains": [],
        "keywords": [],
    },
    "x": {"enabled": True, "bearer_token": "", "public_web_best_effort": True},
    "brave": {"enabled": True, "api_key": "", "count": 10, "country": "US", "search_lang": "en"},
    "reddit": {"enabled": True, "client_id": "", "client_secret": "", "user_agent": "bagua/0.1", "subreddits": []},
    "telegram": {"enabled": True, "bot_token": "", "seed_channels": [], "public_channel_pages": True, "suggest_sources": True},
    "llm": {"enabled": False, "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4.1-mini"},
    "storage": {"sqlite_path": "~/.bagua/bagua.sqlite3"},
    "collection": {"request_timeout": 8, "retry_count": 1, "max_pages": 2, "per_query_limit": 8, "results_per_query": 10},
}


def deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | None) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if not path:
        default_path = Path("~/.bagua/config.toml").expanduser()
        path = str(default_path) if default_path.exists() else None

    if path:
        if tomllib is None:
            raise RuntimeError("Install dependencies first: python3 -m pip install -r requirements.txt")
        with Path(path).expanduser().open("rb") as handle:
            config = deep_merge(config, tomllib.load(handle))

    env_overrides = {
        ("x", "bearer_token"): "X_BEARER_TOKEN",
        ("brave", "api_key"): "BRAVE_API_KEY",
        ("telegram", "bot_token"): "TELEGRAM_BOT_TOKEN",
        ("llm", "api_key"): "OPENAI_API_KEY",
    }
    for (section, key), env_name in env_overrides.items():
        value = os.environ.get(env_name)
        if value:
            config.setdefault(section, {})[key] = value

    collection_env = {
        "request_timeout": "BAGUA_REQUEST_TIMEOUT",
        "retry_count": "BAGUA_RETRY_COUNT",
        "per_query_limit": "BAGUA_PER_QUERY_LIMIT",
        "results_per_query": "BAGUA_RESULTS_PER_QUERY",
    }
    for key, env_name in collection_env.items():
        value = os.environ.get(env_name)
        if value:
            config.setdefault("collection", {})[key] = int(value)

    return config
