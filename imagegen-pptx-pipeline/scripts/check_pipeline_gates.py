#!/usr/bin/env python3
"""Validate hard gates for the ImageGen PPTX pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import zipfile
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except Exception:  # pragma: no cover - reported by final gate if needed
    np = None
    Image = None

try:
    from defusedxml.ElementTree import fromstring as xml_fromstring  # type: ignore
except Exception:  # pragma: no cover - hardened stdlib fallback
    from xml.etree.ElementTree import fromstring as stdlib_xml_fromstring

    def xml_fromstring(data):
        head = (data[:4096] if isinstance(data, bytes) else data[:4096].encode("utf-8", "ignore")).lower()
        if b"<!doctype" in head or b"<!entity" in head:
            raise ValueError("refusing XML with DOCTYPE/ENTITY")
        return stdlib_xml_fromstring(data)


COMP_RE = re.compile(r"slide[-_]\d{1,3}.*comp\.(png|jpg|jpeg)$", re.IGNORECASE)
CONTENT_STYLE_TERMS = (
    "evidence",
    "proof",
    "risk-system",
    "system-map",
    "command-center",
    "roadmap",
    "证据",
    "证明",
    "风控",
    "风险",
    "系统图",
    "驾驶舱",
    "路线",
)
STYLE_SOURCE_VALUES = {"built-in-style-library", "user-specified", "custom-derived-from-reference"}
DIRECT_CONVERSION_MODES = {"reconstruction-only", "repair-existing-pptx"}
ALLOWED_TEXT_STATUS = {"provided", "ocr_verified", "user_accepted_image_text", "image_only_accepted"}
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def load_json(path: Path, failures: list[str], *, required: bool = True) -> dict:
    if not path.exists():
        if required:
            failures.append(f"Missing required file: {path.name}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic surface
        failures.append(f"Invalid JSON in {path.name}: {exc}")
        return {}


def resolve_path(workspace: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = workspace / path
    return path


def require_file(workspace: Path, value: str | None, label: str, failures: list[str]) -> Path | None:
    path = resolve_path(workspace, value)
    if path is None:
        failures.append(f"Missing path for {label}")
        return None
    if not path.exists():
        failures.append(f"Missing file for {label}: {path}")
    return path


def safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def image_size(path: Path) -> tuple[int, int]:
    try:
        with path.open("rb") as handle:
            header = handle.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                width, height = struct.unpack(">II", header[16:24])
                return int(width), int(height)
            if header[:2] == b"\xff\xd8":
                handle.seek(2)
                while True:
                    marker_start = handle.read(1)
                    if not marker_start:
                        return 0, 0
                    if marker_start != b"\xff":
                        continue
                    marker = handle.read(1)
                    while marker == b"\xff":
                        marker = handle.read(1)
                    if marker in {
                        b"\xc0",
                        b"\xc1",
                        b"\xc2",
                        b"\xc3",
                        b"\xc5",
                        b"\xc6",
                        b"\xc7",
                        b"\xc9",
                        b"\xca",
                        b"\xcb",
                        b"\xcd",
                        b"\xce",
                        b"\xcf",
                    }:
                        segment = handle.read(7)
                        height, width = struct.unpack(">HH", segment[3:7])
                        return int(width), int(height)
                    length_bytes = handle.read(2)
                    if len(length_bytes) != 2:
                        return 0, 0
                    length = struct.unpack(">H", length_bytes)[0]
                    handle.seek(max(length - 2, 0), os.SEEK_CUR)
    except OSError:
        return 0, 0
    return 0, 0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def load_json_any(path: Path, failures: list[str]) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"Invalid JSON in {path.name}: {exc}")
        return {}


def resolve_render_path(workspace: Path, log_path: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    if raw.is_absolute():
        return raw
    workspace_candidate = workspace / raw
    if workspace_candidate.exists():
        return workspace_candidate
    return log_path.parent / raw


def icon_manifest_count(path: Path, failures: list[str]) -> int:
    payload = load_json_any(path, failures)
    if not isinstance(payload, dict):
        failures.append(f"icon manifest must be an object: {path}")
        return 0
    extracted = payload.get("extracted")
    if isinstance(extracted, list):
        return len(extracted)
    icons = payload.get("icons")
    if isinstance(icons, list):
        return len(icons)
    return 0


def compute_region_metrics(source: Path, render: Path, failures: list[str], *, threshold_basis=(1920, 1080), regions=None) -> tuple[list[tuple[str, float]], float]:
    if Image is None or np is None:
        failures.append("Pillow and numpy are required for final qa_gate metrics")
        return [], 0.0
    try:
        src = Image.open(source).convert("RGB").resize(threshold_basis)
        ren = Image.open(render).convert("RGB")
    except Exception as exc:
        failures.append(f"Unable to open source/render for real metrics: {exc}")
        return [], 0.0
    scale = ren.width / threshold_basis[0]
    if not regions:
        regions = [
            (f"r{row}c{col}", col * threshold_basis[0] // 6, row * threshold_basis[1] // 4, (col + 1) * threshold_basis[0] // 6, (row + 1) * threshold_basis[1] // 4)
            for row in range(4)
            for col in range(6)
        ]
    rows: list[tuple[str, float]] = []
    max_metric = 0.0
    for name, x0, y0, x1, y1 in regions:
        src_crop = src.crop((x0, y0, x1, y1)).resize((300, 150))
        ren_crop = ren.crop((int(x0 * scale), int(y0 * scale), int(x1 * scale), int(y1 * scale))).resize((300, 150))
        metric = float(np.abs(np.asarray(src_crop).astype(int) - np.asarray(ren_crop).astype(int)).mean())
        rows.append((str(name), metric))
        max_metric = max(max_metric, metric)
    return rows, max_metric


def media_audit(workspace: Path, pptx_path: Path, expected_icons: int | None, failures: list[str], *, label: str, fullpage_frac: float = 0.7) -> dict:
    result = {"media_files": 0, "placed_pictures": 0, "text_runs": 0, "fullpage": []}
    try:
        with zipfile.ZipFile(pptx_path) as archive:
            presentation = xml_fromstring(archive.read("ppt/presentation.xml"))
            size = presentation.find(f"{{{P_NS}}}sldSz")
            if size is None:
                failures.append(f"{label} missing ppt/presentation.xml slide size")
                return result
            slide_w, slide_h = int(size.get("cx")), int(size.get("cy"))
            media_files = [name for name in archive.namelist() if name.startswith("ppt/media/")]
            result["media_files"] = len(media_files)
            slide_xml_names = sorted(name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
            for slide_xml in slide_xml_names:
                root = xml_fromstring(archive.read(slide_xml))
                for pic in root.iter(f"{{{P_NS}}}pic"):
                    result["placed_pictures"] += 1
                    ext = pic.find(f".//{{{A_NS}}}ext")
                    if ext is None:
                        continue
                    cx, cy = int(ext.get("cx")), int(ext.get("cy"))
                    if cx >= fullpage_frac * slide_w and cy >= fullpage_frac * slide_h:
                        result["fullpage"].append({"slide": slide_xml, "width_frac": cx / slide_w, "height_frac": cy / slide_h})
                result["text_runs"] += sum(1 for item in root.iter(f"{{{A_NS}}}t") if (item.text or "").strip())
    except Exception as exc:
        failures.append(f"Unable to audit PPTX media for {label}: {exc}")
        return result
    if result["fullpage"]:
        failures.append(f"{label} contains near-full-page image backgrounds: {result['fullpage']}")
    if expected_icons is not None and result["placed_pictures"] != expected_icons:
        failures.append(f"{label} placed picture count {result['placed_pictures']} does not match icon manifest count {expected_icons}")
    if result["text_runs"] < 8:
        failures.append(f"{label} has only {result['text_runs']} text runs; text may be rasterized or missing")
    return result


def check_strict_render_log(workspace: Path, log_path: Path, minimum_rounds: int, failures: list[str]) -> tuple[int, float]:
    payload = load_json_any(log_path, failures)
    if not isinstance(payload, list):
        failures.append(f"{log_path.relative_to(workspace)} must be a strict render_log.json list, not review-summary metadata")
        return 0, 0.0
    seen: set[Path] = set()
    max_logged = 0.0
    for idx, item in enumerate(payload, 1):
        if not isinstance(item, dict):
            failures.append(f"render_log round {idx} must be an object")
            continue
        for key in ("round", "render", "timestamp", "max_metric", "issues", "fix", "recheck"):
            if key not in item:
                failures.append(f"render_log round {idx} missing required field: {key}")
        render_path = resolve_render_path(workspace, log_path, item.get("render"))
        if not render_path or not render_path.exists():
            failures.append(f"render_log round {idx} references missing render file: {item.get('render')}")
            continue
        resolved = render_path.resolve()
        if resolved in seen:
            failures.append(f"render_log round {idx} reuses an earlier render file: {item.get('render')}")
        seen.add(resolved)
        max_logged = max(max_logged, safe_float(item.get("max_metric")))
    if len(payload) < minimum_rounds:
        failures.append(f"render_log has {len(payload)} rounds but requires at least {minimum_rounds}")
    if len(seen) != len(payload):
        failures.append("render_log rounds must equal distinct render files")
    return len(payload), max_logged


def stage_names(pipeline_state: dict) -> set[str]:
    return {item.get("stage", "") for item in pipeline_state.get("stage_history", []) if isinstance(item, dict)}


def workflow_mode(pipeline_state: dict, deck_spec: dict) -> str:
    return deck_spec.get("deck", {}).get("mode") or pipeline_state.get("mode") or ""


def is_direct_conversion_mode(mode: str) -> bool:
    return mode in DIRECT_CONVERSION_MODES


def deck_spec_fingerprint(deck_spec: dict) -> str:
    deck = deck_spec.get("deck", {})
    payload = {
        "deck": {
            "title": deck.get("title", ""),
            "audience": deck.get("audience", ""),
            "objective": deck.get("objective", ""),
            "deck_profile": deck.get("deck_profile", ""),
            "slide_count": deck.get("slide_count") or len(deck_spec.get("slides", [])),
        },
        "slides": [],
        "sources": deck_spec.get("sources", []),
    }
    invariant_fields = (
        "slide_id",
        "page_number",
        "section",
        "title",
        "claim",
        "body_text",
        "data",
        "proof_object",
        "visual_intent",
        "template_source_slide",
    )
    for slide in deck_spec.get("slides", []):
        payload["slides"].append({field: slide.get(field) for field in invariant_fields})
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def contains_content_style_term(value) -> str:
    text = json.dumps(value, ensure_ascii=False).lower() if not isinstance(value, str) else value.lower()
    for term in CONTENT_STYLE_TERMS:
        if term.lower() in text:
            return term
    return ""


def check_no_html_surrogates(workspace: Path, failures: list[str]) -> None:
    for folder_name in ("slides", "styles"):
        folder = workspace / folder_name
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.suffix.lower() in {".html", ".htm"}:
                failures.append(f"HTML/browser surrogate artifact is forbidden: {path}")


def check_not_html_backed_image(path: Path, label: str, failures: list[str]) -> None:
    normalized = str(path)
    if f"{os.sep}blueprints{os.sep}" in normalized:
        failures.append(f"{label} cannot come from an HTML blueprint path: {path}")
    if path.suffix.lower() in {".html", ".htm"}:
        failures.append(f"{label} cannot be an HTML file: {path}")
        return
    stem = path.stem
    base_stem = re.sub(r"[-_]comp$", "", stem, flags=re.IGNORECASE)
    html_candidates = {
        path.with_suffix(".html"),
        path.parent / f"{base_stem}.html",
        path.parent / "blueprints" / f"{base_stem}-blueprint.html",
        path.parent / "blueprints" / f"{stem}-blueprint.html",
    }
    for candidate in sorted(html_candidates):
        if candidate.exists():
            failures.append(f"{label} appears backed by an HTML/browser blueprint: {candidate}")


def check_content_lock(deck_spec: dict, failures: list[str]) -> None:
    deck = deck_spec.get("deck", {})
    if deck.get("lock_state") != "locked":
        failures.append("deck_spec.json deck.lock_state must be locked before visual work or PPTX export")
    if not deck.get("deck_profile"):
        failures.append("deck_spec.json deck.deck_profile must be selected before visual work")
    slides = deck_spec.get("slides", [])
    if not slides:
        failures.append("deck_spec.json has no slides")
    for idx, slide in enumerate(slides, 1):
        for key in ("title", "claim", "proof_object"):
            if not slide.get(key):
                failures.append(f"slide {idx:03d} missing required deck_spec field: {key}")


def check_slide_intent_lock(workspace: Path, deck_spec: dict, slide_intent_plan: dict, failures: list[str]) -> None:
    fingerprint = deck_spec_fingerprint(deck_spec)
    if slide_intent_plan.get("lock_state") != "locked":
        failures.append("slide_intent_plan.json lock_state must be locked before narrative treatment")
    if slide_intent_plan.get("source_deck_spec_fingerprint") != fingerprint:
        failures.append(f"slide_intent_plan.json source_deck_spec_fingerprint does not match current deck_spec.json; expected {fingerprint}")
    matrix_path = require_file(workspace, slide_intent_plan.get("matrix_path") or "slide_intent_matrix.md", "slide intent matrix", failures)
    if matrix_path and matrix_path.name != "slide_intent_matrix.md":
        failures.append("slide intent matrix should be named slide_intent_matrix.md")
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slides = slide_intent_plan.get("slides", [])
    if expected_count and len(slides) != expected_count:
        failures.append(f"slide_intent_plan.json has {len(slides)} slides but deck_spec expects {expected_count}")
    deck_slide_ids = [slide.get("slide_id") for slide in deck_spec.get("slides", []) if slide.get("slide_id")]
    intent_slide_ids = [slide.get("slide_id") for slide in slides if isinstance(slide, dict)]
    if deck_slide_ids and intent_slide_ids != deck_slide_ids:
        failures.append("slide_intent_plan.json slide order must match deck_spec.json")
    for idx, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            failures.append(f"slide intent {idx:03d} must be an object")
            continue
        for key in ("confirmed_title", "core_idea", "proof_goal"):
            if not slide.get(key):
                failures.append(f"slide intent {idx:03d} missing {key}")
        if slide.get("status") not in {"confirmed", "accepted_assumption"}:
            failures.append(f"slide intent {idx:03d} status must be confirmed or accepted_assumption")
    if slide_intent_plan.get("open_questions"):
        failures.append("slide_intent_plan.json still has open_questions")
    if slide_intent_plan.get("review_status") not in {"approved", "user_accepted_risk"}:
        failures.append("slide_intent_plan.json review_status must be approved or user_accepted_risk")


def check_narrative_lock(workspace: Path, deck_spec: dict, slide_intent_plan: dict, narrative_plan: dict, failures: list[str]) -> None:
    fingerprint = deck_spec_fingerprint(deck_spec)
    if narrative_plan.get("lock_state") != "locked":
        failures.append("narrative_plan.json lock_state must be locked before visual style generation")
    if narrative_plan.get("source_deck_spec_fingerprint") != fingerprint:
        failures.append(f"narrative_plan.json source_deck_spec_fingerprint does not match current deck_spec.json; expected {fingerprint}")
    selected = narrative_plan.get("selected_narrative_id")
    if not selected:
        failures.append("narrative_plan.json selected_narrative_id is empty")
    if narrative_plan.get("slide_intent_lock_state") != "locked" or slide_intent_plan.get("lock_state") != "locked":
        failures.append("slide intent must be locked before narrative_plan.json can be locked")
    matrix_path = require_file(workspace, narrative_plan.get("matrix_path") or "narrative_matrix.md", "narrative matrix", failures)
    if matrix_path and matrix_path.name != "narrative_matrix.md":
        failures.append("narrative matrix should be named narrative_matrix.md")
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slides = narrative_plan.get("slides", [])
    if expected_count and len(slides) != expected_count:
        failures.append(f"narrative_plan.json has {len(slides)} slides but deck_spec expects {expected_count}")
    for idx, slide in enumerate(slides, 1):
        treatment = slide.get("selected_treatment", {}) if isinstance(slide, dict) else {}
        if not treatment:
            failures.append(f"narrative slide {idx:03d} missing selected_treatment")
            continue
        if treatment.get("narrative_id") != selected:
            failures.append(f"narrative slide {idx:03d} selected_treatment.narrative_id must match selected_narrative_id")
        for key in ("presentation_strategy", "content_to_show", "proof_object_expression", "must_preserve"):
            if not treatment.get(key):
                failures.append(f"narrative slide {idx:03d} selected_treatment missing {key}")
    if narrative_plan.get("open_questions"):
        failures.append("narrative_plan.json still has open_questions")
    if narrative_plan.get("review_status") not in {"approved", "user_accepted_risk"}:
        failures.append("narrative_plan.json review_status must be approved or user_accepted_risk")


def has_source(payload: dict, *, name: str, path: str) -> bool:
    sources = payload.get("sources") or []
    if not isinstance(sources, list):
        return False
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("name") == name or source.get("path") == path:
            return True
    return False


def check_style_source_fields(owner: str, item: dict, failures: list[str]) -> None:
    style_id = str(item.get("style_id") or "").strip()
    style_source = str(item.get("style_source") or "").strip()
    if not style_id:
        failures.append(f"{owner} missing style_id from references/style-library.md or custom-*")
    elif not re.match(r"^(custom-)?[a-z0-9][a-z0-9-]*$", style_id):
        failures.append(f"{owner} style_id must be kebab-case, got {style_id!r}")
    if not style_source:
        failures.append(f"{owner} missing style_source")
    elif style_source not in STYLE_SOURCE_VALUES:
        failures.append(f"{owner} style_source must be one of {sorted(STYLE_SOURCE_VALUES)}; got {style_source!r}")
    if not str(item.get("visual_signature") or "").strip():
        failures.append(f"{owner} missing visual_signature")


def check_image_quality_policy(policy, failures: list[str], owner: str) -> dict:
    if not isinstance(policy, dict) or not policy:
        failures.append(f"{owner} image_quality_policy is missing")
        return {}
    if policy.get("enabled") is not True:
        failures.append(f"{owner} image_quality_policy.enabled must be true")
    requested = policy.get("requested_single_slide_canvas_px") or {}
    if safe_int(requested.get("width")) < 1920 or safe_int(requested.get("height")) < 1080:
        failures.append(f"{owner} image_quality_policy.requested_single_slide_canvas_px must target at least 1920x1080")
    minimum = policy.get("minimum_acceptable_comp_px") or {}
    if safe_int(minimum.get("width")) < 1920 or safe_int(minimum.get("height")) < 1080:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_comp_px must be at least 1920x1080")
    if safe_int(policy.get("minimum_acceptable_comp_bytes")) < 1024 * 1024:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_comp_bytes must be at least 1048576")
    if policy.get("prompt_requires_crisp_text_and_icons") is not True:
        failures.append(f"{owner} image_quality_policy.prompt_requires_crisp_text_and_icons must be true")
    if policy.get("review_required_before_pptx") is not True:
        failures.append(f"{owner} image_quality_policy.review_required_before_pptx must be true")
    return policy


def check_style_gate(workspace: Path, deck_spec: dict, slide_intent_plan: dict, narrative_plan: dict, design_system: dict, style_brief: dict, failures: list[str]) -> None:
    check_no_html_surrogates(workspace, failures)
    check_image_quality_policy(style_brief.get("image_quality_policy"), failures, "style_brief.json")
    if style_brief.get("style_variation_scope") != "visual_aesthetic_only":
        failures.append("style_brief.json style_variation_scope must be visual_aesthetic_only")
    if style_brief.get("content_strategy_locked") is not True:
        failures.append("style_brief.json content_strategy_locked must be true before visual style exploration")
    if style_brief.get("selected_narrative_id") != narrative_plan.get("selected_narrative_id"):
        failures.append("style_brief.json selected_narrative_id must match narrative_plan.json")
    if slide_intent_plan.get("lock_state") != "locked":
        failures.append("slide_intent_plan.json must be locked before style selection")
    design_taste = design_system.get("taste_guidance", {})
    style_taste = style_brief.get("taste_guidance", {})
    if design_taste.get("enabled") is not True or style_taste.get("enabled") is not True:
        failures.append("taste guidance must be enabled for style exploration")
    if not has_source(design_taste, name="built-in-ppt-taste-system", path="references/taste-system.md"):
        failures.append("design_system.json taste_guidance.sources must include built-in-ppt-taste-system")
    if not has_source(style_taste, name="built-in-ppt-taste-system", path="references/taste-system.md"):
        failures.append("style_brief.json taste_guidance.sources must include built-in-ppt-taste-system")
    style_library = style_brief.get("style_library") or {}
    if style_library.get("enabled") is not True:
        failures.append("style_brief.json style_library.enabled must be true")
    if not has_source(style_library, name="built-in-ppt-style-library", path="references/style-library.md"):
        failures.append("style_brief.json style_library.sources must include references/style-library.md")

    count = safe_int(style_brief.get("direction_count"))
    if count < 1:
        failures.append("style_brief.json direction_count is 0; style exploration was skipped")
    selected_options = [str(item) for item in (style_brief.get("selected_options") or []) if str(item).strip()]
    if style_brief.get("selected_option") and str(style_brief.get("selected_option")) not in selected_options:
        selected_options.append(str(style_brief.get("selected_option")))
    if not selected_options:
        failures.append("style_brief.json selected_option/selected_options is empty; user or automation did not select a style")

    current_fingerprint = deck_spec_fingerprint(deck_spec)
    narrative_lock = style_brief.get("narrative_lock", {})
    if narrative_lock.get("deck_spec_fingerprint") != current_fingerprint:
        failures.append(f"style_brief.json narrative_lock.deck_spec_fingerprint must match current deck_spec.json; expected {current_fingerprint}")
    candidates = style_brief.get("candidate_directions") or []
    if count and len(candidates) < count:
        failures.append(f"style_brief.json has {len(candidates)} candidate_directions but direction_count is {count}")
    candidate_options = set()
    families = []
    for idx, candidate in enumerate(candidates, 1):
        check_style_source_fields(f"candidate direction {idx}", candidate, failures)
        if candidate.get("option_id"):
            candidate_options.add(str(candidate.get("option_id")))
        if candidate.get("aesthetic_family"):
            families.append(str(candidate.get("aesthetic_family")))
        else:
            failures.append(f"candidate direction {idx} missing aesthetic_family")
        term = contains_content_style_term(
            {
                "style_lane_id": candidate.get("style_lane_id"),
                "name": candidate.get("name"),
                "aesthetic_family": candidate.get("aesthetic_family"),
                "premise": candidate.get("premise") or candidate.get("strategic_premise"),
            }
        )
        if term:
            failures.append(f"candidate direction {idx} uses content/narrative term {term!r} as a style label")
    if count > 1 and len(set(families)) < min(count, len(candidates)):
        failures.append("candidate directions must use distinct aesthetic_family values")
    for option in selected_options:
        if candidate_options and option not in candidate_options:
            failures.append(f"style_brief.json selected option {option!r} is not in candidate_directions")

    contact_min = (style_brief.get("image_quality_policy") or {}).get("minimum_acceptable_contact_sheet_px") or {}
    min_contact_width = safe_int(contact_min.get("width")) or 2400
    min_contact_height = safe_int(contact_min.get("height")) or 1350
    for idx, raw_sheet in enumerate(style_brief.get("style_contact_sheets") or [], 1):
        sheet_path = raw_sheet.get("path") if isinstance(raw_sheet, dict) else raw_sheet
        if isinstance(raw_sheet, dict):
            check_style_source_fields(f"style contact sheet {idx}", raw_sheet, failures)
            if raw_sheet.get("generator") != "imagegen":
                failures.append(f"style contact sheet {idx} must declare generator=imagegen")
            if raw_sheet.get("prompt_path"):
                require_file(workspace, raw_sheet.get("prompt_path"), f"style contact sheet {idx} prompt", failures)
        path = require_file(workspace, sheet_path, f"style contact sheet {idx}", failures)
        if not path:
            continue
        if f"{os.sep}output{os.sep}" in str(path) or f"{os.sep}preview{os.sep}" in str(path):
            failures.append(f"style contact sheet cannot be a final output or PPTX preview image: {path}")
        check_not_html_backed_image(path, "style contact sheet", failures)
        width, height = image_size(path)
        if not width or not height:
            failures.append(f"style contact sheet dimensions could not be read: {path}")
        elif width < min_contact_width or height < min_contact_height:
            failures.append(f"style contact sheet must be at least {min_contact_width}x{min_contact_height}; got {width}x{height}: {path}")


def check_conversion_policy(workspace: Path, visual_contract: dict, failures: list[str]) -> dict:
    policy = visual_contract.get("conversion_policy") or {}
    if not isinstance(policy, dict) or not policy:
        failures.append("visual_contract.json conversion_policy is missing")
        return {}
    if policy.get("enabled") is not True:
        failures.append("visual_contract.json conversion_policy.enabled must be true")
    if policy.get("method") != "strict_slide_image_to_editable_pptx":
        failures.append("visual_contract.json conversion_policy.method must be strict_slide_image_to_editable_pptx")
    for key, expected in (
        ("builder_script", "slidelib.py"),
        ("icon_extractor_script", "iconcut3.py"),
        ("qa_gate_script", "qa_gate.py"),
        ("pitfalls_reference", "PITFALLS.md"),
    ):
        if policy.get(key) != expected:
            failures.append(f"visual_contract.json conversion_policy.{key} must be {expected}")
        require_file(workspace, expected, expected, failures)
    basis = policy.get("basis_px") or {}
    if safe_int(basis.get("width")) != 1920 or safe_int(basis.get("height")) != 1080:
        failures.append("visual_contract.json conversion_policy.basis_px must be 1920x1080")
    required_true = (
        "source_image_is_measurement_target",
        "native_text_required",
        "native_shapes_required",
        "native_charts_tables_connectors_required",
        "only_complex_art_may_be_images",
        "multiline_text_split_required",
        "automatic_text_wrap_for_multiline_forbidden",
        "strict_icon_extraction_required",
        "icon_contact_sheet_audit_required",
        "real_source_icons_must_be_extracted",
        "native_redraw_for_named_pictograms_forbidden",
        "icon_hd_enhancement_required",
    )
    for key in required_true:
        if policy.get(key) is not True:
            failures.append(f"visual_contract.json conversion_policy.{key} must be true")
    for key in ("full_image_backgrounds_allowed", "region_image_backgrounds_allowed"):
        if policy.get(key) is not False:
            failures.append(f"visual_contract.json conversion_policy.{key} must be false")
    if safe_int(policy.get("minimum_render_compare_rounds")) < 10:
        failures.append("visual_contract.json conversion_policy.minimum_render_compare_rounds must be at least 10")
    for key in ("render_round_requires_new_export", "qa_gate_required", "metrics_gate_reads_actual_render", "media_audit_required"):
        if policy.get(key) is not True:
            failures.append(f"visual_contract.json conversion_policy.{key} must be true")
    return policy


def check_strict_icon_policy(workspace: Path, visual_contract: dict, failures: list[str]) -> None:
    policy = visual_contract.get("strict_icon_policy") or {}
    if not isinstance(policy, dict) or not policy:
        failures.append("visual_contract.json strict_icon_policy is missing")
        return
    if policy.get("enabled") is not True:
        failures.append("visual_contract.json strict_icon_policy.enabled must be true")
    if policy.get("extractor_script") != "iconcut3.py":
        failures.append("visual_contract.json strict_icon_policy.extractor_script must be iconcut3.py")
    for key in (
        "transparent_png_required",
        "edge_audit_required",
        "contact_sheet_audit_required",
        "clip_error_fails_closed",
        "no_manual_crop_fallback",
        "source_icon_inventory_required",
        "real_source_icons_must_be_extracted",
        "native_redraw_for_named_pictograms_forbidden",
        "glyph_helpers_are_placeholder_only",
        "icon_hd_enhancement_required",
        "feathered_slices_preserve_alpha",
    ):
        if policy.get(key) is not True:
            failures.append(f"visual_contract.json strict_icon_policy.{key} must be true")
    if safe_int(policy.get("minimum_output_icon_min_dim_px")) < 256:
        failures.append("visual_contract.json strict_icon_policy.minimum_output_icon_min_dim_px must be at least 256")
    if safe_int(policy.get("icon_hd_target_min_px")) < 256:
        failures.append("visual_contract.json strict_icon_policy.icon_hd_target_min_px must be at least 256")
    manifest_path = require_file(workspace, policy.get("manifest_path") or "icons/icon_jobs.json", "icon jobs manifest", failures)
    if manifest_path and manifest_path.exists():
        manifest = load_json(manifest_path, failures)
        if manifest.get("status") not in {"draft", "ready", "processed", "approved", "not_applicable"}:
            failures.append("icon jobs manifest status must be draft, ready, processed, approved, or not_applicable")


def check_render_compare_loop(visual_contract: dict, failures: list[str]) -> dict:
    loop = visual_contract.get("render_compare_loop") or {}
    if not isinstance(loop, dict) or not loop:
        failures.append("visual_contract.json render_compare_loop is missing")
        return {}
    if loop.get("enabled") is not True:
        failures.append("visual_contract.json render_compare_loop.enabled must be true")
    if safe_int(loop.get("minimum_rounds")) < 10:
        failures.append("visual_contract.json render_compare_loop.minimum_rounds must be at least 10")
    if not loop.get("rounds_log_path"):
        failures.append("visual_contract.json render_compare_loop.rounds_log_path is missing")
    if loop.get("paired_crops_required") is not True:
        failures.append("visual_contract.json render_compare_loop.paired_crops_required must be true")
    if safe_float(loop.get("region_diff_blocking_mean_abs")) > 40 or safe_float(loop.get("region_diff_blocking_mean_abs")) <= 0:
        failures.append("visual_contract.json render_compare_loop.region_diff_blocking_mean_abs must be >0 and <=40")
    if loop.get("block_on_unresolved_p0_p1") is not True:
        failures.append("visual_contract.json render_compare_loop.block_on_unresolved_p0_p1 must be true")
    if not loop.get("render_log_path"):
        failures.append("visual_contract.json render_compare_loop.render_log_path is missing")
    if loop.get("round_requires_new_export") is not True:
        failures.append("visual_contract.json render_compare_loop.round_requires_new_export must be true")
    if loop.get("qa_gate_script") != "qa_gate.py":
        failures.append("visual_contract.json render_compare_loop.qa_gate_script must be qa_gate.py")
    if loop.get("media_audit_required") is not True:
        failures.append("visual_contract.json render_compare_loop.media_audit_required must be true")
    return loop


def check_visual_contract(workspace: Path, deck_spec: dict, visual_contract: dict, failures: list[str]) -> None:
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    direct_conversion = is_direct_conversion_mode(deck_spec.get("deck", {}).get("mode", ""))
    quality_policy = check_image_quality_policy(visual_contract.get("image_quality_policy"), failures, "visual_contract.json")
    check_conversion_policy(workspace, visual_contract, failures)
    check_strict_icon_policy(workspace, visual_contract, failures)
    check_render_compare_loop(visual_contract, failures)
    check_no_html_surrogates(workspace, failures)
    if visual_contract.get("conversion_method") != "strict_slide_image_to_editable_pptx":
        failures.append("visual_contract.json conversion_method must be strict_slide_image_to_editable_pptx")
    if visual_contract.get("comp_is_conversion_target") is not True:
        failures.append("visual_contract.json comp_is_conversion_target must be true")
    if visual_contract.get("per_slide_comps_complete") is not True:
        failures.append("visual_contract.json per_slide_comps_complete must be true before PPTX build")
    selected_styles = [str(item) for item in (visual_contract.get("selected_styles") or []) if str(item).strip()]
    if visual_contract.get("selected_style") and str(visual_contract.get("selected_style")) not in selected_styles:
        selected_styles.append(str(visual_contract.get("selected_style")))
    if not selected_styles:
        failures.append("visual_contract.json selected_style/selected_styles is empty")
    contact_sheet = visual_contract.get("contact_sheet")
    if not contact_sheet and not direct_conversion:
        failures.append("visual_contract.json contact_sheet is empty")
    elif contact_sheet:
        require_file(workspace, contact_sheet, "selected style contact sheet", failures)

    if not direct_conversion:
        comp_generation_mode = visual_contract.get("comp_generation_mode")
        parallel_used = visual_contract.get("parallel_page_subagents_used") is True
        parallel_accepted = visual_contract.get("explicit_parallel_comp_generation_accepted") is True
        if comp_generation_mode not in {"main_agent_serial_imagegen", "style_sharded_serial_imagegen"} and not parallel_accepted:
            failures.append("visual_contract.json comp_generation_mode must be main_agent_serial_imagegen or style_sharded_serial_imagegen")
        if parallel_used and not parallel_accepted:
            failures.append("visual_contract.json parallel_page_subagents_used requires explicit_parallel_comp_generation_accepted=true")

    slides = visual_contract.get("slides", [])
    if expected_count and len(slides) != expected_count:
        failures.append(f"visual_contract.json has {len(slides)} slides but deck_spec expects {expected_count}")
    minimum_px = quality_policy.get("minimum_acceptable_comp_px") or {}
    minimum_width = safe_int(minimum_px.get("width"))
    minimum_height = safe_int(minimum_px.get("height"))
    minimum_bytes = safe_int(quality_policy.get("minimum_acceptable_comp_bytes"))
    for idx, slide in enumerate(slides, 1):
        comp = slide.get("comp_path") or slide.get("approved_comp_path")
        path = require_file(workspace, comp, f"slide {idx:03d} approved comp", failures)
        if path:
            normalized = str(path)
            if f"{os.sep}preview{os.sep}" in normalized or f"{os.sep}output{os.sep}" in normalized:
                failures.append(f"slide {idx:03d} approved comp cannot be a PPTX preview/output image: {path}")
            if not direct_conversion and f"{os.sep}slides{os.sep}" not in normalized:
                failures.append(f"slide {idx:03d} approved comp must live under slides/, not {path}")
            if not direct_conversion and not COMP_RE.search(path.name):
                failures.append(f"slide {idx:03d} approved comp filename must look like slide-XXX-comp.png, not {path.name}")
            check_not_html_backed_image(path, f"slide {idx:03d} approved comp", failures)
            width, height = image_size(path)
            if minimum_width and minimum_height:
                if not width or not height:
                    failures.append(f"slide {idx:03d} approved comp dimensions could not be read: {path}")
                elif width < minimum_width or height < minimum_height:
                    failures.append(f"slide {idx:03d} approved comp must be at least {minimum_width}x{minimum_height}; got {width}x{height}: {path}")
            if minimum_bytes and path.exists() and path.stat().st_size < minimum_bytes:
                failures.append(f"slide {idx:03d} approved comp file must be at least {minimum_bytes} bytes; got {path.stat().st_size}: {path}")
        if not slide.get("visual_archetype"):
            failures.append(f"slide {idx:03d} missing visual_archetype in visual_contract.json")
        clarity = slide.get("clarity_review")
        if not isinstance(clarity, dict):
            failures.append(f"slide {idx:03d} missing clarity_review in visual_contract.json")
        else:
            if clarity.get("status") not in {"approved", "user_accepted_risk"}:
                failures.append(f"slide {idx:03d} clarity_review.status must be approved or user_accepted_risk")
            if clarity.get("blocking_blur") is not False:
                failures.append(f"slide {idx:03d} clarity_review.blocking_blur must be false")
        if not direct_conversion:
            source_type = slide.get("image_source_type") or (clarity or {}).get("image_source_type")
            if source_type != "imagegen":
                failures.append(f"slide {idx:03d} image_source_type must be imagegen in generated-deck mode")
            continuity = slide.get("style_continuity_review")
            if not isinstance(continuity, dict) or continuity.get("status") != "approved":
                failures.append(f"slide {idx:03d} style_continuity_review.status must be approved")
        converter = slide.get("converter") or {}
        if not isinstance(converter, dict):
            failures.append(f"slide {idx:03d} converter must be an object")
            converter = {}
        if converter.get("measurement_status") not in {"planned", "completed", "approved"}:
            failures.append(f"slide {idx:03d} converter.measurement_status must be planned, completed, or approved")
        if converter.get("text_split_plan") not in {"planned", "completed", "not_applicable"}:
            failures.append(f"slide {idx:03d} converter.text_split_plan must be planned, completed, or not_applicable")
        if not converter.get("output_slide_pptx"):
            failures.append(f"slide {idx:03d} converter.output_slide_pptx is missing")


def check_conversion_manifest(workspace: Path, deck_spec: dict, manifest: dict, failures: list[str], *, require_outputs: bool = False) -> None:
    if manifest.get("lock_state") != "locked":
        failures.append("conversion_manifest.json lock_state must be locked before PPTX conversion")
    if manifest.get("conversion_method") != "strict_slide_image_to_editable_pptx":
        failures.append("conversion_manifest.json conversion_method must be strict_slide_image_to_editable_pptx")
    basis = manifest.get("basis_px") or {}
    if safe_int(basis.get("width")) != 1920 or safe_int(basis.get("height")) != 1080:
        failures.append("conversion_manifest.json basis_px must be 1920x1080")
    tool_files = manifest.get("tool_files") or {}
    copied = tool_files.get("copied_to_workspace") if isinstance(tool_files, dict) else {}
    for filename in ("slidelib.py", "iconcut3.py", "qa_gate.py", "PITFALLS.md"):
        require_file(workspace, filename, filename, failures)
        if isinstance(copied, dict) and copied.get(filename) is not True:
            failures.append(f"conversion_manifest.json tool_files.copied_to_workspace.{filename} must be true")
    page_modules = manifest.get("page_modules") or {}
    if is_direct_conversion_mode(deck_spec.get("deck", {}).get("mode", "")):
        for key in ("enabled", "per_slide_pptx_required", "merge_after_page_approval"):
            if page_modules.get(key) is not True:
                failures.append(f"conversion_manifest.json page_modules.{key} must be true in direct conversion mode")
    global_rules = manifest.get("global_rules") or {}
    required_true = (
        "source_image_is_measurement_target_not_final_layer",
        "full_image_or_region_layers_forbidden",
        "ordinary_table_or_card_rebuild_forbidden",
        "native_text_shapes_charts_required",
        "hidden_text_layer_does_not_count_as_editable",
        "strict_icon_extraction_required",
        "icon_contact_sheet_audit_required",
        "source_icon_inventory_required",
        "real_source_icons_must_be_extracted",
        "native_redraw_for_named_pictograms_forbidden",
        "multiline_text_split_required",
        "render_round_requires_new_export",
        "qa_gate_required",
        "metrics_gate_reads_actual_render",
        "media_audit_required",
    )
    for key in required_true:
        if global_rules.get(key) is not True:
            failures.append(f"conversion_manifest.json global_rules.{key} must be true")
    if safe_int(global_rules.get("minimum_render_compare_rounds")) < 10:
        failures.append("conversion_manifest.json global_rules.minimum_render_compare_rounds must be at least 10")
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slides = manifest.get("slides", [])
    if expected_count and len(slides) != expected_count:
        failures.append(f"conversion_manifest.json has {len(slides)} slides but deck_spec expects {expected_count}")
    if manifest.get("open_questions"):
        failures.append("conversion_manifest.json still has open_questions")
    for idx, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            failures.append(f"conversion manifest slide {idx:03d} must be an object")
            continue
        if not slide.get("slide_id"):
            failures.append(f"conversion manifest slide {idx:03d} missing slide_id")
        source_path = slide.get("source_image_path") or slide.get("approved_comp_path")
        path = require_file(workspace, source_path, f"conversion slide {idx:03d} source image", failures)
        if path and (f"{os.sep}output{os.sep}" in str(path) or f"{os.sep}preview{os.sep}" in str(path)):
            failures.append(f"conversion slide {idx:03d} source image cannot be a PPTX preview/output image: {path}")
        if slide.get("text_source_status") not in ALLOWED_TEXT_STATUS:
            failures.append(f"conversion slide {idx:03d} text_source_status must be one of {sorted(ALLOWED_TEXT_STATUS)}")
        if slide.get("measurement_status") not in {"planned", "completed", "approved"}:
            failures.append(f"conversion slide {idx:03d} measurement_status must be planned, completed, or approved")
        if slide.get("icon_extraction_status") not in {"planned", "passed", "not_applicable"}:
            failures.append(f"conversion slide {idx:03d} icon_extraction_status must be planned, passed, or not_applicable")
        if slide.get("icon_extraction_status") == "passed":
            if slide.get("icon_edge_audit_status") != "passed":
                failures.append(f"conversion slide {idx:03d} icon_edge_audit_status must be passed")
            if slide.get("icon_contact_sheet_audit_status") != "passed":
                failures.append(f"conversion slide {idx:03d} icon_contact_sheet_audit_status must be passed")
            if safe_int(slide.get("extracted_icon_count")) <= 0:
                failures.append(f"conversion slide {idx:03d} extracted_icon_count must be > 0 when icon_extraction_status is passed")
            require_file(workspace, slide.get("icon_jobs_path") or "icons/icon_jobs.json", f"conversion slide {idx:03d} icon jobs", failures)
            require_file(workspace, slide.get("icon_contact_sheet"), f"conversion slide {idx:03d} icon contact sheet", failures)
        if slide.get("icon_extraction_status") == "not_applicable":
            if slide.get("source_icon_inventory_status") != "no_source_icons_detected":
                failures.append(
                    f"conversion slide {idx:03d} icon_extraction_status=not_applicable requires "
                    "source_icon_inventory_status=no_source_icons_detected"
                )
            if safe_int(slide.get("extracted_icon_count")) > 0:
                failures.append(f"conversion slide {idx:03d} extracted_icon_count must be 0 when icon extraction is not_applicable")
        if not slide.get("build_script_path"):
            failures.append(f"conversion slide {idx:03d} missing build_script_path")
        if not slide.get("output_slide_pptx"):
            failures.append(f"conversion slide {idx:03d} missing output_slide_pptx")
        if not slide.get("preview_path"):
            failures.append(f"conversion slide {idx:03d} missing preview_path")
        if require_outputs:
            require_file(workspace, slide.get("build_script_path"), f"conversion slide {idx:03d} build script", failures)
            require_file(workspace, slide.get("output_slide_pptx"), f"conversion slide {idx:03d} output PPTX", failures)
            require_file(workspace, slide.get("preview_path"), f"conversion slide {idx:03d} preview", failures)
            if slide.get("native_build_status") not in {"passed", "approved"}:
                failures.append(f"conversion slide {idx:03d} native_build_status must be passed or approved")
            if safe_int(slide.get("render_compare_rounds_completed")) < 10:
                failures.append(f"conversion slide {idx:03d} render_compare_rounds_completed must be at least 10")
            if slide.get("paired_crops_status") != "passed":
                failures.append(f"conversion slide {idx:03d} paired_crops_status must be passed")
            max_diff = safe_float(slide.get("max_region_mean_abs"))
            if max_diff > 40:
                failures.append(f"conversion slide {idx:03d} max_region_mean_abs {max_diff:.2f} exceeds 40")
            if slide.get("review_status") not in {"approved", "user_accepted_risk"}:
                failures.append(f"conversion slide {idx:03d} review_status must be approved or user_accepted_risk")


def check_reviews(workspace: Path, deck_spec: dict, failures: list[str]) -> None:
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slide_review_dir = workspace / "qa" / "reviews" / "slide-comp"
    review_files = list(slide_review_dir.glob("*.json")) if slide_review_dir.exists() else []
    if expected_count and len(review_files) < expected_count:
        failures.append(f"slide-comp review JSON files are missing: found {len(review_files)}, expected at least {expected_count}")


def check_render_compare_log(workspace: Path, visual_contract: dict, failures: list[str]) -> None:
    loop = visual_contract.get("render_compare_loop") or {}
    minimum_rounds = safe_int(loop.get("minimum_rounds")) or 10
    rounds_path = require_file(workspace, loop.get("rounds_log_path") or "qa/render-compare/render_compare_rounds.json", "render-compare rounds log", failures)
    if not rounds_path or not rounds_path.exists():
        return
    payload = load_json(rounds_path, failures)
    completed = safe_int(payload.get("completed_rounds"))
    if completed < minimum_rounds:
        failures.append(f"render-compare rounds log completed_rounds must be at least {minimum_rounds}; got {completed}")
    if payload.get("unresolved_p0_p1"):
        failures.append("render-compare rounds log still has unresolved_p0_p1 findings")
    paired_crops = payload.get("paired_crops") or []
    if not paired_crops:
        failures.append("render-compare rounds log must include paired_crops")
    metrics = payload.get("region_metrics") or []
    if not metrics:
        failures.append("render-compare rounds log must include region_metrics")
    for idx, metric in enumerate(metrics, 1):
        if not isinstance(metric, dict):
            continue
        mean_abs = safe_float(metric.get("mean_abs"))
        if mean_abs > 40 and metric.get("user_accepted_risk") is not True:
            failures.append(f"render-compare region metric {idx} mean_abs {mean_abs:.2f} exceeds 40")


def check_mechanical_qa_gates(workspace: Path, visual_contract: dict, conversion_manifest: dict, failures: list[str]) -> None:
    require_file(workspace, "qa_gate.py", "qa_gate.py", failures)
    loop = visual_contract.get("render_compare_loop") or {}
    threshold = safe_float(loop.get("region_diff_blocking_mean_abs")) or 40.0
    minimum_rounds = safe_int(loop.get("minimum_rounds")) or 10
    default_render_log = loop.get("render_log_path") or "qa/render-compare/render_log.json"
    slides = conversion_manifest.get("slides") or []
    for idx, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            continue
        label = f"conversion slide {idx:03d}"
        source_path = require_file(workspace, slide.get("source_image_path") or slide.get("approved_comp_path"), f"{label} source image", failures)
        render_path = require_file(workspace, slide.get("latest_render_path") or slide.get("preview_path"), f"{label} latest render", failures)
        pptx_path = require_file(workspace, slide.get("output_slide_pptx"), f"{label} output PPTX", failures)
        render_log_path = require_file(workspace, slide.get("render_log_path") or default_render_log, f"{label} strict render log", failures)

        if source_path and render_path and source_path.exists() and render_path.exists():
            _, actual_max = compute_region_metrics(source_path, render_path, failures)
            if actual_max >= threshold:
                failures.append(f"{label} real qa_gate max region mean_abs {actual_max:.2f} exceeds threshold {threshold:.2f}")
            for key in ("max_region_mean_abs", "actual_max_region_mean_abs"):
                if key in slide and safe_float(slide.get(key)) + 0.5 < actual_max:
                    failures.append(f"{label} {key}={safe_float(slide.get(key)):.2f} understates real computed max {actual_max:.2f}")
        else:
            actual_max = 0.0

        if render_log_path and render_log_path.exists():
            round_count, max_logged = check_strict_render_log(workspace, render_log_path, minimum_rounds, failures)
            if safe_int(slide.get("render_compare_rounds_completed")) != round_count:
                failures.append(
                    f"{label} render_compare_rounds_completed={safe_int(slide.get('render_compare_rounds_completed'))} "
                    f"does not match strict render_log count {round_count}"
                )
            if actual_max and max_logged + 0.5 < actual_max:
                failures.append(f"{label} render_log max_metric {max_logged:.2f} understates real computed max {actual_max:.2f}")

        expected_icons: int | None = None
        if slide.get("icon_extraction_status") == "passed":
            icon_path = require_file(workspace, slide.get("icon_jobs_path") or "icons/icon_jobs.json", f"{label} icon manifest", failures)
            if icon_path and icon_path.exists():
                expected_icons = icon_manifest_count(icon_path, failures)
                if safe_int(slide.get("extracted_icon_count")) != expected_icons:
                    failures.append(
                        f"{label} extracted_icon_count={safe_int(slide.get('extracted_icon_count'))} "
                        f"does not match real icon manifest count {expected_icons}"
                    )
        elif slide.get("icon_extraction_status") == "not_applicable":
            expected_icons = 0

        if pptx_path and pptx_path.exists():
            media_audit(workspace, pptx_path, expected_icons, failures, label=label)


def check_final(workspace: Path, visual_contract: dict, conversion_manifest: dict, failures: list[str]) -> None:
    final_council = workspace / "qa" / "final-council.md"
    qa_report = workspace / "qa_report.md"
    if not final_council.exists():
        failures.append("Missing qa/final-council.md")
    else:
        text = final_council.read_text(encoding="utf-8")
        for token in ("pptx-conversion-fidelity", "taste-direction", "narrative-invariance", "Export Decision"):
            if token not in text:
                failures.append(f"qa/final-council.md missing required token: {token}")
    if not qa_report.exists():
        failures.append("Missing qa_report.md")
    else:
        text = qa_report.read_text(encoding="utf-8")
        empty_markers = ["## Style Direction Gate\n\n## Visual Comp Gate", "## Reviewer Findings\n\n## Final Council"]
        if any(marker in text for marker in empty_markers):
            failures.append("qa_report.md still looks like an unfilled template")
    output_pptx = list((workspace / "output").glob("*.pptx"))
    if not output_pptx:
        failures.append("No final PPTX found under output/")
    check_render_compare_log(workspace, visual_contract, failures)
    final_outputs = conversion_manifest.get("final_outputs") or []
    if final_outputs:
        records = [item for item in final_outputs if isinstance(item, dict)]
        for output in output_pptx:
            matching = [
                item for item in records
                if resolve_path(workspace, item.get("path")) and resolve_path(workspace, item.get("path")).resolve() == output.resolve()
            ]
            if not matching:
                failures.append(f"conversion_manifest.json final_outputs does not cover {output.relative_to(workspace)}")
                continue
            recorded_sha = matching[0].get("sha256")
            if recorded_sha and recorded_sha != file_sha256(output):
                failures.append(f"conversion_manifest.json final_outputs sha256 is stale for {output.relative_to(workspace)}")
    check_mechanical_qa_gates(workspace, visual_contract, conversion_manifest, failures)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument(
        "--stage",
        choices=[
            "content-lock",
            "slide-intent-lock",
            "narrative-lock",
            "style-selection",
            "conversion-lock",
            "reconstruction-lock",
            "before-pptx",
            "final",
        ],
        required=True,
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    failures: list[str] = []
    if not workspace.exists():
        failures.append(f"Workspace does not exist: {workspace}")

    pipeline_state = load_json(workspace / "pipeline_state.json", failures)
    deck_spec = load_json(workspace / "deck_spec.json", failures)
    mode = workflow_mode(pipeline_state, deck_spec)
    direct_conversion_mode = is_direct_conversion_mode(mode)
    slide_intent_plan = load_json(workspace / "slide_intent_plan.json", failures)
    narrative_plan = load_json(workspace / "narrative_plan.json", failures)
    design_system = load_json(workspace / "design_system.json", failures)
    style_brief = load_json(workspace / "style_brief.json", failures)
    visual_contract = load_json(workspace / "visual_contract.json", failures)
    conversion_manifest = load_json(workspace / "conversion_manifest.json", failures)

    if pipeline_state.get("skill") != "imagegen-pptx-pipeline":
        failures.append("pipeline_state.json does not identify imagegen-pptx-pipeline")
    if args.stage in {"before-pptx", "final"} and pipeline_state.get("current_stage") == "initialized":
        failures.append("pipeline_state.json is still at initialized; stage transitions were not recorded")

    conversion_stage = "conversion-lock" if args.stage == "reconstruction-lock" else args.stage
    if direct_conversion_mode:
        if conversion_stage in {"content-lock", "slide-intent-lock", "narrative-lock", "style-selection"}:
            failures.append(f"{args.stage} is not used in {mode} mode; use conversion-lock or before-pptx")
        if conversion_stage in {"conversion-lock", "before-pptx", "final"}:
            check_conversion_manifest(
                workspace,
                deck_spec,
                conversion_manifest,
                failures,
                require_outputs=conversion_stage == "final",
            )
        if conversion_stage in {"before-pptx", "final"}:
            check_visual_contract(workspace, deck_spec, visual_contract, failures)
            required_stages = {"conversion_input_lock", "visual_contract"}
            if conversion_stage == "final":
                required_stages.add("pptx_conversion")
            missing = required_stages - stage_names(pipeline_state)
            if missing:
                failures.append("pipeline_state.json stage_history missing: " + ", ".join(sorted(missing)))
    else:
        check_content_lock(deck_spec, failures)
        if conversion_stage in {"slide-intent-lock", "narrative-lock", "style-selection", "before-pptx", "final"}:
            check_slide_intent_lock(workspace, deck_spec, slide_intent_plan, failures)
        if conversion_stage in {"narrative-lock", "style-selection", "before-pptx", "final"}:
            check_narrative_lock(workspace, deck_spec, slide_intent_plan, narrative_plan, failures)
        if conversion_stage in {"style-selection", "before-pptx", "final"}:
            check_style_gate(workspace, deck_spec, slide_intent_plan, narrative_plan, design_system, style_brief, failures)
        if conversion_stage in {"conversion-lock", "before-pptx", "final"}:
            check_conversion_manifest(
                workspace,
                deck_spec,
                conversion_manifest,
                failures,
                require_outputs=conversion_stage == "final",
            )
        if conversion_stage in {"before-pptx", "final"}:
            check_visual_contract(workspace, deck_spec, visual_contract, failures)
            check_reviews(workspace, deck_spec, failures)
            required_stages = {
                "content_gate",
                "slide_intent_lock",
                "narrative_selection",
                "style_selection",
                "single_slide_comps",
                "slide_comp_review",
                "visual_contract",
            }
            if conversion_stage == "final":
                required_stages.add("pptx_conversion")
            missing = required_stages - stage_names(pipeline_state)
            if missing:
                failures.append("pipeline_state.json stage_history missing: " + ", ".join(sorted(missing)))
    if conversion_stage == "final":
        check_final(workspace, visual_contract, conversion_manifest, failures)

    result = {
        "status": "FAIL" if failures else "PASS",
        "stage": args.stage,
        "workspace": str(workspace),
        "expected_deck_spec_fingerprint": deck_spec_fingerprint(deck_spec) if deck_spec else "",
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
