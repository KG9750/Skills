#!/usr/bin/env python3
"""Validate structural invariants for the certo skill."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "claude/certo.md",
    "examples/acceptance-cases.md",
]

REQUIRED_TERMS = {
    "SKILL.md": [
        "Do not invent problems",
        "未验证风险",
        "If the user does not specify a mode",
        "do not start the review yet",
        "复审",
        "拷问",
        "深刺",
        "If the user only asks for a generic review",
    ],
    "agents/openai.yaml": [
        "does not specify 快刺, 深刺, 拷问, or 复审",
        "do not start the review yet",
        "深刺",
        "拷问",
        "复审",
        "未验证风险",
        "Score at the end",
        "generic review",
    ],
    "claude/certo.md": [
        "source of truth",
        "Do not invent problems",
        "does not specify `快刺`, `深刺`, `拷问`, or `复审`",
        "do not start the review yet",
        "未验证风险",
        "Score at the end",
        "generic review",
    ],
    "examples/acceptance-cases.md": [
        "## Mode Selection Required",
        "## Article `快刺`",
        "## Product `拷问`",
        "## Code `复审`",
        "## Architecture `深刺`",
        "## No Major Issues",
        "## Generic Review Boundary",
        "## English Language Following",
        "Checkpoints:",
    ],
}

BANNED_DESCRIPTION_PATTERNS = [
    r"\bcritique,\s*review\b",
    r"审查,\s*批判性审阅",
    r"critical challenge",
]

BANNED_BODY_PATTERNS = [
    r"Default to `?快刺`?",
]


def read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    for relpath in REQUIRED_FILES:
        if not (ROOT / relpath).is_file():
            fail(f"missing required file: {relpath}")

    skill = read("SKILL.md")
    match = re.search(r"^description:\s*(.+)$", skill, re.MULTILINE)
    if not match:
        fail("SKILL.md is missing frontmatter description")

    description = match.group(1)
    for pattern in BANNED_DESCRIPTION_PATTERNS:
        if re.search(pattern, description):
            fail(f"description contains broad trigger pattern: {pattern}")

    if "explicitly asks" not in description:
        fail("description must require explicit certo/adversarial intent")

    for pattern in BANNED_BODY_PATTERNS:
        if re.search(pattern, skill):
            fail(f"SKILL.md contains banned body pattern: {pattern}")

    for relpath, terms in REQUIRED_TERMS.items():
        text = read(relpath)
        for term in terms:
            if term not in text:
                fail(f"{relpath} missing required term: {term}")

    cases = read("examples/acceptance-cases.md")
    checkpoint_count = cases.count("Checkpoints:")
    heading_count = len(re.findall(r"^## ", cases, flags=re.MULTILINE))
    if checkpoint_count < heading_count:
        fail(
            "each acceptance case heading should have a Checkpoints section "
            f"(headings={heading_count}, checkpoints={checkpoint_count})"
        )

    print("certo skill structural validation ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
