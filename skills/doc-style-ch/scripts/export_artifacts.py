#!/usr/bin/env python3
"""Export doc-style-CH HTML to PDF and fixed-canvas PNG with Chromium."""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path


MACOS_BROWSER_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
)
BROWSER_COMMANDS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
)


def parse_viewport(value: str) -> tuple[int, int]:
    normalized = value.lower().replace("×", "x")
    parts = normalized.split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("viewport must use WIDTHxHEIGHT")
    try:
        width, height = (int(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("viewport must use integer dimensions") from exc
    if not (720 <= width <= 8192 and 720 <= height <= 8192):
        raise argparse.ArgumentTypeError("viewport dimensions must be between 720 and 8192")
    return width, height


def html_profile(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for profile in ("document", "image"):
        if f'data-output-profile="{profile}"' in text:
            return profile
    raise ValueError("HTML does not declare a supported data-output-profile")


def find_browser(explicit: Path | None = None) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
        raise FileNotFoundError(f"browser is not executable: {explicit}")
    candidates: list[Path] = []
    env_browser = os.environ.get("DOC_STYLE_CH_BROWSER")
    if env_browser:
        candidates.append(Path(env_browser).expanduser())
    candidates.extend(Path(path) for path in MACOS_BROWSER_PATHS)
    for command in BROWSER_COMMANDS:
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise FileNotFoundError(
        "Chrome/Chromium/Edge was not found; pass --browser /absolute/path/to/browser"
    )


def common_browser_args(browser: Path, profile: Path) -> list[str]:
    return [
        str(browser),
        "--headless=new",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--hide-scrollbars",
        "--metrics-recording-only",
        "--mute-audio",
        "--allow-file-access-from-files",
        "--host-resolver-rules=MAP * 0.0.0.0, EXCLUDE localhost",
        f"--user-data-dir={profile}",
    ]


def build_pdf_command(
    browser: Path,
    profile: Path,
    html_url: str,
    output: Path,
) -> list[str]:
    return common_browser_args(browser, profile) + [
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={output}",
        html_url,
    ]


def build_png_command(
    browser: Path,
    profile: Path,
    html_url: str,
    output: Path,
    viewport: tuple[int, int],
) -> list[str]:
    width, height = viewport
    return common_browser_args(browser, profile) + [
        "--force-device-scale-factor=1",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=1000",
        f"--window-size={width},{height}",
        f"--screenshot={output}",
        html_url,
    ]


def verify_pdf(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 100 or not data.startswith(b"%PDF-"):
        raise RuntimeError(f"invalid PDF output: {path}")


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError(f"invalid PNG output: {path}")
    return struct.unpack(">II", data[16:24])


def verify_png(path: Path, expected: tuple[int, int]) -> None:
    actual = png_dimensions(path)
    if actual != expected:
        raise RuntimeError(
            f"PNG dimensions are {actual[0]}x{actual[1]}, expected {expected[0]}x{expected[1]}"
        )


def run_browser(command: list[str], timeout: int) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        suffix = f": {details}" if details else ""
        raise RuntimeError(f"browser export failed with exit {completed.returncode}{suffix}")


def export_one(
    browser: Path,
    html_url: str,
    output: Path,
    kind: str,
    viewport: tuple[int, int],
    timeout: int,
) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="doc-style-ch-browser-") as profile_name:
        profile = Path(profile_name)
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=f".{output.stem}.",
            suffix=output.suffix,
            delete=False,
        ) as handle:
            temporary_output = Path(handle.name)
        temporary_output.unlink()
        try:
            if kind == "pdf":
                command = build_pdf_command(browser, profile, html_url, temporary_output)
            else:
                command = build_png_command(
                    browser,
                    profile,
                    html_url,
                    temporary_output,
                    viewport,
                )
            run_browser(command, timeout)
            if kind == "pdf":
                verify_pdf(temporary_output)
            else:
                verify_png(temporary_output, viewport)
            temporary_output.replace(output)
        finally:
            temporary_output.unlink(missing_ok=True)
    print(f"Exported {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="rendered local HTML input")
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument("--pdf", type=Path, help="PDF output path")
    output_group.add_argument("--png", type=Path, help="PNG output path")
    parser.add_argument(
        "--viewport",
        type=parse_viewport,
        default=(1600, 2000),
        help="PNG canvas as WIDTHxHEIGHT; default: 1600x2000",
    )
    parser.add_argument("--browser", type=Path, help="explicit Chromium-family browser")
    parser.add_argument("--timeout", type=int, default=60, help="seconds per export")
    args = parser.parse_args()

    if args.timeout < 1:
        parser.error("--timeout must be positive")
    html_path = args.html.resolve()
    if not html_path.is_file():
        parser.error(f"HTML input does not exist: {html_path}")
    try:
        profile = html_profile(html_path)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    expected_profile = "document" if args.pdf is not None else "image"
    if profile != expected_profile:
        output_label = "PDF" if args.pdf is not None else "PNG"
        parser.error(
            f"{output_label} export requires the {expected_profile} profile; "
            f"input uses {profile}"
        )
    browser = find_browser(args.browser)
    html_url = html_path.as_uri()
    if args.pdf is not None:
        export_one(browser, html_url, args.pdf, "pdf", args.viewport, args.timeout)
    if args.png is not None:
        export_one(browser, html_url, args.png, "png", args.viewport, args.timeout)


if __name__ == "__main__":
    main()
