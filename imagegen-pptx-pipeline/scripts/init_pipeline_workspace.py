#!/usr/bin/env python3
"""Initialize an ImageGen-to-PPTX pipeline workspace."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path


BUILT_IN_TASTE_SOURCE = {
    "name": "built-in-ppt-taste-system",
    "path": "references/taste-system.md",
    "used_for": "style exploration | comp review | PPTX conversion QA | anti-default QA",
    "constraints_used": [
        "avoid flat table-only decks when richer proof objects fit",
        "require profile-appropriate visual archetypes",
        "preserve ImageGen comp visual grammar during strict PPTX conversion",
    ],
    "constraints_ignored": [],
}

BUILT_IN_STYLE_LIBRARY_SOURCE = {
    "name": "built-in-ppt-style-library",
    "path": "references/style-library.md",
    "used_for": "style lane selection | user style preference mapping | ImageGen style prompts",
    "constraints_used": [
        "choose canonical style_id values instead of vague visual adjectives",
        "map the actual deck task, audience, and occasion to profile-appropriate style ids before recommending options",
        "map user references such as McKinsey, annual report, Apple keynote, Notion, minimalist, promotion defense, interview, and academic defense to concrete style ids",
        "preserve locked narrative and content while changing only visual art direction",
    ],
    "constraints_ignored": [],
}

BUILT_IN_TASTE_RULES = [
    "Avoid generic equal-card grids unless the content requires a matrix",
    "Use intentional whitespace and hierarchy, not decoration",
    "Prefer crafted diagrams and focal objects over default boxes",
    "Use one dominant proof object per slide",
    "Keep template-following designs inside protected template frames",
    "Do not let PPTX conversion collapse rich comps into plain tables or card grids",
]

BUILT_IN_TASTE_ANTI_PATTERNS = [
    "near-identical style options",
    "style options that only swap icons, lines, or small modules while keeping the same layout skeleton",
    "off-profile recommendations, such as personal-defense styles for a company profile deck or annual-report styles for an interview deck, unless the user explicitly asked for them",
    "flat table-only deck",
    "generic equal-card grid",
    "default PPT template feel",
    "flat image-only slide without editable overlays",
]

STYLE_PROFILE_ROUTES = [
    {
        "profile": "company-profile",
        "signals": ["company-profile", "company intro", "enterprise intro", "corporate profile", "企业介绍", "公司介绍", "品牌介绍"],
        "allowed_style_ids": [
            "corporate-profile-architectural",
            "corporate-team-collaboration",
            "nordic-business-future",
            "business-strategy-illustrated",
            "brand-proposal-minimal",
            "editorial-gallery-white",
            "enterprise-annual-report",
        ],
        "allowed_aesthetic_families": ["company-profile", "brand-proposal", "editorial-gallery", "annual-report"],
    },
    {
        "profile": "product-launch",
        "signals": ["product-launch", "product intro", "product deck", "app launch", "产品介绍", "产品发布", "功能发布"],
        "allowed_style_ids": [
            "apple-keynote-black",
            "apple-keynote-white",
            "mobile-app-launch-clean",
            "enterprise-saas-blue",
            "spatial-3d-product",
            "notion-workspace-clean",
            "brand-proposal-minimal",
        ],
        "allowed_aesthetic_families": ["keynote-launch", "product-launch", "product-technical", "spatial-3d", "workspace-minimal", "brand-proposal"],
    },
    {
        "profile": "technical-model",
        "signals": ["technical", "model", "ai", "architecture", "mlops", "技术", "模型", "架构", "系统方案"],
        "allowed_style_ids": [
            "technical-schematic-premium",
            "ai-lab-schematic",
            "data-product-dashboard",
            "glass-os-interface",
            "linear-axis-black",
            "blueprint-architecture",
            "cyber-clean-grid",
            "model-lifecycle-map",
        ],
        "allowed_aesthetic_families": ["technical-schematic", "data-visual", "glassmorphism-blur", "product-technical", "spatial-3d", "technology-polish"],
    },
    {
        "profile": "strategy-executive",
        "signals": ["strategy", "executive", "board", "decision", "战略", "管理层", "决策", "董事会"],
        "allowed_style_ids": [
            "mckinsey-consulting-report",
            "bain-red-dot-consulting",
            "bcg-green-impact-report",
            "deloitte-insight-minimal",
            "black-white-strategy",
            "enterprise-annual-report",
            "portfolio-thesis-premium",
        ],
        "allowed_aesthetic_families": ["consulting-report", "research-report", "annual-report", "investor-finance"],
    },
    {
        "profile": "finance-investor",
        "signals": ["finance", "investor", "fundraising", "earnings", "annual report", "财报", "投资", "融资", "路演", "业绩"],
        "allowed_style_ids": [
            "enterprise-annual-report",
            "shareholder-letter-editorial",
            "jpmorgan-financial-supplement",
            "morgan-stanley-earnings",
            "quarterly-10q-clean",
            "portfolio-thesis-premium",
            "fintech-growth-arrow",
        ],
        "allowed_aesthetic_families": ["annual-report", "financial-report", "investor-finance", "industry-finance"],
    },
    {
        "profile": "sales-gtm",
        "signals": ["sales", "gtm", "proposal", "solution", "销售", "售前", "方案", "解决方案"],
        "allowed_style_ids": [
            "brand-proposal-minimal",
            "corporate-profile-architectural",
            "business-strategy-illustrated",
            "enterprise-saas-blue",
            "mobile-app-launch-clean",
            "data-product-dashboard",
            "premium-market-survey",
        ],
        "allowed_aesthetic_families": ["brand-proposal", "company-profile", "product-technical", "product-launch", "data-visual", "research-report"],
    },
    {
        "profile": "training-enable",
        "signals": ["training", "enablement", "onboarding", "course", "培训", "新员工", "课程", "赋能"],
        "allowed_style_ids": [
            "training-tech-blue",
            "public-course-live",
            "lecture-minimal-white",
            "notion-workspace-clean",
            "math-classroom-illustration",
        ],
        "allowed_aesthetic_families": ["training", "academic", "workspace-minimal", "education-playful"],
    },
    {
        "profile": "defense-personal",
        "signals": ["defense", "promotion", "interview", "performance review", "self review", "答辩", "晋升", "面试", "述职", "个人业绩"],
        "allowed_style_ids": [
            "promotion-defense-evidence",
            "personal-performance-review",
            "interview-case-board",
            "executive-resume-blue",
            "personal-brand-editorial",
            "rigorous-academic-defense",
            "thesis-defense-clean",
        ],
        "allowed_aesthetic_families": ["personal-brand", "academic", "editorial-gallery"],
    },
    {
        "profile": "academic-research",
        "signals": ["academic", "thesis", "research", "seminar", "论文", "学术", "研究", "课题"],
        "allowed_style_ids": [
            "university-academic-formal",
            "thesis-defense-clean",
            "rigorous-academic-defense",
            "conference-dark-stage",
            "research-seminar-wave",
            "grant-report-institutional",
            "whitepaper-curve-pattern",
        ],
        "allowed_aesthetic_families": ["academic", "academic-humanities", "research-report"],
    },
]

DEFAULT_STYLE_RECOMMENDATION_POLICY = {
    "policy_id": "task-aware-style-recommendation-v1",
    "derive_from_deck_profile": True,
    "recommended_styles_must_match_deck_profile": True,
    "ask_before_using_off_profile_styles": True,
    "off_profile_requires_user_request": True,
    "fit_reason_required_per_option": True,
    "default_count_when_automatic": 4,
    "profile_style_routes": STYLE_PROFILE_ROUTES,
}

DEFAULT_STYLE_DIVERSITY_CONTRACT = {
    "policy_id": "style-lane-diversity-v1",
    "forbid_near_identical_contact_sheets": True,
    "reject_icon_only_or_color_only_variation": True,
    "require_distinct_style_ids": True,
    "require_distinct_aesthetic_families": True,
    "require_distinct_layout_archetypes": True,
    "require_distinct_evidence_presentation": True,
    "require_distinct_thumbnail_differentiators": True,
    "minimum_distinct_axes": 5,
    "required_axes": [
        "style_id",
        "aesthetic_family",
        "layout_archetype",
        "evidence_presentation",
        "composition_grammar",
        "density_and_pacing",
    ],
    "same_skeleton_blocklist": [
        "same central hub-and-spoke loop",
        "same four-card ring layout",
        "same red-white consulting dashboard",
        "same top breadcrumb plus bottom metric strip",
        "same equal-card grid with swapped icons",
    ],
}

DEFAULT_IMAGE_QUALITY_POLICY = {
    "policy_id": "imagegen-realesrgan-4k-v1",
    "enabled": True,
    "prompt_detail_level": "highest_available",
    "preferred_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_bytes": 1 * 1024 * 1024,
    "postprocess_policy": {
        "enabled": True,
        "mandatory": True,
        "normalize_every_comp": True,
        "target_px": {"width": 3840, "height": 2160},
        "local_repair_script": "scripts/realesrgan_upscale.py",
        "save_raw_imagegen_output": True,
        "raw_output_dir": "slides/raw",
        "upscaled_output_dir": "slides/upscaled",
        "final_comp_dir": "slides",
        "final_comp_suffix": "-comp.png",
        "manifest_dir": "upscale",
        "manifest_suffix": ".realesrgan.json",
        "upscale_method": "python-realesrganer",
        "realesrgan_backend": "python",
        "realesrgan_engine": "RealESRGANer",
        "realesrgan_model": "RealESRGAN_x4plus",
        "realesrgan_model_file": "RealESRGAN_x4plus.pth",
        "realesrgan_model_path": "assets/models/RealESRGAN_x4plus.pth",
        "realesrgan_device": "cpu",
        "realesrgan_tile": 400,
        "realesrgan_tile_pad": 12,
        "realesrgan_pre_pad": 0,
        "realesrgan_half": False,
        "realesrgan_kind": "comp",
        "same_output_dimensions_required": True,
        "downstream_uses_realesrgan_comp": True,
        "fallback_allowed_for_postprocess": False,
        "limitations": (
            "Every comp used for PPTX conversion must be processed by Python RealESRGANer on CPU with "
            "RealESRGAN_x4plus.pth and tile=400 to exact 3840x2160. "
            "This improves edge clarity but cannot recover text detail that ImageGen never produced; "
            "visual-clarity review remains mandatory."
        ),
    },
    "resolution_fallback_policy": {
        "enabled": True,
        "deck_wide_tier_lock": True,
        "do_not_retry_forever": True,
        "record_log_path": "imagegen_resolution_fallback_log.json",
        "tiers": [
            {
                "tier": "4k",
                "minimum_px": {"width": 3840, "height": 2160},
                "minimum_bytes": 5 * 1024 * 1024,
                "max_attempts": 2,
            },
            {
                "tier": "2k",
                "minimum_px": {"width": 2560, "height": 1440},
                "minimum_bytes": 2 * 1024 * 1024,
                "max_attempts": 1,
            },
            {
                "tier": "1080p",
                "minimum_px": {"width": 1920, "height": 1080},
                "minimum_bytes": 1 * 1024 * 1024,
                "max_attempts": 1,
            },
        ],
        "never_accept_below_px": {"width": 1920, "height": 1080},
        "fallback_requires_reason": True,
    },
    "minimum_acceptable_contact_sheet_px": {"width": 2400, "height": 1350},
    "prompt_requires_crisp_text_and_icons": True,
    "review_required_before_pptx": True,
    "small_text_policy": (
        "Avoid unreadable microtext in ImageGen comps. Main titles, key numbers, labels, "
        "and page markers must be sharp enough for visual review. Body text should be designed "
        "for an editable PPT reading target of at least 10-11pt; exact final small copy comes "
        "from deck_spec.json during PPTX conversion."
    ),
    "blur_rejection_criteria": [
        "soft or blurry main title",
        "blurred key numbers",
        "muddy icons or line art",
        "low-contrast small labels",
        "compression artifacts around text or diagram strokes",
    ],
}

DEFAULT_SLIDE_COMP_REVIEW_POLICY = {
    "enabled": True,
    "required_before_pptx": True,
    "require_subagent_review": True,
    "evidence_dir": "qa/reviews/slide-comp",
    "reviewer_modes_allowed": ["subagent", "main_agent_role_review"],
    "fallback_requires_reason": True,
    "block_on_unresolved_p0_p1": True,
    "required_roles": [
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

DEFAULT_COMP_STYLE_LOCK = {
    "source": "",
    "dimensions_px": {"width": 3840, "height": 2160},
    "chrome_locked": True,
    "locked_chrome_elements": [
        "logo",
        "section label",
        "header rule",
        "footer",
        "page number",
        "page marker",
        "title furniture",
    ],
    "consistency_requirements": [
        "same page number placement and format",
        "same logo placement and size",
        "same header/footer system",
        "same section label treatment",
        "same recurring typography scale",
        "same border/background/chrome rhythm",
    ],
    "generation_owner": "main_agent",
}

DEFAULT_STRICT_ICON_POLICY = {
    "enabled": True,
    "manifest_path": "icons/icon_jobs.json",
    "extractor_script": "iconcut3.py",
    "transparent_png_required": True,
    "edge_audit_required": True,
    "contact_sheet_audit_required": True,
    "clip_error_fails_closed": True,
    "no_manual_crop_fallback": True,
    "source_icon_inventory_required": True,
    "real_source_icons_must_be_extracted": True,
    "native_redraw_for_named_pictograms_forbidden": True,
    "glyph_helpers_are_placeholder_only": True,
    "icon_hd_enhancement_required": True,
    "icon_hd_target_min_px": 256,
    "realesrgan_upscale_required": True,
    "icon_upscale_method": "python-realesrganer",
    "realesrgan_backend": "python",
    "realesrgan_engine": "RealESRGANer",
    "realesrgan_model": "RealESRGAN_x4plus",
    "realesrgan_model_file": "RealESRGAN_x4plus.pth",
    "realesrgan_model_path": "assets/models/RealESRGAN_x4plus.pth",
    "realesrgan_device": "cpu",
    "realesrgan_tile": 400,
    "realesrgan_tile_pad": 12,
    "realesrgan_pre_pad": 0,
    "realesrgan_half": False,
    "icon_upscale_script": "scripts/realesrgan_upscale.py",
    "icon_upscale_manifest_path": "icons/icon_upscale_manifest.json",
    "placement_source_dir": "icons/upscaled",
    "feathered_slices_preserve_alpha": True,
    "minimum_output_icon_min_dim_px": 256,
    "default_padding_px": 10,
    "wide_asset_text_label_flag_aspect_gt": 2.5,
    "allow_feathered_opaque_slices_for_inseparable_art": True,
    "notes": (
        "Before PPTX conversion, inventory recognizable source pictograms and crop them with iconcut3.strict_cut3. "
        "Strict line-art icons must be supersampled/sharpened, then passed through Python RealESRGANer on CPU before placement; "
        "feathered opaque slices must preserve their soft alpha. "
        "A clean alpha edge is not enough; the contact sheet must also prove every asset is a pictogram and not a boxed text label. "
        "slidelib glyph helpers are placeholder scaffolding only, not a fidelity path for named source icons."
    ),
}

DEFAULT_RENDER_COMPARE_LOOP = {
    "enabled": True,
    "minimum_rounds": 10,
    "rounds_log_path": "qa/render-compare/render_compare_rounds.json",
    "render_log_path": "qa/render-compare/render_log.json",
    "compare_against": "approved slide image or generated comp",
    "paired_crops_required": True,
    "region_diff_normal_band_max_mean_abs": 35,
    "region_diff_blocking_mean_abs": 40,
    "markitdown_text_check_recommended": True,
    "block_on_unresolved_p0_p1": True,
    "round_requires_new_export": True,
    "qa_gate_script": "qa_gate.py",
    "metrics_source": "qa_gate.py metrics",
    "media_audit_required": True,
}

DEFAULT_CONVERSION_POLICY = {
    "enabled": True,
    "method": "strict_slide_image_to_editable_pptx",
    "builder_script": "slidelib.py",
    "icon_extractor_script": "iconcut3.py",
    "qa_gate_script": "qa_gate.py",
    "pitfalls_reference": "PITFALLS.md",
    "realesrgan_upscale_script": "scripts/realesrgan_upscale.py",
    "realesrgan_backend": "python",
    "realesrgan_engine": "RealESRGANer",
    "realesrgan_model_file": "RealESRGAN_x4plus.pth",
    "realesrgan_device": "cpu",
    "realesrgan_tile": 400,
    "realesrgan_tile_pad": 12,
    "realesrgan_pre_pad": 0,
    "realesrgan_half": False,
    "basis_px": {"width": 1920, "height": 1080},
    "source_image_is_measurement_target": True,
    "source_comp_realesrgan_4k_required": True,
    "full_image_backgrounds_allowed": False,
    "region_image_backgrounds_allowed": False,
    "native_text_required": True,
    "native_shapes_required": True,
    "native_charts_tables_connectors_required": True,
    "only_complex_art_may_be_images": True,
    "multiline_text_split_required": True,
    "automatic_text_wrap_for_multiline_forbidden": True,
    "strict_icon_extraction_required": True,
    "icon_contact_sheet_audit_required": True,
    "real_source_icons_must_be_extracted": True,
    "native_redraw_for_named_pictograms_forbidden": True,
    "icon_hd_enhancement_required": True,
    "icon_realesrgan_upscale_required": True,
    "minimum_render_compare_rounds": 10,
    "render_round_requires_new_export": True,
    "qa_gate_required": True,
    "metrics_gate_reads_actual_render": True,
    "media_audit_required": True,
    "notes": (
        "Measure the approved slide image, extract icons strictly, build native PPTX with slidelib, "
        "then render and compare until paired crops and region metrics converge. "
        "The approved slide image must be the exact 3840x2160 Python RealESRGANer CPU output."
    ),
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
        "slides/raw",
        "slides/upscaled",
        "upscale",
        "assets",
        "assets/icons",
        "icons",
        "icons/upscaled",
        "icon-sheets",
        "measurements",
        "crops",
        "preview",
        "styles",
        "layout",
        "scripts",
        "builders",
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
        "qa/render-compare",
        "prompts",
        "slide-modules",
        "output",
    ]
    for name in dirs:
        (workspace / name).mkdir(parents=True, exist_ok=True)

    skill_dir = Path(__file__).resolve().parents[1]
    copied_tools: dict[str, bool] = {}
    for filename in ("slidelib.py", "iconcut3.py", "qa_gate.py", "PITFALLS.md"):
        source = skill_dir / filename
        destination = workspace / filename
        if source.exists():
            shutil.copy2(source, destination)
            copied_tools[filename] = destination.exists()
        else:
            copied_tools[filename] = False
    script_source = skill_dir / "scripts" / "realesrgan_upscale.py"
    script_destination = workspace / "scripts" / "realesrgan_upscale.py"
    if script_source.exists():
        shutil.copy2(script_source, script_destination)
        copied_tools["scripts/realesrgan_upscale.py"] = script_destination.exists()
    else:
        copied_tools["scripts/realesrgan_upscale.py"] = False

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
            "conversion_manifest": "conversion_manifest.json",
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
            "sources": [BUILT_IN_TASTE_SOURCE, BUILT_IN_STYLE_LIBRARY_SOURCE],
            "portable_rules": BUILT_IN_TASTE_RULES,
            "ppt_translation_notes": [
                "The built-in taste system is static PPT guidance, not a web interaction system",
                "Frontend-only hover/GSAP/responsive rules from optional external sources are not PPT constraints",
                "The built-in style library provides visual direction ids, not permission to use third-party logos or imply affiliation",
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
        "deck_profile_evidence": {
            "primary_profile": "",
            "secondary_profiles": [],
            "audience": "",
            "occasion": "",
            "source_signals": [],
            "excluded_style_families": [],
            "notes": "",
        },
        "style_recommendation_policy": DEFAULT_STYLE_RECOMMENDATION_POLICY,
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
            "requested_style_ids": [],
            "forbidden_aesthetic_families": [],
            "forbidden_style_ids": [],
            "notes": "",
        },
        "style_library": {
            "enabled": True,
            "sources": [BUILT_IN_STYLE_LIBRARY_SOURCE],
            "selection_rule": (
                "Recommend concrete style_id values from references/style-library.md. "
                "Use custom-* only for user-specified styles not covered by the library."
            ),
            "default_source": "built-in-style-library",
            "allow_custom_style_ids": True,
            "must_not_use_third_party_logos_without_assets": True,
            "style_options_must_remain_visual_only": True,
            "reference_screenshot_categories": [
                "workplace",
                "company-business",
                "consulting-research",
                "finance-investor",
                "industry-solutions",
                "education-academic",
                "creative-brand",
                "personal",
                "lifestyle",
            ],
        },
        "diversity_contract": DEFAULT_STYLE_DIVERSITY_CONTRACT,
        "taste_guidance": {
            "enabled": True,
            "sources": [
                {
                    "name": BUILT_IN_TASTE_SOURCE["name"],
                    "path": BUILT_IN_TASTE_SOURCE["path"],
                    "used_for": "direction diversity, ImageGen art direction, anti-generic review, conversion fidelity",
                },
                {
                    "name": BUILT_IN_STYLE_LIBRARY_SOURCE["name"],
                    "path": BUILT_IN_STYLE_LIBRARY_SOURCE["path"],
                    "used_for": "canonical style ids and concrete style signatures",
                }
            ],
            "style_principles": [
                "each direction differs by visual aesthetic only: art style, material, depth, typography feel, icon/illustration style, chart rendering, composition rhythm, and density",
                "each direction must match the actual deck task, audience, and occasion before it is recommended",
                "multi-style runs must use visibly different layout archetypes and evidence presentation patterns, not only swapped icons, colors, line styles, or small modules",
                "style lanes must not rename or replace the selected narrative treatment, slide content, claim, data, or proof object",
                "single-slide comps must preserve a clear visual archetype",
                "PPTX conversion must retain the approved comp's reader-facing visual grammar",
            ],
            "anti_patterns": BUILT_IN_TASTE_ANTI_PATTERNS,
            "profile_specific_direction_notes": [],
        },
        "diversity_axes": [
            "aesthetic family",
            "task fit and audience fit",
            "layout archetype",
            "evidence presentation pattern",
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
        "selected_options": [],
        "pptx_conversion_selection": {
            "mode": "ask_user | full_automation",
            "selected_style_lane_ids": [],
            "allow_multiple_output_decks": True,
            "user_selection_note": "",
        },
        "option_safety_status": "not_started",
        "image_quality_policy": DEFAULT_IMAGE_QUALITY_POLICY,
        "imagegen_failure_policy": DEFAULT_IMAGEGEN_FAILURE_POLICY,
        "imagegen_retry_log": "imagegen_retry_log.json",
    }
    imagegen_retry_log = {
        "policy_ref": "style_brief.json.imagegen_failure_policy",
        "attempts": [],
    }
    imagegen_resolution_fallback_log = {
        "policy_ref": "style_brief.json.image_quality_policy.resolution_fallback_policy",
        "attempts": [],
        "selected_deck_wide_tier": "",
        "notes": "",
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
        "selected_styles": [],
        "contact_sheet": "",
        "template_mode": "hard" if args.mode == "template-following" else "none",
        "template_contact_sheet": "",
        "template_frame_map": "template-frame-map.json",
        "per_slide_comps_complete": False,
        "comp_generation_mode": "main_agent_serial_imagegen",
        "parallel_style_agents_used": False,
        "parallel_page_subagents_used": False,
        "explicit_parallel_comp_generation_accepted": False,
        "comp_style_lock": DEFAULT_COMP_STYLE_LOCK,
        "style_runs": [],
        "pptx_conversion_selection": {
            "selected_style_lane_ids": [],
            "produce_one_pptx_per_selected_style": True,
            "output_naming_rule": "output/<deck-slug>-<style-lane-id>.pptx",
        },
        "downgrade_mode": False,
        "explicit_downgrade_accepted": False,
        "comp_is_conversion_target": True,
        "conversion_method": "strict_slide_image_to_editable_pptx",
        "minimum_non_title_rich_visual_ratio": 0.6,
        "image_quality_policy": DEFAULT_IMAGE_QUALITY_POLICY,
        "slide_comp_review_policy": DEFAULT_SLIDE_COMP_REVIEW_POLICY,
        "conversion_policy": DEFAULT_CONVERSION_POLICY,
        "strict_icon_policy": DEFAULT_STRICT_ICON_POLICY,
        "render_compare_loop": DEFAULT_RENDER_COMPARE_LOOP,
        "slides": [],
    }
    conversion_manifest = {
        "lock_state": "draft",
        "mode": args.mode,
        "source": "user_supplied_slide_images" if args.mode in {"reconstruction-only", "repair-existing-pptx"} else "approved_imagegen_comps",
        "conversion_method": "strict_slide_image_to_editable_pptx",
        "tool_files": {
            "slidelib": "slidelib.py",
            "iconcut3": "iconcut3.py",
            "qa_gate": "qa_gate.py",
            "realesrgan_upscale": "scripts/realesrgan_upscale.py",
            "pitfalls": "PITFALLS.md",
            "copied_to_workspace": copied_tools,
        },
        "basis_px": {"width": 1920, "height": 1080},
        "slide_count": 0,
        "page_modules": {
            "enabled": args.mode in {"reconstruction-only", "repair-existing-pptx"},
            "per_slide_pptx_required": True,
            "merge_after_page_approval": True,
            "parallel_subagents_recommended": True,
        },
        "global_rules": {
            "skip_full_pipeline_gates": args.mode in {"reconstruction-only", "repair-existing-pptx"},
            "visual_fidelity_priority": "strict_slide_image_to_editable_pptx",
            "source_image_is_measurement_target_not_final_layer": True,
            "source_comp_realesrgan_4k_required": True,
            "full_image_or_region_layers_forbidden": True,
            "ordinary_table_or_card_rebuild_forbidden": True,
            "native_text_shapes_charts_required": True,
            "hidden_text_layer_does_not_count_as_editable": True,
            "strict_icon_extraction_required": True,
            "icon_contact_sheet_audit_required": True,
            "source_icon_inventory_required": True,
            "real_source_icons_must_be_extracted": True,
            "native_redraw_for_named_pictograms_forbidden": True,
            "icon_hd_enhancement_required": True,
            "icon_realesrgan_upscale_required": True,
            "multiline_text_split_required": True,
            "minimum_render_compare_rounds": DEFAULT_RENDER_COMPARE_LOOP["minimum_rounds"],
            "render_round_requires_new_export": True,
            "qa_gate_required": True,
            "metrics_gate_reads_actual_render": True,
            "media_audit_required": True,
        },
        "slides": [],
        "open_questions": [],
    }
    icon_jobs = {
        "status": "draft",
        "policy_ref": "visual_contract.json.strict_icon_policy",
        "source_coordinate_space_px": {"width": 1920, "height": 1080},
        "extractor_script": "iconcut3.py",
        "default_padding_px": DEFAULT_STRICT_ICON_POLICY["default_padding_px"],
        "minimum_output_icon_min_dim_px": DEFAULT_STRICT_ICON_POLICY["minimum_output_icon_min_dim_px"],
        "icon_hd_enhancement_required": DEFAULT_STRICT_ICON_POLICY["icon_hd_enhancement_required"],
        "icon_hd_target_min_px": DEFAULT_STRICT_ICON_POLICY["icon_hd_target_min_px"],
        "realesrgan_upscale_required": DEFAULT_STRICT_ICON_POLICY["realesrgan_upscale_required"],
        "icon_upscale_method": DEFAULT_STRICT_ICON_POLICY["icon_upscale_method"],
        "realesrgan_backend": DEFAULT_STRICT_ICON_POLICY["realesrgan_backend"],
        "realesrgan_engine": DEFAULT_STRICT_ICON_POLICY["realesrgan_engine"],
        "realesrgan_model": DEFAULT_STRICT_ICON_POLICY["realesrgan_model"],
        "realesrgan_model_file": DEFAULT_STRICT_ICON_POLICY["realesrgan_model_file"],
        "realesrgan_model_path": DEFAULT_STRICT_ICON_POLICY["realesrgan_model_path"],
        "realesrgan_device": DEFAULT_STRICT_ICON_POLICY["realesrgan_device"],
        "realesrgan_tile": DEFAULT_STRICT_ICON_POLICY["realesrgan_tile"],
        "realesrgan_tile_pad": DEFAULT_STRICT_ICON_POLICY["realesrgan_tile_pad"],
        "realesrgan_pre_pad": DEFAULT_STRICT_ICON_POLICY["realesrgan_pre_pad"],
        "realesrgan_half": DEFAULT_STRICT_ICON_POLICY["realesrgan_half"],
        "icon_upscale_script": DEFAULT_STRICT_ICON_POLICY["icon_upscale_script"],
        "icon_upscale_manifest_path": DEFAULT_STRICT_ICON_POLICY["icon_upscale_manifest_path"],
        "placement_source_dir": DEFAULT_STRICT_ICON_POLICY["placement_source_dir"],
        "feathered_slices_preserve_alpha": DEFAULT_STRICT_ICON_POLICY["feathered_slices_preserve_alpha"],
        "feathered_slices": [],
        "icons": [],
        "extracted": [],
        "exceptions": [],
    }
    render_compare_rounds = {
        "status": "not_started",
        "policy_ref": "visual_contract.json.render_compare_loop",
        "minimum_rounds": DEFAULT_RENDER_COMPARE_LOOP["minimum_rounds"],
        "completed_rounds": 0,
        "rounds": [],
        "paired_crops": [],
        "region_metrics": [],
        "unresolved_p0_p1": [],
    }
    render_log: list[dict] = []

    files = {
        "pipeline_state.json": json.dumps(pipeline_state, ensure_ascii=False, indent=2) + "\n",
        "deck_spec.json": json.dumps(deck_spec, ensure_ascii=False, indent=2) + "\n",
        "design_system.json": json.dumps(design_system, ensure_ascii=False, indent=2) + "\n",
        "slide_intent_plan.json": json.dumps(slide_intent_plan, ensure_ascii=False, indent=2) + "\n",
        "narrative_plan.json": json.dumps(narrative_plan, ensure_ascii=False, indent=2) + "\n",
        "style_brief.json": json.dumps(style_brief, ensure_ascii=False, indent=2) + "\n",
        "imagegen_retry_log.json": json.dumps(imagegen_retry_log, ensure_ascii=False, indent=2) + "\n",
        "imagegen_resolution_fallback_log.json": json.dumps(
            imagegen_resolution_fallback_log,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "template-frame-map.json": json.dumps(template_frame_map, ensure_ascii=False, indent=2) + "\n",
        "visual_contract.json": json.dumps(visual_contract, ensure_ascii=False, indent=2) + "\n",
        "conversion_manifest.json": json.dumps(conversion_manifest, ensure_ascii=False, indent=2) + "\n",
        "icons/icon_jobs.json": json.dumps(icon_jobs, ensure_ascii=False, indent=2) + "\n",
        "qa/render-compare/render_compare_rounds.json": json.dumps(render_compare_rounds, ensure_ascii=False, indent=2) + "\n",
        "qa/render-compare/render_log.json": json.dumps(render_log, ensure_ascii=False, indent=2) + "\n",
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
            "## PPTX Conversion Gate\n\n"
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
        "conversion_manifest": str(workspace / "conversion_manifest.json"),
        "slidelib": str(workspace / "slidelib.py"),
        "iconcut3": str(workspace / "iconcut3.py"),
        "qa_gate": str(workspace / "qa_gate.py"),
        "pitfalls": str(workspace / "PITFALLS.md"),
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
