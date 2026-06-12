#!/usr/bin/env python3
"""Audit whether reconstructed PPTX slides are real editable native rebuilds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
EMU_PER_INCH = 914400
DEFAULT_SLIDE_W = 13.333333 * EMU_PER_INCH
DEFAULT_SLIDE_H = 7.5 * EMU_PER_INCH


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_visual_contract(path: Path | None) -> dict:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"visual contract does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def slide_threshold(policy: dict, slide_index: int, slide_count: int) -> dict:
    simple = policy.get("simple_slide_thresholds") or {}
    content = policy.get("content_slide_thresholds") or {}
    result = {
        "minimum_native_elements": safe_int(content.get("minimum_native_elements"), 35),
        "minimum_visible_text_shapes": safe_int(content.get("minimum_visible_text_shapes"), 8),
        "minimum_editable_text_chars": safe_int(content.get("minimum_editable_text_chars"), 60),
        "max_full_slide_or_large_raster_images": safe_int(
            policy.get("max_full_slide_or_large_raster_images_per_slide"), 0
        ),
        "allow_large_raster": policy.get("allow_full_slide_backplate_by_default") is True,
    }
    if slide_index == 1 or slide_index == slide_count:
        result.update(
            {
                "minimum_native_elements": safe_int(simple.get("minimum_native_elements"), 10),
                "minimum_visible_text_shapes": safe_int(simple.get("minimum_visible_text_shapes"), 2),
                "minimum_editable_text_chars": safe_int(simple.get("minimum_editable_text_chars"), 10),
            }
        )
    return result


def text_value(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.findall(".//a:t", NS)).strip()


def shape_extents(node: ET.Element) -> tuple[int, int, int, int] | None:
    xfrm = node.find(".//a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return (
        safe_int(off.get("x")),
        safe_int(off.get("y")),
        safe_int(ext.get("cx")),
        safe_int(ext.get("cy")),
    )


def presentation_size(zip_file: ZipFile) -> tuple[int, int]:
    try:
        root = ET.fromstring(zip_file.read("ppt/presentation.xml"))
    except KeyError:
        return int(DEFAULT_SLIDE_W), int(DEFAULT_SLIDE_H)
    sz = root.find("p:sldSz", NS)
    if sz is None:
        return int(DEFAULT_SLIDE_W), int(DEFAULT_SLIDE_H)
    return safe_int(sz.get("cx"), int(DEFAULT_SLIDE_W)), safe_int(sz.get("cy"), int(DEFAULT_SLIDE_H))


def slide_files(zip_file: ZipFile) -> list[str]:
    return sorted(
        (
            name
            for name in zip_file.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ),
        key=lambda value: safe_int("".join(ch for ch in Path(value).stem if ch.isdigit())),
    )


def analyze_slide(
    xml_bytes: bytes,
    slide_w: int,
    slide_h: int,
    slide_index: int,
    slide_count: int,
    policy: dict,
) -> dict:
    root = ET.fromstring(xml_bytes)
    shapes = root.findall(".//p:sp", NS)
    pictures = root.findall(".//p:pic", NS)
    connectors = root.findall(".//p:cxnSp", NS)
    graphic_frames = root.findall(".//p:graphicFrame", NS)
    text_shapes = [sp for sp in shapes if text_value(sp)]
    editable_chars = sum(len(text_value(sp)) for sp in text_shapes)

    large_pictures = []
    max_ratio = 0.0
    full_threshold = float(policy.get("full_slide_or_large_picture_area_ratio", 0.85))
    for pic in pictures:
        ext = shape_extents(pic)
        if not ext:
            continue
        _, _, cx, cy = ext
        area_ratio = (cx * cy) / float(max(slide_w * slide_h, 1))
        max_ratio = max(max_ratio, area_ratio)
        if area_ratio >= full_threshold or (cx >= slide_w * 0.94 and cy >= slide_h * 0.94):
            large_pictures.append({"area_ratio": round(area_ratio, 4), "cx": cx, "cy": cy})

    native_elements = len(shapes) + len(connectors) + len(graphic_frames)
    thresholds = slide_threshold(policy, slide_index, slide_count)
    failures = []

    if not thresholds["allow_large_raster"] and len(large_pictures) > thresholds["max_full_slide_or_large_raster_images"]:
        failures.append(
            "large/full-slide raster image is not allowed for native-trace reconstruction"
        )
    if native_elements < thresholds["minimum_native_elements"]:
        failures.append(
            f"native element count {native_elements} below required {thresholds['minimum_native_elements']}"
        )
    if len(text_shapes) < thresholds["minimum_visible_text_shapes"]:
        failures.append(
            f"editable visible text shape count {len(text_shapes)} below required "
            f"{thresholds['minimum_visible_text_shapes']}"
        )
    if editable_chars < thresholds["minimum_editable_text_chars"]:
        failures.append(
            f"editable text characters {editable_chars} below required {thresholds['minimum_editable_text_chars']}"
        )
    if len(pictures) == len(large_pictures) and pictures and native_elements < thresholds["minimum_native_elements"]:
        failures.append("slide appears to be image-only or image-dominant, not editable reconstruction")

    return {
        "slide_index": slide_index,
        "status": "FAIL" if failures else "PASS",
        "native_elements": native_elements,
        "auto_shapes": len(shapes),
        "connectors": len(connectors),
        "graphic_frames": len(graphic_frames),
        "pictures": len(pictures),
        "large_or_full_slide_pictures": len(large_pictures),
        "max_picture_area_ratio": round(max_ratio, 4),
        "editable_text_shapes": len(text_shapes),
        "editable_text_chars": editable_chars,
        "thresholds": thresholds,
        "failures": failures,
    }


def accepted_native_trace_exception(slide: dict) -> bool:
    exception = slide.get("native_trace_exception") or {}
    return (
        slide.get("explicit_downgrade_accepted") is True
        or exception.get("user_accepted_risk") is True
        or exception.get("explicit_downgrade_accepted") is True
    )


def visual_contract_failures(visual_contract: dict, slide_count: int, policy: dict) -> list[str]:
    slides = visual_contract.get("slides") if isinstance(visual_contract, dict) else None
    if not isinstance(slides, list) or not slides:
        return []

    failures: list[str] = []
    require_native = policy.get("require_native_trace_hybrid_by_default") is not False
    if len(slides) != slide_count:
        failures.append(
            f"visual_contract slide count {len(slides)} does not match PPTX slide count {slide_count}"
        )

    for idx, slide in enumerate(slides[:slide_count], 1):
        if not isinstance(slide, dict):
            failures.append(f"visual_contract slide {idx:03d} is not an object")
            continue
        mode = slide.get("reconstruction_mode") or visual_contract.get("default_reconstruction_mode")
        if require_native and mode != "native_trace_hybrid" and not accepted_native_trace_exception(slide):
            failures.append(
                f"visual_contract slide {idx:03d} reconstruction_mode must be native_trace_hybrid; got {mode!r}"
            )
        trace_plan = slide.get("native_trace_plan") or {}
        if require_native and not accepted_native_trace_exception(slide):
            if not isinstance(trace_plan, dict) or not trace_plan:
                failures.append(f"visual_contract slide {idx:03d} missing native_trace_plan")
            else:
                if trace_plan.get("source_image_used_as_coordinate_blueprint") is not True:
                    failures.append(
                        f"visual_contract slide {idx:03d} native_trace_plan must mark the source image as coordinate blueprint"
                    )
                if trace_plan.get("source_image_not_retained_as_full_slide_layer") is not True:
                    failures.append(
                        f"visual_contract slide {idx:03d} native_trace_plan must forbid retaining the source image as a full-slide layer"
                    )
                if trace_plan.get("pixel_to_inch_mapping_recorded") is not True:
                    failures.append(
                        f"visual_contract slide {idx:03d} native_trace_plan must record pixel-to-inch mapping"
                    )
    return failures


def audit_pptx(pptx_path: Path, visual_contract: dict | None = None) -> dict:
    if not pptx_path.exists():
        raise FileNotFoundError(f"PPTX does not exist: {pptx_path}")
    visual_contract = visual_contract or {}
    policy = (
        visual_contract.get("pptx_native_reconstruction_policy")
        or visual_contract.get("native_reconstruction_policy")
        or {}
    )
    if not policy:
        policy = {
            "enabled": True,
            "full_slide_or_large_picture_area_ratio": 0.85,
            "allow_full_slide_backplate_by_default": False,
            "max_full_slide_or_large_raster_images_per_slide": 0,
            "content_slide_thresholds": {
                "minimum_native_elements": 35,
                "minimum_visible_text_shapes": 8,
                "minimum_editable_text_chars": 60,
            },
            "simple_slide_thresholds": {
                "minimum_native_elements": 10,
                "minimum_visible_text_shapes": 2,
                "minimum_editable_text_chars": 10,
            },
        }

    with ZipFile(pptx_path) as zip_file:
        slide_w, slide_h = presentation_size(zip_file)
        files = slide_files(zip_file)
        slides = [
            analyze_slide(zip_file.read(name), slide_w, slide_h, idx, len(files), policy)
            for idx, name in enumerate(files, 1)
        ]
    failures = [
        f"slide {slide['slide_index']:03d}: {failure}"
        for slide in slides
        for failure in slide["failures"]
    ]
    failures.extend(visual_contract_failures(visual_contract, len(slides), policy))
    summary = {
        "slide_count": len(slides),
        "total_native_elements": sum(slide["native_elements"] for slide in slides),
        "total_editable_text_shapes": sum(slide["editable_text_shapes"] for slide in slides),
        "total_pictures": sum(slide["pictures"] for slide in slides),
        "total_large_or_full_slide_pictures": sum(slide["large_or_full_slide_pictures"] for slide in slides),
    }
    return {
        "status": "FAIL" if failures else "PASS",
        "pptx_path": str(pptx_path),
        "policy": policy,
        "summary": summary,
        "slides": slides,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", required=True, help="PPTX to audit.")
    parser.add_argument("--visual-contract", help="Optional visual_contract.json containing thresholds.")
    parser.add_argument("--report", help="Optional output report JSON path.")
    args = parser.parse_args()

    try:
        contract = read_visual_contract(Path(args.visual_contract).expanduser().resolve()) if args.visual_contract else {}
        report = audit_pptx(Path(args.pptx).expanduser().resolve(), contract)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
