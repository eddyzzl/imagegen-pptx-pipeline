#!/usr/bin/env python3
"""Crop slide icons into padded transparent PNG assets for PPTX reconstruction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError as exc:  # pragma: no cover - dependency diagnostic
    print(
        "FAIL: Pillow is required. Install it with `conda run -n py_313 python -m pip install pillow` "
        "or `python -m pip install pillow`.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


def resolve_path(workspace: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()


def int_box(raw: dict, expansion: int, max_width: int, max_height: int) -> tuple[int, int, int, int]:
    left = int(raw.get("left", 0)) - expansion
    top = int(raw.get("top", 0)) - expansion
    width = int(raw.get("width", 0)) + expansion * 2
    height = int(raw.get("height", 0)) + expansion * 2
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid bbox: {raw}")
    x1 = max(left, 0)
    y1 = max(top, 0)
    x2 = min(left + width, max_width)
    y2 = min(top + height, max_height)
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"bbox is outside source image: {raw}")
    return x1, y1, x2, y2


def remove_light_background(image: Image.Image, threshold: int) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if r >= threshold and g >= threshold and b >= threshold:
                pixels[x, y] = (r, g, b, 0)
    return rgba


def touches_edge(alpha_bbox: tuple[int, int, int, int] | None, width: int, height: int) -> bool:
    if alpha_bbox is None:
        return True
    left, top, right, bottom = alpha_bbox
    return left <= 0 or top <= 0 or right >= width or bottom >= height


def process_icon(workspace: Path, entry: dict, defaults: dict) -> dict:
    source_path = resolve_path(workspace, entry["source_image_path"])
    output_path = resolve_path(workspace, entry["output_path"])
    padding = int(entry.get("padding_px", defaults["padding_px"]))
    expansion = int(entry.get("crop_expansion_px", defaults["crop_expansion_px"]))
    threshold = int(entry.get("white_threshold", defaults["white_threshold"]))
    min_output_px = int(entry.get("minimum_output_icon_px", defaults["minimum_output_icon_px"]))

    if not source_path.exists():
        raise FileNotFoundError(f"source image does not exist: {source_path}")
    with Image.open(source_path) as source:
        source.load()
        crop_box = int_box(entry.get("bbox_px", {}), expansion, source.width, source.height)
        crop = source.convert("RGBA").crop(crop_box)

    keyed = remove_light_background(crop, threshold)
    alpha = keyed.getchannel("A")
    alpha_bbox = alpha.getbbox()
    if alpha_bbox is None:
        raise ValueError(f"icon {entry.get('id', '')} has no non-background pixels after transparency key")
    possible_clip = touches_edge(alpha_bbox, keyed.width, keyed.height)
    trimmed = keyed.crop(alpha_bbox)

    scale = 1.0
    largest = max(trimmed.width, trimmed.height)
    if largest < min_output_px:
        scale = min_output_px / largest
        trimmed = trimmed.resize(
            (max(1, round(trimmed.width * scale)), max(1, round(trimmed.height * scale))),
            Image.Resampling.LANCZOS,
        ).filter(ImageFilter.UnsharpMask(radius=0.8, percent=120, threshold=2))

    canvas = Image.new("RGBA", (trimmed.width + padding * 2, trimmed.height + padding * 2), (255, 255, 255, 0))
    canvas.alpha_composite(trimmed, (padding, padding))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", compress_level=6)
    final_alpha_bbox = canvas.getchannel("A").getbbox()
    edge_clear = final_alpha_bbox is not None and not touches_edge(final_alpha_bbox, canvas.width, canvas.height)
    return {
        "id": entry.get("id", output_path.stem),
        "status": "completed",
        "source_image_path": str(source_path),
        "output_path": str(output_path),
        "source_crop_px": {
            "left": crop_box[0],
            "top": crop_box[1],
            "width": crop_box[2] - crop_box[0],
            "height": crop_box[3] - crop_box[1],
        },
        "content_bbox_before_padding_px": {
            "left": alpha_bbox[0],
            "top": alpha_bbox[1],
            "width": alpha_bbox[2] - alpha_bbox[0],
            "height": alpha_bbox[3] - alpha_bbox[1],
        },
        "output_dimensions_px": {"width": canvas.width, "height": canvas.height},
        "transparent_padding_px": padding,
        "minimum_output_icon_px": min_output_px,
        "upscale_factor": round(scale, 4),
        "transparent_background": True,
        "edge_clear": edge_clear,
        "possible_crop_clipping": possible_clip,
        "file_size_bytes": output_path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Icon crop manifest JSON.")
    parser.add_argument("--workspace", default=".", help="Base directory for relative paths.")
    parser.add_argument("--report", help="Optional processed icon report JSON.")
    parser.add_argument("--strict", action="store_true", help="Fail if colored pixels touch the expanded crop edge.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    defaults = {
        "padding_px": int(payload.get("default_padding_px", 16)),
        "crop_expansion_px": int(payload.get("default_crop_expansion_px", 12)),
        "white_threshold": int(payload.get("white_threshold", 246)),
        "minimum_output_icon_px": int(payload.get("minimum_output_icon_px", 256)),
    }
    results = []
    failures = []
    for idx, entry in enumerate(payload.get("icons", []), 1):
        try:
            result = process_icon(workspace, entry, defaults)
            results.append(result)
            if args.strict and (not result["edge_clear"] or result["possible_crop_clipping"]):
                failures.append(
                    f"icon {result['id']} may be clipped; enlarge bbox_px or crop_expansion_px and rerun"
                )
        except Exception as exc:  # pragma: no cover - CLI diagnostic
            failures.append(f"icon entry {idx} failed: {exc}")

    report = {
        "status": "failed" if failures else "completed",
        "manifest_path": str(manifest_path),
        "workspace": str(workspace),
        "processed_count": len(results),
        "results": results,
        "failures": failures,
    }
    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
