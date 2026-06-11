#!/usr/bin/env python3
"""Normalize a slide comp image to a uniform 4K canvas with light sharpening."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError as exc:  # pragma: no cover - dependency diagnostic
    print(
        "FAIL: Pillow is required. Install it with `conda run -n py_313 python -m pip install pillow` "
        "or `python -m pip install pillow`.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


def parse_bg(value: str) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) not in {6, 8}:
        raise argparse.ArgumentTypeError("background must be #RRGGBB or #RRGGBBAA")
    parts = [int(value[i : i + 2], 16) for i in range(0, len(value), 2)]
    if len(parts) == 3:
        parts.append(255)
    return tuple(parts)  # type: ignore[return-value]


def resize_to_canvas(
    image: Image.Image,
    *,
    width: int,
    height: int,
    fit: str,
    background: tuple[int, int, int, int],
) -> Image.Image:
    image = image.convert("RGBA")
    input_ratio = image.width / image.height
    target_ratio = width / height
    if fit == "stretch" or abs(input_ratio - target_ratio) / target_ratio <= 0.01:
        return image.resize((width, height), Image.Resampling.LANCZOS)

    if fit == "cover":
        scaled = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        return scaled.convert("RGBA")

    contained = ImageOps.contain(image, (width, height), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height), background)
    x = (width - contained.width) // 2
    y = (height - contained.height) // 2
    canvas.alpha_composite(contained, (x, y))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw ImageGen/source slide image.")
    parser.add_argument("--output", required=True, help="Normalized 4K comp image path.")
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--fit", choices=["contain", "cover", "stretch"], default="contain")
    parser.add_argument("--background", type=parse_bg, default=parse_bg("#FFFFFFFF"))
    parser.add_argument("--sharpen-radius", type=float, default=1.15)
    parser.add_argument("--sharpen-percent", type=int, default=125)
    parser.add_argument("--sharpen-threshold", type=int, default=3)
    parser.add_argument("--manifest", help="Optional JSON report path.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        print(f"FAIL: input image does not exist: {input_path}", file=sys.stderr)
        return 1

    with Image.open(input_path) as source:
        source.load()
        raw_size = {"width": source.width, "height": source.height}
        normalized = resize_to_canvas(
            source,
            width=args.width,
            height=args.height,
            fit=args.fit,
            background=args.background,
        )

    if args.sharpen_percent > 0:
        normalized = normalized.filter(
            ImageFilter.UnsharpMask(
                radius=args.sharpen_radius,
                percent=args.sharpen_percent,
                threshold=args.sharpen_threshold,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(output_path, format="PNG", compress_level=0)
    report = {
        "status": "completed",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_dimensions_px": raw_size,
        "output_dimensions_px": {"width": normalized.width, "height": normalized.height},
        "target_dimensions_px": {"width": args.width, "height": args.height},
        "fit": args.fit,
        "upscale_factor": round(max(args.width / raw_size["width"], args.height / raw_size["height"]), 4),
        "upscale_method": "lanczos",
        "sharpen_after_resize": args.sharpen_percent > 0,
        "sharpen": {
            "radius": args.sharpen_radius,
            "percent": args.sharpen_percent,
            "threshold": args.sharpen_threshold,
        },
        "output_file_size_bytes": output_path.stat().st_size,
        "limitations": (
            "Upscaling and sharpening improve uniformity and edge crispness, but they cannot recover "
            "unreadable text or missing icon detail from a weak source image."
        ),
    }
    if args.manifest:
        manifest_path = Path(args.manifest).expanduser().resolve()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
