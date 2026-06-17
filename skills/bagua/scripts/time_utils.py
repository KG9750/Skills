from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), timezone.utc).replace(microsecond=0)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return datetime.fromtimestamp(float(text), timezone.utc).replace(microsecond=0)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0)
    except ValueError:
        return None


def age_hours(created_at: str, now: datetime | None = None) -> float | None:
    parsed = parse_datetime(created_at)
    if not parsed:
        return None
    current = now or utc_now()
    return max(0.0, (current - parsed).total_seconds() / 3600)


def date_bucket(created_at: str) -> str:
    parsed = parse_datetime(created_at)
    if not parsed:
        return "unknown-date"
    return parsed.strftime("%Y-%m-%d")
