# Schemas

Use these structures as the stable handoff between phases. Keep files compact but complete.

## pipeline_state.json

```json
{
  "skill": "imagegen-pptx-pipeline",
  "workspace": "/absolute/path/to/workspace",
  "title": "Deck title",
  "mode": "create | template-following | targeted-edit | reconstruction-only | repair-existing-pptx",
  "current_stage": "initialized | input_reading | conversion_input_lock | content_gate | slide_intent_lock | narrative_selection | style_count | style_selection | single_slide_comps | multi_style_comp_selection | slide_comp_review | visual_contract | pptx_conversion | final_review | complete",
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
    "conversion_manifest": "conversion_manifest.json",
    "latest_preview": ""
  },
  "stage_history": [
    {
      "stage": "content_gate | slide_intent_lock | narrative_selection | style_selection | single_slide_comps | slide_comp_review | conversion_input_lock | visual_contract | pptx_conversion | final_review",
      "status": "waiting_for_user | completed | needs_iteration | blocked",
      "timestamp": "ISO-8601",
      "notes": ""
    }
  ]
}
```

## deck_spec.json

```json
{
  "deck": {
    "title": "Deck title",
    "audience": "board | investor | executive | sales | training | other",
    "objective": "What the deck must accomplish",
    "deck_profile": "product-pitch | company-profile | model-technical | sales-gtm | strategy-executive | investor-finance | training-enable | internal-review | other",
    "content_input_type": "explicit_per_page | brief_outline | template_only | reference_only | mixed | final_slide_images",
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
    "editability": "main text, numbers, labels, footers, page markers editable",
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
      "data": [{"label": "Metric", "value": "Exact value", "unit": "%", "source_id": "source-001"}],
      "proof_object": "chart | table | process | timeline | image | diagram | comparison | quote",
      "visual_intent": "What the visual should communicate",
      "visual_expression_must_preserve": "loop | radial | system map | maturity arc | funnel | dashboard | process chain | table | other",
      "template_source_slide": "source slide id when template-following",
      "template_required_elements": ["logo", "footer", "page marker"],
      "visual_comp_required": true,
      "comp_path": "slides/slide-001-comp.png",
      "comp_review_status": "not_started | needs_iteration | approved | user_accepted_risk",
      "pptx_conversion_status": "not_started | planned | needs_iteration | approved",
      "editable_text": ["title", "body_text", "data labels", "footer", "page_number"],
      "image_assets": [],
      "open_questions": []
    }
  ],
  "sources": [{"source_id": "source-001", "title": "Source name", "path_or_url": "", "date": "", "notes": ""}]
}
```

`deck.lock_state` must be `locked` before visual generation or direct conversion.

## design_system.json

```json
{
  "mode": "create | template-following | targeted-edit | reconstruction-only | repair-existing-pptx",
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
  "palette": {"primary": [], "secondary": [], "neutral": [], "semantic": {}},
  "typography": {
    "title": {"font": "", "weight": "", "size_range": ""},
    "body": {"font": "", "weight": "", "size_range": ""},
    "numbers": {"font": "", "weight": "", "size_range": ""}
  },
  "layout": {"aspect_ratio": "16:9", "grid": "", "safe_margins": "", "footer_rule": "", "page_number_rule": ""},
  "visual_language": {
    "backgrounds": "",
    "cards": "",
    "charts": "",
    "icons": "",
    "photography": "",
    "texture_depth": "",
    "visual_ambition": "restrained | polished | premium | cinematic-business",
    "avoid_visual_regressions": ["flat table-only deck", "generic equal-card grid", "default PPT template feel", "near-identical style options"]
  },
  "taste_guidance": {
    "enabled": true,
    "sources": [
      {"name": "built-in-ppt-taste-system", "path": "references/taste-system.md", "used_for": "style exploration | comp review | PPTX conversion QA | anti-default QA"},
      {"name": "built-in-ppt-style-library", "path": "references/style-library.md", "used_for": "style lane selection | user preference mapping | ImageGen style prompts"}
    ],
    "portable_rules": ["avoid generic card grids", "use one dominant proof object per slide", "preserve ImageGen comp visual grammar during strict conversion"]
  }
}
```

## slide_intent_plan.json

```json
{
  "lock_state": "draft | needs_user_confirmation | locked",
  "source_deck_spec_fingerprint": "sha256:<hash>",
  "matrix_path": "slide_intent_matrix.md",
  "selection_mode": "ask_user | full_automation",
  "review_status": "not_started | needs_iteration | approved | user_accepted_risk",
  "slides": [
    {
      "slide_id": "slide-001",
      "page_number": 1,
      "proposed_title": "",
      "confirmed_title": "",
      "core_idea": "",
      "proof_goal": "",
      "evidence_candidates": [],
      "data_to_extract": [],
      "content_gaps": [],
      "accepted_assumptions": [],
      "status": "draft | confirmed | accepted_assumption"
    }
  ],
  "open_questions": []
}
```

## narrative_plan.json

```json
{
  "lock_state": "draft | needs_user_confirmation | locked",
  "source_deck_spec_fingerprint": "sha256:<hash>",
  "slide_intent_plan": "slide_intent_plan.json",
  "slide_intent_lock_state": "draft | locked",
  "matrix_path": "narrative_matrix.md",
  "selection_mode": "ask_user | full_automation",
  "selected_narrative_id": "evidence-first",
  "narrative_options": [{"narrative_id": "evidence-first", "name": "", "summary": ""}],
  "slides": [
    {
      "slide_id": "slide-001",
      "page_number": 1,
      "confirmed_core_idea": "",
      "selected_treatment": {
        "narrative_id": "evidence-first",
        "presentation_strategy": "",
        "content_to_show": "",
        "proof_object_expression": "",
        "must_preserve": ""
      }
    }
  ],
  "review_status": "not_started | approved | user_accepted_risk",
  "open_questions": []
}
```

## style_brief.json

```json
{
  "direction_count": 4,
  "selection_mode": "ask_user | full_automation",
  "generation_mode": "parallel_style_lanes | sequential_style_lanes | single_prompt_fallback",
  "style_variation_scope": "visual_aesthetic_only",
  "content_strategy_locked": true,
  "deck_profile": "",
  "deck_profile_evidence": {
    "primary_profile": "",
    "secondary_profiles": [],
    "audience": "",
    "occasion": "",
    "source_signals": [],
    "excluded_style_families": [],
    "notes": ""
  },
  "style_recommendation_policy": {
    "policy_id": "task-aware-style-recommendation-v1",
    "derive_from_deck_profile": true,
    "recommended_styles_must_match_deck_profile": true,
    "ask_before_using_off_profile_styles": true,
    "off_profile_requires_user_request": true,
    "fit_reason_required_per_option": true,
    "profile_style_routes": [
      {
        "profile": "company-profile",
        "signals": ["company-profile", "company intro", "enterprise intro", "企业介绍", "公司介绍"],
        "allowed_style_ids": ["corporate-profile-architectural", "corporate-team-collaboration", "nordic-business-future", "brand-proposal-minimal"],
        "allowed_aesthetic_families": ["company-profile", "brand-proposal", "editorial-gallery", "annual-report"]
      },
      {
        "profile": "defense-personal",
        "signals": ["defense", "promotion", "interview", "答辩", "晋升", "面试"],
        "allowed_style_ids": ["promotion-defense-evidence", "personal-performance-review", "interview-case-board", "rigorous-academic-defense", "thesis-defense-clean"],
        "allowed_aesthetic_families": ["personal-brand", "academic", "editorial-gallery"]
      }
    ]
  },
  "selected_narrative_id": "",
  "narrative_lock": {
    "deck_spec_fingerprint": "sha256:<hash>",
    "locked_slide_count": 0,
    "locked_slide_order": ["slide-001"],
    "slide_intent_plan": "slide_intent_plan.json",
    "slide_intent_lock_state": "locked",
    "narrative_plan": "narrative_plan.json",
    "narrative_plan_lock_state": "locked",
    "slide_order_locked": true,
    "section_flow_locked": true,
    "titles_locked": true,
    "claims_locked": true,
    "required_data_locked": true,
    "core_proof_objects_locked": true
  },
  "style_library": {
    "enabled": true,
    "sources": [{"name": "built-in-ppt-style-library", "path": "references/style-library.md"}],
    "style_options_must_remain_visual_only": true,
    "must_not_use_third_party_logos_without_assets": true
  },
  "taste_guidance": {
    "enabled": true,
    "sources": [{"name": "built-in-ppt-taste-system", "path": "references/taste-system.md"}]
  },
  "diversity_contract": {
    "policy_id": "style-lane-diversity-v1",
    "forbid_near_identical_contact_sheets": true,
    "reject_icon_only_or_color_only_variation": true,
    "require_distinct_style_ids": true,
    "require_distinct_aesthetic_families": true,
    "require_distinct_layout_archetypes": true,
    "require_distinct_evidence_presentation": true,
    "require_distinct_thumbnail_differentiators": true,
    "minimum_distinct_axes": 5,
    "required_axes": ["style_id", "aesthetic_family", "layout_archetype", "evidence_presentation", "composition_grammar"]
  },
  "candidate_directions": [
    {
      "option_id": "option-a",
      "style_lane_id": "lane-a",
      "style_id": "mckinsey-consulting-report",
      "style_source": "built-in-style-library",
      "aesthetic_family": "consulting-report",
      "visual_signature": "",
      "task_fit": {
        "profile_match": true,
        "fit_reason": "",
        "profile_signals_used": [],
        "user_requested_off_profile": false
      },
      "layout_archetype": "",
      "evidence_presentation": "",
      "composition_grammar": "",
      "density_and_pacing": "",
      "thumbnail_differentiators": [],
      "must_not_reuse": "",
      "narrative_behavior": "same_story_reexpressed"
    }
  ],
  "style_lanes": [
    {
      "option_id": "option-a",
      "style_lane_id": "lane-a",
      "style_id": "mckinsey-consulting-report",
      "style_source": "built-in-style-library",
      "aesthetic_family": "consulting-report",
      "visual_signature": "",
      "layout_archetype": "",
      "evidence_presentation": "",
      "composition_grammar": "",
      "generator": "imagegen",
      "prompt_path": "prompts/style-lane-a.txt",
      "output_path": "styles/lane-a-contact-sheet.png",
      "status": "generated | ready_for_user | selected",
      "narrative_lock_ref": "sha256:<hash>",
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
  "style_contact_sheets": [],
  "selected_option": "",
  "selected_options": [],
  "image_quality_policy": {
    "enabled": true,
    "prompt_detail_level": "highest_available",
    "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_bytes": 1048576,
    "postprocess_policy": {
      "enabled": true,
      "mandatory": true,
      "local_repair_script": "scripts/realesrgan_upscale.py",
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
      "realesrgan_half": false,
      "target_px": {"width": 3840, "height": 2160},
      "raw_output_dir": "slides/raw",
      "upscaled_output_dir": "slides/upscaled",
      "manifest_dir": "upscale",
      "downstream_uses_realesrgan_comp": true,
      "fallback_allowed_for_postprocess": false
    },
    "minimum_acceptable_contact_sheet_px": {"width": 2400, "height": 1350},
    "prompt_requires_crisp_text_and_icons": true,
    "review_required_before_pptx": true
  }
}
```

## visual_contract.json

```json
{
  "selected_style": "option-a",
  "selected_styles": ["option-a"],
  "contact_sheet": "styles/lane-a-contact-sheet.png",
  "template_mode": "none | hard",
  "per_slide_comps_complete": true,
  "comp_generation_mode": "main_agent_serial_imagegen | style_sharded_serial_imagegen",
  "parallel_style_agents_used": false,
  "parallel_page_subagents_used": false,
  "explicit_parallel_comp_generation_accepted": false,
  "comp_is_conversion_target": true,
  "conversion_method": "strict_slide_image_to_editable_pptx",
  "image_quality_policy": {
    "enabled": true,
    "requested_single_slide_canvas_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_px": {"width": 3840, "height": 2160},
    "minimum_acceptable_comp_bytes": 1048576,
    "postprocess_policy": {
      "enabled": true,
      "mandatory": true,
      "local_repair_script": "scripts/realesrgan_upscale.py",
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
      "realesrgan_half": false,
      "target_px": {"width": 3840, "height": 2160},
      "downstream_uses_realesrgan_comp": true,
      "fallback_allowed_for_postprocess": false
    },
    "prompt_requires_crisp_text_and_icons": true,
    "review_required_before_pptx": true
  },
  "slide_comp_review_policy": {
    "enabled": true,
    "required_before_pptx": true,
    "require_subagent_review": true,
    "evidence_dir": "qa/reviews/slide-comp",
    "reviewer_modes_allowed": ["subagent", "main_agent_role_review"],
    "fallback_requires_reason": true,
    "block_on_unresolved_p0_p1": true,
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
      "visual-clarity"
    ]
  },
  "conversion_policy": {
    "enabled": true,
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
    "realesrgan_half": false,
    "basis_px": {"width": 1920, "height": 1080},
    "source_image_is_measurement_target": true,
    "source_comp_realesrgan_4k_required": true,
    "full_image_backgrounds_allowed": false,
    "region_image_backgrounds_allowed": false,
    "native_text_required": true,
    "native_shapes_required": true,
    "native_charts_tables_connectors_required": true,
    "only_complex_art_may_be_images": true,
    "multiline_text_split_required": true,
    "automatic_text_wrap_for_multiline_forbidden": true,
    "strict_icon_extraction_required": true,
    "icon_contact_sheet_audit_required": true,
    "real_source_icons_must_be_extracted": true,
    "native_redraw_for_named_pictograms_forbidden": true,
    "icon_hd_enhancement_required": true,
    "icon_realesrgan_upscale_required": true,
    "minimum_render_compare_rounds": 10,
    "render_round_requires_new_export": true,
    "qa_gate_required": true,
    "metrics_gate_reads_actual_render": true,
    "media_audit_required": true
  },
  "strict_icon_policy": {
    "enabled": true,
    "manifest_path": "icons/icon_jobs.json",
    "extractor_script": "iconcut3.py",
    "transparent_png_required": true,
    "edge_audit_required": true,
    "contact_sheet_audit_required": true,
    "clip_error_fails_closed": true,
    "no_manual_crop_fallback": true,
    "source_icon_inventory_required": true,
    "real_source_icons_must_be_extracted": true,
    "native_redraw_for_named_pictograms_forbidden": true,
    "glyph_helpers_are_placeholder_only": true,
    "icon_hd_enhancement_required": true,
    "icon_hd_target_min_px": 256,
    "realesrgan_upscale_required": true,
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
    "realesrgan_half": false,
    "icon_upscale_script": "scripts/realesrgan_upscale.py",
    "icon_upscale_manifest_path": "icons/icon_upscale_manifest.json",
    "placement_source_dir": "icons/upscaled",
    "feathered_slices_preserve_alpha": true,
    "minimum_output_icon_min_dim_px": 256
  },
  "render_compare_loop": {
    "enabled": true,
    "minimum_rounds": 10,
    "rounds_log_path": "qa/render-compare/render_compare_rounds.json",
    "render_log_path": "qa/render-compare/render_log.json",
    "paired_crops_required": true,
    "region_diff_normal_band_max_mean_abs": 35,
    "region_diff_blocking_mean_abs": 40,
    "block_on_unresolved_p0_p1": true,
    "round_requires_new_export": true,
    "qa_gate_script": "qa_gate.py",
    "media_audit_required": true
  },
  "slides": [
    {
      "slide_id": "slide-001",
      "comp_path": "slides/slide-001-comp.png",
      "raw_comp_path": "slides/raw/slide-001-raw.png",
      "upscale_manifest_path": "upscale/slide-001-comp.realesrgan.json",
      "image_source_type": "imagegen | user_supplied",
      "visual_archetype": "system map | timeline | dashboard | table | other",
      "clarity_review": {
        "status": "approved | user_accepted_risk",
        "blocking_blur": false,
        "image_dimensions_px": {"width": 3840, "height": 2160},
        "image_file_size_bytes": 5242880,
        "upscale_manifest_path": "upscale/slide-001-comp.realesrgan.json"
      },
      "style_continuity_review": {"status": "approved"},
      "converter": {
        "measurement_status": "planned | completed | approved",
        "source_icon_inventory_status": "pending | icons_detected | no_source_icons_detected",
        "icon_extraction_status": "planned | passed | not_applicable",
        "icon_jobs_path": "icons/icon_jobs.json",
        "icon_contact_sheet": "icon-sheets/icon-contact-sheet.png",
        "extracted_icon_count": 0,
        "text_split_plan": "planned | completed | not_applicable",
        "build_script_path": "builders/slide-001.py",
        "output_slide_pptx": "slide-modules/slide-001.pptx",
        "preview_path": "preview/slide-001-render.png"
      }
    }
  ]
}
```

## qa/reviews/slide-comp/slide-XXX.json

Required for generated ImageGen comp workflows before PPTX conversion. Direct conversion from user-supplied final images does not use this artifact.

```json
{
  "review_type": "slide_comp",
  "stage": "slide_comp",
  "slide_id": "slide-001",
  "style_lane_id": "lane-a",
  "approved_comp_path": "slides/slide-001-comp.png",
  "subagent_review_required": true,
  "reviewer_mode": "subagent | main_agent_role_review",
  "subagent_fallback_reason": "",
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
    "visual-clarity"
  ],
  "role_reviews": [
    {
      "role": "content-integrity",
      "stage": "slide_comp",
      "scope": "slide-001",
      "approval_to_advance": true,
      "findings": [],
      "accepted_risks": [],
      "notes": ""
    }
  ],
  "unresolved_p0_p1": [],
  "overall_status": "approved",
  "approval_to_advance": true
}
```

## conversion_manifest.json

Use for both generated comps and direct image-to-PPTX conversion. `reconstruction-only` remains a compatibility mode name, but this manifest owns the new strict converter path.

```json
{
  "lock_state": "draft | locked",
  "mode": "create | template-following | targeted-edit | reconstruction-only | repair-existing-pptx",
  "source": "approved_imagegen_comps | user_supplied_slide_images",
  "conversion_method": "strict_slide_image_to_editable_pptx",
  "tool_files": {
    "slidelib": "slidelib.py",
    "iconcut3": "iconcut3.py",
    "qa_gate": "qa_gate.py",
    "realesrgan_upscale": "scripts/realesrgan_upscale.py",
    "pitfalls": "PITFALLS.md",
    "copied_to_workspace": {"slidelib.py": true, "iconcut3.py": true, "qa_gate.py": true, "PITFALLS.md": true, "scripts/realesrgan_upscale.py": true}
  },
  "basis_px": {"width": 1920, "height": 1080},
  "slide_count": 1,
  "page_modules": {
    "enabled": true,
    "per_slide_pptx_required": true,
    "merge_after_page_approval": true,
    "parallel_subagents_recommended": true
  },
  "global_rules": {
    "skip_full_pipeline_gates": false,
    "visual_fidelity_priority": "strict_slide_image_to_editable_pptx",
    "source_image_is_measurement_target_not_final_layer": true,
    "source_comp_realesrgan_4k_required": true,
    "full_image_or_region_layers_forbidden": true,
    "ordinary_table_or_card_rebuild_forbidden": true,
    "native_text_shapes_charts_required": true,
    "hidden_text_layer_does_not_count_as_editable": true,
    "strict_icon_extraction_required": true,
    "icon_contact_sheet_audit_required": true,
    "source_icon_inventory_required": true,
    "real_source_icons_must_be_extracted": true,
    "native_redraw_for_named_pictograms_forbidden": true,
    "icon_hd_enhancement_required": true,
    "icon_realesrgan_upscale_required": true,
    "multiline_text_split_required": true,
    "minimum_render_compare_rounds": 10,
    "render_round_requires_new_export": true,
    "qa_gate_required": true,
    "metrics_gate_reads_actual_render": true,
    "media_audit_required": true
  },
  "slides": [
    {
      "slide_id": "slide-001",
      "source_image_path": "slides/slide-001-comp.png",
      "raw_source_image_path": "slides/raw/slide-001-raw.png",
      "upscale_manifest_path": "upscale/slide-001-comp.realesrgan.json",
      "basis_image_path": "measurements/slide-001-src.png",
      "text_source_status": "provided | ocr_verified | user_accepted_image_text | image_only_accepted",
      "measurement_status": "planned | completed | approved",
      "icon_extraction_status": "planned | passed | not_applicable",
      "icon_edge_audit_status": "pending | passed | not_applicable",
      "icon_contact_sheet_audit_status": "pending | passed | not_applicable",
      "source_icon_inventory_status": "pending | icons_detected | no_source_icons_detected",
      "extracted_icon_count": 0,
      "icon_jobs_path": "icons/icon_jobs.json",
      "icon_upscale_manifest_path": "icons/icon_upscale_manifest.json",
      "icon_contact_sheet": "icon-sheets/icon-contact-sheet.png",
      "build_script_path": "builders/slide-001.py",
      "output_slide_pptx": "slide-modules/slide-001.pptx",
      "preview_path": "preview/slide-001-render.png",
      "latest_render_path": "preview/slide-001-render-r10.jpg",
      "render_log_path": "qa/render-compare/render_log.json",
      "qa_gate_output_path": "qa/render-compare/qa_gate-slide-001.txt",
      "native_build_status": "planned | passed | approved",
      "render_compare_rounds_completed": 0,
      "paired_crops_status": "pending | passed",
      "max_region_mean_abs": 0,
      "review_status": "not_started | approved | user_accepted_risk"
    }
  ],
  "final_outputs": [{"path": "output/deck.pptx", "sha256": "sha256:<hash>"}],
  "open_questions": []
}
```

## qa/render-compare/render_compare_rounds.json

```json
{
  "status": "not_started | running | passed",
  "policy_ref": "visual_contract.json.render_compare_loop",
  "minimum_rounds": 10,
  "completed_rounds": 10,
  "rounds": [
    {
      "round": 1,
      "pptx": "slide-modules/slide-001.pptx",
      "render": "preview/r-001-slide-001.jpg",
      "fixes": ["adjusted title x", "re-extracted icon a"],
      "unresolved": []
    }
  ],
  "paired_crops": [
    {"slide_id": "slide-001", "source_crop": "crops/src-title.png", "render_crop": "crops/render-title.png", "status": "passed"}
  ],
  "region_metrics": [
    {"slide_id": "slide-001", "region": "title", "mean_abs": 22.4, "status": "normal"}
  ],
  "unresolved_p0_p1": []
}
```

## qa/render-compare/render_log.json

Strict log used by `qa_gate.py rounds`. This is separate from the human-readable comparison summary above. A counted round must have a distinct, existing render file produced by a fresh LibreOffice/Poppler export.

```json
[
  {
    "round": 1,
    "render": "preview/slide-001-render-r01.jpg",
    "timestamp": "2026-06-13T10:00:00",
    "max_metric": 52.0,
    "issues": "title band y offset and clipped target icon",
    "fix": "shifted title band +14px and widened target extraction box",
    "recheck": "title band aligned; target icon no longer clipped"
  }
]
```

## QA Reports

`qa_report.md` should include:

- Source Truth
- Slide Intent Gate
- Narrative Treatment Gate
- Style Direction Gate
- Visual Comp Gate
- Template Fidelity Gate
- PPTX Conversion Gate
- Reviewer Findings
- Final Council
- Editability
- Known Limitations

`qa/final-council.md` must include the token `pptx-conversion-fidelity` and an `Export Decision`.
