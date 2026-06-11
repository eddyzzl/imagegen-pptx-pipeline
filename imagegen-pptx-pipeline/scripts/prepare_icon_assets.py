#!/usr/bin/env python3
"""Crop slide icons into padded transparent PNG assets for PPTX reconstruction."""

from __future__ import annotations

import argparse
from collections import deque
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
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


def remove_edge_background(image: Image.Image, threshold: int) -> Image.Image:
    """Remove only edge-connected background, preserving intentional white icon strokes."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    corners = [rgb.getpixel(point) for point in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))]
    bg = tuple(sum(color[i] for color in corners) // 4 for i in range(3))
    padded = Image.new("RGB", (width + 6, height + 6), bg)
    padded.paste(rgb, (3, 3))
    ImageDraw.floodfill(padded, (0, 0), (255, 0, 255), thresh=threshold)
    flood = padded.load()
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if flood[x + 3, y + 3] == (255, 0, 255):
                pixels[x, y] = (r, g, b, 0)
    return rgba


def keep_components_intersecting_core(image: Image.Image, core_box: tuple[int, int, int, int]) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    alpha_mask = [[pixels[x, y][3] > 40 for x in range(width)] for y in range(height)]
    seen = [[False] * width for _ in range(height)]
    keep = [[False] * width for _ in range(height)]
    cx1, cy1, cx2, cy2 = core_box
    for sy in range(height):
        for sx in range(width):
            if not alpha_mask[sy][sx] or seen[sy][sx]:
                continue
            queue = deque([(sx, sy)])
            seen[sy][sx] = True
            component: list[tuple[int, int]] = []
            intersects_core = False
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                if cx1 <= x <= cx2 and cy1 <= y <= cy2:
                    intersects_core = True
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and alpha_mask[ny][nx]
                            and not seen[ny][nx]
                        ):
                            seen[ny][nx] = True
                            queue.append((nx, ny))
            if intersects_core and len(component) >= 12:
                for x, y in component:
                    keep[y][x] = True
    for y in range(height):
        for x in range(width):
            if not keep[y][x]:
                r, g, b, _ = pixels[x, y]
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
        raw_box = entry.get("bbox_px", {})
        crop_box = int_box(raw_box, expansion, source.width, source.height)
        crop = source.convert("RGBA").crop(crop_box)

    core_box = (
        max(int(raw_box.get("left", 0)) - crop_box[0], 0),
        max(int(raw_box.get("top", 0)) - crop_box[1], 0),
        min(int(raw_box.get("left", 0)) + int(raw_box.get("width", 0)) - crop_box[0], crop.width - 1),
        min(int(raw_box.get("top", 0)) + int(raw_box.get("height", 0)) - crop_box[1], crop.height - 1),
    )
    keyed = remove_edge_background(crop, threshold)
    keyed = keep_components_intersecting_core(keyed, core_box)
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
        "background_removal": "edge_floodfill_plus_core_component_filter",
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
