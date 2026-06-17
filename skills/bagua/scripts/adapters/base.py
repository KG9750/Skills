from dataclasses import dataclass, field


@dataclass
class AdapterResult:
    items: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_sources: list[dict] = field(default_factory=list)


def warning(platform: str, message: str) -> str:
    return f"{platform}: {message}"
