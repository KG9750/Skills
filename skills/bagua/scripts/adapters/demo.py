import json
from pathlib import Path

from adapters.base import AdapterResult


def collect(config: dict, skill_root: Path) -> AdapterResult:
    sample_path = skill_root / "assets" / "sample_items.jsonl"
    items = []
    with sample_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return AdapterResult(items=items)
