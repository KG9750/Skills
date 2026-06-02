#!/usr/bin/env python3
"""Validate a Novel to Webcomic asset manifest.

Usage:
  validate_manifest.py <project_dir>
  validate_manifest.py <path/to/asset-manifest.json>
"""

import argparse
import json
import sys
from pathlib import Path


ALLOWED_FORMATS = {
    "vertical-webtoon",
    "storyboard-panels",
    "finished-comic-pages",
    "html-overlay-dialogue",
}


def load_manifest(target: Path):
    if target.is_dir():
        manifest_path = target / "public" / "asset-manifest.json"
        public_root = target / "public"
    else:
        manifest_path = target
        public_root = target.parent

    if not manifest_path.exists():
        return None, None, [f"manifest not found: {manifest_path}"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, None, [f"invalid JSON: {exc}"]

    return data, public_root, []


def image_path(public_root: Path, image: str) -> Path:
    if image.startswith("/"):
        return public_root / image.lstrip("/")
    return public_root / image


def validate(data, public_root: Path, strict_prompts: bool):
    errors = []
    warnings = []

    fmt = data.get("format")
    if fmt not in ALLOWED_FORMATS:
        errors.append(f"format must be one of {sorted(ALLOWED_FORMATS)}, got {fmt!r}")

    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        errors.append("chapters must be a non-empty list")
        return errors, warnings

    for chapter_index, chapter in enumerate(chapters, start=1):
        prefix = f"chapter {chapter_index}"
        if not chapter.get("id"):
            errors.append(f"{prefix}: missing id")
        if not chapter.get("title"):
            errors.append(f"{prefix}: missing title")

        panels = chapter.get("panels")
        if not isinstance(panels, list) or not panels:
            errors.append(f"{prefix}: panels must be a non-empty list")
            continue

        seen_ids = set()
        for panel_index, panel in enumerate(panels, start=1):
            panel_prefix = f"{prefix} panel {panel_index}"
            panel_id = panel.get("id")
            if not panel_id:
                errors.append(f"{panel_prefix}: missing id")
            elif panel_id in seen_ids:
                errors.append(f"{panel_prefix}: duplicate id {panel_id!r}")
            else:
                seen_ids.add(panel_id)

            image = panel.get("image")
            if not image:
                errors.append(f"{panel_prefix}: missing image")
            else:
                resolved = image_path(public_root, image)
                if not resolved.exists():
                    errors.append(f"{panel_prefix}: image not found: {image}")

            if not panel.get("alt"):
                errors.append(f"{panel_prefix}: missing alt")

            dialogue = panel.get("dialogue", [])
            if dialogue is not None and not isinstance(dialogue, list):
                errors.append(f"{panel_prefix}: dialogue must be a list when present")

            prompt = panel.get("prompt", "")
            if prompt:
                prompt_lower = prompt.lower()
                missing_prompt_terms = [
                    term
                    for term in ("no text", "no watermark")
                    if term not in prompt_lower
                ]
                if missing_prompt_terms:
                    message = (
                        f"{panel_prefix}: prompt missing recommended constraint(s): "
                        + ", ".join(missing_prompt_terms)
                    )
                    if strict_prompts:
                        errors.append(message)
                    else:
                        warnings.append(message)

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Project directory or asset-manifest.json path")
    parser.add_argument(
        "--strict-prompts",
        action="store_true",
        help="Fail when prompt constraints such as no text/no watermark are missing.",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    data, public_root, load_errors = load_manifest(target)
    if load_errors:
        for error in load_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    errors, warnings = validate(data, public_root, args.strict_prompts)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        return 1

    panel_count = sum(len(chapter.get("panels", [])) for chapter in data["chapters"])
    print(f"Manifest valid: format={data.get('format')} chapters={len(data['chapters'])} panels={panel_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
