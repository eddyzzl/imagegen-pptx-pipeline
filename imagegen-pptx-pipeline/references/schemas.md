# Schemas

Use these structures as the stable handoff between phases. Keep them compact but complete.

## pipeline_state.json

Write this before every user-facing pause and update it at every stage transition.

```json
{
  "skill": "imagegen-pptx-pipeline",
  "workspace": "/absolute/path/to/workspace",
  "title": "Deck title",
  "mode": "create | template-following | targeted-edit | reconstruction-only | repair-existing-pptx",
  "current_stage": "initialized | input_reading | reconstruction_input_lock | content_gate | slide_intent_lock | narrative_selection | style_count | style_selection | single_slide_comps | multi_style_comp_selection | slide_comp_review | visual_contract | page_reconstruction | pptx_reconstruction | final_review | complete",
  "awaiting_user": false,
  "required_user_reply": "",
  "next_action": "",
  "resume_instructions": "Read pipeline_state.json, deck_spec.json, user_decisions.md, then continue this stage; do not restart unless the user requests a restart.",
  "last_completed_artifacts": {
    "deck_spec": "deck_spec.json",
    "design_system": "design_system.json",
    "slide_intent_plan": "slide_intent_plan.json",
    "narrative_plan": "narrative_plan.json",
    "style_brief": "style_brief.json",
    "selected_style": "",
    "visual_contract": "visual_contract.json",
    "latest_preview": ""
  },
  "stage_history": [
    {
      "stage": "content_gate",
      "status": "waiting_for_user | completed | needs_iteration | blocked",
      "timestamp": "ISO-8601",
      "notes": ""
    }
  ]
}
```

Rules:

- If `awaiting_user` is true, do not continue until the user answers or explicitly asks for full automation.
- Generic delegation such as "帮我做 PPT" does not count as explicit full automation.
- On resume, append the answer to `user_decisions.md`, set `awaiting_user=false`, and continue from `next_action`.
- Do not reinitialize or discard artifacts when this file exists and points to the current task.

## deck_spec.json

```json
{
  "deck": {
    "title": "Deck title",
    "audience": "board | investor | executive | sales | training | other",
    "objective": "What the deck must accomplish",
    "deck_profile": "product-pitch | company-profile | model-technical | sales-gtm | strategy-executive | investor-finance | training-enable | internal-review | other",
    "content_input_type": "explicit_per_page | brief_outline | template_only | reference_only | mixed",
    "language": "zh-CN",
    "aspect_ratio": "16:9",
    "mode": "create | template-following | targeted-edit | reconstruction-only | repair-existing-pptx",
    "slide_count": 0,
    "lock_state": "draft | needs_user_confirmation | locked"
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
    "content_confirmation_required": true
  },
  "profile_requirements": {
    "primary_profile": "",
    "secondary_profiles": [],
    "required_proof_objects": [],
    "source_requirements": [],
    "visual_density": "low | medium | high",
    "audience_tolerance_for_complexity": "low | medium | high"
  },
  "slides": [
    {
      "slide_id": "slide-001",
      "page_number": 1,
      "section": "Section name",
      "title": "Exact title",
      "claim": "One-sentence slide takeaway",
      "body_text": ["Exact bullet or paragraph text"],
      "data": [
        {
          "label": "Metric name",
          "value": "Exact value",
          "unit": "%",
          "source_id": "source-001"
        }
      ],
      "proof_object": "chart | table | process | timeline | image | diagram | comparison | quote",
      "proof_object_strength": "weak | adequate | strong",
      "visual_intent": "What the visual should communicate",
      "visual_expression_must_preserve": "loop | radial | system map | maturity arc | funnel | dashboard | process chain | table | other",
      "layout_hint": "Optional composition guidance",
      "template_source_slide": "source slide id when template-following",
      "template_required_elements": ["logo", "footer", "page marker", "section label"],
      "visual_comp_required": true,
      "comp_path": "slides/slide-001-comp.png",
      "comp_review_status": "not_started | needs_iteration | approved | user_accepted_risk",
      "pptx_restoration_status": "not_started | preview_failed | needs_iteration | approved",
      "editable_text": ["title", "body_text", "data labels", "footer", "page_number"],
      "image_assets": [
        {
          "asset_id": "asset-001",
          "role": "photo | logo | icon | screenshot | texture | generated",
          "source": "user-provided | verified-url | generated",
          "required": false
        }
      ],
      "speaker_notes": "",
      "open_questions": []
    }
  ],
  "sources": [
    {
      "source_id": "source-001",
      "title": "Source name",
      "path_or_url": "",
      "date": "",
      "notes": ""
    }
  ]
}
```

Lock rules:

- `draft`: inputs are still being parsed or the story is incomplete.
- `needs_user_confirmation`: there are blocking questions or assumptions that need user approval before visual generation.
- `locked`: content is approved for ImageGen. Do not set this if P0/P1 content findings remain unresolved.

## design_system.json

```json
{
  "mode": "create | template-following | targeted-edit",
  "deck_profile": "product-pitch | company-profile | model-technical | sales-gtm | strategy-executive | investor-finance | training-enable | internal-review | other",
  "template_constraints": {
    "source_pptx": "",
    "template_mode": "none | hard",
    "template_contact_sheet": "",
    "template_frame_map": "template-frame-map.json",
    "preserve_master": true,
    "preserve_footer": true,
    "preserve_logo": true,
    "preserve_page_markers": true,
    "preserve_title_furniture": true,
    "protected_elements": [],
    "allowed_deviations": []
  },
  "palette": {
    "primary": [],
    "secondary": [],
    "neutral": [],
    "semantic": {}
  },
  "typography": {
    "title": {"font": "", "weight": "", "size_range": ""},
    "body": {"font": "", "weight": "", "size_range": ""},
    "numbers": {"font": "", "weight": "", "size_range": ""}
  },
  "layout": {
    "aspect_ratio": "16:9",
    "grid": "",
    "safe_margins": "",
    "footer_rule": "",
    "page_number_rule": ""
  },
  "visual_language": {
    "backgrounds": "",
    "cards": "",
    "charts": "",
    "icons": "",
    "photography": "",
    "texture_depth": "",
    "visual_ambition": "restrained | polished | premium | cinematic-business",
    "avoid_visual_regressions": [
      "flat table-only deck",
      "generic equal-card grid",
      "default PPT template feel",
      "near-identical style options"
    ]
  },
  "taste_guidance": {
    "enabled": true,
    "sources": [
      {
        "name": "built-in-ppt-taste-system",
        "path": "references/taste-system.md",
        "used_for": "style exploration | comp review | PPTX reconstruction QA | anti-default QA",
        "constraints_used": [
          "avoid flat table-only decks when richer proof objects fit",
          "require profile-appropriate visual archetypes",
          "preserve ImageGen comp visual grammar during PPTX reconstruction"
        ],
        "constraints_ignored": []
      }
    ],
    "portable_rules": [
      "Avoid generic equal-card grids unless the content requires a matrix",
      "Use intentional whitespace and hierarchy, not decoration",
      "Prefer crafted diagrams and focal objects over default boxes",
      "Use one dominant proof object per slide",
      "Keep template-following designs inside protected template frames"
    ],
    "ppt_translation_notes": [
      "The built-in taste system is static PPT guidance, not a web interaction system",
      "Frontend-only hover/GSAP/responsive rules from optional external sources are not PPT constraints"
    ]
  },
  "reference_patterns": [
    {
      "source": "reference deck or slide id",
      "pattern": "What to borrow",
      "avoid": "What not to copy"
    }
  ],
  "asset_rules": {
    "identity_assets": "Use verified or user-provided only",
    "generated_assets": "Allowed for non-identity illustrative material",
    "image_retention": "Preserve complex visuals as images when native rebuild would reduce quality"
  }
}
```

## slide_intent_plan.json

Use after content/source review and before narrative treatment. This file owns the user-confirmed page intent: what each slide is trying to say and how it can be proven. It does not need final polished copy.

```json
{
  "lock_state": "draft | needs_user_confirmation | locked",
  "source_deck_spec_fingerprint": "sha256:<hash of invariant deck fields>",
  "matrix_path": "slide_intent_matrix.md",
  "selection_mode": "ask_user | full_automation",
  "review_status": "not_started | needs_iteration | approved | user_accepted_risk",
  "slides": [
    {
      "slide_id": "slide-001",
      "page_number": 1,
      "proposed_title": "Exact or proposed title",
      "confirmed_title": "User-confirmed title",
      "core_idea": "The one thing this page must make the audience believe",
      "proof_goal": "What must be proven for the core idea to hold",
      "content_scope": ["what this slide should include", "what it should not include"],
      "evidence_candidates": [
        {
          "source_id": "source-001",
          "source_path": "input/source.pdf",
          "evidence": "Metric, fact, quote, case, chart input, or artifact available in supplied materials",
          "confidence": "low | medium | high",
          "usage": "primary proof | supporting detail | optional"
        }
      ],
      "data_to_extract": ["metric or table still to extract from supplied materials"],
      "content_gaps": ["missing user confirmation or source gap"],
      "accepted_assumptions": [],
      "status": "draft | needs_user | confirmed | accepted_assumption"
    }
  ],
  "open_questions": []
}
```

Rules:

- `slide_intent_matrix.md` must have one row per slide and columns: page, proposed title, core idea, proof goal, evidence/data candidates, gaps/questions, confidence.
- Every slide must have `confirmed_title`, `core_idea`, `proof_goal`, and either evidence candidates or accepted assumptions before narrative treatment.
- If the user only supplied a brief outline, the agent should infer proposed slide intent from all supplied materials and ask for confirmation.
- If the user supplied exact per-page content, do not rewrite broadly; confirm intent and source coverage.
- This stage may leave final wording incomplete, but not the slide's purpose.

## narrative_plan.json

Use after content lock and before any ImageGen style generation. This file owns the selected presentation narrative, while `deck_spec.json` still owns source truth.

```json
{
  "lock_state": "draft | needs_user_confirmation | locked",
  "source_deck_spec_fingerprint": "sha256:<hash of invariant deck fields>",
  "slide_intent_plan": "slide_intent_plan.json",
  "slide_intent_lock_state": "locked",
  "matrix_path": "narrative_matrix.md",
  "selection_mode": "ask_user | full_automation",
  "selected_narrative_id": "",
  "user_selection_note": "",
  "narrative_options": [
    {
      "narrative_id": "evidence-first",
      "name": "Evidence-first",
      "premise": "Lead with claim and proof on each slide for fast executive review",
      "best_for": "executive decision, internal review, board update",
      "tradeoffs": "Less emotional build-up; strongest for source-backed decisions"
    },
    {
      "narrative_id": "technical-system",
      "name": "Technical system",
      "premise": "Show mechanism, architecture, process, validation, and operational control",
      "best_for": "model, AI, engineering, risk, platform, technical product",
      "tradeoffs": "More diagram density; requires audience tolerance for complexity"
    }
  ],
  "slides": [
    {
      "slide_id": "slide-001",
      "page_number": 1,
      "title": "Exact title from deck_spec",
      "confirmed_core_idea": "Copied from slide_intent_plan",
      "selected_treatment": {
        "narrative_id": "evidence-first",
        "presentation_strategy": "Lead with the strongest result, then show source-backed proof",
        "content_to_show": ["claim", "2-3 evidence bullets", "key metric"],
        "proof_object_expression": "scorecard plus short evidence strip",
        "emphasis": "decision-ready impact",
        "must_preserve": ["title meaning", "claim", "metric values", "source IDs"],
        "visual_notes_for_style_lanes": "Any aesthetic family should keep the scorecard/evidence relationship"
      },
      "option_cells": [
        {
          "narrative_id": "evidence-first",
          "cell_markdown": "Lead with result; show key metric as scorecard; keep evidence strip below."
        },
        {
          "narrative_id": "technical-system",
          "cell_markdown": "Frame as mechanism; show process/control map; keep same claim and metrics."
        }
      ]
    }
  ],
  "review_status": "not_started | needs_iteration | approved",
  "open_questions": []
}
```

Rules:

- `narrative_matrix.md` must have one row per slide and one column per narrative option.
- Every cell must explain how the slide is presented and which content/proof is shown.
- `slide_intent_plan.json.lock_state` must be `locked` before this file can be locked.
- `selected_treatment` must be populated for every slide before visual style generation.
- The selected narrative may change presentation strategy, emphasis, and proof-object expression, but not source truth, claims, metrics, sources, or slide order.
- If the user edits individual cells, update `selected_treatment` and record the decision in `user_decisions.md`.

## style_brief.json

Use after narrative lock and before style contact-sheet ImageGen calls.

```json
{
  "direction_count": 4,
  "user_requested_count": null,
  "selection_mode": "ask_user | full_automation",
  "full_automation_trigger": "exact user wording or empty",
  "generation_mode": "parallel_style_lanes | sequential_style_lanes | single_prompt_fallback",
  "style_variation_scope": "visual_aesthetic_only",
  "content_strategy_locked": true,
  "visual_ambition": "premium executive business deck with template fidelity",
  "deck_profile": "product-pitch | company-profile | model-technical | sales-gtm | strategy-executive | investor-finance | training-enable | internal-review | other",
  "template_is_hard_constraint": true,
  "selected_narrative_id": "evidence-first",
  "narrative_lock": {
    "source": "deck_spec.json",
    "slide_intent_plan": "slide_intent_plan.json",
    "slide_intent_lock_state": "locked",
    "narrative_plan": "narrative_plan.json",
    "deck_spec_fingerprint": "sha256:<hash of invariant deck fields>",
    "narrative_plan_lock_state": "locked",
    "locked_slide_count": 12,
    "locked_slide_order": ["slide-001", "slide-002"],
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
      "template_source_slide"
    ],
    "slide_order_locked": true,
    "section_flow_locked": true,
    "titles_locked": true,
    "claims_locked": true,
    "required_data_locked": true,
    "core_proof_objects_locked": true,
    "allowed_style_adaptations": [
      "change visual archetype expression while preserving proof-object intent",
      "adjust density, depth, material, diagram grammar, and pacing",
      "change chart/diagram styling without changing data or source meaning"
    ],
    "forbidden_story_changes": [
      "add/delete/reorder slides",
      "replace claims",
      "invent metrics or sources",
      "change deck objective",
      "turn a content proof object into a different narrative point",
      "ignore the selected narrative treatment"
    ]
  },
  "user_style_preferences": {
    "requested_aesthetic_families": [],
    "forbidden_aesthetic_families": [],
    "notes": ""
  },
  "taste_guidance": {
    "enabled": true,
    "sources": [
      {
        "name": "built-in-ppt-taste-system",
        "path": "references/taste-system.md",
        "used_for": "direction diversity, ImageGen art direction, anti-generic review, reconstruction fidelity"
      }
    ],
    "style_principles": [
      "each direction differs by visual aesthetic only: art style, material, depth, typography feel, icon/illustration style, chart rendering, composition rhythm, and density",
      "style lanes must not rename or replace the selected narrative treatment, slide content, claim, data, or proof object",
      "single-slide comps must preserve a clear visual archetype",
      "PPTX reconstruction must retain the approved comp's reader-facing visual grammar"
    ],
    "anti_patterns": [
      "near-identical style options",
      "flat table-only deck",
      "generic equal-card grid",
      "default PPT template feel",
      "flat image-only slide without editable overlays"
    ],
    "profile_specific_direction_notes": []
  },
    "image_quality_policy": {
    "policy_id": "imagegen-max-clarity-v1",
    "enabled": true,
    "prompt_detail_level": "highest_available",
    "preferred_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_px": {"width": 1920, "height": 1080},
    "minimum_acceptable_comp_bytes": 1048576,
    "postprocess_policy": {
      "enabled": true,
      "normalize_every_comp": true,
      "target_px": {"width": 3840, "height": 2160},
      "local_repair_script": "scripts/normalize_slide_comp.py",
      "save_raw_imagegen_output": true,
      "raw_output_dir": "slides/raw",
      "normalized_output_suffix": "-comp.png",
      "upscale_method": "lanczos",
      "sharpen_after_resize": true,
      "same_output_dimensions_required": true,
      "downstream_uses_normalized_comp": true,
      "limitations": "Local repair standardizes and sharpens comps but cannot recover text detail not present in the raw image."
    },
    "resolution_fallback_policy": {
      "enabled": true,
      "deck_wide_tier_lock": true,
      "do_not_retry_forever": true,
      "record_log_path": "imagegen_resolution_fallback_log.json",
      "tiers": [
        {
          "tier": "4k",
          "minimum_px": {"width": 3840, "height": 2160},
          "minimum_bytes": 5242880,
          "max_attempts": 2
        },
        {
          "tier": "2k",
          "minimum_px": {"width": 2560, "height": 1440},
          "minimum_bytes": 2097152,
          "max_attempts": 1
        },
        {
          "tier": "1080p",
          "minimum_px": {"width": 1920, "height": 1080},
          "minimum_bytes": 1048576,
          "max_attempts": 1
        }
      ],
      "never_accept_below_px": {"width": 1920, "height": 1080},
      "fallback_requires_reason": true
    },
    "minimum_acceptable_contact_sheet_px": {"width": 2400, "height": 1350},
    "prompt_requires_crisp_text_and_icons": true,
    "review_required_before_pptx": true,
    "small_text_policy": "Avoid unreadable microtext in ImageGen comps; exact final small text comes from deck_spec.json during PPTX reconstruction.",
    "blur_rejection_criteria": [
      "soft or blurry main title",
      "blurred key numbers",
      "muddy icons or line art",
      "low-contrast small labels",
      "compression artifacts around text or diagram strokes"
    ]
  },
  "imagegen_failure_policy": {
    "policy_id": "imagegen-fail-closed-v1",
    "enabled": true,
    "fail_closed": true,
    "max_retries_per_asset": 2,
    "prompt_compression_allowed": true,
    "prompt_compression_scope": [
      "remove duplicated source prose",
      "remove internal reasoning",
      "remove repeated constraints",
      "summarize verbose citations while preserving source IDs"
    ],
    "prompt_compression_must_preserve": [
      "locked slide order",
      "slide titles",
      "core claims",
      "required data",
      "proof-object intent",
      "template constraints",
      "visual density floor",
      "aesthetic family"
    ],
    "content_density_may_be_reduced": false,
    "visual_complexity_may_be_reduced": false,
    "html_surrogate_allowed": false,
    "generic_ppt_fallback_allowed": false,
    "block_after_repeated_failures": true,
    "retry_log_path": "imagegen_retry_log.json"
  },
  "imagegen_retry_log": "imagegen_retry_log.json",
  "diversity_axes": [
    "aesthetic family",
    "composition grammar",
    "diagram/chart language",
    "density and pacing",
    "background/depth treatment",
    "material and texture treatment",
    "title and section treatment"
  ],
  "candidate_directions": [
    {
      "option_id": "A",
      "style_lane_id": "style-lane-A",
      "aesthetic_family": "premium-flat",
      "style_variation_scope": "visual_aesthetic_only",
      "name": "Premium flat",
      "premise": "Refined flat editorial/business visual skin with exact hierarchy, crisp rules, and restrained depth",
      "profile_fit": "internal-review",
      "must_differ_by": ["flat editorial hierarchy", "minimal depth", "precise spacing", "clean chart styling"],
      "narrative_behavior": "same_story_reexpressed"
    },
    {
      "option_id": "B",
      "style_lane_id": "style-lane-B",
      "aesthetic_family": "glassmorphism-blur",
      "style_variation_scope": "visual_aesthetic_only",
      "name": "Glassmorphism",
      "premise": "Layered translucent panels, subtle blur, luminous edges, and high-contrast readable typography",
      "must_differ_by": ["glass material", "translucent depth", "soft layered backgrounds", "clean icon glow"],
      "narrative_behavior": "same_story_reexpressed"
    },
    {
      "option_id": "C",
      "style_lane_id": "style-lane-C",
      "aesthetic_family": "skeuomorphic-material",
      "style_variation_scope": "visual_aesthetic_only",
      "name": "Skeuomorphic material",
      "premise": "Tactile material modules, physical controls, soft shadows, paper/metal depth, and object-like surfaces",
      "must_differ_by": ["tactile material", "physical controls", "soft shadow depth", "object-like modules"],
      "narrative_behavior": "same_story_reexpressed"
    }
  ],
  "style_lanes": [
    {
      "style_lane_id": "style-lane-A",
      "option_id": "A",
      "aesthetic_family": "premium-flat",
      "style_variation_scope": "visual_aesthetic_only",
      "subagent_role": "style-lane-art-director",
      "generator": "imagegen",
      "status": "planned | prompt_ready | generating | generated | needs_regeneration | rejected | selected",
      "prompt_path": "prompts/style-lane-A.txt",
      "output_path": "styles/option-A-contact-sheet.png",
      "narrative_lock_ref": "sha256:<hash of invariant deck fields>",
      "invariance_check": {
        "slide_count_ok": true,
        "order_ok": true,
        "claims_preserved": true,
        "data_sources_preserved": true,
        "proof_object_intent_preserved": true,
        "selected_narrative_preserved": true,
        "violations": []
      },
      "must_preserve_from_deck_spec": ["slide order", "titles", "claims", "required data", "core proof objects"],
      "style_may_change": ["composition grammar", "material/depth", "chart styling", "diagram styling", "density", "typography style", "icon style"],
      "notes": ""
    }
  ],
  "selected_option": "",
  "selected_options": [],
  "pptx_conversion_selection": {
    "mode": "ask_user | full_automation",
    "selected_style_lane_ids": [],
    "allow_multiple_output_decks": true,
    "user_selection_note": ""
  },
  "style_contact_sheets": [
    {
      "option_id": "A",
      "style_lane_id": "style-lane-A",
      "aesthetic_family": "premium-flat",
      "style_variation_scope": "visual_aesthetic_only",
      "generator": "imagegen",
      "path": "styles/option-A-contact-sheet.png",
      "prompt_path": "prompts/style-lane-A.txt",
      "narrative_lock_ref": "sha256:<hash of invariant deck fields>",
      "invariance_check": {
        "slide_count_ok": true,
        "order_ok": true,
        "claims_preserved": true,
        "data_sources_preserved": true,
        "proof_object_intent_preserved": true,
        "selected_narrative_preserved": true,
        "violations": []
      }
    }
  ],
  "option_safety_status": "not_started | needs_regeneration | ready_for_user | selected"
}
```

Rules:

- If the user did not choose a count, ask unless full automation is explicitly requested.
- Full automation must be triggered by explicit wording such as "全自动", "不用问我", "你自己决定", or a recorded answer. Do not infer it from "帮我做 PPT".
- `selection_mode` may only be `ask_user` or `full_automation`; ad hoc values such as `auto` are invalid.
- `direction_count: 1` is valid only when the user explicitly requested one direction and `user_requested_count` records it.
- `style_contact_sheets` must point to style-option images, not final output previews.
- `selected_options` may contain one or multiple option IDs. If exactly one option is selected, also populate `selected_option` for backward compatibility.
- After single-slide comps exist for multiple selected styles, ask which style set(s) to convert to PPTX and record that answer in `pptx_conversion_selection.selected_style_lane_ids`.
- `style_contact_sheets[].generator` must be `imagegen`; rendered PPTX previews, template screenshots, or hand-made placeholders are invalid style previews.
- `style_variation_scope` must be `visual_aesthetic_only`, and `content_strategy_locked` must be true before ImageGen style exploration.
- Each candidate direction must have a distinct visual `aesthetic_family`, material/depth treatment, typography/icon/chart language, density, and visual rhythm. Recolored variants fail the style gate.
- Candidate direction names, lane IDs, aesthetic families, and premises must not use content/narrative/proof-object terms such as evidence chain, risk system map, growth maturity, roadmap, achievement, command center, or their Chinese equivalents.
- Candidate directions must fit the selected `deck_profile`; do not reuse defense-deck direction names for product, company, model, or sales decks unless they genuinely fit.
- Candidate directions must preserve `narrative_lock`; style differences may change visual expression but not slide order, title meaning, claims, required data, sources, or proof-object intent.
- `narrative_lock.deck_spec_fingerprint` must match the current locked deck spec. If content changes, regenerate style lanes.
- `slide_intent_lock_state` must be `locked`; visual style generation cannot bypass user-confirmed slide intent.
- `selected_narrative_id` must match `narrative_plan.json.selected_narrative_id`, and `narrative_plan_lock_state` must be `locked`.
- Each lane/contact sheet must record an `invariance_check`. Any violation blocks style selection.
- Built-in taste guidance should be reflected as portable PPT rules and anti-patterns. External taste sources are optional supplements only and must not be copied wholesale from frontend skills.
- Template-following directions may not change protected template elements; they must differentiate inside allowed content zones.
- `image_quality_policy` must request the highest available ImageGen detail/resolution. The policy is used by ImageGen prompts, visual-clarity review, and the `before-pptx` gate. Single-slide comps must request `3840x2160` first, then fall back only through the recorded 2K and 1080p tiers when the service cannot produce 4K. Every raw ImageGen return must then be normalized with `scripts/normalize_slide_comp.py` to a downstream `3840x2160` approved comp. Never knowingly accept below `1920x1080` raw output without explicit risk acceptance, and all approved normalized comps in one style set must have identical pixel dimensions.
- `imagegen_failure_policy` must fail closed. ImageGen server/tool failures, timeouts, or long-prompt failures may trigger prompt compression only if locked content, visual density, template constraints, proof-object intent, and aesthetic family are preserved. They may not trigger HTML/browser surrogates, generic PPT fallback, lower information density, or lower visual complexity.
- `imagegen_retry_log.json` is optional only when every ImageGen call succeeds on the first try. If it exists and contains attempts, each attempt must record failure class, prompt paths, compression strategy, preserved fields, and final status. Any attempt that removed locked content, reduced content/visual density, used HTML/browser output, switched to generic PPT, or marked a failed asset ready blocks style selection.
- HTML/CSS/browser blueprints, browser screenshots, React pages, canvas renders, PPTX previews, and hand-made static previews are invalid style/contact-sheet or single-slide comp sources.

## imagegen_retry_log.json

Use whenever ImageGen fails, times out, returns a server/service error, returns the wrong asset type, returns a low-resolution/blurry asset, or needs prompt compression.

```json
{
  "policy_ref": "style_brief.json.imagegen_failure_policy",
  "attempts": [
    {
      "asset_id": "style-lane-A",
      "stage": "style-contact-sheet | single-slide-comp",
      "attempt_index": 1,
      "failure_class": "server_error | timeout | prompt_too_large | wrong_asset_type | low_resolution | blur | other",
      "original_prompt_path": "prompts/style-lane-A.txt",
      "retry_prompt_path": "prompts/style-lane-A-retry-01.txt",
      "compression_strategy": "removed duplicate source prose and repeated constraints only",
      "compression_preserved": {
        "locked_slide_order": true,
        "slide_titles": true,
        "core_claims": true,
        "required_data": true,
        "proof_object_intent": true,
        "template_constraints": true,
        "visual_density_floor": true,
        "aesthetic_family": true
      },
      "removed_locked_content": false,
      "reduced_content_density": false,
      "reduced_visual_density": false,
      "used_html_surrogate": false,
      "switched_to_generic_ppt": false,
      "next_action": "retry_imagegen | blocked_ask_user | regenerate_asset",
      "final_status": "retry_pending | generated | blocked_imagegen_failure"
    }
  ]
}
```

## imagegen_resolution_fallback_log.json

Use when ImageGen is available but cannot return the preferred 4K size. This is not a generic failure log and must not justify lower content density or simpler design.

```json
{
  "policy_ref": "style_brief.json.image_quality_policy.resolution_fallback_policy",
  "selected_deck_wide_tier": "4k | 2k | 1080p",
  "attempts": [
    {
      "slide_id": "slide-001",
      "requested_tier": "4k",
      "returned_px": {"width": 1672, "height": 941},
      "returned_bytes": 900000,
      "reason": "service returned below requested 4K despite valid prompt",
      "next_tier": "2k",
      "accepted": false
    },
    {
      "slide_id": "slide-001",
      "requested_tier": "2k",
      "returned_px": {"width": 2560, "height": 1440},
      "returned_bytes": 2400000,
      "reason": "2K is the highest stable tier returned by ImageGen",
      "next_tier": "",
      "accepted": true
    }
  ],
  "notes": "If the selected tier is lower than 4K, all approved comps in the deck must use the same selected tier."
}
```

## template-frame-map.json

Use when a template/source PPTX exists. This file is mandatory in `template-following` mode.

```json
{
  "source_pptx": "input/template.pptx",
  "template_contact_sheet": "previews/template-contact-sheet.png",
  "rules": {
    "inherit_source_slides": true,
    "never_start_from_blank": true,
    "preserve_master": true,
    "preserve_brand_chrome": true,
    "deviation_log": "deviation-log.md"
  },
  "slide_map": [
    {
      "target_slide_id": "slide-001",
      "source_slide_id": "template-slide-001",
      "source_preview": "previews/template-slide-001.png",
      "layout_archetype": "cover | section | content | chart | dashboard | closing | other",
      "protected_elements": [
        "logo",
        "footer",
        "page number",
        "title block",
        "section label",
        "background frame"
      ],
      "editable_zones": [
        {
          "zone_id": "main-content",
          "bounds": "approximate x,y,w,h or verbal description",
          "allowed_content": "diagram | chart | text | image | table"
        }
      ],
      "allowed_deviations": []
    }
  ]
}
```

Rules:

- Every final slide in `template-following` mode must map to a source slide or document a user-approved exception in `deviation-log.md`.
- Protected elements must appear in the ImageGen comp and final PPTX preview unless the user explicitly accepts the deviation.
- If no source slide can support a target slide, ask the user, split the slide, or regenerate the comp within a compatible template frame; do not silently rebuild from blank.

## qa_report.md

Use short sections:

```markdown
# QA Report

## Status
PASS | NEEDS_ITERATION | BLOCKED

## Source Truth
- Deck spec:
- Slide intent plan:
- Narrative plan:
- Design system:
- Style brief:
- Template:
- Reference decks:

## Slide Intent Gate
| slide | confirmed_title | core_idea | proof_goal | evidence_status | gaps |

## Narrative Treatment Gate
| narrative_id | selected | matrix_complete | review_status | action |

## Reviewer Findings
| role | severity | slide | finding | action |

## Visual Comp Gate
| slide | comp_path | comp_review_status | clarity_review_status | dimensions | iteration_count | approved_by |

## Style Direction Gate
| option | premise | diversity_check | template_check | decision |

## Template Fidelity Gate
| slide | template_source_slide | protected_elements_preserved | deviations |

## PPTX Reconstruction Gate
| slide | preview_path | comp_match_status | reconstruction_fidelity | editability_status | action |

## Final Council
| role | status | approval_to_advance | remaining_p0_p1 |

## Editability
- Native editable text:
- Native editable shapes/charts:
- Retained image areas:

## Known Limitations
- Data approximations:
- Missing inputs:
```

## visual_contract.json

Use after ImageGen style selection and single-slide comps, before PPTX authoring:

```json
{
  "selected_style": "Option B + template fidelity",
  "selected_styles": ["Option B"],
  "contact_sheet": "preview/imagegen-style-contact-sheet.png",
  "template_mode": "none | hard",
  "template_contact_sheet": "previews/template-contact-sheet.png",
  "template_frame_map": "template-frame-map.json",
  "per_slide_comps_complete": true,
  "comp_generation_mode": "main_agent_serial_imagegen | style_sharded_serial_imagegen",
  "parallel_style_agents_used": false,
  "parallel_page_subagents_used": false,
  "explicit_parallel_comp_generation_accepted": false,
  "comp_style_lock": {
    "source": "selected contact sheet + first approved comp",
    "dimensions_px": {"width": 3840, "height": 2160},
    "chrome_locked": true,
    "locked_chrome_elements": [
      "logo",
      "section label",
      "header rule",
      "footer",
      "page number",
      "page marker",
      "title furniture"
    ],
    "consistency_requirements": [
      "same page number placement and format",
      "same logo placement and size",
      "same header/footer system",
      "same section label treatment",
      "same recurring typography scale",
      "same border/background/chrome rhythm"
    ],
    "generation_owner": "main_agent | style_agent"
  },
  "style_runs": [
    {
      "style_lane_id": "style-lane-A",
      "option_id": "A",
      "selected_for_pptx": true,
      "contact_sheet": "styles/option-A-contact-sheet.png",
      "comp_generation_mode": "style_sharded_serial_imagegen",
      "generation_owner": "style_agent",
      "per_slide_comps_complete": true,
      "normalized_4k_complete": true,
      "comp_style_lock": {},
      "slides": []
    }
  ],
  "pptx_conversion_selection": {
    "selected_style_lane_ids": ["style-lane-A"],
    "produce_one_pptx_per_selected_style": true,
    "output_naming_rule": "output/<deck-slug>-<style-lane-id>.pptx"
  },
  "downgrade_mode": false,
  "explicit_downgrade_accepted": false,
  "comp_is_construction_drawing": true,
  "default_reconstruction_mode": "pixel_locked_hybrid",
  "pixel_locked_hybrid_required": true,
  "minimum_non_title_rich_visual_ratio": 0.6,
  "image_quality_policy": {
    "policy_id": "imagegen-max-clarity-v1",
    "enabled": true,
    "prompt_detail_level": "highest_available",
    "preferred_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_px": {"width": 1920, "height": 1080},
    "minimum_acceptable_comp_bytes": 1048576,
    "postprocess_policy": {
      "enabled": true,
      "normalize_every_comp": true,
      "target_px": {"width": 3840, "height": 2160},
      "local_repair_script": "scripts/normalize_slide_comp.py",
      "save_raw_imagegen_output": true,
      "raw_output_dir": "slides/raw",
      "normalized_output_suffix": "-comp.png",
      "upscale_method": "lanczos",
      "sharpen_after_resize": true,
      "same_output_dimensions_required": true,
      "downstream_uses_normalized_comp": true
    },
    "resolution_fallback_policy": {
      "enabled": true,
      "deck_wide_tier_lock": true,
      "do_not_retry_forever": true,
      "record_log_path": "imagegen_resolution_fallback_log.json",
      "tiers": [
        {
          "tier": "4k",
          "minimum_px": {"width": 3840, "height": 2160},
          "minimum_bytes": 5242880,
          "max_attempts": 2
        },
        {
          "tier": "2k",
          "minimum_px": {"width": 2560, "height": 1440},
          "minimum_bytes": 2097152,
          "max_attempts": 1
        },
        {
          "tier": "1080p",
          "minimum_px": {"width": 1920, "height": 1080},
          "minimum_bytes": 1048576,
          "max_attempts": 1
        }
      ],
      "never_accept_below_px": {"width": 1920, "height": 1080},
      "fallback_requires_reason": true
    },
    "minimum_acceptable_contact_sheet_px": {"width": 2400, "height": 1350},
    "prompt_requires_crisp_text_and_icons": true,
    "review_required_before_pptx": true,
    "small_text_policy": "Avoid unreadable microtext in ImageGen comps; exact final small text comes from deck_spec.json during PPTX reconstruction.",
    "blur_rejection_criteria": [
      "soft or blurry main title",
      "blurred key numbers",
      "muddy icons or line art",
      "low-contrast small labels",
      "compression artifacts around text or diagram strokes"
    ]
  },
  "icon_asset_policy": {
    "enabled": true,
    "manifest_path": "assets/icon-manifests/icon_asset_manifest.json",
    "processor_script": "scripts/prepare_icon_assets.py",
    "transparent_png_required": true,
    "minimum_transparent_padding_px": 16,
    "crop_expansion_px": 12,
    "minimum_output_icon_px": 256,
    "forbid_edge_touching_colored_pixels": true,
    "use_processed_icons_in_pptx": true
  },
  "pptx_render_fix_loop": {
    "enabled": true,
    "minimum_rounds": 9,
    "rounds_log_path": "qa/render-fix/render_fix_rounds.json",
    "compare_against": "approved 4K normalized comps",
    "block_on_unresolved_p0_p1": true
  },
  "slides": [
    {
      "slide_id": "slide-001",
      "template_source_slide": "template-slide-001",
      "template_elements_to_preserve": [
        "logo",
        "footer",
        "page marker",
        "title furniture"
      ],
      "comp_path": "slides/slide-001-comp.png",
      "raw_comp_path": "slides/raw/style-lane-A/slide-001-imagegen.png",
      "normalization": {
        "status": "completed",
        "raw_imagegen_output_path": "slides/raw/style-lane-A/slide-001-imagegen.png",
        "output_path": "slides/style-lane-A/slide-001-comp.png",
        "input_dimensions_px": {"width": 2560, "height": 1440},
        "output_dimensions_px": {"width": 3840, "height": 2160},
        "local_repair_applied": true,
        "script_path": "scripts/normalize_slide_comp.py",
        "normalization_report_path": "layout/style-lane-A-slide-001-normalization.json"
      },
      "comp_prompt_path": "prompts/slide-001-comp.txt",
      "comp_review_status": "approved",
      "clarity_review": {
        "status": "not_started | needs_iteration | approved | user_accepted_risk",
        "image_source_type": "imagegen | user_supplied | template_render",
        "image_dimensions_px": {"width": 3840, "height": 2160},
        "image_file_size_bytes": 5242880,
        "resolution_tier": "4k | 2k | 1080p",
        "fallback_reason": "",
        "text_legibility": "not_started | failed | acceptable | approved | user_accepted_risk",
        "icon_line_clarity": "not_started | failed | acceptable | approved | user_accepted_risk",
        "edge_sharpness": "not_started | failed | acceptable | approved | user_accepted_risk",
        "blocking_blur": false,
        "small_text_strategy": "regenerate | enlarge labels | simplify microtext | defer exact small copy to PPTX native text | user accepted risk",
        "reviewer": "visual-clarity"
      },
      "style_continuity_review": {
        "status": "approved | needs_regeneration | user_accepted_risk",
        "matches_comp_style_lock": true,
        "page_chrome_consistent": true,
        "recurring_elements_consistent": true,
        "issues": []
      },
      "iteration_count": 1,
      "visual_archetype": "maturity arc | system map | loop | funnel | radial | timeline | swimlane | matrix | scorecard | dashboard | process chain | comparison | title",
      "reconstruction_mode": "pixel_locked_hybrid | sliced_hybrid | native_trace_hybrid | native_rebuild",
      "comp_backplate": {
        "strategy": "full_slide | sliced_layers | none",
        "path": "slides/slide-001-comp.png",
        "insert_first": true,
        "covers_full_slide": true
      },
      "text_mask_plan": [
        {
          "region": "title area",
          "method": "matching background patch | shape mask | crop without text | no mask needed",
          "reason": "avoid duplicate image text behind editable text"
        }
      ],
      "editable_overlay_plan": [
        "editable title",
        "editable claim",
        "editable key numbers",
        "editable footer/page marker",
        "editable main labels"
      ],
      "must_preserve": [
        "large maturity arc from lower left to upper right",
        "three phase nodes connected by red line",
        "single focal metric ring on right"
      ],
      "reader_facing_fidelity_targets": [
        "same visual archetype",
        "same focal object",
        "same flow direction",
        "similar density and hierarchy",
        "same relative region layout"
      ],
      "native_reconstruction": [
        "editable title/subtitle/footer",
        "editable arc approximated with lines and nodes",
        "editable metric labels and callouts"
      ],
      "retained_images": [],
      "processed_icon_assets": [
        {
          "id": "slide-001-icon-01",
          "output_path": "assets/icons/style-lane-A/slide-001-icon-01.png",
          "transparent_background": true,
          "transparent_padding_px": 16,
          "edge_clear": true,
          "pptx_target_region": "top metric icon"
        }
      ],
      "allowed_simplifications": [
        "replace textured background with template white background",
        "simplify icon detail while keeping icon placement"
      ],
      "prohibited_regressions": [
        "table-only",
        "square-card-only",
        "generic three-column card grid",
        "rebuild-from-blank when template exists",
        "missing template logo/footer/page marker",
        "proof object changed from system map to text table"
      ],
      "comparison_gate": {
        "pptx_preview_path": "previews/slide-001-pptx.png",
        "comp_match_status": "not_started | needs_iteration | approved",
        "reconstruction_fidelity": "not_started | failed | partial | approved",
        "template_match_status": "not_started | needs_iteration | approved",
        "editability_status": "not_started | needs_iteration | approved"
      },
      "deviation_notes": ""
    }
  ]
}
```

Rules:

- `default_reconstruction_mode` should be `pixel_locked_hybrid`; use `native_rebuild` only with preview evidence or explicit user acceptance.
- In generated-deck mode, `comp_generation_mode` must be `main_agent_serial_imagegen` or `style_sharded_serial_imagegen`; page-level subagents may review or draft prompt notes but must not independently call ImageGen for final single-slide comps.
- `style_sharded_serial_imagegen` means one style-lane agent generates one whole style set serially. It requires `parallel_style_agents_used=true`, `parallel_page_subagents_used=false`, and `comp_style_lock.generation_owner="style_agent"` or `"main_agent"`.
- `parallel_page_subagents_used` must be false unless the user explicitly accepted the style-drift risk in `user_decisions.md` and `explicit_parallel_comp_generation_accepted=true`.
- `comp_style_lock.chrome_locked` must be true. The lock must include at least logo, footer, page number/page marker, and a header/title/section treatment so recurring slide chrome cannot drift between pages.
- Each slide must have `reconstruction_mode`, `comp_backplate`, `text_mask_plan`, and `editable_overlay_plan` before PPTX authoring.
- Each generated-deck slide must have a completed `normalization` record from `scripts/normalize_slide_comp.py`; `comp_path` points to the normalized 4K image, while `raw_comp_path` points to the raw ImageGen return.
- Each slide must have `clarity_review.status=approved` or `user_accepted_risk` before PPTX authoring. Blurry titles, key numbers, icons, fine lines, or comps below the normalized 4K target block `before-pptx`. A raw fallback to 2K or 1080p is acceptable only when recorded in `imagegen_resolution_fallback_log.json`; final approved comps still normalize to 3840x2160.
- Each generated-deck slide must have `style_continuity_review.status=approved`, `matches_comp_style_lock=true`, `page_chrome_consistent=true`, and `recurring_elements_consistent=true` before PPTX authoring.
- `pixel_locked_hybrid` and `sliced_hybrid` slides must insert the approved comp or cropped comp layers before native overlays.
- A whole-slide comp backplate is allowed. A final slide that is only a flat image with no editable main information is not allowed unless the user explicitly requested non-editable output.
- In `reconstruction-only` and `repair-existing-pptx` modes, `contact_sheet` is optional and `selected_style` should be `user-supplied-final-images` or `repaired-from-source-images`.
- A final PPTX slide must keep the slide's `visual_archetype` unless `deviation_notes` explains a source/template/editability blocker.
- If `template_mode` is `hard`, every slide must preserve its mapped source slide's protected elements unless `deviation_notes` and `deviation-log.md` document explicit user acceptance.
- If `per_slide_comps_complete` is false, PPTX authoring is blocked.
- Approved comp paths must point to independently generated slide comp images, normally under `slides/slide-XXX-comp.png`. Paths under `preview/`, `output/`, `template-starter-preview/`, or any rendered PPTX preview are invalid.
- If multiple style sets are selected, `style_runs[]` keeps all completed sets, but the top-level `slides[]` must be the set currently being converted or checked.
- `icon_asset_policy` requires transparent padded PNG icon assets before PPTX reconstruction. Processed icons may be retained image layers, but they must not be clipped or pasted with unwanted white backgrounds.
- `pptx_render_fix_loop.minimum_rounds` must be at least 9 and its rounds log must be complete before final export.
- If `downgrade_mode` is true, `user_decisions.md` must explain that the user accepted a style-inspired rebuild rather than comp-faithful reconstruction. Do not infer this from automation mode.
- The final council must compare PPTX previews against this file.

## icon_asset_manifest.json

Use before PPTX reconstruction when retaining icons from approved comps as image layers:

```json
{
  "status": "draft | ready | processed | approved",
  "policy_ref": "visual_contract.json.icon_asset_policy",
  "source_coordinate_space_px": {"width": 3840, "height": 2160},
  "default_padding_px": 16,
  "default_crop_expansion_px": 12,
  "white_threshold": 246,
  "minimum_output_icon_px": 256,
  "icons": [
    {
      "id": "slide-005-pipeline-icon-01",
      "slide_id": "slide-005",
      "source_image_path": "slides/style-lane-A/slide-005-comp.png",
      "bbox_px": {"left": 310, "top": 620, "width": 96, "height": 96},
      "output_path": "assets/icons/style-lane-A/slide-005-pipeline-icon-01.png",
      "padding_px": 16,
      "pptx_target_region": "pipeline step 1 icon",
      "notes": "Crop includes full icon stroke and no adjacent text."
    }
  ]
}
```

Rules:

- Run `scripts/prepare_icon_assets.py --manifest <manifest> --workspace <workspace> --strict`.
- If strict mode reports possible clipping, enlarge `bbox_px` or `default_crop_expansion_px` and rerun.
- Processed icons must have transparent background, transparent padding, and `edge_clear=true` before they are inserted into PPTX.
- Do not use this for large complex diagrams. Use sliced comp backplates for complex visual systems and processed icons only for reusable simple pictograms, badges, and line symbols.

## render_fix_rounds.json

Use after PPTX construction and before final export:

```json
{
  "status": "not_started | running | completed | blocked",
  "policy_ref": "visual_contract.json.pptx_render_fix_loop",
  "minimum_rounds": 9,
  "completed_rounds": 9,
  "rounds": [
    {
      "round": 1,
      "pptx_path": "output/deck-style-lane-A.pptx",
      "rendered_contact_sheet": "preview/render-round-01-contact-sheet.png",
      "comparison_source": "approved 4K normalized comps",
      "findings": ["slide 5 icon clipped", "slide 8 footer shifted"],
      "fixes_applied": ["replaced icon with padded transparent PNG", "aligned footer group"],
      "remaining_p0_p1": []
    }
  ],
  "unresolved_p0_p1": []
}
```

Rules:

- `completed_rounds` must be at least `visual_contract.json.pptx_render_fix_loop.minimum_rounds`.
- Each round must render the PPTX or slide modules to PNG and compare against approved normalized 4K comps.
- Do not set `status="completed"` while `unresolved_p0_p1` is non-empty.

## reconstruction_manifest.json

Use when `deck.mode` is `reconstruction-only` or `repair-existing-pptx`.

```json
{
  "lock_state": "draft | locked",
  "mode": "reconstruction-only | repair-existing-pptx",
  "source": "user_supplied_slide_images",
  "slide_count": 0,
  "page_sharding": {
    "enabled": true,
    "per_slide_pptx_required": true,
    "merge_after_page_approval": true,
    "parallel_subagents_recommended": true
  },
  "global_rules": {
    "skip_full_pipeline_gates": true,
    "visual_fidelity_priority": "pixel_locked_hybrid",
    "ordinary_table_or_card_rebuild_forbidden": true,
    "native_text_boxes_allowed_only_as_transparent_overlays": true
  },
  "slides": [
    {
      "slide_id": "slide-001",
      "page_number": 1,
      "source_image_path": "slides/slide-001-comp.png",
      "text_source_status": "provided | ocr_verified | user_accepted_image_text | image_only_accepted",
      "text_source_path": "input/slide-001-text.md",
      "reconstruction_mode": "pixel_locked_hybrid",
      "required_editable_overlays": [
        "title",
        "body",
        "key numbers",
        "footer/page marker"
      ],
      "output_slide_pptx": "slide-modules/slide-001.pptx",
      "preview_path": "preview/slide-001-pptx.png",
      "review_status": "not_started | needs_iteration | approved | user_accepted_risk"
    }
  ],
  "open_questions": []
}
```

Rules:

- `lock_state` must be `locked` before PPTX reconstruction starts.
- Each slide must point to an existing high-resolution source image. A full-deck contact sheet is not a substitute unless the user accepts lower fidelity.
- `text_source_status` must be explicit. If text is OCR-derived, it must be verified or accepted before final export.
- `page_sharding.enabled`, `per_slide_pptx_required`, and `merge_after_page_approval` must be true.
- `output_slide_pptx` and `preview_path` are required before final export.

## content_review.md

Use before ImageGen:

```markdown
# Content Review

## Status
PASS | NEEDS_USER | BLOCKED

## Story Spine
- Thesis:
- Chapters:
- Decision required:

## Grill Questions
| priority | question | why it matters | default assumption |

## Content Findings
| role | severity | slide | finding | recommended action |

## Lock Recommendation
LOCK | ASK_USER | REVISE_SPEC | BLOCK
```

## user_decisions.md

Record user decisions and automation assumptions:

```markdown
# User Decisions

## Confirmed By User
- 

## Accepted Automation Assumptions
- 

## Explicitly Accepted Risks
- 
```

## qa/final-council.md

Use after rendering PPTX previews:

```markdown
# Final Deck Council

## Status
PASS | NEEDS_ITERATION | BLOCKED

## Role Results
| role | status | score | approval_to_advance |

## Blocking Findings
| severity | role | slide | finding | fix |

## Export Decision
EXPORT | ITERATE | ASK_USER | BLOCK
```
