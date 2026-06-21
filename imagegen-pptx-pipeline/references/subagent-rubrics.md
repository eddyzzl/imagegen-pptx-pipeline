# Subagent Rubrics

Use these reviewer roles for bounded review. Subagents may review source material, draft prompt notes, inspect comps, or audit finished conversion artifacts. They must not independently generate isolated final single-slide ImageGen comps unless the user explicitly accepted style drift risk.

## Review Stages

| Stage | Roles | Gate |
| --- | --- | --- |
| content/source lock | `content-completeness`, `deck-profile-strategist`, `brief-interrogator`, `content-strategist`, `source-data-verifier`, `audience-advocate` | no ImageGen until deck_spec is locked |
| slide intent | `slide-intent-reviewer`, `content-strategist`, `source-data-verifier`, `audience-advocate` | no narrative options until slide_intent_plan is locked |
| narrative selection | `narrative-invariance`, `content-strategist`, `audience-advocate` | no style options until narrative_plan is locked |
| style direction | `narrative-invariance`, `style-coherence`, `color-brand`, `executive-polish`, `taste-direction`, `design-diversity`, `image-art-director`, `template-fidelity` | no single-slide comps until selected styles pass |
| slide comp review | `content-integrity`, `text-typography`, `visual-fidelity`, `style-continuity`, `image-art-director`, `layout-pptx-feasibility`, `chart-logic`, `asset-authenticity`, `template-fidelity`, `accessibility-readability`, `visual-clarity` | no PPTX conversion until approved comps pass |
| conversion input lock | `conversion-input-verifier`, `text-typography`, `layout-pptx-feasibility`, `strict-icon-auditor`, `template-fidelity` | no PPTX build until every page has source image, text status, measurement plan, icon plan, and output path |
| PPTX conversion | `pptx-conversion-fidelity`, `visual-fidelity`, `visual-clarity`, `text-typography`, `strict-icon-auditor`, `render-compare-auditor`, `accessibility-readability`, `template-fidelity` | no merge/export until 10+ rounds and no P0/P1 conversion defects |
| final synthesis | `deck-council-synthesizer` | export only when every required role approves |

## Shared Feedback Schema

```json
{
  "role": "role-name",
  "stage": "pre_visual | slide_intent | narrative_selection | style_selection | slide_comp | conversion_input | pptx_conversion | final_council",
  "scope": "slide-001 | style-lane-a | deck",
  "approval_to_advance": true,
  "findings": [
    {
      "severity": "P0 | P1 | P2 | P3",
      "location": "artifact/path or slide id",
      "issue": "",
      "evidence": "",
      "recommended_fix": ""
    }
  ],
  "accepted_risks": [],
  "notes": ""
}
```

Severity:

- `P0`: factual error, invented data/source/logo, wrong slide order, missing slide, non-editable main text in final PPTX, final slide mostly a flat source image, unverified icon extraction, missing approved comp/source image, template-breaking output, or skipped required render-compare rounds.
- `P1`: major readability, brand, layout, source, chart, story, design-quality, icon clipping, CJK wrapping, or conversion-fidelity problem that should block the next phase.
- `P2`: fix before final if time allows.
- `P3`: polish note.

## Slide Comp Review Evidence

For generated ImageGen workflows, every approved comp must have one JSON file in `qa/reviews/slide-comp/` before PPTX conversion. Use `reviewer_mode="subagent"` when reviewer subagents were actually dispatched. If subagent tooling is unavailable, use `reviewer_mode="main_agent_role_review"` only with a concrete `subagent_fallback_reason`; do not silently omit the review.

Each slide-comp review JSON must include:

- `review_type="slide_comp"`, `stage="slide_comp"`, `slide_id`, and `approved_comp_path`.
- `subagent_review_required=true`.
- all slide-comp roles in `required_roles` and `role_reviews`.
- `approval_to_advance=true` for every role.
- `unresolved_p0_p1=[]`, `overall_status="approved"`, and top-level `approval_to_advance=true`.

The required slide-comp roles are `content-integrity`, `text-typography`, `visual-fidelity`, `style-continuity`, `image-art-director`, `layout-pptx-feasibility`, `chart-logic`, `asset-authenticity`, `template-fidelity`, `accessibility-readability`, and `visual-clarity`. Roles that are not applicable to a page, such as `chart-logic` on a non-chart page or `template-fidelity` without a template, still write an approving role review with a short not-applicable note.

## Role Prompts

### content-completeness

Check whether the user supplied enough content to lock a deck. Classify input type. Flag missing audience, objective, slide scope, required claims, proof objects, source data, brand assets, and template constraints.

### deck-profile-strategist

Select the primary deck_profile and check whether slide proof objects fit that profile. Flag weak proof objects for technical, board, investor, sales, training, or company-profile decks.

### brief-interrogator

Ask the fewest hard questions needed to proceed. Focus on objective, audience, stakes, tone, constraints, success criteria, and unavailable source truth.

### content-strategist

Check story spine, slide order, redundancy, claim strength, and whether each slide has one dominant proof object.

### source-data-verifier

Check source coverage, metric definitions, units, dates, unsupported claims, fake logos, fake screenshots, and unverified identity assets.

### audience-advocate

Check whether the deck fits the reader's knowledge level, objections, and decision context.

### slide-intent-reviewer

Review `slide_intent_plan.json` and `slide_intent_matrix.md`. Flag missing titles, weak core ideas, unclear proof goals, evidence gaps, unsupported assumptions, or slide order drift.

### narrative-invariance

Verify that style lanes, comps, and final PPTX preserve locked slide count, order, claims, data, proof-object intent, and selected narrative treatment.

### style-coherence

Check whether a style option or comp is a coherent visual system with consistent typography, color, background, chart language, icon style, and page chrome.

### color-brand

Check color contrast, brand fit, palette consistency, and template/source brand preservation.

### executive-polish

Check whether the deck looks finished enough for the target audience. Flag generic table/card layouts, weak hierarchy, uneven spacing, decorative noise, and low-ambition compositions.

### taste-direction

Apply `references/taste-system.md`. Flag flat/default layouts when a richer proof object is appropriate, near-identical style options, weak focal objects, and unintentional one-note visual systems.

### design-diversity

For style options, check that directions differ by aesthetic family, composition grammar, material/depth, chart language, density, and typography feel. They must not differ by story or content strategy.

### image-art-director

Check whether ImageGen is being used for real art direction instead of default PPT boxes. Flag comps that are much flatter or less designed than the selected style lane.

### content-integrity

Compare comp/final slides against `deck_spec.json`. Flag missing claims, wrong numbers, invented source material, wrong units, changed meaning, or unsupported visual conclusions.

### text-typography

Check exact text plan, title/body hierarchy, line breaks, overflow, CJK wrapping risk, mixed-size numeric runs, and whether final PPTX text is visible and editable. Flag reliance on automatic wrapping for multi-line text.

### visual-fidelity

Compare approved source images/comps against rendered PPTX previews. Flag changed proof-object shape, altered flow direction, missing visual hierarchy, degraded density, or generic rebuilds.

### style-continuity

For generated comps, compare each slide against the selected contact sheet and previous approved comps. Check recurring chrome, page number placement, footer, title furniture, logo, background rhythm, and chart/icon stroke.

### visual-clarity

Flag blurry titles, unreadable key numbers, muddy icons, soft fine lines, low-resolution images, or compression artifacts. Recommend regeneration before PPTX conversion when the source image itself is unusable.

### layout-pptx-feasibility

Check whether the source image can be rebuilt with native PowerPoint text, shapes, connectors, charts, and tables using the strict converter. Flag areas requiring a documented feathered art slice.

### chart-logic

Check chart type, units, labels, scale, data-to-visual fit, and whether approximations are acceptable.

### asset-authenticity

Check logos, screenshots, people, product UI, official marks, icons, and identity assets for provenance. Generated non-identity decoration is allowed; fake identity assets are not.

### template-fidelity

When a template/source PPTX exists, check that protected elements remain: master/layout feel, typography, palette, logos, footer, page markers, title furniture, and brand chrome.

### accessibility-readability

Check projection readability, contrast, color-only encoding, small text, visual noise, and whether important labels survive conversion.

### conversion-input-verifier

Review `conversion_manifest.json`, `visual_contract.json`, source slide images, and optional text files. Check that every slide has:

- source_image_path
- exact 3840x2160 Real-ESRGAN comp source, not a raw 1080p/2K image
- `upscale_manifest_path` proving Python `RealESRGANer` processed the comp with `RealESRGAN_x4plus.pth`, CPU, and tile=400
- valid text_source_status
- 1920x1080 basis path or a plan to create it
- measurement_status planned/completed
- strict icon plan, or `not_applicable` backed by `source_icon_inventory_status=no_source_icons_detected`
- build_script_path
- output_slide_pptx
- preview_path

Flag P0 if only a contact sheet was supplied for multiple slides without user acceptance, if page order is ambiguous, if `conversion_manifest.lock_state` is not locked, or if bundled tools are missing.

### strict-icon-auditor

Review icon extraction jobs, outputs, and contact sheets. Require:

- `iconcut3.strict_cut3` or `iconcut3.run_jobs`
- source icon inventory before extraction
- every named source pictogram is extracted; native redraw via `slidelib` glyph helpers is not accepted for real icons
- no manual crop fallback after ClipError
- strict line-art icons are HD-enhanced and then processed with Python `RealESRGANer` on CPU before PPTX placement
- icon jobs reference `icons/icon_upscale_manifest.json`, and PPTX placement uses `icons/upscaled/*`
- 4-edge alpha audit passes for transparent icons
- contact sheet proves every asset is a pictogram, not text
- wide assets with aspect >2.5 are justified row strips or re-extracted
- feathered opaque slices are documented, placed over sampled native fill, and enhanced with alpha crisping disabled

Flag P0 for clipped icons, icons touching image edges, text labels captured as icons, missing Real-ESRGAN HD enhancement/contact-sheet audit, source pictograms redrawn with native glyph helpers, feathered slices sharpened into visible seams, or `not_applicable` without a no-source-icons inventory.

### render-compare-auditor

Review `qa/render-compare/render_compare_rounds.json`, strict `qa/render-compare/render_log.json`, full-page renders, paired crops, and `qa_gate.py` output. Require at least 10 rounds backed by distinct existing render files. Region mean abs over 40 is a blocking defect because the mechanical gate recomputes the real value from the latest render; do not accept hand-written lower blocking values.

### pptx-conversion-fidelity

Compare approved source images/comps against final rendered PPTX previews and `conversion_manifest.json`.

Flag P0 for:

- final slides that are only one flat image with no editable main information
- missing visible editable main text
- source/comp paths that point to PPTX previews or output images
- skipped strict icon audits
- all-vector icon redraw when the source contains recognizable pictograms
- skipped 10-round render-compare loop, reused render files, or missing `qa_gate.py all` PASS
- final output that ignores the source image layout

Flag P1 for:

- rich comp becomes ordinary table/card grid
- major diagram geometry changes
- title/body line breaks drift materially
- icons are clipped, boxed, or wrong
- CJK text wraps differently from the source
- region diff metrics remain over threshold

Accept complex art/photo/texture/image fragments only when they are documented exceptions and do not replace the main slide structure.

### deck-council-synthesizer

Deduplicate findings, resolve role conflicts, assign final severity, and decide PASS, NEEDS_ITERATION, NEEDS_USER, or BLOCKED. For final PPTX review, export is allowed only when every required role has `approval_to_advance=true` and no P0/P1 remains unless `user_decisions.md` explicitly accepts the risk.
