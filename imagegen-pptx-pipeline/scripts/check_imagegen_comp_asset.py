#!/usr/bin/env python3
"""Validate ImageGen single-slide comp prompts and generated image assets."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path


DEFAULT_WIDTH = 3840
DEFAULT_HEIGHT = 2160
DEFAULT_MIN_BYTES = 5 * 1024 * 1024


def image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        header = path.read_bytes()[:32]
    except OSError:
        return None, None
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        return struct.unpack(">II", header[16:24])
    return None, None


def validate_prompt(prompt_path: Path, failures: list[str]) -> None:
    if not prompt_path.exists():
        failures.append(f"prompt file does not exist: {prompt_path}")
        return
    text = prompt_path.read_text(encoding="utf-8").lower()
    compact = re.sub(r"\s+", " ", text)

    required_patterns = {
        "3840 width": r"3840",
        "2160 height": r"2160",
        "4K requirement": r"\b4k\b|true 4k|ultra-sharp|highest detail|maximum detail|最高",
        "5 MiB minimum": r"5\s*mib|5\s*mb|5242880|5\s*\*\s*1024\s*\*\s*1024",
        "same dimensions": r"same (pixel )?dimensions|identical (pixel )?dimensions|same pixel size|同(一|样).*(尺寸|分辨率)",
        "no blur": r"no blur|not blurry|sharp|crisp|清晰|锐利|不.*模糊",
    }
    for label, pattern in required_patterns.items():
        if not re.search(pattern, compact):
            failures.append(f"prompt missing required ImageGen comp constraint: {label}")


def validate_image(image_path: Path, expected_width: int, expected_height: int, min_bytes: int, failures: list[str]) -> None:
    if not image_path.exists():
        failures.append(f"image file does not exist: {image_path}")
        return
    width, height = image_size(image_path)
    if width is None or height is None:
        failures.append(f"image dimensions could not be read: {image_path}")
    elif width < expected_width or height < expected_height:
        failures.append(
            f"image must be at least {expected_width}x{expected_height}; got {width}x{height}: {image_path}"
        )
    size = image_path.stat().st_size
    if size < min_bytes:
        failures.append(f"image must be at least {min_bytes} bytes; got {size}: {image_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Path to the ImageGen prompt file.")
    parser.add_argument("--image", help="Optional generated comp image to validate after ImageGen returns.")
    parser.add_argument("--expected-width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--expected-height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--min-bytes", type=int, default=DEFAULT_MIN_BYTES)
    args = parser.parse_args()

    failures: list[str] = []
    validate_prompt(Path(args.prompt).expanduser().resolve(), failures)
    if args.image:
        validate_image(
            Path(args.image).expanduser().resolve(),
            args.expected_width,
            args.expected_height,
            args.min_bytes,
            failures,
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
