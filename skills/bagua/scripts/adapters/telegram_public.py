from __future__ import annotations

import re
import json
from datetime import datetime, timezone

from adapters.base import AdapterResult, warning
from models import BaguaItem, utc_now_iso
from query_builder import infer_category, infer_entities


TELEGRAM_API = "https://api.telegram.org"


def collect(config: dict, client=None) -> AdapterResult:
    telegram_config = config.get("telegram", {})
    if not telegram_config.get("enabled", True):
        return AdapterResult()

    items = []
    warnings = []
    seed_channels = telegram_config.get("seed_channels") or []
    if seed_channels and telegram_config.get("public_channel_pages", True):
        for channel in seed_channels:
            try:
                items.extend(collect_public_channel(config, client, channel))
            except Exception as error:  # noqa: BLE001
                warnings.append(warning("telegram", f"public channel failed for {channel}: {error}"))

    if telegram_config.get("bot_token"):
        try:
            items.extend(collect_bot_updates(config, client))
        except Exception as error:  # noqa: BLE001
            warnings.append(warning("telegram", f"bot updates failed: {error}"))

    if not seed_channels and not telegram_config.get("bot_token"):
        warnings.append(warning("telegram", "skipped: no bot_token or seed_channels configured"))
    return AdapterResult(items=items, warnings=warnings)


def collect_public_channel(config: dict, client, channel: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as error:  # pragma: no cover - environment dependent
        raise RuntimeError("Install dependencies first: python3 -m pip install -r requirements.txt") from error

    channel_name = channel.strip().removeprefix("@").split("/")[-1]
    html = client.get_text(f"https://t.me/s/{channel_name}")
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for message in soup.select(".tgme_widget_message"):
        post_ref = message.get("data-post") or ""
        text_node = message.select_one(".tgme_widget_message_text")
        if not text_node:
            continue
        text = text_node.get_text(" ", strip=True)
        if not text:
            continue
        post_id = post_ref.replace("/", ":") or f"{channel_name}:{len(items)}"
        url = f"https://t.me/s/{post_ref}" if post_ref else f"https://t.me/s/{channel_name}"
        time_node = message.select_one("time")
        created_at = time_node.get("datetime") if time_node and time_node.get("datetime") else utc_now_iso()
        views = parse_count((message.select_one(".tgme_widget_message_views") or {}).get_text("", strip=True) if message.select_one(".tgme_widget_message_views") else "")
        items.append(BaguaItem(
            platform="telegram",
            post_id=post_id,
            url=url,
            author=channel_name,
            source_type="aggregator",
            evidence_type="public_channel_post",
            created_at=created_at,
            text=text,
            entities=infer_entities(text, config),
            category=infer_category(text),
            engagement={"views": views},
            raw={"channel": channel_name},
        ).to_dict())
    return items


def collect_bot_updates(config: dict, client) -> list[dict]:
    token = config.get("telegram", {}).get("bot_token")
    data = client.get_json(f"{TELEGRAM_API}/bot{token}/getUpdates", params={"allowed_updates": json.dumps(["message", "channel_post"])})
    items = []
    for update in data.get("result", []):
        message = update.get("channel_post") or update.get("message") or {}
        text = message.get("text") or message.get("caption") or ""
        if not text:
            continue
        chat = message.get("chat", {})
        date = datetime.fromtimestamp(int(message["date"]), timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if message.get("date") else utc_now_iso()
        chat_name = chat.get("username") or chat.get("title") or str(chat.get("id", "unknown"))
        message_id = str(message.get("message_id", ""))
        url = f"https://t.me/{chat.get('username')}/{message_id}" if chat.get("username") else ""
        items.append(BaguaItem(
            platform="telegram",
            post_id=f"{chat_name}:{message_id}",
            url=url,
            author=chat_name,
            source_type="authorized_bot",
            evidence_type="bot_visible_message",
            created_at=date,
            text=text,
            entities=infer_entities(text, config),
            category=infer_category(text),
            engagement={},
            raw={"update_id": update.get("update_id")},
        ).to_dict())
    return items


def parse_count(value: str) -> int:
    match = re.match(r"([\d.]+)([KMB]?)", value.strip(), re.I)
    if not match:
        return 0
    number = float(match.group(1))
    suffix = match.group(2).upper()
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[suffix]
    return int(number * multiplier)
