#!/usr/bin/env python3
"""Validate hard gates for the ImageGen-to-PPTX pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path


COMP_RE = re.compile(r"slide[-_]\d{1,3}.*comp\.(png|jpg|jpeg)$", re.IGNORECASE)
CONTENT_STYLE_TERMS = (
    "evidence",
    "proof",
    "risk-system",
    "system-map",
    "command-center",
    "growth",
    "maturity",
    "roadmap",
    "achievement",
    "operating",
    "dossier",
    "证据",
    "证明",
    "风控",
    "风险",
    "系统图",
    "经营",
    "驾驶舱",
    "成长",
    "成熟",
    "路线",
    "成果",
)
REQUIRED_RETRY_PRESERVED_FIELDS = (
    "locked_slide_order",
    "slide_titles",
    "core_claims",
    "required_data",
    "proof_object_intent",
    "template_constraints",
    "visual_density_floor",
    "aesthetic_family",
)
RETRY_FAILURE_CLASSES = {
    "server_error",
    "service_error",
    "timeout",
    "prompt_too_large",
    "wrong_asset_type",
    "low_resolution",
    "blur",
    "other",
}
RETRY_FINAL_STATUSES = {"retry_pending", "generated", "blocked_imagegen_failure"}
RETRY_NEXT_ACTIONS = {"retry_imagegen", "blocked_ask_user", "regenerate_asset", "accept_generated"}
RETRY_DEGRADATION_FLAGS = (
    "removed_locked_content",
    "reduced_content_density",
    "reduced_visual_density",
    "reduced_visual_complexity",
    "used_html_surrogate",
    "used_browser_surrogate",
    "switched_to_generic_ppt",
)
REQUIRED_FAILURE_POLICY_PRESERVE = (
    "locked slide order",
    "slide titles",
    "core claims",
    "required data",
    "proof-object intent",
    "template constraints",
    "visual density floor",
    "aesthetic family",
)


def load_json(path: Path, failures: list[str]) -> dict:
    if not path.exists():
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


def list_paths(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                path = item.get("path") or item.get("contact_sheet") or item.get("file")
                if path:
                    result.append(path)
        return result
    return []


def require_file(workspace: Path, value: str | None, label: str, failures: list[str]) -> Path | None:
    path = resolve_path(workspace, value)
    if path is None:
        failures.append(f"Missing path for {label}")
        return None
    if not path.exists():
        failures.append(f"Missing file for {label}: {path}")
    return path


def image_size(path: Path) -> tuple[int, int]:
    """Read PNG/JPEG dimensions without external dependencies."""
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
                    if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"}:
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
        for html_path in folder.rglob("*"):
            if html_path.suffix.lower() in {".html", ".htm"}:
                failures.append(
                    f"HTML/CSS/browser surrogate artifact is forbidden in ImageGen pipeline: {html_path}"
                )


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
            failures.append(
                f"{label} appears backed by an HTML/browser blueprint, not a direct ImageGen image: {candidate}"
            )


def stage_names(pipeline_state: dict) -> set[str]:
    return {
        item.get("stage", "")
        for item in pipeline_state.get("stage_history", [])
        if isinstance(item, dict)
    }


def workflow_mode(pipeline_state: dict, deck_spec: dict) -> str:
    return deck_spec.get("deck", {}).get("mode") or pipeline_state.get("mode") or ""


def is_reconstruction_mode(mode: str) -> bool:
    return mode in {"reconstruction-only", "repair-existing-pptx"}


def deck_spec_fingerprint(deck_spec: dict) -> str:
    """Stable fingerprint of content fields style lanes may not mutate."""
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
        failures.append(
            "slide_intent_plan.json source_deck_spec_fingerprint does not match current deck_spec.json; "
            f"expected {fingerprint}"
        )
    matrix_path = require_file(
        workspace,
        slide_intent_plan.get("matrix_path") or "slide_intent_matrix.md",
        "slide intent matrix",
        failures,
    )
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
        evidence = slide.get("evidence_candidates") or []
        assumptions = slide.get("accepted_assumptions") or []
        if not evidence and not assumptions:
            failures.append(
                f"slide intent {idx:03d} must have evidence_candidates or accepted_assumptions"
            )
        if slide.get("status") not in {"confirmed", "accepted_assumption"}:
            failures.append(
                f"slide intent {idx:03d} status must be confirmed or accepted_assumption"
            )
    if slide_intent_plan.get("open_questions"):
        failures.append("slide_intent_plan.json still has open_questions")
    if slide_intent_plan.get("review_status") not in {"approved", "user_accepted_risk"}:
        failures.append("slide_intent_plan.json review_status must be approved or user_accepted_risk")


def check_narrative_lock(
    workspace: Path,
    deck_spec: dict,
    slide_intent_plan: dict,
    narrative_plan: dict,
    failures: list[str],
) -> None:
    fingerprint = deck_spec_fingerprint(deck_spec)
    if narrative_plan.get("lock_state") != "locked":
        failures.append("narrative_plan.json lock_state must be locked before visual style generation")
    if narrative_plan.get("source_deck_spec_fingerprint") != fingerprint:
        failures.append(
            "narrative_plan.json source_deck_spec_fingerprint does not match current deck_spec.json; "
            f"expected {fingerprint}"
        )
    selected = narrative_plan.get("selected_narrative_id")
    if not selected:
        failures.append("narrative_plan.json selected_narrative_id is empty")
    if narrative_plan.get("slide_intent_plan") != "slide_intent_plan.json":
        failures.append("narrative_plan.json slide_intent_plan must be slide_intent_plan.json")
    if narrative_plan.get("slide_intent_lock_state") != "locked":
        failures.append("narrative_plan.json slide_intent_lock_state must be locked")
    if slide_intent_plan.get("lock_state") != "locked":
        failures.append("slide_intent_plan.json must be locked before narrative_plan.json can be locked")
    option_ids = {
        item.get("narrative_id")
        for item in narrative_plan.get("narrative_options", [])
        if isinstance(item, dict)
    }
    if selected and option_ids and selected not in option_ids:
        failures.append(f"narrative_plan.json selected_narrative_id {selected!r} is not in narrative_options")
    matrix_path = require_file(workspace, narrative_plan.get("matrix_path") or "narrative_matrix.md", "narrative matrix", failures)
    if matrix_path and matrix_path.name != "narrative_matrix.md":
        failures.append("narrative matrix should be named narrative_matrix.md")
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slides = narrative_plan.get("slides", [])
    if expected_count and len(slides) != expected_count:
        failures.append(f"narrative_plan.json has {len(slides)} slides but deck_spec expects {expected_count}")
    deck_slide_ids = [slide.get("slide_id") for slide in deck_spec.get("slides", []) if slide.get("slide_id")]
    narrative_slide_ids = [slide.get("slide_id") for slide in slides if isinstance(slide, dict)]
    if deck_slide_ids and narrative_slide_ids != deck_slide_ids:
        failures.append("narrative_plan.json slide order must match deck_spec.json")
    for idx, slide in enumerate(slides, 1):
        treatment = slide.get("selected_treatment", {}) if isinstance(slide, dict) else {}
        if not treatment:
            failures.append(f"narrative slide {idx:03d} missing selected_treatment")
            continue
        if not slide.get("confirmed_core_idea"):
            failures.append(f"narrative slide {idx:03d} missing confirmed_core_idea from slide_intent_plan.json")
        if treatment.get("narrative_id") != selected:
            failures.append(f"narrative slide {idx:03d} selected_treatment.narrative_id must match selected_narrative_id")
        for key in ("presentation_strategy", "content_to_show", "proof_object_expression", "must_preserve"):
            if not treatment.get(key):
                failures.append(f"narrative slide {idx:03d} selected_treatment missing {key}")
    if narrative_plan.get("open_questions"):
        failures.append("narrative_plan.json still has open_questions")
    if narrative_plan.get("review_status") not in {"approved", "user_accepted_risk"}:
        failures.append("narrative_plan.json review_status must be approved or user_accepted_risk")


def has_built_in_taste_source(taste_guidance: dict) -> bool:
    sources = taste_guidance.get("sources") or []
    if not isinstance(sources, list):
        return False
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("name") == "built-in-ppt-taste-system":
            return True
        if source.get("path") == "references/taste-system.md":
            return True
    return False


def safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def check_image_quality_policy(policy, failures: list[str], owner: str) -> dict:
    if not isinstance(policy, dict) or not policy:
        failures.append(f"{owner} image_quality_policy is missing")
        return {}
    if policy.get("enabled") is not True:
        failures.append(f"{owner} image_quality_policy.enabled must be true")
    if policy.get("prompt_detail_level") not in {"highest_available", "maximum", "max"}:
        failures.append(f"{owner} image_quality_policy.prompt_detail_level must request highest_available quality")
    requested = policy.get("requested_single_slide_canvas_px") or {}
    if safe_int(requested.get("width")) < 3840 or safe_int(requested.get("height")) < 2160:
        failures.append(f"{owner} image_quality_policy.requested_single_slide_canvas_px must target at least 3840x2160")
    minimum = policy.get("minimum_acceptable_comp_px") or {}
    if safe_int(minimum.get("width")) < 3840 or safe_int(minimum.get("height")) < 2160:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_comp_px must be at least 3840x2160")
    if safe_int(policy.get("minimum_acceptable_comp_bytes")) < 5 * 1024 * 1024:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_comp_bytes must be at least 5242880")
    contact_min = policy.get("minimum_acceptable_contact_sheet_px") or {}
    if safe_int(contact_min.get("width")) < 2400 or safe_int(contact_min.get("height")) < 1350:
        failures.append(f"{owner} image_quality_policy.minimum_acceptable_contact_sheet_px must be at least 2400x1350")
    if policy.get("prompt_requires_crisp_text_and_icons") is not True:
        failures.append(f"{owner} image_quality_policy.prompt_requires_crisp_text_and_icons must be true")
    if policy.get("review_required_before_pptx") is not True:
        failures.append(f"{owner} image_quality_policy.review_required_before_pptx must be true")
    if not policy.get("small_text_policy"):
        failures.append(f"{owner} image_quality_policy.small_text_policy is missing")
    criteria = policy.get("blur_rejection_criteria") or []
    if not isinstance(criteria, list) or len(criteria) < 3:
        failures.append(f"{owner} image_quality_policy.blur_rejection_criteria must list at least 3 rejection criteria")
    return policy


def check_imagegen_failure_policy(policy, failures: list[str], owner: str) -> dict:
    if not isinstance(policy, dict) or not policy:
        failures.append(f"{owner} imagegen_failure_policy is missing")
        return {}
    if policy.get("enabled") is not True:
        failures.append(f"{owner} imagegen_failure_policy.enabled must be true")
    if policy.get("fail_closed") is not True:
        failures.append(f"{owner} imagegen_failure_policy.fail_closed must be true")
    if safe_int(policy.get("max_retries_per_asset")) < 1:
        failures.append(f"{owner} imagegen_failure_policy.max_retries_per_asset must be at least 1")
    if policy.get("prompt_compression_allowed") is not True:
        failures.append(f"{owner} imagegen_failure_policy.prompt_compression_allowed must be true")
    for key in (
        "content_density_may_be_reduced",
        "visual_complexity_may_be_reduced",
        "html_surrogate_allowed",
        "generic_ppt_fallback_allowed",
    ):
        if policy.get(key) is not False:
            failures.append(f"{owner} imagegen_failure_policy.{key} must be false")
    if policy.get("block_after_repeated_failures") is not True:
        failures.append(f"{owner} imagegen_failure_policy.block_after_repeated_failures must be true")
    preserve = policy.get("prompt_compression_must_preserve") or []
    preserve_text = {str(item).strip().lower() for item in preserve if item}
    for required in REQUIRED_FAILURE_POLICY_PRESERVE:
        if required.lower() not in preserve_text:
            failures.append(
                f"{owner} imagegen_failure_policy.prompt_compression_must_preserve missing {required!r}"
            )
    if not policy.get("retry_log_path"):
        failures.append(f"{owner} imagegen_failure_policy.retry_log_path is missing")
    return policy


def ready_style_asset_ids(style_brief: dict) -> set[str]:
    ready: set[str] = set()
    ready_statuses = {"generated", "ready_for_user", "selected", "approved"}
    for lane in style_brief.get("style_lanes") or []:
        if not isinstance(lane, dict) or lane.get("status") not in ready_statuses:
            continue
        for key in ("asset_id", "style_lane_id", "option_id", "output_path"):
            value = lane.get(key)
            if value:
                ready.add(str(value))
    for sheet in style_brief.get("style_contact_sheets") or []:
        if not isinstance(sheet, dict):
            continue
        for key in ("asset_id", "style_lane_id", "option_id", "path", "output_path"):
            value = sheet.get(key)
            if value:
                ready.add(str(value))
    return ready


def load_imagegen_retry_log(workspace: Path, style_brief: dict, policy: dict, failures: list[str]) -> dict:
    embedded = style_brief.get("imagegen_retry_log")
    if isinstance(embedded, dict):
        return embedded
    retry_log_ref = embedded or policy.get("retry_log_path")
    if not retry_log_ref:
        return {}
    path = resolve_path(workspace, retry_log_ref)
    if path is None:
        return {}
    if not path.exists():
        failures.append(f"imagegen retry log is referenced but missing: {path}")
        return {}
    return load_json(path, failures)


def check_imagegen_retry_log(workspace: Path, style_brief: dict, policy: dict, failures: list[str]) -> None:
    retry_log = load_imagegen_retry_log(workspace, style_brief, policy, failures)
    if not retry_log:
        return
    attempts = retry_log.get("attempts") or []
    if not isinstance(attempts, list):
        failures.append("imagegen_retry_log.json attempts must be a list")
        return
    ready_assets = ready_style_asset_ids(style_brief)
    max_retries = safe_int(policy.get("max_retries_per_asset")) or 1
    max_attempt_by_asset: dict[str, int] = {}
    for idx, attempt in enumerate(attempts, 1):
        if not isinstance(attempt, dict):
            failures.append(f"imagegen retry attempt {idx} must be an object")
            continue
        asset_id = str(attempt.get("asset_id") or "").strip()
        if not asset_id:
            failures.append(f"imagegen retry attempt {idx} missing asset_id")
        stage = attempt.get("stage")
        if stage not in {"style-contact-sheet", "single-slide-comp"}:
            failures.append(f"imagegen retry attempt {idx} stage is invalid: {stage!r}")
        attempt_index = safe_int(attempt.get("attempt_index"))
        if attempt_index < 1:
            failures.append(f"imagegen retry attempt {idx} attempt_index must be at least 1")
        elif asset_id:
            max_attempt_by_asset[asset_id] = max(max_attempt_by_asset.get(asset_id, 0), attempt_index)
        failure_class = attempt.get("failure_class")
        if failure_class not in RETRY_FAILURE_CLASSES:
            failures.append(f"imagegen retry attempt {idx} failure_class is invalid: {failure_class!r}")
        next_action = attempt.get("next_action")
        if next_action not in RETRY_NEXT_ACTIONS:
            failures.append(f"imagegen retry attempt {idx} next_action is invalid: {next_action!r}")
        final_status = attempt.get("final_status")
        if final_status not in RETRY_FINAL_STATUSES:
            failures.append(f"imagegen retry attempt {idx} final_status is invalid: {final_status!r}")
        for flag in RETRY_DEGRADATION_FLAGS:
            if attempt.get(flag) is True:
                failures.append(f"imagegen retry attempt {idx} used forbidden downgrade flag: {flag}")
        if attempt.get("used_html_surrogate") is True or attempt.get("used_browser_surrogate") is True:
            failures.append(f"imagegen retry attempt {idx} cannot use HTML/browser output after ImageGen failure")
        if attempt.get("switched_to_generic_ppt") is True:
            failures.append(f"imagegen retry attempt {idx} cannot switch to a generic PPT fallback")
        if final_status in {"retry_pending", "blocked_imagegen_failure"} and asset_id in ready_assets:
            failures.append(
                f"imagegen retry attempt {idx} leaves asset {asset_id!r} unresolved but it is marked ready/selected"
            )
        compression_strategy = str(attempt.get("compression_strategy") or "").strip()
        retry_prompt_path = attempt.get("retry_prompt_path")
        if compression_strategy or retry_prompt_path:
            preserved = attempt.get("compression_preserved") or {}
            if not isinstance(preserved, dict):
                failures.append(f"imagegen retry attempt {idx} compression_preserved must be an object")
                preserved = {}
            for field in REQUIRED_RETRY_PRESERVED_FIELDS:
                if preserved.get(field) is not True:
                    failures.append(f"imagegen retry attempt {idx} compression_preserved.{field} must be true")
        for path_key in ("original_prompt_path", "retry_prompt_path"):
            value = attempt.get(path_key)
            if value:
                require_file(workspace, value, f"imagegen retry attempt {idx} {path_key}", failures)
    for asset_id, max_attempt in max_attempt_by_asset.items():
        if max_attempt > max_retries:
            failures.append(
                f"imagegen retry asset {asset_id!r} exceeded max_retries_per_asset={max_retries}; "
                f"highest attempt_index={max_attempt}"
            )


def check_style_gate(
    workspace: Path,
    deck_spec: dict,
    slide_intent_plan: dict,
    narrative_plan: dict,
    design_system: dict,
    style_brief: dict,
    failures: list[str],
) -> None:
    count = style_brief.get("direction_count") or 0
    selection_mode = style_brief.get("selection_mode")
    generation_mode = style_brief.get("generation_mode")
    deck_profile = deck_spec.get("deck", {}).get("deck_profile")
    if deck_profile and style_brief.get("deck_profile") and style_brief.get("deck_profile") != deck_profile:
        failures.append(
            "style_brief.json deck_profile does not match deck_spec.json: "
            f"{style_brief.get('deck_profile')!r} != {deck_profile!r}"
        )
    if deck_profile and not style_brief.get("deck_profile"):
        failures.append("style_brief.json deck_profile is missing")
    design_taste = design_system.get("taste_guidance", {})
    style_taste = style_brief.get("taste_guidance", {})
    if design_taste.get("enabled") is not True:
        failures.append("design_system.json taste_guidance.enabled must be true for style exploration")
    if style_taste.get("enabled") is not True:
        failures.append("style_brief.json taste_guidance.enabled must be true for style exploration")
    if not has_built_in_taste_source(design_taste):
        failures.append("design_system.json taste_guidance.sources must include built-in-ppt-taste-system")
    if not has_built_in_taste_source(style_taste):
        failures.append("style_brief.json taste_guidance.sources must include built-in-ppt-taste-system")
    quality_policy = check_image_quality_policy(style_brief.get("image_quality_policy"), failures, "style_brief.json")
    failure_policy = check_imagegen_failure_policy(
        style_brief.get("imagegen_failure_policy"),
        failures,
        "style_brief.json",
    )
    check_imagegen_retry_log(workspace, style_brief, failure_policy, failures)
    contact_min = quality_policy.get("minimum_acceptable_contact_sheet_px") or {}
    min_contact_width = safe_int(contact_min.get("width"))
    min_contact_height = safe_int(contact_min.get("height"))
    check_no_html_surrogates(workspace, failures)
    if style_brief.get("style_variation_scope") != "visual_aesthetic_only":
        failures.append("style_brief.json style_variation_scope must be visual_aesthetic_only")
    if style_brief.get("content_strategy_locked") is not True:
        failures.append("style_brief.json content_strategy_locked must be true before visual style exploration")
    if selection_mode not in {"ask_user", "full_automation"}:
        failures.append(
            "style_brief.json selection_mode must be ask_user or full_automation; "
            f"got {selection_mode!r}"
        )
    if generation_mode not in {"parallel_style_lanes", "sequential_style_lanes", "single_prompt_fallback"}:
        failures.append(
            "style_brief.json generation_mode must be parallel_style_lanes, "
            f"sequential_style_lanes, or single_prompt_fallback; got {generation_mode!r}"
        )
    narrative_lock = style_brief.get("narrative_lock", {})
    current_fingerprint = deck_spec_fingerprint(deck_spec)
    recorded_fingerprint = narrative_lock.get("deck_spec_fingerprint")
    if not recorded_fingerprint:
        failures.append(
            "style_brief.json narrative_lock.deck_spec_fingerprint is missing; "
            f"expected {current_fingerprint}"
        )
    elif recorded_fingerprint != current_fingerprint:
        failures.append(
            "style_brief.json narrative_lock.deck_spec_fingerprint does not match current deck_spec.json; "
            f"expected {current_fingerprint}"
        )
    expected_slide_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    if expected_slide_count and narrative_lock.get("locked_slide_count") != expected_slide_count:
        failures.append("style_brief.json narrative_lock.locked_slide_count does not match deck_spec.json")
    expected_order = [slide.get("slide_id") for slide in deck_spec.get("slides", []) if slide.get("slide_id")]
    if expected_order and narrative_lock.get("locked_slide_order") != expected_order:
        failures.append("style_brief.json narrative_lock.locked_slide_order does not match deck_spec.json")
    selected_narrative = narrative_plan.get("selected_narrative_id")
    if style_brief.get("selected_narrative_id") != selected_narrative:
        failures.append("style_brief.json selected_narrative_id must match narrative_plan.json")
    if narrative_lock.get("slide_intent_plan") != "slide_intent_plan.json":
        failures.append("style_brief.json narrative_lock.slide_intent_plan must be slide_intent_plan.json")
    if narrative_lock.get("slide_intent_lock_state") != "locked":
        failures.append("style_brief.json narrative_lock.slide_intent_lock_state must be locked")
    if slide_intent_plan.get("lock_state") != "locked":
        failures.append("slide_intent_plan.json must be locked before style selection")
    if narrative_lock.get("narrative_plan") != "narrative_plan.json":
        failures.append("style_brief.json narrative_lock.narrative_plan must be narrative_plan.json")
    if narrative_lock.get("narrative_plan_lock_state") != "locked":
        failures.append("style_brief.json narrative_lock.narrative_plan_lock_state must be locked")
    for key in (
        "slide_order_locked",
        "section_flow_locked",
        "titles_locked",
        "claims_locked",
        "required_data_locked",
        "core_proof_objects_locked",
    ):
        if narrative_lock.get(key) is not True:
            failures.append(f"style_brief.json narrative_lock.{key} must be true")
    if count < 1:
        failures.append("style_brief.json direction_count is 0; style exploration was skipped")
    if count == 1 and not style_brief.get("user_requested_count"):
        failures.append(
            "style_brief.json direction_count is 1 without an explicit user_requested_count; "
            "multiple style directions were skipped"
        )
    if selection_mode == "full_automation" and not style_brief.get("full_automation_trigger"):
        failures.append("style_brief.json full_automation requires full_automation_trigger")
    if not style_brief.get("selected_option"):
        failures.append("style_brief.json selected_option is empty; user or automation did not select a style")
    candidates = style_brief.get("candidate_directions") or []
    selected_option = style_brief.get("selected_option")
    if count and len(candidates) < count:
        failures.append(
            f"style_brief.json has {len(candidates)} candidate_directions but direction_count is {count}"
        )
    families: list[str] = []
    lane_ids: set[str] = set()
    candidate_options: set[str] = set()
    for idx, candidate in enumerate(candidates, 1):
        if candidate.get("option_id"):
            candidate_options.add(str(candidate.get("option_id")))
        family = candidate.get("aesthetic_family")
        if not family:
            failures.append(f"candidate direction {idx} missing aesthetic_family")
        else:
            families.append(str(family))
        if not candidate.get("style_lane_id"):
            failures.append(f"candidate direction {idx} missing style_lane_id")
        if candidate.get("narrative_behavior") not in {None, "same_story_reexpressed"}:
            failures.append(
                f"candidate direction {idx} narrative_behavior must be same_story_reexpressed"
            )
        if candidate.get("style_variation_scope") not in {None, "visual_aesthetic_only"}:
            failures.append(f"candidate direction {idx} style_variation_scope must be visual_aesthetic_only")
        term = contains_content_style_term(
            {
                "style_lane_id": candidate.get("style_lane_id"),
                "name": candidate.get("name"),
                "aesthetic_family": candidate.get("aesthetic_family"),
                "premise": candidate.get("premise") or candidate.get("strategic_premise"),
            }
        )
        if term:
            failures.append(
                f"candidate direction {idx} uses content/narrative term {term!r} as a style label; "
                "style options must be pure visual/aesthetic skins"
            )
        may_change = candidate.get("style_may_change") or candidate.get("must_differ_by") or []
        if isinstance(may_change, list):
            for item in may_change:
                if contains_content_style_term(item):
                    failures.append(
                        f"candidate direction {idx} style_may_change cannot include content/story/proof-object terms: {item!r}"
                    )
    if count > 1 and len(set(families)) < min(count, len(candidates)):
        failures.append("candidate directions must use distinct aesthetic_family values")
    if selected_option and candidate_options and selected_option not in candidate_options:
        failures.append(f"style_brief.json selected_option {selected_option!r} is not in candidate_directions")
    lanes = style_brief.get("style_lanes") or []
    if count and len(lanes) < count:
        failures.append(f"style_brief.json has {len(lanes)} style_lanes but direction_count is {count}")
    lane_options: set[str] = set()
    for idx, lane in enumerate(lanes, 1):
        lane_id = lane.get("style_lane_id")
        if lane_id:
            lane_ids.add(str(lane_id))
        else:
            failures.append(f"style lane {idx} missing style_lane_id")
        if lane.get("option_id"):
            lane_options.add(str(lane.get("option_id")))
        if not lane.get("aesthetic_family"):
            failures.append(f"style lane {idx} missing aesthetic_family")
        if lane.get("style_variation_scope") not in {None, "visual_aesthetic_only"}:
            failures.append(f"style lane {idx} style_variation_scope must be visual_aesthetic_only")
        term = contains_content_style_term(
            {
                "style_lane_id": lane.get("style_lane_id"),
                "name": lane.get("name"),
                "aesthetic_family": lane.get("aesthetic_family"),
                "premise": lane.get("premise") or lane.get("strategic_premise"),
            }
        )
        if term:
            failures.append(
                f"style lane {idx} uses content/narrative term {term!r} as a style label; "
                "use pure visual labels such as flat, glass, skeuomorphic, editorial, technical-schematic, or illustration"
            )
        if lane.get("generator") != "imagegen":
            failures.append(f"style lane {idx} generator must be imagegen")
        if lane.get("narrative_lock_ref") != recorded_fingerprint:
            failures.append(f"style lane {idx} narrative_lock_ref must match narrative_lock.deck_spec_fingerprint")
        status = lane.get("status")
        if status not in {"generated", "ready_for_user", "selected"}:
            failures.append(f"style lane {idx} status must be generated, ready_for_user, or selected; got {status!r}")
        prompt_path = require_file(workspace, lane.get("prompt_path"), f"style lane {idx} prompt", failures)
        output_path = require_file(workspace, lane.get("output_path"), f"style lane {idx} output", failures)
        if output_path and f"{os.sep}preview{os.sep}" in str(output_path):
            failures.append(f"style lane {idx} output cannot be a PPTX preview image: {output_path}")
        if output_path:
            check_not_html_backed_image(output_path, f"style lane {idx} output", failures)
            width, height = image_size(output_path)
            if min_contact_width and min_contact_height:
                if not width or not height:
                    failures.append(f"style lane {idx} output dimensions could not be read: {output_path}")
                elif width < min_contact_width or height < min_contact_height:
                    failures.append(
                        f"style lane {idx} output must be at least {min_contact_width}x{min_contact_height}; "
                        f"got {width}x{height}"
                    )
        invariance = lane.get("invariance_check", {})
        for key in (
            "slide_count_ok",
            "order_ok",
            "claims_preserved",
            "data_sources_preserved",
            "proof_object_intent_preserved",
            "selected_narrative_preserved",
        ):
            if invariance.get(key) is not True:
                failures.append(f"style lane {idx} invariance_check.{key} must be true")
        if invariance.get("violations"):
            failures.append(f"style lane {idx} has narrative invariance violations")
    if selected_option and lane_options and selected_option not in lane_options:
        failures.append(f"style_brief.json selected_option {selected_option!r} is not in style_lanes")
    sheets = list_paths(style_brief.get("style_contact_sheets"))
    if count and len(sheets) < count:
        failures.append(
            f"style_brief.json lists {len(sheets)} contact sheets but direction_count is {count}"
        )
    sheet_options: set[str] = set()
    for raw_sheet, sheet in zip(style_brief.get("style_contact_sheets") or [], sheets):
        if isinstance(raw_sheet, dict):
            if raw_sheet.get("option_id"):
                sheet_options.add(str(raw_sheet.get("option_id")))
            if raw_sheet.get("generator") != "imagegen":
                failures.append(f"style contact sheet must declare generator=imagegen: {sheet}")
            if raw_sheet.get("style_lane_id") and lane_ids and raw_sheet.get("style_lane_id") not in lane_ids:
                failures.append(f"style contact sheet references unknown style_lane_id: {raw_sheet.get('style_lane_id')}")
            if not raw_sheet.get("style_lane_id"):
                failures.append(f"style contact sheet missing style_lane_id: {sheet}")
            if not raw_sheet.get("aesthetic_family"):
                failures.append(f"style contact sheet missing aesthetic_family: {sheet}")
            if raw_sheet.get("style_variation_scope") not in {None, "visual_aesthetic_only"}:
                failures.append(f"style contact sheet style_variation_scope must be visual_aesthetic_only: {sheet}")
            term = contains_content_style_term(
                {
                    "style_lane_id": raw_sheet.get("style_lane_id"),
                    "name": raw_sheet.get("name"),
                    "aesthetic_family": raw_sheet.get("aesthetic_family"),
                }
            )
            if term:
                failures.append(
                    f"style contact sheet {sheet} uses content/narrative term {term!r} as a style label"
                )
            if raw_sheet.get("narrative_lock_ref") != recorded_fingerprint:
                failures.append(f"style contact sheet narrative_lock_ref must match narrative lock: {sheet}")
            if not raw_sheet.get("prompt_path"):
                failures.append(f"style contact sheet missing prompt_path: {sheet}")
            else:
                require_file(workspace, raw_sheet.get("prompt_path"), "style contact sheet prompt", failures)
            invariance = raw_sheet.get("invariance_check", {})
            if invariance:
                for key in (
                    "slide_count_ok",
                    "order_ok",
                    "claims_preserved",
                    "data_sources_preserved",
                    "proof_object_intent_preserved",
                    "selected_narrative_preserved",
                ):
                    if invariance.get(key) is not True:
                        failures.append(f"style contact sheet {sheet} invariance_check.{key} must be true")
                if invariance.get("violations"):
                    failures.append(f"style contact sheet {sheet} has narrative invariance violations")
        path = require_file(workspace, sheet, "style contact sheet", failures)
        if not path:
            continue
        normalized = str(path)
        if f"{os.sep}output{os.sep}" in normalized:
            failures.append(f"style contact sheet cannot be a final output image: {path}")
        if f"{os.sep}preview{os.sep}" in normalized:
            failures.append(f"style contact sheet cannot be a PPTX preview image: {path}")
        check_not_html_backed_image(path, "style contact sheet", failures)
        width, height = image_size(path)
        if min_contact_width and min_contact_height:
            if not width or not height:
                failures.append(f"style contact sheet dimensions could not be read: {path}")
            elif width < min_contact_width or height < min_contact_height:
                failures.append(
                    f"style contact sheet must be at least {min_contact_width}x{min_contact_height}; "
                    f"got {width}x{height}: {path}"
                )
    if selected_option and sheet_options and selected_option not in sheet_options:
        failures.append(f"style_brief.json selected_option {selected_option!r} is not in style_contact_sheets")


def check_reconstruction_manifest(
    workspace: Path,
    deck_spec: dict,
    reconstruction_manifest: dict,
    failures: list[str],
    *,
    require_outputs: bool = False,
) -> None:
    mode = deck_spec.get("deck", {}).get("mode") or reconstruction_manifest.get("mode")
    if not is_reconstruction_mode(mode):
        failures.append("reconstruction_manifest.json is only valid for reconstruction-only or repair-existing-pptx mode")
    if deck_spec.get("deck", {}).get("lock_state") != "locked":
        failures.append("deck_spec.json deck.lock_state must be locked for reconstruction-only PPTX work")
    if reconstruction_manifest.get("lock_state") != "locked":
        failures.append("reconstruction_manifest.json lock_state must be locked before PPTX reconstruction")
    page_sharding = reconstruction_manifest.get("page_sharding", {})
    for key in ("enabled", "per_slide_pptx_required", "merge_after_page_approval"):
        if page_sharding.get(key) is not True:
            failures.append(f"reconstruction_manifest.json page_sharding.{key} must be true")
    global_rules = reconstruction_manifest.get("global_rules", {})
    if global_rules.get("ordinary_table_or_card_rebuild_forbidden") is not True:
        failures.append("reconstruction_manifest.json must forbid ordinary table/card rebuilds")
    if global_rules.get("native_text_boxes_allowed_only_as_transparent_overlays") is not True:
        failures.append("reconstruction_manifest.json must restrict native text boxes to transparent overlays")
    if global_rules.get("hidden_text_layer_does_not_count_as_editable") is not True:
        failures.append("reconstruction_manifest.json must state hidden text layers do not count as editable output")
    if global_rules.get("visible_native_overlays_required") is not True:
        failures.append("reconstruction_manifest.json must require visible native editable overlays")
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slides = reconstruction_manifest.get("slides", [])
    if expected_count and len(slides) != expected_count:
        failures.append(
            f"reconstruction_manifest.json has {len(slides)} slides but deck_spec expects {expected_count}"
        )
    if reconstruction_manifest.get("open_questions"):
        failures.append("reconstruction_manifest.json still has open_questions")
    allowed_text_status = {"provided", "ocr_verified", "user_accepted_image_text", "image_only_accepted"}
    for idx, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            failures.append(f"reconstruction manifest slide {idx:03d} must be an object")
            continue
        if not slide.get("slide_id"):
            failures.append(f"reconstruction manifest slide {idx:03d} missing slide_id")
        source_image = slide.get("source_image_path")
        path = require_file(workspace, source_image, f"reconstruction slide {idx:03d} source image", failures)
        if path and (f"{os.sep}output{os.sep}" in str(path) or f"{os.sep}preview{os.sep}" in str(path)):
            failures.append(f"reconstruction slide {idx:03d} source image cannot be a PPTX preview/output image: {path}")
        if slide.get("text_source_status") not in allowed_text_status:
            failures.append(
                f"reconstruction slide {idx:03d} text_source_status must be one of {sorted(allowed_text_status)}"
            )
        if slide.get("reconstruction_mode") not in {"pixel_locked_hybrid", "sliced_hybrid", "native_trace_hybrid"}:
            failures.append(
                f"reconstruction slide {idx:03d} reconstruction_mode must be pixel_locked_hybrid, sliced_hybrid, or native_trace_hybrid"
            )
        if not slide.get("required_editable_overlays"):
            failures.append(f"reconstruction slide {idx:03d} missing required_editable_overlays")
        coverage = slide.get("editable_overlay_coverage", {})
        if not isinstance(coverage, dict):
            failures.append(f"reconstruction slide {idx:03d} editable_overlay_coverage must be an object")
            coverage = {}
        if coverage.get("visible_native_text_overlay") is not True:
            failures.append(
                f"reconstruction slide {idx:03d} must have visible native text overlays; hidden/behind-image text does not count"
            )
        if int(coverage.get("visible_overlay_count") or 0) < 1:
            failures.append(f"reconstruction slide {idx:03d} visible_overlay_count must be at least 1")
        output_slide = slide.get("output_slide_pptx")
        preview = slide.get("preview_path")
        if not output_slide:
            failures.append(f"reconstruction slide {idx:03d} missing output_slide_pptx")
        if not preview:
            failures.append(f"reconstruction slide {idx:03d} missing preview_path")
        if require_outputs:
            if output_slide:
                require_file(workspace, output_slide, f"reconstruction slide {idx:03d} output PPTX", failures)
            if preview:
                require_file(workspace, preview, f"reconstruction slide {idx:03d} preview", failures)
            if slide.get("review_status") not in {"approved", "user_accepted_risk"}:
                failures.append(
                    f"reconstruction slide {idx:03d} review_status must be approved or user_accepted_risk"
                )


def check_visual_contract(workspace: Path, deck_spec: dict, visual_contract: dict, failures: list[str]) -> None:
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slides = visual_contract.get("slides", [])
    reconstruction_mode = is_reconstruction_mode(deck_spec.get("deck", {}).get("mode", ""))
    quality_policy = check_image_quality_policy(
        visual_contract.get("image_quality_policy"),
        failures,
        "visual_contract.json",
    )
    minimum_px = quality_policy.get("minimum_acceptable_comp_px") or {}
    minimum_width = safe_int(minimum_px.get("width"))
    minimum_height = safe_int(minimum_px.get("height"))
    minimum_bytes = safe_int(quality_policy.get("minimum_acceptable_comp_bytes"))
    check_no_html_surrogates(workspace, failures)
    if not visual_contract.get("selected_style"):
        failures.append("visual_contract.json selected_style is empty")
    contact_sheet = visual_contract.get("contact_sheet")
    if not contact_sheet and not reconstruction_mode:
        failures.append("visual_contract.json contact_sheet is empty")
    elif contact_sheet and require_file(workspace, contact_sheet, "selected style contact sheet", failures):
        pass
    if visual_contract.get("per_slide_comps_complete") is not True:
        failures.append("visual_contract.json per_slide_comps_complete must be true before PPTX build")
    default_mode = visual_contract.get("default_reconstruction_mode")
    if default_mode not in {"pixel_locked_hybrid", "sliced_hybrid", "native_trace_hybrid", "native_rebuild"}:
        failures.append("visual_contract.json default_reconstruction_mode must be pixel_locked_hybrid, sliced_hybrid, native_trace_hybrid, or native_rebuild")
    if (
        visual_contract.get("pixel_locked_hybrid_required") is not True
        and visual_contract.get("explicit_downgrade_accepted") is not True
    ):
        failures.append("visual_contract.json pixel_locked_hybrid_required must be true unless explicit_downgrade_accepted is true")
    if expected_count and len(slides) != expected_count:
        failures.append(
            f"visual_contract.json has {len(slides)} slides but deck_spec expects {expected_count}"
        )
    expected_comp_size: tuple[int, int] | None = None
    for idx, slide in enumerate(slides, 1):
        comp = slide.get("comp_path") or slide.get("approved_comp_path")
        path = require_file(workspace, comp, f"slide {idx:03d} approved comp", failures)
        if not path:
            continue
        normalized = str(path)
        if f"{os.sep}slides{os.sep}" not in normalized:
            failures.append(
                f"slide {idx:03d} approved comp must live under slides/, not {path}"
            )
        if not COMP_RE.search(path.name):
            failures.append(
                f"slide {idx:03d} approved comp filename must look like slide-XXX-comp.png, not {path.name}"
            )
        if f"{os.sep}preview{os.sep}" in normalized or f"{os.sep}output{os.sep}" in normalized:
            failures.append(
                f"slide {idx:03d} approved comp cannot be a PPTX preview/output image: {path}"
            )
        check_not_html_backed_image(path, f"slide {idx:03d} approved comp", failures)
        actual_width, actual_height = image_size(path)
        try:
            actual_bytes = path.stat().st_size
        except OSError:
            actual_bytes = 0
        if actual_width and actual_height:
            actual_size = (actual_width, actual_height)
            if expected_comp_size is None:
                expected_comp_size = actual_size
            elif actual_size != expected_comp_size:
                failures.append(
                    f"slide {idx:03d} approved comp dimensions must match every other slide in this deck; "
                    f"expected {expected_comp_size[0]}x{expected_comp_size[1]}, got {actual_width}x{actual_height}: {path}"
                )
        if minimum_width and minimum_height:
            if not actual_width or not actual_height:
                failures.append(f"slide {idx:03d} approved comp dimensions could not be read: {path}")
            elif actual_width < minimum_width or actual_height < minimum_height:
                failures.append(
                    f"slide {idx:03d} approved comp file must be at least {minimum_width}x{minimum_height}; "
                    f"got {actual_width}x{actual_height}: {path}"
                )
        if minimum_bytes and actual_bytes < minimum_bytes:
            failures.append(
                f"slide {idx:03d} approved comp file must be at least {minimum_bytes} bytes; "
                f"got {actual_bytes}: {path}"
            )
        if not slide.get("visual_archetype"):
            failures.append(f"slide {idx:03d} missing visual_archetype in visual_contract.json")
        clarity = slide.get("clarity_review")
        if not isinstance(clarity, dict):
            failures.append(f"slide {idx:03d} missing clarity_review in visual_contract.json")
            clarity = {}
        else:
            if clarity.get("status") not in {"approved", "user_accepted_risk"}:
                failures.append(
                    f"slide {idx:03d} clarity_review.status must be approved or user_accepted_risk"
                )
            if clarity.get("blocking_blur") is not False:
                failures.append(f"slide {idx:03d} clarity_review.blocking_blur must be false")
            if clarity.get("text_legibility") not in {"approved", "acceptable", "user_accepted_risk"}:
                failures.append(f"slide {idx:03d} clarity_review.text_legibility must be approved or acceptable")
            if clarity.get("icon_line_clarity") not in {"approved", "acceptable", "user_accepted_risk"}:
                failures.append(f"slide {idx:03d} clarity_review.icon_line_clarity must be approved or acceptable")
            if clarity.get("edge_sharpness") not in {"approved", "acceptable", "user_accepted_risk"}:
                failures.append(f"slide {idx:03d} clarity_review.edge_sharpness must be approved or acceptable")
            if not clarity.get("small_text_strategy"):
                failures.append(f"slide {idx:03d} clarity_review.small_text_strategy is missing")
            dimensions = clarity.get("image_dimensions_px") or {}
            width = safe_int(dimensions.get("width"))
            height = safe_int(dimensions.get("height"))
            recorded_bytes = safe_int(clarity.get("image_file_size_bytes") or clarity.get("file_size_bytes"))
            if width and height and minimum_width and minimum_height:
                if width < minimum_width or height < minimum_height:
                    failures.append(
                        f"slide {idx:03d} clarity_review.image_dimensions_px must be at least "
                        f"{minimum_width}x{minimum_height}; got {width}x{height}"
                    )
            elif minimum_width and minimum_height:
                failures.append(f"slide {idx:03d} clarity_review.image_dimensions_px is missing")
            if recorded_bytes and minimum_bytes:
                if recorded_bytes < minimum_bytes:
                    failures.append(
                        f"slide {idx:03d} clarity_review.image_file_size_bytes must be at least "
                        f"{minimum_bytes}; got {recorded_bytes}"
                    )
            elif minimum_bytes:
                failures.append(f"slide {idx:03d} clarity_review.image_file_size_bytes is missing")
        source_type = slide.get("image_source_type") or clarity.get("image_source_type")
        if not reconstruction_mode and source_type != "imagegen":
            failures.append(f"slide {idx:03d} image_source_type must be imagegen in generated-deck mode")
        if slide.get("rendered_from_html") is True or slide.get("browser_rendered") is True:
            failures.append(f"slide {idx:03d} approved comp cannot be rendered from HTML/browser output")
        reconstruction_mode = slide.get("reconstruction_mode")
        if reconstruction_mode not in {"pixel_locked_hybrid", "sliced_hybrid", "native_trace_hybrid", "native_rebuild"}:
            failures.append(
                f"slide {idx:03d} reconstruction_mode must be pixel_locked_hybrid, sliced_hybrid, native_trace_hybrid, or native_rebuild"
            )
        if reconstruction_mode == "native_rebuild" and visual_contract.get("explicit_downgrade_accepted") is not True:
            comparison = slide.get("comparison_gate", {})
            if comparison.get("comp_match_status") != "approved":
                failures.append(
                    f"slide {idx:03d} native_rebuild requires approved comp_match_status or explicit downgrade acceptance"
                )
        backplate = slide.get("comp_backplate", {})
        if reconstruction_mode in {"pixel_locked_hybrid", "sliced_hybrid"}:
            if not isinstance(backplate, dict):
                failures.append(f"slide {idx:03d} comp_backplate must be an object")
                backplate = {}
            if backplate.get("strategy") not in {"full_slide", "sliced_layers"}:
                failures.append(f"slide {idx:03d} comp_backplate.strategy must be full_slide or sliced_layers")
            backplate_path = backplate.get("path") or comp
            require_file(workspace, backplate_path, f"slide {idx:03d} comp backplate", failures)
            if backplate.get("insert_first") is not True:
                failures.append(f"slide {idx:03d} comp_backplate.insert_first must be true")
        if reconstruction_mode == "native_trace_hybrid":
            trace_plan = slide.get("native_trace_plan")
            if not isinstance(trace_plan, dict):
                failures.append(f"slide {idx:03d} native_trace_plan must be an object")
                trace_plan = {}
            if (
                trace_plan.get("source_image_used_as_coordinate_reference") is not True
                and trace_plan.get("source_image_used_as_coordinate_blueprint") is not True
            ):
                failures.append(
                    f"slide {idx:03d} native_trace_plan.source_image_used_as_coordinate_reference must be true"
                )
            if int(trace_plan.get("native_element_count") or 0) < 10:
                failures.append(f"slide {idx:03d} native_trace_plan.native_element_count must be at least 10")
            if int(trace_plan.get("visible_text_box_count") or 0) < 3:
                failures.append(f"slide {idx:03d} native_trace_plan.visible_text_box_count must be at least 3")
            if trace_plan.get("render_fix_verify_loop") is not True:
                failures.append(f"slide {idx:03d} native_trace_plan.render_fix_verify_loop must be true")
        if not slide.get("text_mask_plan"):
            failures.append(f"slide {idx:03d} missing text_mask_plan in visual_contract.json")
        else:
            mask_plan = slide.get("text_mask_plan")
            mask_text = json.dumps(mask_plan, ensure_ascii=False).lower()
            if "none" in mask_text or "no mask" in mask_text or "不遮" in mask_text:
                failures.append(
                    f"slide {idx:03d} text_mask_plan cannot skip masking editable text regions"
                )
        overlay_plan = slide.get("editable_overlay_plan")
        if not overlay_plan:
            failures.append(f"slide {idx:03d} missing editable_overlay_plan in visual_contract.json")
        else:
            overlay_text = json.dumps(overlay_plan, ensure_ascii=False).lower()
            if "hidden" in overlay_text or "behind" in overlay_text or "backplate后" in overlay_text or "背后" in overlay_text:
                failures.append(
                    f"slide {idx:03d} editable_overlay_plan cannot count hidden/behind-backplate text as editable"
                )
            if isinstance(overlay_plan, dict):
                if overlay_plan.get("visible_native_text_overlay") is not True:
                    failures.append(
                        f"slide {idx:03d} editable_overlay_plan.visible_native_text_overlay must be true"
                    )
                if int(overlay_plan.get("visible_overlay_count") or 0) < 1:
                    failures.append(f"slide {idx:03d} editable_overlay_plan.visible_overlay_count must be at least 1")
            else:
                failures.append(
                    f"slide {idx:03d} editable_overlay_plan must be an object with visible native overlay coverage"
                )


def check_reviews(workspace: Path, deck_spec: dict, failures: list[str]) -> None:
    expected_count = deck_spec.get("deck", {}).get("slide_count") or len(deck_spec.get("slides", []))
    slide_review_dir = workspace / "qa" / "reviews" / "slide-comp"
    review_files = list(slide_review_dir.glob("*.json")) if slide_review_dir.exists() else []
    if expected_count and len(review_files) < expected_count:
        failures.append(
            f"slide-comp review JSON files are missing: found {len(review_files)}, expected at least {expected_count}"
        )


def check_final(workspace: Path, failures: list[str]) -> None:
    final_council = workspace / "qa" / "final-council.md"
    qa_report = workspace / "qa_report.md"
    if not final_council.exists():
        failures.append("Missing qa/final-council.md")
    else:
        text = final_council.read_text(encoding="utf-8")
        for token in ("pptx-reconstruction-fidelity", "taste-direction", "narrative-invariance", "Export Decision"):
            if token not in text:
                failures.append(f"qa/final-council.md missing required token: {token}")
    if not qa_report.exists():
        failures.append("Missing qa_report.md")
    else:
        text = qa_report.read_text(encoding="utf-8")
        empty_markers = [
            "## Style Direction Gate\n\n## Visual Comp Gate",
            "## Reviewer Findings\n\n## Final Council",
        ]
        if any(marker in text for marker in empty_markers):
            failures.append("qa_report.md still looks like an unfilled template")
    output_pptx = list((workspace / "output").glob("*.pptx"))
    if not output_pptx:
        failures.append("No final PPTX found under output/")


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
    reconstruction_mode = is_reconstruction_mode(mode)
    slide_intent_plan = load_json(workspace / "slide_intent_plan.json", failures)
    narrative_plan = load_json(workspace / "narrative_plan.json", failures)
    design_system = load_json(workspace / "design_system.json", failures)
    style_brief = load_json(workspace / "style_brief.json", failures)
    visual_contract = load_json(workspace / "visual_contract.json", failures)
    reconstruction_manifest = (
        load_json(workspace / "reconstruction_manifest.json", failures)
        if reconstruction_mode or (workspace / "reconstruction_manifest.json").exists()
        else {}
    )

    if pipeline_state.get("skill") != "imagegen-pptx-pipeline":
        failures.append("pipeline_state.json does not identify imagegen-pptx-pipeline")
    if args.stage in {"before-pptx", "final"} and pipeline_state.get("current_stage") == "initialized":
        failures.append("pipeline_state.json is still at initialized; stage transitions were not recorded")

    if reconstruction_mode:
        if args.stage in {"content-lock", "slide-intent-lock", "narrative-lock", "style-selection"}:
            failures.append(f"{args.stage} is not used in {mode} mode; use reconstruction-lock or before-pptx")
        if args.stage in {"reconstruction-lock", "before-pptx", "final"}:
            check_reconstruction_manifest(
                workspace,
                deck_spec,
                reconstruction_manifest,
                failures,
                require_outputs=args.stage == "final",
            )
        if args.stage in {"before-pptx", "final"}:
            check_visual_contract(workspace, deck_spec, visual_contract, failures)
            required_stages = {"reconstruction_input_lock", "visual_contract"}
            if args.stage == "final":
                required_stages.add("page_reconstruction")
            missing = required_stages - stage_names(pipeline_state)
            if missing:
                failures.append("pipeline_state.json stage_history missing: " + ", ".join(sorted(missing)))
    else:
        check_content_lock(deck_spec, failures)
        if args.stage in {"slide-intent-lock", "narrative-lock", "style-selection", "before-pptx", "final"}:
            check_slide_intent_lock(workspace, deck_spec, slide_intent_plan, failures)
        if args.stage in {"narrative-lock", "style-selection", "before-pptx", "final"}:
            check_narrative_lock(workspace, deck_spec, slide_intent_plan, narrative_plan, failures)
        if args.stage in {"style-selection", "before-pptx", "final"}:
            check_style_gate(workspace, deck_spec, slide_intent_plan, narrative_plan, design_system, style_brief, failures)
        if args.stage in {"before-pptx", "final"}:
            check_visual_contract(workspace, deck_spec, visual_contract, failures)
            check_reviews(workspace, deck_spec, failures)
            required_stages = {
                "content_gate",
                "slide_intent_lock",
                "narrative_selection",
                "style_selection",
                "single_slide_comps",
                "slide_comp_review",
            }
            missing = required_stages - stage_names(pipeline_state)
            if missing:
                failures.append("pipeline_state.json stage_history missing: " + ", ".join(sorted(missing)))
    if args.stage == "final":
        check_final(workspace, failures)

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
