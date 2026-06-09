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
        choices=["create", "template-following", "targeted-edit"],
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
        "qa/reviews/pptx-preview",
        "qa/reviews/final-council",
        "prompts",
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
                "each direction differs by aesthetic family, composition grammar, proof-object expression, density, depth, and visual rhythm",
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
        "slides": [],
    }

    files = {
        "pipeline_state.json": json.dumps(pipeline_state, ensure_ascii=False, indent=2) + "\n",
        "deck_spec.json": json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n",
        "design_system.json": json.dumps(design_system, ensure_ascii=False, indent=2) + "\n",
        "slide_intent_plan.json": json.dumps(slide_intent_plan, ensure_ascii=False, indent=2) + "\n",
        "narrative_plan.json": json.dumps(narrative_plan, ensure_ascii=False, indent=2) + "\n",
        "style_brief.json": json.dumps(style_brief, ensure_ascii=False, indent=2) + "\n",
        "template-frame-map.json": json.dumps(template_frame_map, ensure_ascii=False, indent=2) + "\n",
        "visual_contract.json": json.dumps(visual_contract, ensure_ascii=False, indent=2) + "\n",
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
        "template_frame_map": str(workspace / "template-frame-map.json"),
        "visual_contract": str(workspace / "visual_contract.json"),
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
