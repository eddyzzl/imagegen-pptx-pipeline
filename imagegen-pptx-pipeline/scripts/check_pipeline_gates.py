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
STYLE_TASK_POLICY_ID = "task-aware-style-recommendation-v1"
STYLE_DIVERSITY_POLICY_ID = "style-lane-diversity-v1"
DIRECT_CONVERSION_MODES = {"reconstruction-only", "repair-existing-pptx"}
ALLOWED_TEXT_STATUS = {"provided", "ocr_verified", "user_accepted_image_text", "image_only_accepted"}
SLIDE_COMP_REVIEW_ROLES = (
    "content-integrity",
    "text-typography",
    "visual-fidelity",
    "style-continuity",
    "image-art-director",
    "layout-pptx-feasibility",
    "chart-logic",
    "asset-authenticity",
    "template-fidelity",
    "accessibility-readability",
    "visual-clarity",
)
ALLOWED_SLIDE_COMP_REVIEW_MODES = {"subagent", "main_agent_role_review"}
REALESRGAN_TOOL = "python-realesrganer"
REALESRGAN_ENGINE = "RealESRGANer"
REALESRGAN_MODEL = "RealESRGAN_x4plus"
REALESRGAN_MODEL_FILE = "RealESRGAN_x4plus.pth"
REALESRGAN_DEVICE = "cpu"
REALESRGAN_TILE = 400
REALESRGAN_TILE_PAD = 12
REALESRGAN_PRE_PAD = 0
REALESRGAN_TARGET_WIDTH = 3840
REALESRGAN_TARGET_HEIGHT = 2160
REALESRGAN_ICON_TARGET_MIN = 256
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


def normalized_token(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", "-"))


def nonempty_list(value) -> list:
    if not isinstance(value, list):
        return []
    return [item for item in value if str(item).strip()]


def normalized_text_blob(values: list) -> str:
    tokens = []
    for value in values:
        if isinstance(value, list):
            tokens.extend(normalized_token(item) for item in value if str(item).strip())
        elif isinstance(value, dict):
            tokens.extend(normalized_token(item) for item in value.values() if str(item).strip())
        elif str(value or "").strip():
            tokens.append(normalized_token(value))
    return " | ".join(token for token in tokens if token)


def text_matches_signal(text: str, signal: str) -> bool:
    signal = normalized_token(signal)
    if not signal:
        return False
    if re.fullmatch(r"[a-z0-9-]{1,3}", signal):
        return re.search(rf"(?<![a-z0-9-]){re.escape(signal)}(?![a-z0-9-])", text) is not None
    return signal in text


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


def same_resolved_path(a: Path | None, b: Path | None) -> bool:
    if not a or not b:
        return False
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return str(a) == str(b)


def check_realesrgan_manifest(
    workspace: Path,
    manifest_value: str | None,
    failures: list[str],
    *,
    label: str,
    kind: str,
    expected_output: str | None = None,
) -> dict:
    manifest_path = require_file(workspace, manifest_value, f"{label} Real-ESRGAN manifest", failures)
    if not manifest_path or not manifest_path.exists():
        return {}
    payload = load_json(manifest_path, failures)
    if payload.get("status") not in {"processed", "approved"}:
        failures.append(f"{label} Real-ESRGAN manifest status must be processed or approved")
    if payload.get("tool") != REALESRGAN_TOOL:
        failures.append(f"{label} Real-ESRGAN manifest.tool must be {REALESRGAN_TOOL}")
    if payload.get("kind") != kind:
        failures.append(f"{label} Real-ESRGAN manifest.kind must be {kind}")
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        failures.append(f"{label} Real-ESRGAN manifest must include processed items")
        return payload

    expected_path = resolve_path(workspace, expected_output) if expected_output else None
    matching_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        output_path = resolve_path(workspace, item.get("output_path"))
        if expected_path is None or same_resolved_path(output_path, expected_path):
            matching_items.append((item, output_path))
    if expected_path is not None and not matching_items:
        failures.append(f"{label} Real-ESRGAN manifest does not reference expected output {expected_path}")
        return payload
    if not matching_items:
        failures.append(f"{label} Real-ESRGAN manifest has no valid processed item")
        return payload

    item, output_path = matching_items[0]
    if item.get("status") not in {"processed", "approved"}:
        failures.append(f"{label} Real-ESRGAN item.status must be processed or approved")
    if item.get("kind") != kind:
        failures.append(f"{label} Real-ESRGAN item.kind must be {kind}")
    if item.get("tool") != REALESRGAN_TOOL:
        failures.append(f"{label} Real-ESRGAN item.tool must be {REALESRGAN_TOOL}")
    if item.get("engine") != REALESRGAN_ENGINE:
        failures.append(f"{label} Real-ESRGAN item.engine must be {REALESRGAN_ENGINE}")
    if item.get("backend") != "python":
        failures.append(f"{label} Real-ESRGAN item.backend must be python")
    if item.get("model") != REALESRGAN_MODEL:
        failures.append(f"{label} Real-ESRGAN item.model must be {REALESRGAN_MODEL}")
    if item.get("model_file") != REALESRGAN_MODEL_FILE:
        failures.append(f"{label} Real-ESRGAN item.model_file must be {REALESRGAN_MODEL_FILE}")
    model_path = resolve_path(workspace, item.get("model_path"))
    if not model_path:
        failures.append(f"{label} Real-ESRGAN item.model_path is missing")
    elif not model_path.exists():
        failures.append(f"{label} Real-ESRGAN model_path does not exist: {model_path}")
    elif model_path.name != REALESRGAN_MODEL_FILE:
        failures.append(f"{label} Real-ESRGAN model_path must point to {REALESRGAN_MODEL_FILE}")
    elif item.get("model_sha256") and item.get("model_sha256") != file_sha256(model_path):
        failures.append(f"{label} Real-ESRGAN model_sha256 does not match {model_path}")
    if item.get("device") != REALESRGAN_DEVICE:
        failures.append(f"{label} Real-ESRGAN device must be cpu")
    if item.get("half") is not False:
        failures.append(f"{label} Real-ESRGAN half must be false")
    if safe_int(item.get("scale")) != 4:
        failures.append(f"{label} Real-ESRGAN item.scale must be 4")
    if safe_float(item.get("outscale")) <= 0:
        failures.append(f"{label} Real-ESRGAN item.outscale must be positive")
    if safe_int(item.get("tile")) != REALESRGAN_TILE:
        failures.append(f"{label} Real-ESRGAN tile must be {REALESRGAN_TILE}")
    if safe_int(item.get("tile_pad")) != REALESRGAN_TILE_PAD:
        failures.append(f"{label} Real-ESRGAN tile_pad must be {REALESRGAN_TILE_PAD}")
    if safe_int(item.get("pre_pad")) != REALESRGAN_PRE_PAD:
        failures.append(f"{label} Real-ESRGAN pre_pad must be {REALESRGAN_PRE_PAD}")

    if not output_path:
        failures.append(f"{label} Real-ESRGAN item.output_path is missing")
        return payload
    if not output_path.exists():
        failures.append(f"{label} Real-ESRGAN output file is missing: {output_path}")
        return payload
    expected_sha = item.get("output_sha256")
    if expected_sha and expected_sha != file_sha256(output_path):
        failures.append(f"{label} Real-ESRGAN output_sha256 does not match {output_path}")

    width, height = image_size(output_path)
    declared = item.get("output_px") or {}
    if declared and (safe_int(declared.get("width")) != width or safe_int(declared.get("height")) != height):
        failures.append(f"{label} Real-ESRGAN output_px does not match real image dimensions")
    if kind == "comp":
        target = item.get("target_px") or {}
        if safe_int(target.get("width")) != REALESRGAN_TARGET_WIDTH or safe_int(target.get("height")) != REALESRGAN_TARGET_HEIGHT:
            failures.append(f"{label} Real-ESRGAN target_px must be {REALESRGAN_TARGET_WIDTH}x{REALESRGAN_TARGET_HEIGHT}")
        if width != REALESRGAN_TARGET_WIDTH or height != REALESRGAN_TARGET_HEIGHT:
            failures.append(
                f"{label} Real-ESRGAN comp output must be exactly "
                f"{REALESRGAN_TARGET_WIDTH}x{REALESRGAN_TARGET_HEIGHT}; got {width}x{height}"
            )
    elif kind == "icon":
        if safe_int(item.get("target_min_px")) < REALESRGAN_ICON_TARGET_MIN:
            failures.append(f"{label} Real-ESRGAN icon target_min_px must be at least {REALESRGAN_ICON_TARGET_MIN}")
        if min(width, height) < REALESRGAN_ICON_TARGET_MIN:
            failures.append(f"{label} Real-ESRGAN icon output minimum dimension must be at least {REALESRGAN_ICON_TARGET_MIN}; got {width}x{height}")
    return payload


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


def deck_slide_ids(deck_spec: dict) -> list[str]:
    slides = deck_spec.get("slides") or []
    ids: list[str] = []
    for idx, slide in enumerate(slides, 1):
        slide_id = ""
        if isinstance(slide, dict):
            slide_id = str(slide.get("slide_id") or "").strip()
        ids.append(slide_id or f"slide-{idx:03d}")
    return ids


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


def select_style_profile_route(deck_spec: dict, style_brief: dict, policy: dict) -> dict:
    evidence = style_brief.get("deck_profile_evidence") or {}
    deck = deck_spec.get("deck", {}) if isinstance(deck_spec, dict) else {}
    text = normalized_text_blob(
        [
            style_brief.get("deck_profile"),
            deck.get("deck_profile"),
            evidence.get("primary_profile"),
            evidence.get("secondary_profiles"),
            evidence.get("audience"),
            evidence.get("occasion"),
            evidence.get("source_signals"),
            evidence.get("notes"),
        ]
    )
    for route in policy.get("profile_style_routes") or []:
        if not isinstance(route, dict):
            continue
        profile = normalized_token(route.get("profile"))
        signals = [profile, *nonempty_list(route.get("signals"))]
        if any(text_matches_signal(text, signal) for signal in signals):
            return route
    return {}


def check_style_task_policy(deck_spec: dict, style_brief: dict, failures: list[str]) -> dict:
    deck_profile = normalized_token(style_brief.get("deck_profile") or deck_spec.get("deck", {}).get("deck_profile"))
    evidence = style_brief.get("deck_profile_evidence") or {}
    if not deck_profile and not normalized_token(evidence.get("primary_profile")):
        failures.append("style_brief.json must declare deck_profile or deck_profile_evidence.primary_profile before recommending styles")
    for key in ("primary_profile", "audience", "occasion"):
        if not normalized_token(evidence.get(key)):
            failures.append(f"style_brief.json deck_profile_evidence.{key} is required for task-aware style recommendations")
    if not nonempty_list(evidence.get("source_signals")):
        failures.append("style_brief.json deck_profile_evidence.source_signals must record task/audience/occasion cues")

    policy = style_brief.get("style_recommendation_policy") or {}
    if policy.get("policy_id") != STYLE_TASK_POLICY_ID:
        failures.append(f"style_brief.json style_recommendation_policy.policy_id must be {STYLE_TASK_POLICY_ID}")
    for key in (
        "derive_from_deck_profile",
        "recommended_styles_must_match_deck_profile",
        "ask_before_using_off_profile_styles",
        "off_profile_requires_user_request",
        "fit_reason_required_per_option",
    ):
        if policy.get(key) is not True:
            failures.append(f"style_brief.json style_recommendation_policy.{key} must be true")
    routes = policy.get("profile_style_routes") or []
    if not isinstance(routes, list) or not routes:
        failures.append("style_brief.json style_recommendation_policy.profile_style_routes must be non-empty")
    for idx, route in enumerate(routes, 1):
        if not isinstance(route, dict):
            failures.append(f"style profile route {idx} must be an object")
            continue
        for key in ("profile", "signals", "allowed_style_ids", "allowed_aesthetic_families"):
            if key == "profile":
                if not normalized_token(route.get(key)):
                    failures.append(f"style profile route {idx} missing {key}")
            elif not nonempty_list(route.get(key)):
                failures.append(f"style profile route {idx} missing {key}")
    return select_style_profile_route(deck_spec, style_brief, policy)


def check_style_diversity_contract(style_brief: dict, failures: list[str]) -> dict:
    contract = style_brief.get("diversity_contract") or {}
    if contract.get("policy_id") != STYLE_DIVERSITY_POLICY_ID:
        failures.append(f"style_brief.json diversity_contract.policy_id must be {STYLE_DIVERSITY_POLICY_ID}")
    for key in (
        "forbid_near_identical_contact_sheets",
        "reject_icon_only_or_color_only_variation",
        "require_distinct_style_ids",
        "require_distinct_aesthetic_families",
        "require_distinct_layout_archetypes",
        "require_distinct_evidence_presentation",
        "require_distinct_thumbnail_differentiators",
    ):
        if contract.get(key) is not True:
            failures.append(f"style_brief.json diversity_contract.{key} must be true")
    if safe_int(contract.get("minimum_distinct_axes")) < 5:
        failures.append("style_brief.json diversity_contract.minimum_distinct_axes must be at least 5")
    required_axes = {normalized_token(item) for item in nonempty_list(contract.get("required_axes"))}
    for axis in ("style-id", "aesthetic-family", "layout-archetype", "evidence-presentation", "composition-grammar"):
        if axis not in required_axes:
            failures.append(f"style_brief.json diversity_contract.required_axes must include {axis}")
    return contract


def candidate_off_profile_allowed(candidate: dict, style_brief: dict) -> bool:
    style_id = normalized_token(candidate.get("style_id"))
    family = normalized_token(candidate.get("aesthetic_family"))
    task_fit = candidate.get("task_fit") or {}
    if isinstance(task_fit, dict) and task_fit.get("user_requested_off_profile") is True:
        return True
    prefs = style_brief.get("user_style_preferences") or {}
    requested_ids = {normalized_token(item) for item in nonempty_list(prefs.get("requested_style_ids"))}
    requested_families = {normalized_token(item) for item in nonempty_list(prefs.get("requested_aesthetic_families"))}
    return style_id in requested_ids or family in requested_families


def check_candidate_route_fit(owner: str, candidate: dict, style_brief: dict, route: dict, failures: list[str]) -> None:
    if not route:
        return
    style_source = normalized_token(candidate.get("style_source"))
    if style_source != "built-in-style-library":
        return
    style_id = normalized_token(candidate.get("style_id"))
    family = normalized_token(candidate.get("aesthetic_family"))
    allowed_ids = {normalized_token(item) for item in nonempty_list(route.get("allowed_style_ids"))}
    allowed_families = {normalized_token(item) for item in nonempty_list(route.get("allowed_aesthetic_families"))}
    if style_id in allowed_ids or family in allowed_families:
        return
    if candidate_off_profile_allowed(candidate, style_brief):
        return
    profile = route.get("profile") or "matched profile"
    failures.append(
        f"{owner} style_id/aesthetic_family is off-profile for {profile}; "
        "use a route-approved style or record explicit user_requested_off_profile"
    )


def check_candidate_task_and_diversity_fields(owner: str, candidate: dict, style_brief: dict, route: dict, failures: list[str]) -> None:
    task_fit = candidate.get("task_fit") or {}
    if not isinstance(task_fit, dict):
        failures.append(f"{owner} task_fit must be an object")
        task_fit = {}
    if task_fit.get("profile_match") is not True and not candidate_off_profile_allowed(candidate, style_brief):
        failures.append(f"{owner} task_fit.profile_match must be true unless this was explicitly requested by the user")
    if not normalized_token(task_fit.get("fit_reason") or candidate.get("fit_reason")):
        failures.append(f"{owner} missing task_fit.fit_reason")
    if not nonempty_list(task_fit.get("profile_signals_used")):
        failures.append(f"{owner} task_fit.profile_signals_used must be non-empty")

    for key in ("layout_archetype", "evidence_presentation", "composition_grammar", "density_and_pacing"):
        if not normalized_token(candidate.get(key)):
            failures.append(f"{owner} missing {key}")
    differentiators = candidate.get("thumbnail_differentiators")
    if len(nonempty_list(differentiators)) < 2:
        failures.append(f"{owner} thumbnail_differentiators must list at least 2 visible differences")
    if not normalized_token(candidate.get("must_not_reuse")):
        failures.append(f"{owner} missing must_not_reuse anti-repetition note")
    check_candidate_route_fit(owner, candidate, style_brief, route, failures)


def require_distinct_values(owner: str, values: list[str], count: int, failures: list[str]) -> None:
    cleaned = [normalized_token(value) for value in values if normalized_token(value)]
    if count > 1 and len(set(cleaned)) < min(count, len(cleaned)):
        failures.append(f"candidate directions must use distinct {owner} values")


def check_image_quality_policy(policy, failures: list[str], owner: str) -> dict:
    if not isinstance(policy, dict) or not policy:
        failures.append(f"{owner} image_quality_policy is missing")
        return {}
    if policy.get("enabled") is not True:
        failures.append(f"{owner} image_quality_policy.enabled must be true")
    requested = policy.get("requested_single_slide_canvas_px") or {}
    if safe_int(requested.get("width")) < REALESRGAN_TARGET_WIDTH or safe_int(requested.get("height")) < REALESRGAN_TARGET_HEIGHT:
        failures.append(f"{owner} image_quality_policy.requested_single_slide_canvas_px must target at least 3840x2160")
    minimum = policy.get("minimum_acceptable_comp_px") or {}
    if safe_int(minimum.get("width")) < REALESRGAN_TARGET_WIDTH or safe_int(minimum.get("height")) < REALESRGAN_TARGET_HEIGHT:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_comp_px must be at least 3840x2160")
    if safe_int(policy.get("minimum_acceptable_comp_bytes")) < 1024 * 1024:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_comp_bytes must be at least 1048576")
    post = policy.get("postprocess_policy") or {}
    if not isinstance(post, dict) or not post:
        failures.append(f"{owner} image_quality_policy.postprocess_policy is missing")
    else:
        if post.get("enabled") is not True:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.enabled must be true")
        if post.get("mandatory") is not True:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.mandatory must be true")
        if post.get("normalize_every_comp") is not True:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.normalize_every_comp must be true")
        target = post.get("target_px") or {}
        if safe_int(target.get("width")) != REALESRGAN_TARGET_WIDTH or safe_int(target.get("height")) != REALESRGAN_TARGET_HEIGHT:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.target_px must be 3840x2160")
        if post.get("local_repair_script") != "scripts/realesrgan_upscale.py":
            failures.append(f"{owner} image_quality_policy.postprocess_policy.local_repair_script must be scripts/realesrgan_upscale.py")
        if post.get("upscale_method") != REALESRGAN_TOOL:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.upscale_method must be {REALESRGAN_TOOL}")
        if post.get("realesrgan_backend") != "python":
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_backend must be python")
        if post.get("realesrgan_engine") != REALESRGAN_ENGINE:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_engine must be {REALESRGAN_ENGINE}")
        if post.get("realesrgan_model") != REALESRGAN_MODEL:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_model must be {REALESRGAN_MODEL}")
        if post.get("realesrgan_model_file") != REALESRGAN_MODEL_FILE:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_model_file must be {REALESRGAN_MODEL_FILE}")
        if post.get("realesrgan_device") != REALESRGAN_DEVICE:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_device must be cpu")
        if safe_int(post.get("realesrgan_tile")) != REALESRGAN_TILE:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_tile must be {REALESRGAN_TILE}")
        if safe_int(post.get("realesrgan_tile_pad")) != REALESRGAN_TILE_PAD:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_tile_pad must be {REALESRGAN_TILE_PAD}")
        if safe_int(post.get("realesrgan_pre_pad")) != REALESRGAN_PRE_PAD:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_pre_pad must be {REALESRGAN_PRE_PAD}")
        if post.get("realesrgan_half") is not False:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.realesrgan_half must be false")
        if post.get("same_output_dimensions_required") is not True:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.same_output_dimensions_required must be true")
        if post.get("downstream_uses_realesrgan_comp") is not True:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.downstream_uses_realesrgan_comp must be true")
        if post.get("fallback_allowed_for_postprocess") is not False:
            failures.append(f"{owner} image_quality_policy.postprocess_policy.fallback_allowed_for_postprocess must be false")
    if policy.get("prompt_requires_crisp_text_and_icons") is not True:
        failures.append(f"{owner} image_quality_policy.prompt_requires_crisp_text_and_icons must be true")
    if policy.get("review_required_before_pptx") is not True:
        failures.append(f"{owner} image_quality_policy.review_required_before_pptx must be true")
    return policy


def check_style_gate(workspace: Path, deck_spec: dict, slide_intent_plan: dict, narrative_plan: dict, design_system: dict, style_brief: dict, failures: list[str]) -> None:
    check_no_html_surrogates(workspace, failures)
    check_image_quality_policy(style_brief.get("image_quality_policy"), failures, "style_brief.json")
    matched_profile_route = check_style_task_policy(deck_spec, style_brief, failures)
    diversity_contract = check_style_diversity_contract(style_brief, failures)
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
    style_ids = []
    families = []
    layout_archetypes = []
    evidence_presentations = []
    composition_grammars = []
    for idx, candidate in enumerate(candidates, 1):
        check_style_source_fields(f"candidate direction {idx}", candidate, failures)
        check_candidate_task_and_diversity_fields(f"candidate direction {idx}", candidate, style_brief, matched_profile_route, failures)
        if candidate.get("option_id"):
            candidate_options.add(str(candidate.get("option_id")))
        if candidate.get("style_id"):
            style_ids.append(str(candidate.get("style_id")))
        if candidate.get("aesthetic_family"):
            families.append(str(candidate.get("aesthetic_family")))
        else:
            failures.append(f"candidate direction {idx} missing aesthetic_family")
        if candidate.get("layout_archetype"):
            layout_archetypes.append(str(candidate.get("layout_archetype")))
        if candidate.get("evidence_presentation"):
            evidence_presentations.append(str(candidate.get("evidence_presentation")))
        if candidate.get("composition_grammar"):
            composition_grammars.append(str(candidate.get("composition_grammar")))
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
    if diversity_contract.get("require_distinct_style_ids", True):
        require_distinct_values("style_id", style_ids, count, failures)
    if diversity_contract.get("require_distinct_aesthetic_families", True):
        require_distinct_values("aesthetic_family", families, count, failures)
    if diversity_contract.get("require_distinct_layout_archetypes", True):
        require_distinct_values("layout_archetype", layout_archetypes, count, failures)
    if diversity_contract.get("require_distinct_evidence_presentation", True):
        require_distinct_values("evidence_presentation", evidence_presentations, count, failures)
    require_distinct_values("composition_grammar", composition_grammars, count, failures)
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
            for key in ("layout_archetype", "evidence_presentation", "composition_grammar"):
                if not normalized_token(raw_sheet.get(key)):
                    failures.append(f"style contact sheet {idx} missing {key}")
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
    if policy.get("realesrgan_upscale_script") != "scripts/realesrgan_upscale.py":
        failures.append("visual_contract.json conversion_policy.realesrgan_upscale_script must be scripts/realesrgan_upscale.py")
    require_file(workspace, "scripts/realesrgan_upscale.py", "scripts/realesrgan_upscale.py", failures)
    if policy.get("realesrgan_backend") != "python":
        failures.append("visual_contract.json conversion_policy.realesrgan_backend must be python")
    if policy.get("realesrgan_engine") != REALESRGAN_ENGINE:
        failures.append(f"visual_contract.json conversion_policy.realesrgan_engine must be {REALESRGAN_ENGINE}")
    if policy.get("realesrgan_model_file") != REALESRGAN_MODEL_FILE:
        failures.append(f"visual_contract.json conversion_policy.realesrgan_model_file must be {REALESRGAN_MODEL_FILE}")
    if policy.get("realesrgan_device") != REALESRGAN_DEVICE:
        failures.append("visual_contract.json conversion_policy.realesrgan_device must be cpu")
    if safe_int(policy.get("realesrgan_tile")) != REALESRGAN_TILE:
        failures.append(f"visual_contract.json conversion_policy.realesrgan_tile must be {REALESRGAN_TILE}")
    if safe_int(policy.get("realesrgan_tile_pad")) != REALESRGAN_TILE_PAD:
        failures.append(f"visual_contract.json conversion_policy.realesrgan_tile_pad must be {REALESRGAN_TILE_PAD}")
    if safe_int(policy.get("realesrgan_pre_pad")) != REALESRGAN_PRE_PAD:
        failures.append(f"visual_contract.json conversion_policy.realesrgan_pre_pad must be {REALESRGAN_PRE_PAD}")
    if policy.get("realesrgan_half") is not False:
        failures.append("visual_contract.json conversion_policy.realesrgan_half must be false")
    basis = policy.get("basis_px") or {}
    if safe_int(basis.get("width")) != 1920 or safe_int(basis.get("height")) != 1080:
        failures.append("visual_contract.json conversion_policy.basis_px must be 1920x1080")
    required_true = (
        "source_image_is_measurement_target",
        "source_comp_realesrgan_4k_required",
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
        "icon_realesrgan_upscale_required",
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
        "realesrgan_upscale_required",
        "feathered_slices_preserve_alpha",
    ):
        if policy.get(key) is not True:
            failures.append(f"visual_contract.json strict_icon_policy.{key} must be true")
    if policy.get("icon_upscale_method") != REALESRGAN_TOOL:
        failures.append(f"visual_contract.json strict_icon_policy.icon_upscale_method must be {REALESRGAN_TOOL}")
    if policy.get("realesrgan_backend") != "python":
        failures.append("visual_contract.json strict_icon_policy.realesrgan_backend must be python")
    if policy.get("realesrgan_engine") != REALESRGAN_ENGINE:
        failures.append(f"visual_contract.json strict_icon_policy.realesrgan_engine must be {REALESRGAN_ENGINE}")
    if policy.get("realesrgan_model") != REALESRGAN_MODEL:
        failures.append(f"visual_contract.json strict_icon_policy.realesrgan_model must be {REALESRGAN_MODEL}")
    if policy.get("realesrgan_model_file") != REALESRGAN_MODEL_FILE:
        failures.append(f"visual_contract.json strict_icon_policy.realesrgan_model_file must be {REALESRGAN_MODEL_FILE}")
    if policy.get("realesrgan_device") != REALESRGAN_DEVICE:
        failures.append("visual_contract.json strict_icon_policy.realesrgan_device must be cpu")
    if safe_int(policy.get("realesrgan_tile")) != REALESRGAN_TILE:
        failures.append(f"visual_contract.json strict_icon_policy.realesrgan_tile must be {REALESRGAN_TILE}")
    if safe_int(policy.get("realesrgan_tile_pad")) != REALESRGAN_TILE_PAD:
        failures.append(f"visual_contract.json strict_icon_policy.realesrgan_tile_pad must be {REALESRGAN_TILE_PAD}")
    if safe_int(policy.get("realesrgan_pre_pad")) != REALESRGAN_PRE_PAD:
        failures.append(f"visual_contract.json strict_icon_policy.realesrgan_pre_pad must be {REALESRGAN_PRE_PAD}")
    if policy.get("realesrgan_half") is not False:
        failures.append("visual_contract.json strict_icon_policy.realesrgan_half must be false")
    if policy.get("icon_upscale_script") != "scripts/realesrgan_upscale.py":
        failures.append("visual_contract.json strict_icon_policy.icon_upscale_script must be scripts/realesrgan_upscale.py")
    if policy.get("placement_source_dir") != "icons/upscaled":
        failures.append("visual_contract.json strict_icon_policy.placement_source_dir must be icons/upscaled")
    if safe_int(policy.get("minimum_output_icon_min_dim_px")) < 256:
        failures.append("visual_contract.json strict_icon_policy.minimum_output_icon_min_dim_px must be at least 256")
    if safe_int(policy.get("icon_hd_target_min_px")) < 256:
        failures.append("visual_contract.json strict_icon_policy.icon_hd_target_min_px must be at least 256")
    manifest_path = require_file(workspace, policy.get("manifest_path") or "icons/icon_jobs.json", "icon jobs manifest", failures)
    if manifest_path and manifest_path.exists():
        manifest = load_json(manifest_path, failures)
        if manifest.get("status") not in {"draft", "ready", "processed", "approved", "not_applicable"}:
            failures.append("icon jobs manifest status must be draft, ready, processed, approved, or not_applicable")
        for key in (
            "realesrgan_upscale_required",
            "icon_upscale_method",
            "realesrgan_backend",
            "realesrgan_engine",
            "realesrgan_model",
            "realesrgan_model_file",
            "realesrgan_model_path",
            "realesrgan_device",
            "realesrgan_tile",
            "realesrgan_tile_pad",
            "realesrgan_pre_pad",
            "realesrgan_half",
            "icon_upscale_script",
            "icon_upscale_manifest_path",
            "placement_source_dir",
        ):
            if policy.get(key) != manifest.get(key):
                failures.append(f"icon jobs manifest {key} must match visual_contract.json strict_icon_policy")


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


def check_slide_comp_review_policy(visual_contract: dict, failures: list[str]) -> dict:
    policy = visual_contract.get("slide_comp_review_policy") or {}
    if not isinstance(policy, dict) or not policy:
        failures.append("visual_contract.json slide_comp_review_policy is missing")
        return {}
    if policy.get("enabled") is not True:
        failures.append("visual_contract.json slide_comp_review_policy.enabled must be true")
    if policy.get("required_before_pptx") is not True:
        failures.append("visual_contract.json slide_comp_review_policy.required_before_pptx must be true")
    if policy.get("require_subagent_review") is not True:
        failures.append("visual_contract.json slide_comp_review_policy.require_subagent_review must be true")
    if policy.get("evidence_dir") != "qa/reviews/slide-comp":
        failures.append("visual_contract.json slide_comp_review_policy.evidence_dir must be qa/reviews/slide-comp")
    if policy.get("block_on_unresolved_p0_p1") is not True:
        failures.append("visual_contract.json slide_comp_review_policy.block_on_unresolved_p0_p1 must be true")
    required_roles = set(policy.get("required_roles") or [])
    missing = [role for role in SLIDE_COMP_REVIEW_ROLES if role not in required_roles]
    if missing:
        failures.append("visual_contract.json slide_comp_review_policy.required_roles missing: " + ", ".join(missing))
    return policy


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
        check_slide_comp_review_policy(visual_contract, failures)
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
                elif width != REALESRGAN_TARGET_WIDTH or height != REALESRGAN_TARGET_HEIGHT:
                    failures.append(
                        f"slide {idx:03d} approved comp must be exact Real-ESRGAN 4K "
                        f"{REALESRGAN_TARGET_WIDTH}x{REALESRGAN_TARGET_HEIGHT}; got {width}x{height}: {path}"
                    )
            if minimum_bytes and path.exists() and path.stat().st_size < minimum_bytes:
                failures.append(f"slide {idx:03d} approved comp file must be at least {minimum_bytes} bytes; got {path.stat().st_size}: {path}")
            check_realesrgan_manifest(
                workspace,
                slide.get("upscale_manifest_path") or (slide.get("clarity_review") or {}).get("upscale_manifest_path"),
                failures,
                label=f"slide {idx:03d} approved comp",
                kind="comp",
                expected_output=comp,
            )
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
            dims = clarity.get("image_dimensions_px") or {}
            if dims and (safe_int(dims.get("width")) != REALESRGAN_TARGET_WIDTH or safe_int(dims.get("height")) != REALESRGAN_TARGET_HEIGHT):
                failures.append(f"slide {idx:03d} clarity_review.image_dimensions_px must be 3840x2160 after Real-ESRGAN")
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
    if tool_files.get("realesrgan_upscale") != "scripts/realesrgan_upscale.py":
        failures.append("conversion_manifest.json tool_files.realesrgan_upscale must be scripts/realesrgan_upscale.py")
    require_file(workspace, "scripts/realesrgan_upscale.py", "scripts/realesrgan_upscale.py", failures)
    if isinstance(copied, dict) and copied.get("scripts/realesrgan_upscale.py") is not True:
        failures.append("conversion_manifest.json tool_files.copied_to_workspace.scripts/realesrgan_upscale.py must be true")
    page_modules = manifest.get("page_modules") or {}
    if is_direct_conversion_mode(deck_spec.get("deck", {}).get("mode", "")):
        for key in ("enabled", "per_slide_pptx_required", "merge_after_page_approval"):
            if page_modules.get(key) is not True:
                failures.append(f"conversion_manifest.json page_modules.{key} must be true in direct conversion mode")
    global_rules = manifest.get("global_rules") or {}
    required_true = (
        "source_image_is_measurement_target_not_final_layer",
        "source_comp_realesrgan_4k_required",
        "full_image_or_region_layers_forbidden",
        "ordinary_table_or_card_rebuild_forbidden",
        "native_text_shapes_charts_required",
        "hidden_text_layer_does_not_count_as_editable",
        "strict_icon_extraction_required",
        "icon_contact_sheet_audit_required",
        "source_icon_inventory_required",
        "real_source_icons_must_be_extracted",
        "native_redraw_for_named_pictograms_forbidden",
        "icon_hd_enhancement_required",
        "icon_realesrgan_upscale_required",
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
        if path and path.exists():
            width, height = image_size(path)
            if width != REALESRGAN_TARGET_WIDTH or height != REALESRGAN_TARGET_HEIGHT:
                failures.append(
                    f"conversion slide {idx:03d} source image must be exact Real-ESRGAN 4K "
                    f"{REALESRGAN_TARGET_WIDTH}x{REALESRGAN_TARGET_HEIGHT}; got {width}x{height}: {path}"
                )
        check_realesrgan_manifest(
            workspace,
            slide.get("upscale_manifest_path"),
            failures,
            label=f"conversion slide {idx:03d} source image",
            kind="comp",
            expected_output=source_path,
        )
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
            check_realesrgan_manifest(
                workspace,
                slide.get("icon_upscale_manifest_path"),
                failures,
                label=f"conversion slide {idx:03d} icons",
                kind="icon",
            )
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


def check_reviews(workspace: Path, deck_spec: dict, visual_contract: dict, failures: list[str]) -> None:
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    expected_slide_ids = deck_slide_ids(deck_spec)
    slide_review_dir = workspace / "qa" / "reviews" / "slide-comp"
    review_files = list(slide_review_dir.glob("*.json")) if slide_review_dir.exists() else []
    if expected_count and len(review_files) < expected_count:
        failures.append(f"slide-comp review JSON files are missing: found {len(review_files)}, expected at least {expected_count}")

    contract_comp_by_slide = {}
    for idx, slide in enumerate(visual_contract.get("slides") or [], 1):
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("slide_id") or f"slide-{idx:03d}")
        contract_comp_by_slide[slide_id] = slide.get("comp_path") or slide.get("approved_comp_path")

    reviews_by_slide: dict[str, list[tuple[Path, dict]]] = {}
    for path in sorted(review_files):
        payload = load_json(path, failures)
        if not payload:
            continue
        slide_id = str(payload.get("slide_id") or path.stem).strip()
        reviews_by_slide.setdefault(slide_id, []).append((path, payload))

    for slide_id in expected_slide_ids:
        reviews = reviews_by_slide.get(slide_id, [])
        if not reviews:
            failures.append(f"missing slide-comp review JSON for {slide_id}")
            continue
        if len(reviews) > 1:
            failures.append(f"multiple slide-comp review JSON files found for {slide_id}; keep one approved review artifact")
        review_path, review = reviews[-1]
        label = review_path.relative_to(workspace)
        if review.get("review_type") != "slide_comp":
            failures.append(f"{label} review_type must be slide_comp")
        if review.get("stage") not in {"slide_comp", "slide_comp_review"}:
            failures.append(f"{label} stage must be slide_comp or slide_comp_review")
        if review.get("subagent_review_required") is not True:
            failures.append(f"{label} subagent_review_required must be true")
        mode = review.get("reviewer_mode")
        if mode not in ALLOWED_SLIDE_COMP_REVIEW_MODES:
            failures.append(f"{label} reviewer_mode must be one of {sorted(ALLOWED_SLIDE_COMP_REVIEW_MODES)}")
        if mode == "main_agent_role_review" and not str(review.get("subagent_fallback_reason") or "").strip():
            failures.append(f"{label} main_agent_role_review requires subagent_fallback_reason")
        if review.get("overall_status") != "approved":
            failures.append(f"{label} overall_status must be approved")
        if review.get("approval_to_advance") is not True:
            failures.append(f"{label} approval_to_advance must be true")
        if review.get("unresolved_p0_p1"):
            failures.append(f"{label} unresolved_p0_p1 must be empty")
        required_roles = set(review.get("required_roles") or [])
        missing_required = [role for role in SLIDE_COMP_REVIEW_ROLES if role not in required_roles]
        if missing_required:
            failures.append(f"{label} required_roles missing: {', '.join(missing_required)}")

        role_reviews = review.get("role_reviews") or []
        if not isinstance(role_reviews, list):
            failures.append(f"{label} role_reviews must be a list")
            role_reviews = []
        roles_seen: dict[str, dict] = {}
        for role_review in role_reviews:
            if not isinstance(role_review, dict):
                failures.append(f"{label} role_reviews entries must be objects")
                continue
            role = str(role_review.get("role") or "").strip()
            if not role:
                failures.append(f"{label} role_reviews entry missing role")
                continue
            roles_seen[role] = role_review
            if role_review.get("approval_to_advance") is not True:
                failures.append(f"{label} role {role} approval_to_advance must be true")
            if role_review.get("stage") not in {None, "", "slide_comp", "slide_comp_review"}:
                failures.append(f"{label} role {role} stage must be slide_comp or slide_comp_review")
            for finding in role_review.get("findings") or []:
                if not isinstance(finding, dict):
                    continue
                if finding.get("severity") in {"P0", "P1"}:
                    failures.append(f"{label} role {role} still has blocking {finding.get('severity')} finding")
        missing_roles = [role for role in SLIDE_COMP_REVIEW_ROLES if role not in roles_seen]
        if missing_roles:
            failures.append(f"{label} role_reviews missing: {', '.join(missing_roles)}")

        approved_comp = review.get("approved_comp_path")
        approved_path = require_file(workspace, approved_comp, f"{slide_id} approved comp referenced by slide-comp review", failures)
        contract_comp = contract_comp_by_slide.get(slide_id)
        if approved_path and contract_comp:
            contract_path = resolve_path(workspace, contract_comp)
            if contract_path and approved_path.resolve() != contract_path.resolve():
                failures.append(f"{label} approved_comp_path does not match visual_contract.json for {slide_id}")


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
            check_reviews(workspace, deck_spec, visual_contract, failures)
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
