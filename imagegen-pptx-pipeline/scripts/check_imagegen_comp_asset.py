#!/usr/bin/env python3
"""Validate ImageGen single-slide comp prompts and generated image assets."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path


QUALITY_TIERS = {
    "4k": {"width": 3840, "height": 2160, "min_bytes": 5 * 1024 * 1024},
    "2k": {"width": 2560, "height": 1440, "min_bytes": 2 * 1024 * 1024},
    "1080p": {"width": 1920, "height": 1080, "min_bytes": 1 * 1024 * 1024},
}
TIER_ORDER = ["4k", "2k", "1080p"]


def image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        header = path.read_bytes()[:32]
    except OSError:
        return None, None
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        return struct.unpack(">II", header[16:24])
    return None, None


def acceptable_tiers(target_tier: str, allow_fallback: bool) -> list[str]:
    if not allow_fallback:
        return [target_tier]
    return TIER_ORDER[TIER_ORDER.index(target_tier) :]


def validate_prompt(prompt_path: Path, target_tier: str, require_fallback_policy: bool, failures: list[str]) -> None:
    if not prompt_path.exists():
        failures.append(f"prompt file does not exist: {prompt_path}")
        return
    text = prompt_path.read_text(encoding="utf-8").lower()
    compact = re.sub(r"\s+", " ", text)

    tier = QUALITY_TIERS[target_tier]
    required_patterns = {
        f"{tier['width']} width": str(tier["width"]),
        f"{tier['height']} height": str(tier["height"]),
        f"{target_tier} requirement": rf"\b{re.escape(target_tier)}\b|{tier['width']}\s*[x×]\s*{tier['height']}|ultra-sharp|highest detail|maximum detail|最高",
        "tier file-size minimum": rf"{tier['min_bytes']}|{tier['min_bytes'] // (1024 * 1024)}\s*mib|{tier['min_bytes'] // (1024 * 1024)}\s*mb",
        "same dimensions": r"same (pixel )?dimensions|identical (pixel )?dimensions|same pixel size|同(一|样).*(尺寸|分辨率)",
        "no blur": r"no blur|not blurry|sharp|crisp|清晰|锐利|不.*模糊",
    }
    for label, pattern in required_patterns.items():
        if not re.search(pattern, compact):
            failures.append(f"prompt missing required ImageGen comp constraint: {label}")
    if require_fallback_policy:
        fallback_patterns = {
            "2K fallback": r"\b2k\b|2560\s*[x×]\s*1440",
            "1080p fallback": r"1080p|1920\s*[x×]\s*1080",
            "fallback stop rule": r"fallback|降级|tier|阶梯|as high as possible|尽可能高清|do not retry forever|不要.*一直.*重试",
        }
        for label, pattern in fallback_patterns.items():
            if not re.search(pattern, compact):
                failures.append(f"prompt missing required ImageGen fallback policy: {label}")


def validate_image(image_path: Path, target_tier: str, allow_fallback: bool, failures: list[str]) -> None:
    if not image_path.exists():
        failures.append(f"image file does not exist: {image_path}")
        return
    width, height = image_size(image_path)
    if width is None or height is None:
        failures.append(f"image dimensions could not be read: {image_path}")
        return
    matching_tier = None
    for tier_name in acceptable_tiers(target_tier, allow_fallback):
        tier = QUALITY_TIERS[tier_name]
        if width >= tier["width"] and height >= tier["height"] and image_path.stat().st_size >= tier["min_bytes"]:
            matching_tier = tier_name
            break
    floor = QUALITY_TIERS[acceptable_tiers(target_tier, allow_fallback)[-1]]
    if matching_tier is None:
        failures.append(
            f"image must satisfy {target_tier}"
            f"{' or fallback tiers 2k/1080p' if allow_fallback and target_tier == '4k' else ''}; "
            f"floor is {floor['width']}x{floor['height']} and {floor['min_bytes']} bytes; "
            f"got {width}x{height} and {image_path.stat().st_size} bytes: {image_path}"
        )
    elif matching_tier != target_tier:
        print(f"PASS_WITH_FALLBACK tier={matching_tier} requested={target_tier}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Path to the ImageGen prompt file.")
    parser.add_argument("--image", help="Optional generated comp image to validate after ImageGen returns.")
    parser.add_argument("--tier", choices=TIER_ORDER, default="4k")
    parser.add_argument("--allow-fallback", action="store_true")
    parser.add_argument("--require-fallback-policy", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    validate_prompt(Path(args.prompt).expanduser().resolve(), args.tier, args.require_fallback_policy, failures)
    if args.image:
        validate_image(Path(args.image).expanduser().resolve(), args.tier, args.allow_fallback, failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
