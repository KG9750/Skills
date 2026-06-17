from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import re

from time_utils import utc_now_iso


@dataclass
class RunWarning:
    platform: str
    message: str

    def text(self) -> str:
        return f"{self.platform}: {self.message}"


@dataclass
class BaguaItem:
    platform: str
    post_id: str
    url: str
    author: str
    source_type: str
    evidence_type: str
    created_at: str
    text: str
    entities: list[str] = field(default_factory=list)
    category: str = "community-backlash"
    engagement: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaguaItem":
        return cls(
            platform=str(data.get("platform", "unknown")),
            post_id=str(data.get("post_id") or data.get("id") or ""),
            url=str(data.get("url") or ""),
            author=str(data.get("author") or "unknown"),
            source_type=str(data.get("source_type") or "unknown"),
            evidence_type=str(data.get("evidence_type") or "unknown"),
            created_at=str(data.get("created_at") or utc_now_iso()),
            text=str(data.get("text") or ""),
            entities=[str(entity) for entity in data.get("entities", [])],
            category=str(data.get("category") or "community-backlash"),
            engagement=parse_engagement(data.get("engagement", {})),
            raw=data.get("raw", {}) if isinstance(data.get("raw", {}), dict) else {},
        )


def item_dict(data: dict[str, Any] | BaguaItem) -> dict[str, Any]:
    if isinstance(data, BaguaItem):
        return data.to_dict()
    return BaguaItem.from_dict(data).to_dict()


def parse_engagement(engagement: dict[str, Any]) -> dict[str, int]:
    parsed = {}
    for key, value in engagement.items():
        number = parse_count(value)
        if number is not None:
            parsed[str(key)] = number
    return parsed


def parse_count(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().replace(",", "")
    match = re.fullmatch(r"([\d.]+)([KMBkmb]?)", text)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[match.group(2).upper()]
    return int(number * multiplier)
