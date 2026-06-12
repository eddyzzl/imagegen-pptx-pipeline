# Prompt Templates

Use these as starting points. Fill placeholders from `deck_spec.json` and `design_system.json`.

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
0. Classify the input as explicit_per_page, brief_outline, template_only, reference_only, or mixed.
1. Select the primary deck profile: product-pitch, company-profile, model-technical, sales-gtm, strategy-executive, investor-finance, training-enable, internal-review, or other.
2. Is the audience clear enough to choose tone, density, proof level, and visuals?
3. Is the deck objective explicit: inform, persuade, sell, raise money, approve a plan, train, or report?
4. Does every planned slide have a claim and proof object appropriate to the deck profile?
5. Are any claims unsupported by data/source/user confirmation?
6. Are there missing metrics, dates, definitions, units, logos, screenshots, or brand assets?
7. Are there slide-order, redundancy, or narrative gaps?
8. What assumptions can be made safely if the user wants full automation?

Output:
- content_review.md with PASS | NEEDS_USER | BLOCKED
- 3 to 7 user-facing questions only if they block visual work
- if content is only a brief outline, draft the proposed slide-by-slide content plan and ask for confirmation unless full automation was explicitly requested
- if content is explicit per page, avoid broad rewriting; ask only for P0/P1 factual, source, audience, or scope gaps
- suggested `deck_spec.json.lock_state`: draft | needs_user_confirmation | locked
- selected deck_profile and profile_requirements
- updated pipeline_state.json if user input is required
- run `check_pipeline_gates.py --stage content-lock` before advancing

Do not generate images. Do not design slides. Do not write PPTX.
```

## 2. Slide Intent Matrix

```text
Run a slide-intent confirmation stage before any narrative treatment or ImageGen work.

Inputs:
- Locked or near-locked deck_spec.json: <slide order, proposed titles, claims, body/data, proof objects, sources>
- source_notes.md: <source extracts, assumptions, missing inputs>
- Template/reference notes: <template slide requirements and historical reference lessons>
- User brief classification: explicit_per_page | brief_outline | template_only | reference_only | mixed
- User preferences: <audience, objective, must/avoid, full automation if explicitly requested>

Goal:
Confirm each planned slide's title, core idea, proof goal, and evidence strategy before asking the user to choose a narrative treatment. This is the bridge between "content is roughly known" and "every page has a locked intent."

Requirements:
1. Do not generate images, narrative options, style options, or PPTX.
2. Do not add/delete/reorder slides unless the content grill already decided the deck structure should change.
3. Do not invent metrics, facts, logos, sources, customer names, product UI, or outcomes.
4. If the user provided explicit per-page content, preserve it and only confirm title/core idea/proof goal/source gaps.
5. If the user provided only a brief outline, infer a slide-by-slide intent plan from the brief, template, references, and supplied sources, then ask the user to confirm or edit it.
6. Evidence must come from supplied materials, verified sources, or accepted assumptions clearly labeled as such.
7. A slide may still need final wording later, but it cannot advance without a confirmed core idea and proof goal.

Produce `slide_intent_matrix.md` as a Markdown table:
- rows are slides in planned order
- columns: Page, Proposed title, Core idea, Proof goal, Evidence/data candidates, Gaps/questions, Confidence
- each row should be concise enough for the user to review quickly

Produce `slide_intent_plan.json`:
- lock_state: draft | needs_user_confirmation | locked
- matrix_path: slide_intent_matrix.md
- review_status: not_started | approved | user_accepted_risk
- slides[] with slide_id, page_number, proposed_title, confirmed_title, core_idea, proof_goal, evidence_candidates, data_to_extract, content_gaps, accepted_assumptions, status
- open_questions[] with only P0/P1 questions that block useful narrative choices

After user confirmation:
- apply any user edits back to deck_spec.json titles/claims/proof objects where needed
- set slide_intent_plan.json.lock_state=locked
- set every slide status to confirmed or accepted_assumption
- set slide_intent_plan.json.review_status=approved or user_accepted_risk
- update pipeline_state.json current_stage=slide_intent_lock and stage_history
- run `check_pipeline_gates.py --stage slide-intent-lock`

Do not continue to narrative treatment until the slide-intent gate passes.
```

## 3. Narrative Treatment Matrix

```text
Run a narrative-treatment selection stage before any ImageGen style work.

Inputs:
- Locked deck_spec.json: <exact slide order, titles, claims, body text, data, proof objects, sources>
- Locked slide_intent_plan.json: <confirmed title, core idea, proof goal, evidence strategy for each slide>
- design_system.json: <template constraints, deck profile, audience, density>
- source_notes.md: <assumptions, sources, missing inputs>
- User preferences: <tone, audience, desired emphasis, must/avoid>

Goal:
Create multiple narrative treatments for the same locked deck content so the user can choose how each page should present the content before visual generation.

Requirements:
1. Do not generate images or PPTX.
2. Do not add/delete/reorder slides unless the user explicitly asked to restructure the deck.
3. Do not invent claims, data, sources, logos, people, product UI, or outcomes.
4. Recommend 3 to 5 narrative options that fit the deck profile and audience.
5. Treat slide_intent_plan.json as the confirmed source of each page's core idea and proof goal. Narrative options may change the presentation angle, not what the slide argues.
6. Produce `narrative_matrix.md` as a Markdown table:
   - rows are slides in locked order
   - first columns: page number, slide title, confirmed core idea, proof goal
   - one column per narrative option
   - each option cell states how this page is presented, what content is shown/emphasized, and which proof object expression is used
7. Produce `narrative_plan.json` with the same options and per-slide cells.
8. If the user did not request full automation, ask them to choose one narrative option or edit cells. If the user requested full automation, select the strongest option and record why.

Suggested narrative option families:
- evidence-first: lead with claim and source-backed proof
- story-arc: context, tension, progress, outcome, next step
- technical-system: mechanism, architecture, process, validation, control
- executive-decision: tradeoffs, risks, recommendation, roadmap
- customer-value: pain, solution, impact, adoption, next action
- growth-maturity: baseline, capability build, milestone arc, future commitment

Markdown table cell format:
`展现方式: ...; 展现内容: ...; 证明对象: ...; 保持不变: ...`

Output:
- narrative_matrix.md
- narrative_plan.json with lock_state draft or needs_user_confirmation
- pipeline_state.json updated to current_stage=narrative_selection if user input is required

After user selection:
- set narrative_plan.json.selected_narrative_id
- set narrative_plan.json.slide_intent_plan=slide_intent_plan.json
- set narrative_plan.json.slide_intent_lock_state=locked
- populate confirmed_core_idea for every slide from slide_intent_plan.json
- populate selected_treatment for every slide
- set narrative_plan.json.lock_state=locked
- set narrative_plan.json.review_status=approved or user_accepted_risk
- update style_brief.json.selected_narrative_id, narrative_lock.slide_intent_plan=slide_intent_plan.json, narrative_lock.slide_intent_lock_state=locked, and narrative_lock.narrative_plan_lock_state=locked
- run `check_pipeline_gates.py --stage narrative-lock`
```

## 4A. Parallel Style Lane Contact Sheet

```text
Use case: productivity-visual
Asset type: one 16:9 business PPT full-deck contact-sheet style lane

Primary request:
Use /imagegen to generate exactly one full-deck PPT visual direction contact sheet for <style_lane_id> / Option <option_id>.

Inputs:
- Deck spec: <summarize deck title, audience, objective, slide list, proof objects>
- Slide intent plan: <confirmed core idea and proof goal for each slide>
- Narrative plan: <selected_narrative_id and selected_treatment for each slide>
- Design constraints: <summarize template/reference palette, typography, brand rules, density, footer/page rules>
- Style lane: <option_id, style_id, style_source, style_lane_id, style_name, aesthetic_family, visual_signature, name, premise, must_differ_by>
- Narrative lock: <deck_spec_fingerprint, locked_slide_count, locked_slide_order, invariant fields, forbidden story mutations>
- Style brief: <deck_profile, direction_count, diversity axes, visual ambition, built-in taste guidance>
- Image quality policy: <image_quality_policy; request highest available detail/resolution, 4K single-slide comps, at least 5 MiB per approved comp, identical comp dimensions across the deck, crisp text/icons/fine lines, no blur>
- Built-in style library: <relevant entries from references/style-library.md, including screenshot-inspired categories and style signatures>
- Built-in PPT taste system: <relevant rules from references/taste-system.md, plus any optional supplemental taste sources>
- Template contact sheet and source-slide screenshots, if supplied: <attach or reference images>
- Slide count: <N>

Output requirements:
1. Output exactly one contact sheet for Option <option_id>, not multiple options.
2. The contact sheet must contain all <N> slides in the locked order.
3. Every thumbnail must be a 16:9 landscape PPT slide.
4. Express the assigned `style_id` and `visual_signature` deeply through visual-only choices: composition grammar, material/depth, typography, density, icon/illustration language, chart rendering, and diagram styling. Do not treat the style id as a color label.
5. The option must be a coherent deck system: typography, colors, backgrounds, charts, icons, modules, footers, and page numbers.
6. Preserve the narrative lock and selected narrative treatment. Use only the confirmed outline and content. Do not add, delete, reorder, replace claims, ignore selected treatment, or invent slides.
7. Do not invent data, logos, people, product UI, brands, or sources.
8. Make major titles, key numbers, proof objects, and page structure readable enough for direction selection.
9. Do not generate PPTX and do not generate separate single-slide images in this phase.
10. If a template/source PPTX is supplied, it is a hard frame: preserve its logo/footer/page marker/title furniture/brand chrome and explore different visual expressions only inside its allowed content zones.
11. Use stronger Image2-driven visual design where appropriate to the already-locked slide proof objects: layered diagrams, radial compositions, arcs, funnels, custom process chains, data-story layouts, premium editorial composition, tactile modules, or restrained glass layers.
12. Avoid flat all-card/all-table decks unless the source content truly requires them. A deck that looks like only bordered rectangles and plain tables is not an acceptable high-design option.
13. Make this direction identifiable at thumbnail scale by its assigned canonical style id and visual signature, not by label text alone.
14. Adapt only taste, density, and visual polish to the deck profile. Do not create product, strategy, evidence, roadmap, or system-map content lanes here; those belong in the locked narrative plan.
15. Apply the built-in PPT taste system from `taste_guidance`: avoid generic equal-card grids, flat table-only decks, default PPT template feel, and near-identical variants; use profile-appropriate proof objects and crafted diagram language.
16. If optional external taste sources were recorded, apply only their portable PPT rules and anti-patterns. Do not copy frontend-only interactions, web navigation, hover/GSAP, or responsive layout rules into the slide design.
17. After generation, record the output as `styles/option-<option_id>-contact-sheet.png`, set `generator=imagegen`, and run a narrative-invariance check against the lock.
18. Request maximum available ImageGen fidelity: high-detail rendering, crisp vector-like icons, sharp fine lines, clean anti-aliased typography, high-contrast labels, and no blur/compression artifacts. Note that later single-slide comps must be true 4K and dimension-consistent across the deck.
19. Use a large, clean contact-sheet canvas. Each thumbnail must be sharp enough to judge composition, icon style, title hierarchy, chart strokes, and module boundaries. Do not accept fuzzy thumbnails.
20. Do not create HTML/CSS/SVG blueprints, browser screenshots, React pages, canvas renders, PPTX previews, or static mockups as substitutes for ImageGen outputs.
21. If ImageGen fails and this prompt must be retried shorter, preserve the locked slide order, slide titles, core claims, required data, proof-object intent, template constraints, visual density floor, assigned style id, visual signature, and aesthetic family. Remove only duplicated prose, internal rationale, repeated constraints, or verbose citations. Do not simplify the deck into sparse cards/tables, do not reduce slide count, and do not switch to HTML or browser-rendered previews.

Visual quality bar:
The result should look like a polished commercial/executive deck direction, not a generic default PPT template or scattered draft pages. Use ImageGen's strength to explore crafted composition, depth, diagrams, and visual metaphor while staying within source and template constraints.

Process bar:
If `style_brief.direction_count` is 0 or `selection_mode` is ask_user with no selected option, stop and ask the user. "Help me make a PPT" is not permission to skip style options.
```

## 4B. Multi-Option Fallback Contact Sheet

Use this only when independent style-lane ImageGen calls are unavailable. Prefer 4A. Do not use this as a workaround for ImageGen server errors or prompt failures if it would reduce content density, visual ambition, or option clarity; use the ImageGen retry policy and block after repeated failures instead.

```text
Use case: productivity-visual
Asset type: 16:9 business PPT full-deck multi-option contact-sheet fallback

Primary request:
Generate <K> distinct full-deck PPT visual directions as contact sheets: Option A through Option <K>.

Inputs:
- Deck spec and narrative lock: <locked slide order, claims, proof objects, data, fingerprint>
- Slide intent plan: <confirmed core idea and proof goal for each slide>
- Narrative plan: <selected narrative treatment for each slide>
- Style lanes: <all option_id, style_id, style_source, style_lane_id, style_name, aesthetic_family, visual_signature, premise>
- Built-in style library: <references/style-library.md relevant entries>
- Built-in PPT taste system: <relevant rules>
- Template contact sheet and source-slide screenshots, if supplied: <attach/reference>

Requirements:
1. Output exactly <K> labeled contact sheets.
2. Each option must preserve the same deck narrative lock and slide order.
3. Each option must express a different canonical style id and aesthetic family, not merely recolor a layout.
4. Do not invent, delete, reorder, or rewrite content.
5. Record fallback use in `style_brief.json.generation_mode=single_prompt_fallback` and explain why independent lanes were unavailable.
6. If the fallback prompt has to be shortened, preserve the locked content and visual density floor; shortening is allowed only by removing duplicated prose, not by removing slide content or diagram requirements.
```

## 4C. ImageGen Failure Retry Log

Create or update this whenever an ImageGen style contact sheet or single-slide comp fails, times out, returns a service/server error, returns a wrong asset type, or requires prompt compression.

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

Gate rule: a retry log is not required when ImageGen succeeds on the first try. If a retry log exists, any entry that removes locked content, reduces content/visual density, uses HTML/browser output, switches to generic PPT, or marks a failed asset ready must fail the pipeline.

## 5. Selected Style To Single-Slide Comps

```text
Use case: productivity-visual
Asset type: one high-resolution 16:9 PPT slide visual comp

Primary request:
I selected <Option X>. Based on that PPT contact sheet, continue using /imagegen and generate slide <slide_id> as one independent ultra-sharp high-resolution 16:9 PPT visual comp. Use the highest detail/resolution available. Request true 4K 16:9 (`3840x2160`) first, at least 5 MiB. If the service cannot produce 4K after configured attempts, fall back to 2K (`2560x1440`, at least 2 MiB), then 1080p (`1920x1080`, at least 1 MiB). Use the exact same pixel dimensions as every other approved single-slide comp in this deck.

Preflight contract:
Before calling /imagegen, this prompt must pass `scripts/check_imagegen_comp_asset.py --prompt <prompt-path> --require-fallback-policy`. Keep these constraints explicit: true 4K `3840x2160` first, 2K `2560x1440` fallback, 1080p `1920x1080` target floor, tier file-size minimums, same/identical pixel dimensions across the deck, highest/maximum detail, crisp sharp text/icons/fine lines, no blur/compression artifacts, and no infinite retry loop. If the returned raw image is below the target floor, record it as a raw service fallback and run local normalization only if the visual-clarity reviewer can still approve the normalized output; otherwise regenerate or ask the user.

Execution ownership:
This is part of a serial ImageGen pass inside one style lane. Do not delegate final per-slide ImageGen calls to page-owning subagents. If multiple styles were selected, a style-lane subagent may own this entire style and generate all pages for this style serially. Preserve the same `comp_style_lock` from slide to slide within the style lane.

Inputs:
- Selected contact sheet: <attach or reference image>
- Original PPT outline / deck_spec.json: <exact content source>
- Slide intent plan: <confirmed core idea and proof goal for this slide>
- Narrative plan: <selected treatment for this slide>
- Deck spec for this slide: <exact title, claim, body text, data, proof object, visual intent>
- Design system: <palette, typography, background, chart/icon/card/page rules, built-in taste rules>
- Comp style lock: <comp_style_lock; page chrome, logo/header/footer/page-number/title-furniture rules locked from the selected contact sheet and previous approved comps>
- Previous approved comps: <paths or thumbnails for slide-001..previous slide, used only to keep recurring page chrome consistent>
- Image quality policy: <image_quality_policy; maximum detail, 3840x2160 or higher single-slide output, at least 5 MiB per approved comp, same pixel dimensions for every page, crisp text/icons/fine lines, no blur>
- Template/source slide screenshot, if template-following: <attach mapped source slide screenshot>
- Template protected elements, if template-following: <logo/footer/page marker/title furniture/background frame/etc.>

Task goal:
This is not a redesign, not a content rewrite, and not a generic style application. The selected contact sheet is the parent visual system. The mapped template slide, when present, is the hard canvas frame. Generate the corresponding page as a full-size, clearer, more complete single-slide image for later editable PPTX reconstruction.

Requirements:
1. Generate only this one slide as a complete 16:9 landscape PPT page.
2. Do not generate a contact sheet, grid, or multi-slide image.
3. Preserve the selected option's visual system: type character, size hierarchy, colors, backgrounds, chart language, icon style, cards, margins, white space, footer, page number, and density.
4. If a template/source PPTX is supplied, preserve the mapped source slide's logo, footer, page marker, title furniture, background frame, typography feel, and brand chrome. Do not replace them with a new invented design.
5. Match `comp_style_lock`: same logo placement/size, same header/footer system, same page number placement/format, same title or section treatment, same recurring typography scale, same border/background/chrome rhythm.
6. Compare against previous approved comps. If page chrome, title furniture, footer, page number, logo, recurring icon stroke, or background rhythm drifts, regenerate instead of accepting a near match.
7. Use this slide's confirmed content. Do not invent brands, logos, people, data, products, or sources.
8. Major title, claim, key numbers, chart labels, and page number should be legible.
9. Avoid garbled text, pseudo-Chinese, repeated page numbers, wrong page numbers, missing page numbers, and misspellings.
10. If tiny text is hard to render exactly, preserve the layout relationship and leave final exact text to PPTX reconstruction from `deck_spec.json`.
11. The rendered image must be crisp at full size. Prefer true 4K 16:9 (`3840x2160`) or higher; fallback only to 2K (`2560x1440`) or 1080p (`1920x1080`) when the service cannot produce 4K. Keep sharp title edges, readable key numbers, clean icon strokes, clear chart/diagram lines, high-contrast labels, and no soft-focus blur, glow over text, or compression artifacts.
12. Avoid unreadable microtext. Prefer fewer/larger labels, abbreviated labels, callout grouping, or leaving exact tiny copy to PPTX reconstruction rather than producing blurry pseudo-text.
13. The comp should look like a finished slide, not a wireframe or design note.
14. Output only the high-resolution single-slide image for this page. Do not generate PPTX in this phase.
15. Preserve or improve the selected direction's design quality. Do not simplify the page into plain tables, equal square cards, generic white boxes, or default PPT placeholders unless that exact structure was intentionally selected.
16. Use a slide-specific visual archetype: system map, maturity arc, loop, funnel, radial, timeline, swimlane, matrix, scorecard, dashboard, process chain, comparison, or title composition. Make the archetype obvious.
17. Balance editability with visual richness: keep main text regions clean enough to rebuild later, but allow complex depth, background, icon, and diagram layers that can be retained as cropped image assets in PPTX.
18. Save the raw generated image under `slides/raw/<style-lane-id>/slide-XXX-imagegen.png`. Do not use a PPTX preview, template screenshot, output contact sheet, or final render as this comp.
19. Immediately run `scripts/normalize_slide_comp.py` to create the downstream approved comp as `slides/<style-lane-id>/slide-XXX-comp.png` or `slides/slide-XXX-comp.png` for a single selected style. The normalized comp must be 3840x2160 and is the only file used for visual review and PPTX reconstruction.
20. The raw saved file should meet the active tier when the service can provide it: 4K at least 5 MiB, 2K at least 2 MiB, or 1080p at least 1 MiB. If the service returns less, do not retry forever; normalize, review clarity, and regenerate only when titles, key numbers, icons, or fine lines remain blurry/unusable.
```

## 6. Reviewer Iteration Prompt

```text
Revise the slide visual comp using only the following targeted fixes:
<paste P0/P1 reviewer findings>

Keep unchanged:
- confirmed content and slide order
- selected deck visual system
- proof object type
- page number and footer location
- brand/source constraints
- template frame and protected elements, when a template/source PPTX exists

If findings include visual clarity problems, explicitly fix them: sharpen title/key-number edges, replace muddy icons with cleaner vector-like icons, increase contrast, remove text blur/glow, simplify unreadable microtext, and use the highest available detail/resolution.

Do not redesign unrelated parts. Return a revised single-slide image, not PPTX.
```

## 7. Image Comp To Editable PPTX

```text
Rebuild this slide visual comp as an editable 16:9 PPTX slide.

Inputs:
- Visual comp image: <slide-XXX-comp.png>
- Processed icon manifest and report: <assets/icon-manifests/icon_asset_manifest.json, icon_asset_report.json>
- Deck spec slide: <slide JSON>
- Slide intent plan slide: <confirmed core idea, proof goal, evidence strategy>
- Narrative plan slide: <selected treatment JSON>
- Design system: <design JSON>
- Visual contract slide: <visual_contract.json entry>
- Template/source PPTX and mapped source slide screenshot, if template-following: <paths/images>
- Template frame map, if template-following: <template-frame-map.json entry>
- Template mode: <create | template-following>

Core strategy:
Use native trace hybrid reconstruction by default: preserve the approved visual comp's design quality and composition by treating it as a pixel coordinate blueprint, then rebuild the visible reader-facing structure as native PowerPoint elements. Do not insert the whole comp as the final visible slide layer unless the user explicitly accepted limited editability.

Reconstruction modes:
- native_trace_hybrid: use the approved comp as a pixel coordinate reference, rebuild major structures with native text/shapes/connectors/icons/chart primitives, and keep only genuinely complex visual details as cropped image snippets. This is the default.
- sliced_hybrid: crop stable visual regions from the comp, but rebuild all main text, cards, simple charts, connectors, and page furniture natively. Use only for documented complex subregions.
- pixel_locked_hybrid: use the approved comp as a full-slide backplate, mask text areas, then overlay editable native PPT text/numbers/simple shapes. This is a downgrade exception, not the default.
- native_rebuild: rebuild everything natively only if preview comparison still matches or the user accepted a fidelity downgrade.

Hard requirements:
1. Final text content must come from `deck_spec.json`, not OCR from the comp.
2. Main titles, subtitles, paragraphs, quotes, key numbers, chart labels, annotations, footers, section names, and page numbers must be native editable PPT text unless explicitly impossible.
3. Simple shapes, dividers, geometric frames, labels, buttons, tables, and simple charts should be rebuilt as editable PPT elements.
4. Complex images, photos, texture, 3D, glass, metal, dense icons, official logos, product UI, and complicated diagrams may be retained as cropped high-quality images.
5. Do not rebuild from a blank slide when that would lose the approved comp's composition. Use the comp as a coordinate blueprint and trace the major structure.
6. Preserve composition, hierarchy, color, contrast, spacing, rounded corners, shadows, opacity, alignment, and visual rhythm.
7. If a chart's exact data cannot be inferred from sources, use the data in `deck_spec.json`; if no exact data exists, mark it as visual approximation in QA.
8. Render a preview and iterate if it visibly diverges from the approved comp.
9. Preserve the comp's proof-object archetype. If the comp uses a radial, loop, flow, maturity arc, system map, funnel, or layered diagram, the PPTX must rebuild that same visual expression with editable geometry or documented retained image areas.
10. Do not replace rich visual comps with generic tables, square card grids, or plain text blocks merely because they are easier to implement.
11. If exact geometry cannot be rebuilt, preserve the reader-facing relationship: focal object, flow direction, hierarchy, relative scale, whitespace, and callout placement.
12. In template-following mode, start by duplicating/importing the mapped template/source slide. Preserve protected elements from `template-frame-map.json`; do not start from a blank slide.
13. If the approved comp conflicts with the template frame, stop and request/regenerate a comp inside the template frame. Do not silently discard either the comp or the template.
14. Use retained cropped image layers when needed to preserve ImageGen quality: complex depth fields, textured backgrounds, detailed illustrations, official marks, and ornamental fragments may remain images while all main text/numbers/cards/simple diagrams stay native.
15. Render a preview beside the source comp. If visual fidelity, template fidelity, reconstruction fidelity, or editability fails, iterate before exporting.
16. A whole-slide comp backplate is not allowed by default. It requires `native_trace_exception.user_accepted_risk=true` or `explicit_downgrade_accepted=true`.
17. If a retained image subregion contains duplicated text, mask/cover that subregion text first with matching background patches, then place native editable text above it. If clean masking is impossible, document the exception and keep the retained area as small as practical.
18. If a manual/native rebuild would lose the approved comp's premium feel, use cropped retained image fragments for those regions rather than downgrading the entire slide to a full-slide image.
19. Before starting PPTX reconstruction, run `check_pipeline_gates.py --stage before-pptx`. If it fails, fix the missing ImageGen/style/review artifacts instead of building from scratch.
20. Before placing retained icon images, crop and process icons through `scripts/prepare_icon_assets.py --strict`. Insert only transparent PNGs with padding and no clipped colored pixels.
21. After building the slide/deck, run render/compare/fix loops and record them in `qa/render-fix/render_fix_rounds.json`. Do not finalize the deck until at least 9 rounds are completed with no unresolved P0/P1 findings.
22. Run `scripts/audit_pptx_reconstruction.py --pptx <output.pptx> --visual-contract <visual_contract.json> --report <qa/pptx-reconstruction-audit.json>` and do not finalize unless it returns PASS.
23. Run `scripts/audit_visual_fidelity.py --summary <qa/manual-visual-diff/visual_diff_summary.json> --policy <visual_contract.json> --output-pptx <output.pptx> --report <qa/pptx-visual-fidelity-audit.json>` and do not finalize unless it returns PASS with source/PPTX sha256 binding to the current files. A native-heavy PPTX that visually diverges from the comp is still a failed reconstruction.

Output:
- one editable PPTX or slide module as required by the Presentations workflow
- rendered preview PNG
- short note listing editable elements, retained image areas, and any fidelity deviations
```

## 7B. Reconstruction-Only Image To PPTX

```text
Run only the image-to-editable-PPTX reconstruction phase. Do not redo content planning, narrative selection, style exploration, or ImageGen.

Inputs:
- Final per-slide source images: <slide-001 image ... slide-N image>
- Per-slide exact text or OCR verification plan: <text paths/status>
- Optional template/source PPTX: <template path>
- Output deck name: <name>

Goal:
Convert user-supplied final slide images into an editable 16:9 PPTX using page-sharded native_trace_hybrid reconstruction.

Required setup:
1. Initialize workspace with `--mode reconstruction-only` or `--mode repair-existing-pptx`.
2. Copy/register each source image as `slides/slide-XXX-comp.png` or record its path in `reconstruction_manifest.json`.
3. Create minimal locked `deck_spec.json` with slide count, slide IDs, exact overlay text when available, and editability targets.
4. Set `style_brief.json.selected_option=user-supplied-final-images`.
5. Create `visual_contract.json` with each source image as the approved comp, `reconstruction_mode=native_trace_hybrid`, `native_trace_plan`, `editable_overlay_plan`, processed icon policy, and retained-image exceptions. Do not plan a full-slide backplate unless the user explicitly accepted limited editability.
6. Set `reconstruction_manifest.json.lock_state=locked` only after each slide has a source image and text_source_status is provided, ocr_verified, user_accepted_image_text, or image_only_accepted.

Per-slide build:
1. Build each page independently as `slide-modules/slide-XXX.pptx`.
2. Use the source image as a pixel coordinate blueprint, not the final full-slide layer.
3. Rebuild visible titles, body text, key numbers, labels, page markers, cards, simple charts, tables, dividers, flows, arrows, loops, and page furniture as native PPT elements.
4. Place processed transparent PNG icons and cropped complex image fragments only where native tracing would visibly degrade fidelity.
5. Do not redraw the design as plain tables, card grids, boxes, or generic diagrams.
6. Render `preview/slide-XXX-pptx.png` and compare it with the source image.
7. Iterate only the failed slide module until P0/P1 reconstruction findings are resolved.

Merge:
- Merge approved slide modules only after every page review is approved or user_accepted_risk.
- Then run final council review on the merged deck.

Forbidden:
- Do not use a full-deck contact sheet as a replacement for per-slide source images unless the user accepts lower fidelity.
- Do not create a normal-looking PPT table/card/text layout as a substitute for the source image.
- Do not deliver a slide as only one flat image unless the user explicitly requested non-editable output.
```

## 8. Visual Contract Extraction

```text
Extract a visual reconstruction contract from the selected ImageGen contact sheet and single-slide comps.

Inputs:
- selected contact sheet: <path/image>
- slide comps: <paths/images>
- deck_spec.json: <path/content>
- slide_intent_plan.json: <path/content>
- narrative_plan.json: <path/content>
- design_system.json: <path/content>

For each slide, identify:
1. visual archetype: title, system map, maturity arc, loop, funnel, radial, timeline, swimlane, matrix, scorecard, dashboard, process chain, comparison, or other.
2. reconstruction_mode: native_trace_hybrid by default; sliced_hybrid or pixel_locked_hybrid only with documented exception/user acceptance.
3. native trace plan: pixel-to-inch mapping, native element targets, source image not retained as full-slide layer, and retained-image exceptions.
4. text mask plan: only for retained image subregions where comp-rendered text would duplicate native editable text.
5. editable native plan: titles, body text, key numbers, labels, footers, page markers, cards, simple charts, dividers, connectors, and callouts that must be native PPT.
6. must-preserve composition: focal object, diagram geometry, flow direction, regions, callouts, whitespace, and hierarchy.
7. native reconstruction plan: editable shapes, text, connectors, charts, tables, icons.
8. retained image plan: complex textures, photos, official logos, generated diagram layers, or elements impossible to reconstruct without quality loss.
9. raw comp path, normalized comp path, normalization report path, and final 3840x2160 dimensions.
10. processed icon assets: which simple icons should be cropped into transparent PNGs, the crop boxes, padding, and target PPTX coordinates.
11. prohibited regressions: table-only, square-card-only, generic card grid, default template, text-heavy version, proof-object downgrade, or native-only redraw without proof.
12. acceptable simplifications for editability/template fidelity.
13. reader-facing fidelity targets: what must still match even if pixel-level details differ.
14. preview comparison target: what visual differences are acceptable after rendering the PPTX preview.

Output valid `visual_contract.json`.

Forbidden:
- Do not set approved comp paths to `preview/slide-XX.png`, `output/*.png`, template-starter previews, or any image rendered from the PPTX.
- Do not mark `per_slide_comps_complete=true` unless every comp exists under `slides/slide-XXX-comp.png` or a user-approved equivalent.
```

## 9. Final Deck Council

```text
Run final all-role review before export.

Inputs:
- final editable PPTX path: <path>
- rendered final preview PNGs: <paths>
- final preview contact sheet: <path>
- deck_spec.json: <path or content>
- slide_intent_plan.json: <path or content>
- narrative_plan.json: <path or content>
- design_system.json: <path or content>
- visual_contract.json: <path or content>
- source_notes.md: <path or content>
- user_decisions.md: <path or content>

Goal:
Decide whether the deck can be exported to the user or must iterate.

Required role coverage:
content-integrity, narrative-invariance, text-typography, source-data-verifier, chart-logic, asset-authenticity, color-brand, style-coherence, accessibility-readability, layout-pptx-feasibility, visual-fidelity, pptx-reconstruction-fidelity, executive-polish, taste-direction, and template-fidelity when a template/source deck exists.

Rules:
1. Final text and numbers must match deck_spec.json, not the generated visual comps.
2. Main text, numbers, footers, page markers, and simple shapes must be editable unless explicitly documented as retained images.
3. No P0/P1 findings may remain unless user_decisions.md explicitly accepts the risk.
4. Every required role must return approval_to_advance=true.
5. If roles conflict, prefer content/source truth over visual polish, and prefer editability over pixel-perfect decoration for main information.
6. If final slides ignore visual_contract.json by collapsing rich visual comps into table/card grids without documented acceptance, return ITERATE with P1 visual-fidelity findings.
7. If final slides are logically correct but visually flatter than the approved comps, return ITERATE with P1 reconstruction-fidelity findings unless the user accepted the downgrade.
8. If the deck used a user template, verify both: the template frame survived and the selected ImageGen comp was faithfully reconstructed inside that frame.
9. Verify `qa/render-fix/render_fix_rounds.json` shows at least 9 completed render/compare/fix rounds and no unresolved P0/P1 findings.
10. Verify retained icon assets are transparent PNGs with padding and no clipped colored pixels.

Output:
- qa/final-council.md
- updated qa_report.md
- export decision: EXPORT | ITERATE | ASK_USER | BLOCK

After writing final QA, run `check_pipeline_gates.py --stage final`. If it fails, export decision must be ITERATE or BLOCK, not EXPORT.
```

## 10. User Pause And Resume Note

```text
Before asking the user for content clarification, slide-intent confirmation, narrative treatment selection, design count, or visual style selection:

1. Update pipeline_state.json:
   - current_stage: <stage>
   - awaiting_user: true
   - required_user_reply: <exact question>
   - next_action: <what to do after answer>
   - last_completed_artifacts: <paths>
2. Append the question to user_decisions.md under "Pending User Reply".
3. Ask a concise question in chat.
4. End with: 回复后我会继续用 `$imagegen-pptx-pipeline` 从 `pipeline_state.json` 继续。

On resume:
1. Read pipeline_state.json, deck_spec.json, user_decisions.md, and the stage artifacts.
2. Record the user's answer.
3. Set awaiting_user=false.
4. Continue from next_action without restarting earlier stages.
```
