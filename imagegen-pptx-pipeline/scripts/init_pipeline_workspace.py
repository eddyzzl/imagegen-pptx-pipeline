#!/usr/bin/env python3
"""Initialize an ImageGen-to-PPTX pipeline workspace."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path


BUILT_IN_TASTE_SOURCE = {
    "name": "built-in-ppt-taste-system",
    "path": "references/taste-system.md",
    "used_for": "style exploration | comp review | PPTX reconstruction QA | anti-default QA",
    "constraints_used": [
        "avoid flat table-only decks when richer proof objects fit",
        "require profile-appropriate visual archetypes",
        "preserve ImageGen comp visual grammar during PPTX reconstruction",
    ],
    "constraints_ignored": [],
}

BUILT_IN_TASTE_RULES = [
    "Avoid generic equal-card grids unless the content requires a matrix",
    "Use intentional whitespace and hierarchy, not decoration",
    "Prefer crafted diagrams and focal objects over default boxes",
    "Use one dominant proof object per slide",
    "Keep template-following designs inside protected template frames",
    "Do not let PPTX reconstruction collapse rich comps into plain tables or card grids",
]

BUILT_IN_TASTE_ANTI_PATTERNS = [
    "near-identical style options",
    "flat table-only deck",
    "generic equal-card grid",
    "default PPT template feel",
    "flat image-only slide without editable overlays",
]

DEFAULT_IMAGE_QUALITY_POLICY = {
    "policy_id": "imagegen-max-clarity-v1",
    "enabled": True,
    "prompt_detail_level": "highest_available",
    "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_bytes": 5 * 1024 * 1024,
    "minimum_acceptable_contact_sheet_px": {"width": 2400, "height": 1350},
    "prompt_requires_crisp_text_and_icons": True,
    "review_required_before_pptx": True,
    "small_text_policy": (
        "Avoid unreadable microtext in ImageGen comps. Main titles, key numbers, labels, "
        "and page markers must be sharp enough for visual review; exact final small copy "
        "comes from deck_spec.json during PPTX reconstruction."
    ),
    "blur_rejection_criteria": [
        "soft or blurry main title",
        "blurred key numbers",
        "muddy icons or line art",
        "low-contrast small labels",
        "compression artifacts around text or diagram strokes",
    ],
}

DEFAULT_IMAGEGEN_FAILURE_POLICY = {
    "policy_id": "imagegen-fail-closed-v1",
    "enabled": True,
    "fail_closed": True,
    "max_retries_per_asset": 2,
    "prompt_compression_allowed": True,
    "prompt_compression_scope": [
        "remove duplicated source prose",
        "remove internal reasoning",
        "remove repeated constraints",
        "summarize verbose citations while preserving source IDs",
    ],
    "prompt_compression_must_preserve": [
        "locked slide order",
        "slide titles",
        "core claims",
        "required data",
        "proof-object intent",
        "template constraints",
        "visual density floor",
        "aesthetic family",
    ],
    "content_density_may_be_reduced": False,
    "visual_complexity_may_be_reduced": False,
    "html_surrogate_allowed": False,
    "generic_ppt_fallback_allowed": False,
    "block_after_repeated_failures": True,
    "retry_log_path": "imagegen_retry_log.json",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "pptx-pipeline"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--mode",
        choices=["create", "template-following", "targeted-edit", "reconstruction-only", "repair-existing-pptx"],
        default="create",
    )
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    thread_id = os.environ.get("CODEX_THREAD_ID")
    if not thread_id:
        thread_id = "manual-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)

    base = Path(args.root).expanduser().resolve() if args.root else Path.cwd().resolve() / "outputs"
    workspace = base / thread_id / "presentations" / slugify(args.slug)

    dirs = [
        "input",
        "slides",
        "assets",
        "preview",
        "styles",
        "layout",
        "qa",
        "qa/reviews",
        "qa/reviews/pre-visual",
        "qa/reviews/style-count",
        "qa/reviews/style-selection",
        "qa/reviews/slide-comp",
        "qa/reviews/visual-contract",
        "qa/reviews/reconstruction-only",
        "qa/reviews/pptx-preview",
        "qa/reviews/final-council",
        "prompts",
        "slide-modules",
        "output",
    ]
    for name in dirs:
        (workspace / name).mkdir(parents=True, exist_ok=True)

    deck_spec = {
        "deck": {
            "title": args.title,
            "audience": "",
            "objective": "",
            "deck_profile": "",
            "content_input_type": "",
            "language": "zh-CN",
            "aspect_ratio": "16:9",
            "mode": args.mode,
            "slide_count": 0,
            "lock_state": "draft",
        },
        "global_constraints": {
            "must_include": [],
            "must_not_include": [],
            "source_rules": [],
            "editability": "main text, numbers, footers, page markers editable",
            "assumptions": [],
            "user_confirmed_decisions": [],
            "content_risks": [],
            "grill_questions": [],
            "content_confirmation_required": True,
        },
        "profile_requirements": {
            "primary_profile": "",
            "secondary_profiles": [],
            "required_proof_objects": [],
            "source_requirements": [],
            "visual_density": "",
            "audience_tolerance_for_complexity": "",
        },
        "slides": [],
        "sources": [],
    }
    pipeline_state = {
        "skill": "imagegen-pptx-pipeline",
        "workspace": str(workspace),
        "title": args.title,
        "mode": args.mode,
        "current_stage": "initialized",
        "awaiting_user": False,
        "required_user_reply": "",
        "next_action": "read inputs and draft truth files",
        "resume_instructions": (
            "Read pipeline_state.json, deck_spec.json, user_decisions.md, then continue this stage; "
            "do not restart unless the user requests a restart."
        ),
        "last_completed_artifacts": {
            "deck_spec": "deck_spec.json",
            "design_system": "design_system.json",
            "slide_intent_plan": "slide_intent_plan.json",
            "narrative_plan": "narrative_plan.json",
            "style_brief": "style_brief.json",
            "selected_style": "",
            "visual_contract": "visual_contract.json",
            "latest_preview": "",
        },
        "stage_history": [
            {
                "stage": "initialized",
                "status": "completed",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "notes": "Workspace created.",
            }
        ],
    }
    design_system = {
        "mode": args.mode,
        "deck_profile": "",
        "template_constraints": {
            "source_pptx": "",
            "template_mode": "hard" if args.mode == "template-following" else "none",
            "template_contact_sheet": "",
            "template_frame_map": "template-frame-map.json",
            "preserve_master": args.mode == "template-following",
            "preserve_footer": True,
            "preserve_logo": True,
            "preserve_page_markers": True,
            "preserve_title_furniture": True,
            "protected_elements": [],
            "allowed_deviations": [],
        },
        "palette": {"primary": [], "secondary": [], "neutral": [], "semantic": {}},
        "typography": {
            "title": {"font": "", "weight": "", "size_range": ""},
            "body": {"font": "", "weight": "", "size_range": ""},
            "numbers": {"font": "", "weight": "", "size_range": ""},
        },
        "layout": {
            "aspect_ratio": "16:9",
            "grid": "",
            "safe_margins": "",
            "footer_rule": "",
            "page_number_rule": "",
        },
        "visual_language": {
            "backgrounds": "",
            "cards": "",
            "charts": "",
            "icons": "",
            "photography": "",
            "texture_depth": "",
            "visual_ambition": "polished",
            "avoid_visual_regressions": [
                "flat table-only deck",
                "generic equal-card grid",
                "default PPT template feel",
                "near-identical style options",
            ],
        },
        "taste_guidance": {
            "enabled": True,
            "sources": [BUILT_IN_TASTE_SOURCE],
            "portable_rules": BUILT_IN_TASTE_RULES,
            "ppt_translation_notes": [
                "The built-in taste system is static PPT guidance, not a web interaction system",
                "Frontend-only hover/GSAP/responsive rules from optional external sources are not PPT constraints",
            ],
        },
        "reference_patterns": [],
        "asset_rules": {
            "identity_assets": "Use verified or user-provided only",
            "generated_assets": "Allowed for non-identity illustrative material",
            "image_retention": "Preserve complex visuals as images when native rebuild would reduce quality",
        },
    }
    slide_intent_plan = {
        "lock_state": "draft",
        "source_deck_spec_fingerprint": "",
        "matrix_path": "slide_intent_matrix.md",
        "selection_mode": "ask_user",
        "review_status": "not_started",
        "slides": [],
        "open_questions": [],
    }
    narrative_plan = {
        "lock_state": "draft",
        "source_deck_spec_fingerprint": "",
        "slide_intent_plan": "slide_intent_plan.json",
        "slide_intent_lock_state": "draft",
        "matrix_path": "narrative_matrix.md",
        "selection_mode": "ask_user",
        "selected_narrative_id": "",
        "user_selection_note": "",
        "narrative_options": [],
        "slides": [],
        "review_status": "not_started",
        "open_questions": [],
    }
    style_brief = {
        "direction_count": 0,
        "user_requested_count": None,
        "selection_mode": "ask_user",
        "full_automation_trigger": "",
        "generation_mode": "parallel_style_lanes",
        "style_variation_scope": "visual_aesthetic_only",
        "content_strategy_locked": False,
        "visual_ambition": "premium business deck with template fidelity",
        "deck_profile": "",
        "template_is_hard_constraint": args.mode == "template-following",
        "selected_narrative_id": "",
        "narrative_lock": {
            "source": "deck_spec.json",
            "slide_intent_plan": "slide_intent_plan.json",
            "slide_intent_lock_state": "draft",
            "narrative_plan": "narrative_plan.json",
            "deck_spec_fingerprint": "",
            "narrative_plan_lock_state": "draft",
            "locked_slide_count": 0,
            "locked_slide_order": [],
            "invariant_fields": [
                "slide_id",
                "page_number",
                "section",
                "title",
                "claim",
                "body_text",
                "data",
                "source_id",
                "proof_object",
                "visual_intent",
                "template_source_slide",
            ],
            "slide_order_locked": True,
            "section_flow_locked": True,
            "titles_locked": True,
            "claims_locked": True,
            "required_data_locked": True,
            "core_proof_objects_locked": True,
            "allowed_style_adaptations": [
                "change visual archetype expression while preserving proof-object intent",
                "adjust density, depth, material, diagram grammar, and pacing",
                "change chart/diagram styling without changing data or source meaning",
            ],
            "forbidden_story_changes": [
                "add/delete/reorder slides",
                "replace claims",
                "invent metrics or sources",
                "change deck objective",
                "turn a content proof object into a different narrative point",
                "ignore the selected narrative treatment",
            ],
        },
        "user_style_preferences": {
            "requested_aesthetic_families": [],
            "forbidden_aesthetic_families": [],
            "notes": "",
        },
        "taste_guidance": {
            "enabled": True,
            "sources": [
                {
                    "name": BUILT_IN_TASTE_SOURCE["name"],
                    "path": BUILT_IN_TASTE_SOURCE["path"],
                    "used_for": "direction diversity, ImageGen art direction, anti-generic review, reconstruction fidelity",
                }
            ],
            "style_principles": [
                "each direction differs by visual aesthetic only: art style, material, depth, typography feel, icon/illustration style, chart rendering, composition rhythm, and density",
                "style lanes must not rename or replace the selected narrative treatment, slide content, claim, data, or proof object",
                "single-slide comps must preserve a clear visual archetype",
                "PPTX reconstruction must retain the approved comp's reader-facing visual grammar",
            ],
            "anti_patterns": BUILT_IN_TASTE_ANTI_PATTERNS,
            "profile_specific_direction_notes": [],
        },
        "diversity_axes": [
            "aesthetic family",
            "composition grammar",
            "diagram/chart language",
            "density and pacing",
            "background/depth treatment",
            "material and texture treatment",
            "title and section treatment",
        ],
        "candidate_directions": [],
        "style_lanes": [],
        "selected_option": "",
        "style_contact_sheets": [],
        "option_safety_status": "not_started",
        "image_quality_policy": DEFAULT_IMAGE_QUALITY_POLICY,
        "imagegen_failure_policy": DEFAULT_IMAGEGEN_FAILURE_POLICY,
        "imagegen_retry_log": "imagegen_retry_log.json",
    }
    imagegen_retry_log = {
        "policy_ref": "style_brief.json.imagegen_failure_policy",
        "attempts": [],
    }
    template_frame_map = {
        "source_pptx": "",
        "template_contact_sheet": "",
        "rules": {
            "inherit_source_slides": args.mode == "template-following",
            "never_start_from_blank": args.mode == "template-following",
            "preserve_master": args.mode == "template-following",
            "preserve_brand_chrome": args.mode == "template-following",
            "deviation_log": "deviation-log.md",
        },
        "slide_map": [],
    }
    visual_contract = {
        "selected_style": "",
        "contact_sheet": "",
        "template_mode": "hard" if args.mode == "template-following" else "none",
        "template_contact_sheet": "",
        "template_frame_map": "template-frame-map.json",
        "per_slide_comps_complete": False,
        "downgrade_mode": False,
        "explicit_downgrade_accepted": False,
        "comp_is_construction_drawing": True,
        "default_reconstruction_mode": "pixel_locked_hybrid",
        "pixel_locked_hybrid_required": True,
        "minimum_non_title_rich_visual_ratio": 0.6,
        "image_quality_policy": DEFAULT_IMAGE_QUALITY_POLICY,
        "slides": [],
    }
    reconstruction_manifest = {
        "lock_state": "draft",
        "mode": args.mode,
        "source": "user_supplied_slide_images",
        "slide_count": 0,
        "page_sharding": {
            "enabled": args.mode in {"reconstruction-only", "repair-existing-pptx"},
            "per_slide_pptx_required": True,
            "merge_after_page_approval": True,
            "parallel_subagents_recommended": True,
        },
        "global_rules": {
            "skip_full_pipeline_gates": args.mode in {"reconstruction-only", "repair-existing-pptx"},
            "visual_fidelity_priority": "pixel_locked_hybrid",
            "ordinary_table_or_card_rebuild_forbidden": True,
            "native_text_boxes_allowed_only_as_transparent_overlays": True,
            "hidden_text_layer_does_not_count_as_editable": True,
            "visible_native_overlays_required": True,
        },
        "slides": [],
        "open_questions": [],
    }

    files = {
        "pipeline_state.json": json.dumps(pipeline_state, ensure_ascii=False, indent=2) + "\n",
        "deck_spec.json": json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n",
        "design_system.json": json.dumps(design_system, ensure_ascii=False, indent=2) + "\n",
        "slide_intent_plan.json": json.dumps(slide_intent_plan, ensure_ascii=False, indent=2) + "\n",
        "narrative_plan.json": json.dumps(narrative_plan, ensure_ascii=False, indent=2) + "\n",
        "style_brief.json": json.dumps(style_brief, ensure_ascii=False, indent=2) + "\n",
        "imagegen_retry_log.json": json.dumps(imagegen_retry_log, ensure_ascii=False, indent=2) + "\n",
        "template-frame-map.json": json.dumps(template_frame_map, ensure_ascii=False, indent=2) + "\n",
        "visual_contract.json": json.dumps(visual_contract, ensure_ascii=False, indent=2) + "\n",
        "reconstruction_manifest.json": json.dumps(reconstruction_manifest, ensure_ascii=False, indent=2) + "\n",
        "template-audit.md": (
            "# Template Audit\n\n"
            "## Status\nNOT_STARTED\n\n"
            "## Source PPTX\n\n"
            "## Masters And Layouts\n\n"
            "## Protected Elements\n\n"
            "## Reusable Slide Archetypes\n\n"
            "## Contact Sheets And Previews\n"
        ),
        "deviation-log.md": (
            "# Deviation Log\n\n"
            "Record only user-approved deviations from template, visual comp, editability, or source truth.\n"
        ),
        "source_notes.md": (
            "# Source Notes\n\n"
            "## Inputs\n\n"
            "## Provenance\n\n"
            "## Taste Guidance Sources\n\n"
            "- built-in-ppt-taste-system: references/taste-system.md\n\n"
            "## Assumptions\n\n"
            "## Missing Inputs\n"
        ),
        "slide_intent_matrix.md": (
            "# Slide Intent Matrix\n\n"
            "## Status\nDRAFT\n\n"
            "| Page | Proposed title | Core idea | Proof goal | Evidence/data candidates | Gaps/questions | Confidence |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
        ),
        "narrative_matrix.md": (
            "# Narrative Matrix\n\n"
            "## Status\nDRAFT\n\n"
            "Rows are slides. Columns are narrative options. Fill this after content lock and before ImageGen.\n"
        ),
        "content_review.md": (
            "# Content Review\n\n"
            "## Status\nNEEDS_USER\n\n"
            "## Story Spine\n\n"
            "## Grill Questions\n\n"
            "## Content Findings\n\n"
            "## Lock Recommendation\nASK_USER\n"
        ),
        "user_decisions.md": (
            "# User Decisions\n\n"
            "## Confirmed By User\n\n"
            "## Pending User Reply\n\n"
            "## Accepted Automation Assumptions\n\n"
            "## Explicitly Accepted Risks\n"
        ),
        "qa_report.md": (
            "# QA Report\n\n"
            "## Status\nNEEDS_ITERATION\n\n"
            "## Source Truth\n\n"
            "## Slide Intent Gate\n\n"
            "## Narrative Treatment Gate\n\n"
            "## Style Direction Gate\n\n"
            "## Visual Comp Gate\n\n"
            "## Template Fidelity Gate\n\n"
            "## PPTX Reconstruction Gate\n\n"
            "## Reviewer Findings\n\n"
            "## Final Council\n\n"
            "## Editability\n\n"
            "## Known Limitations\n"
        ),
        "qa/final-council.md": (
            "# Final Deck Council\n\n"
            "## Status\nNEEDS_ITERATION\n\n"
            "## Role Results\n\n"
            "## Blocking Findings\n\n"
            "## Export Decision\nITERATE\n"
        ),
    }
    for filename, content in files.items():
        path = workspace / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    print(json.dumps({
        "workspace": str(workspace),
        "pipeline_state": str(workspace / "pipeline_state.json"),
        "deck_spec": str(workspace / "deck_spec.json"),
        "design_system": str(workspace / "design_system.json"),
        "slide_intent_plan": str(workspace / "slide_intent_plan.json"),
        "narrative_plan": str(workspace / "narrative_plan.json"),
        "style_brief": str(workspace / "style_brief.json"),
        "imagegen_retry_log": str(workspace / "imagegen_retry_log.json"),
        "template_frame_map": str(workspace / "template-frame-map.json"),
        "visual_contract": str(workspace / "visual_contract.json"),
        "reconstruction_manifest": str(workspace / "reconstruction_manifest.json"),
        "template_audit": str(workspace / "template-audit.md"),
        "deviation_log": str(workspace / "deviation-log.md"),
        "source_notes": str(workspace / "source_notes.md"),
        "slide_intent_matrix": str(workspace / "slide_intent_matrix.md"),
        "narrative_matrix": str(workspace / "narrative_matrix.md"),
        "content_review": str(workspace / "content_review.md"),
        "user_decisions": str(workspace / "user_decisions.md"),
        "qa_report": str(workspace / "qa_report.md"),
        "final_council": str(workspace / "qa" / "final-council.md"),
        "output_dir": str(workspace / "output"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
