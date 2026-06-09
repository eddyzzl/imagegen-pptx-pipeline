#!/usr/bin/env python3
"""Validate hard gates for the ImageGen-to-PPTX pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


COMP_RE = re.compile(r"slide[-_]\d{1,3}.*comp\.(png|jpg|jpeg)$", re.IGNORECASE)


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
        if slide.get("reconstruction_mode") not in {"pixel_locked_hybrid", "sliced_hybrid"}:
            failures.append(
                f"reconstruction slide {idx:03d} reconstruction_mode must be pixel_locked_hybrid or sliced_hybrid"
            )
        if not slide.get("required_editable_overlays"):
            failures.append(f"reconstruction slide {idx:03d} missing required_editable_overlays")
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
    if default_mode not in {"pixel_locked_hybrid", "sliced_hybrid", "native_rebuild"}:
        failures.append("visual_contract.json default_reconstruction_mode must be pixel_locked_hybrid, sliced_hybrid, or native_rebuild")
    if (
        visual_contract.get("pixel_locked_hybrid_required") is not True
        and visual_contract.get("explicit_downgrade_accepted") is not True
    ):
        failures.append("visual_contract.json pixel_locked_hybrid_required must be true unless explicit_downgrade_accepted is true")
    if expected_count and len(slides) != expected_count:
        failures.append(
            f"visual_contract.json has {len(slides)} slides but deck_spec expects {expected_count}"
        )
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
        if not slide.get("visual_archetype"):
            failures.append(f"slide {idx:03d} missing visual_archetype in visual_contract.json")
        reconstruction_mode = slide.get("reconstruction_mode")
        if reconstruction_mode not in {"pixel_locked_hybrid", "sliced_hybrid", "native_rebuild"}:
            failures.append(
                f"slide {idx:03d} reconstruction_mode must be pixel_locked_hybrid, sliced_hybrid, or native_rebuild"
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
        if not slide.get("text_mask_plan"):
            failures.append(f"slide {idx:03d} missing text_mask_plan in visual_contract.json")
        if not slide.get("editable_overlay_plan"):
            failures.append(f"slide {idx:03d} missing editable_overlay_plan in visual_contract.json")


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
