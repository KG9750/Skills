from __future__ import annotations


SECRET_KEYS = ("api_key", "token", "secret", "bearer", "password")


def redact_value(value: str) -> str:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


def redact_mapping(data: dict) -> dict:
    redacted = {}
    for key, value in data.items():
        if isinstance(value, dict):
            redacted[key] = redact_mapping(value)
        elif any(secret in key.lower() for secret in SECRET_KEYS):
            redacted[key] = redact_value(str(value))
        else:
            redacted[key] = value
    return redacted


def redact_text(text: str) -> str:
    redacted = str(text)
    markers = ("sk-", "Bearer ", "Basic ")
    for marker in markers:
        start = redacted.find(marker)
        while start != -1:
            end = start
            while end < len(redacted) and not redacted[end].isspace() and redacted[end] not in "'\"),]}":
                end += 1
            redacted = redacted[:start] + marker + "***" + redacted[end:]
            start = redacted.find(marker, start + len(marker) + 3)
    return redacted
