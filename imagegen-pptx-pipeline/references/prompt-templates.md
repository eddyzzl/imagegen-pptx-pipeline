# Prompt Templates

Use these as starting points. Fill placeholders from `deck_spec.json`, `design_system.json`, and the current workspace artifacts.

## 1. Brief Grill And Content Lock

```text
Run a content-only grill before any ImageGen work.

Inputs:
- User brief or outline: <outline>
- Template/reference notes: <summaries>
- Current deck_spec.json: <draft spec>
- source_notes.md: <sources, assumptions, missing inputs>

Goal:
Find the fewest highest-leverage questions or fixes needed before visual generation.

Check:
1. Classify the input as explicit_per_page, brief_outline, template_only, reference_only, mixed, or final_slide_images.
2. Select deck_profile.
3. Confirm audience, objective, tone, density, proof level, and template constraints.
4. Check every planned slide has a claim and proof object.
5. Remove unsupported claims, fake sources, fake logos, fake UI, or unverifiable numbers.

Output:
- content_review.md with PASS | NEEDS_USER | BLOCKED
- 3 to 7 user-facing questions only if they block useful work
- updated deck_spec.json and pipeline_state.json
- run `check_pipeline_gates.py --stage content-lock` before advancing

Do not generate images. Do not design slides. Do not write PPTX.
```

## 2. Slide Intent Matrix

```text
Run a slide-intent confirmation stage before narrative treatment or ImageGen.

Inputs:
- deck_spec.json
- source_notes.md
- template/reference notes
- user preferences and automation status

Produce `slide_intent_matrix.md`:
| Page | Proposed title | Core idea | Proof goal | Evidence/data candidates | Gaps/questions | Confidence |

Produce `slide_intent_plan.json`:
- lock_state
- source_deck_spec_fingerprint
- matrix_path
- review_status
- slides[] with slide_id, page_number, proposed_title, confirmed_title, core_idea, proof_goal, evidence_candidates, data_to_extract, content_gaps, accepted_assumptions, status
- open_questions[]

After user confirmation:
- update deck_spec.json if titles/claims/proof objects changed
- set lock_state=locked
- set every slide status to confirmed or accepted_assumption
- run `check_pipeline_gates.py --stage slide-intent-lock`

Do not continue to narrative treatment until the gate passes.
```

## 3. Narrative Treatment Matrix

```text
Run a narrative-treatment selection stage before ImageGen style work.

Inputs:
- locked deck_spec.json
- locked slide_intent_plan.json
- design_system.json
- source_notes.md
- user preferences

Create 3 to 5 narrative options. Narrative options may change presentation angle and emphasis, but may not change slide count, order, claims, data, logos, sources, products, or results.

Produce `narrative_matrix.md`:
- rows: slides in locked order
- first columns: page number, slide title, confirmed core idea, proof goal
- one column per narrative option
- each option cell states: presentation strategy, content to show, proof object expression, must preserve

Produce `narrative_plan.json` with the same options and per-slide selected_treatment fields.

After user selection:
- set selected_narrative_id
- set slide_intent_lock_state=locked
- populate selected_treatment for every slide
- set lock_state=locked
- update style_brief.json narrative_lock fields
- run `check_pipeline_gates.py --stage narrative-lock`
```

## 4. Style Lane Contact Sheet

```text
Use ImageGen to generate exactly one full-deck 16:9 contact-sheet style lane for <style_lane_id> / Option <option_id>.

Inputs:
- deck_spec.json summary
- slide_intent_plan.json summary
- narrative_plan.json selected treatment
- design_system.json template and brand constraints
- deck_profile_evidence and style_recommendation_policy from style_brief.json
- diversity_contract from style_brief.json
- style lane: option_id, style_id, style_source, aesthetic_family, visual_signature, task_fit, layout_archetype, evidence_presentation, composition_grammar, density_and_pacing, thumbnail_differentiators, must_not_reuse
- narrative lock fingerprint and locked slide order
- image_quality_policy
- relevant entries from references/style-library.md and references/taste-system.md
- template/source slide screenshots if any

Requirements:
1. Output exactly one contact sheet for Option <option_id>.
2. Include all slides in locked order.
3. Keep the same story, claims, data, and proof-object intent.
4. Express only visual/aesthetic differences: composition grammar, material/depth, typography feel, density, icon language, chart rendering, and diagram style.
5. Make agent-recommended options task-appropriate for deck_profile_evidence and its selected profile route. If the user explicitly asked for an off-profile style, render it and record `task_fit.profile_match=false` plus `task_fit.user_requested_off_profile=true` instead of pretending it is the default task-fit recommendation.
6. Make this option structurally different from the other options. The difference must be visible at thumbnail scale through layout_archetype, evidence_presentation, composition_grammar, density/pacing, and title treatment. Merely changing icons, line styles, accent colors, or small modules is a failed option.
7. Respect must_not_reuse. Do not reuse the same center loop, four-card ring, top breadcrumb, bottom metric strip, equal-card grid, or red-white frame from another option unless that is the declared unique archetype for this lane.
8. Keep body copy readable for editable PPT conversion: design around 10-11pt minimum body text, larger key labels, and no dense microtext.
9. Do not invent logos, people, product UI, brands, numbers, or sources.
10. If a template/source PPTX exists, preserve its protected frame and explore only inside allowed content zones.
11. Make titles, key numbers, proof objects, and page structure readable enough for selection.

Output path:
- `styles/<style_lane_id>-contact-sheet.png`
- prompt saved under `prompts/<style_lane_id>-contact-sheet.txt`
- update style_brief.json style_lanes[] and style_contact_sheets[]
```

## 5. Single-Slide Comp

```text
Use ImageGen to generate one high-resolution 16:9 single-slide comp.

This is part of a serial pass within one selected style lane. Do not delegate isolated final pages to separate page-owning agents unless the user accepted style drift risk.

Inputs:
- deck_spec.json slide <slide_id>
- slide_intent_plan.json row
- narrative_plan.json selected_treatment row
- selected style contact sheet
- comp_style_lock from previous approved slides in this lane
- template/source slide screenshot if any
- image_quality_policy

Requirements:
1. Generate only the requested slide, not a contact sheet.
2. Preserve title meaning, claim, proof object, data, sources, and selected narrative treatment.
3. Preserve recurring chrome: logo, page number, footer, title furniture, section labels, and background rhythm.
4. Request crisp text edges, vector-like icons, sharp fine lines, no blur, and highest available detail.
5. Avoid unreadable microtext. If exact tiny text is hard, preserve spatial intent and leave exact final copy to strict PPTX conversion from deck_spec.json.
6. Save raw output under `slides/raw/`.
7. Save downstream comp as `slides/slide-XXX-comp.png` or `slides/<style-lane-id>/slide-XXX-comp.png`.
8. Run slide-comp reviewer roles from `references/subagent-rubrics.md` before accepting.
9. Write `qa/reviews/slide-comp/slide-XXX.json` with all required role reviews, no unresolved P0/P1, and `overall_status="approved"`.
```

## 6. Conversion Contract

```text
Extract the strict slide-image-to-PPTX conversion contract from approved comps or user-supplied final slide images.

Inputs:
- approved slide images
- deck_spec.json exact text
- visual_contract.json draft
- conversion_manifest.json draft
- PITFALLS.md
- qa_gate.py

For every slide, record:
1. source_image_path and basis_image_path
2. text_source_status
3. measurement_status
4. expected native text, shape, connector, chart, table, and page chrome elements
5. text line-splitting plan, especially for multi-line CJK and mixed-size numeric runs
6. source icon inventory status: `icons_detected` or `no_source_icons_detected`
7. icon extraction jobs for every recognizable source pictogram; use `not_applicable` only with `source_icon_inventory_status=no_source_icons_detected`
8. icon_edge_audit_status, icon_contact_sheet_audit_status, extracted_icon_count, icon_jobs_path, and icon_contact_sheet
9. build_script_path, output_slide_pptx, preview_path, latest_render_path
10. render_compare_rounds_completed, strict render_log_path, QA gate output path, and paired crop plan
11. accepted risks, if any

Set:
- visual_contract.json conversion_method=strict_slide_image_to_editable_pptx
- visual_contract.json conversion_policy.method=strict_slide_image_to_editable_pptx
- visual_contract.json strict_icon_policy.extractor_script=iconcut3.py
- visual_contract.json render_compare_loop.minimum_rounds=10
- visual_contract.json render_compare_loop.render_log_path=qa/render-compare/render_log.json
- visual_contract.json render_compare_loop.round_requires_new_export=true
- visual_contract.json conversion_policy.qa_gate_required=true
- conversion_manifest.json lock_state=locked only after every slide has a valid source image and text_source_status

Run `check_pipeline_gates.py --stage before-pptx` before writing final PPTX code.
```

## 7. Strict Slide Image To PPTX

```text
Convert approved slide images into editable PPTX using the bundled converter.

Before coding:
- Read PITFALLS.md.
- Copy slidelib.py, iconcut3.py, qa_gate.py, PITFALLS.md, and scripts/realesrgan_upscale.py into the workspace if missing.
- Process every approved or supplied source slide through `scripts/realesrgan_upscale.py --kind comp --model-path <RealESRGAN_x4plus.pth> --tile 400 --tile-pad 12 --pre-pad 0` first.
- Use only the exact 3840x2160 Real-ESRGAN comp as `source_image_path`; record `upscale_manifest_path`.
- Work in 1920x1080 basis coordinates after that.
- Keep the Real-ESRGAN 4K source as `hd`; use `scale = hd.width / 1920`.

Phase 1: Measure
- Create `measurements/slide-XXX-src.png` at 1920x1080.
- Use numpy scans for card/box edges, text rows, column runs, color masks, and exact sampled colors.
- For ambiguous areas, create magnified labeled grid crops with burnt-in coordinates.
- Transcribe text from full-resolution narrow strips, not thumbnails.

Phase 2: Extract icons
- Inventory every recognizable source pictogram. If you can name it (target, shield, database, briefcase, person, building, bulb, cube, chart, people), extract it.
- Use `iconcut3.run_jobs` or `iconcut3.strict_cut3`; strict extraction HD-enhances line-art icons to at least 256px minimum dimension before placement.
- Run `scripts/realesrgan_upscale.py --kind icon --input icons --output icons/upscaled --manifest icons/icon_upscale_manifest.json --model-path <RealESRGAN_x4plus.pth> --target-min 256 --tile 400 --tile-pad 12 --pre-pad 0`.
- Place only `icons/upscaled/*` assets into PPTX.
- On ClipError, fix the box, clear rects, or core box and rerun.
- Never hand-crop, alpha-key manually, or add a lenient fallback.
- If icons were already extracted, run `iconcut3.enhance_dir(outdir, feathered=(...))` before building the PPTX.
- If art is inseparable from its background, use a feathered opaque slice with sampled native underlay color, document it, and keep alpha crisping disabled for that slice name.
- Build an icon contact sheet and confirm every asset is a pictogram, not a text label.

Phase 3: Build native PPTX
- Use `SB(1920,1080,bg)` from slidelib.py.
- Use native text boxes, shapes, connectors, charts, tables, cards, dividers, and page chrome.
- Do not place the full source image or large regions as a background.
- Split CJK multi-line text into separate absolute boxes.
- Split mixed-size numeric runs into separate absolute boxes.
- Use native geometry for simple dots, chevrons, rings, checks, and arrows.
- Do not use `slidelib` glyph helpers to redraw named source pictograms; those helpers are placeholder scaffolding only.

Phase 4: Render and compare
- Render with LibreOffice and Poppler:
  `soffice --headless --convert-to pdf --outdir pdf out.pptx`
  `pdftoppm -jpeg -r 150 -scale-to-x 2001 -scale-to-y -1 pdf/out.pdf r`
- Each round must create a new LibreOffice/Poppler export, full-page side-by-side output, and paired source/render crops.
- Compute region mean absolute diff on matched crops.
- 15-35 is normal for font rendering; >40 means a real defect.
- Fix one issue cluster per round.
- Run at least 10 real export rounds; re-reviewing the same render does not count.
- Update `qa/render-compare/render_log.json` as a strict list where every entry references a distinct existing render file.
- Update `qa/render-compare/render_compare_rounds.json` as the human-readable crop/metric summary.
- Run `python qa_gate.py all SRC.png LATEST_RENDER.jpg out.pptx qa/render-compare/render_log.json icons/icon_jobs.json`; paste or save the real output.

Do not finalize until `qa_gate.py all`, the conversion gate, and final gate pass.
```

## 8. Direct Image Conversion

```text
Run only the image-to-editable-PPTX conversion phase.

Use this when the user supplies final slide images. Do not redo content planning, narrative selection, style exploration, or ImageGen.

Steps:
1. Initialize workspace with `--mode reconstruction-only` or `--mode repair-existing-pptx`.
2. Copy/register each source image.
3. Copy slidelib.py, iconcut3.py, qa_gate.py, and PITFALLS.md into the workspace.
4. Create minimal locked deck_spec.json.
5. Create locked conversion_manifest.json.
6. Create visual_contract.json with conversion_method=strict_slide_image_to_editable_pptx.
7. Run `check_pipeline_gates.py --stage conversion-lock`.
8. Measure, extract icons, build native PPTX, render, compare, and iterate for at least 10 real export rounds.
9. Run `check_pipeline_gates.py --stage final`.
```

## 9. Final Council

```text
Run final all-role review before export.

Inputs:
- final editable PPTX path
- rendered final preview PNGs
- final preview contact sheet
- deck_spec.json
- visual_contract.json
- conversion_manifest.json
- qa/render-compare/render_compare_rounds.json
- qa/render-compare/render_log.json
- qa_gate.py output
- source_notes.md
- qa_report.md

Roles:
content-integrity, narrative-invariance, text-typography, source-data-verifier, chart-logic, asset-authenticity, color-brand, style-coherence, accessibility-readability, layout-pptx-feasibility, visual-fidelity, pptx-conversion-fidelity, executive-polish, taste-direction, and template-fidelity when a template/source deck exists.

Return:
- qa/final-council.md
- updated qa_report.md
- Export Decision: EXPORT | ITERATE | NEEDS_USER | BLOCKED

Export only when:
- final slide count and order match deck_spec.json
- all main text and numbers are visible and editable
- no full-slide or region-image layer is used as the primary slide
- every retained icon passed strict extraction/contact-sheet audit or has a documented art-slice exception
- render_compare_rounds completed_rounds >= 10 and strict render_log has >=10 distinct existing render files
- `qa_gate.py all` passes with the actual latest render and PPTX
- paired crops and real region metrics support visual fidelity
- no P0/P1 findings remain unless explicitly accepted

After writing final QA, run `check_pipeline_gates.py --stage final`.
```
