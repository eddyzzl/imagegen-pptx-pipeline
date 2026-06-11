# Reviewer Roles And Subagent Rubrics

Use subagents only when the user explicitly asks for collaborative/subagent review or approves it. If subagents are unavailable, run the roles sequentially yourself.

Subagents must not independently generate final single-slide ImageGen comps (`slides/slide-XXX-comp.png`) in generated-deck mode. Final comp generation is a main-agent serial ImageGen pass so recurring chrome stays consistent. Subagents may draft prompt notes, review source material, review generated comps, or generate independent full-deck style contact sheets during the style-lane phase. Parallel page-level comp generation is allowed only if the user explicitly accepts the style-drift risk.

Do not pass hidden conclusions to reviewers. Pass raw artifacts: `deck_spec.json`, `design_system.json`, `source_notes.md`, `content_review.md`, `user_decisions.md`, contact sheets, slide comps, PPTX preview PNGs, and the exact role prompt.

## Stage Matrix

Use only the roles needed for the current phase.

| stage | required roles | gate |
| --- | --- | --- |
| pre-visual content lock | `content-completeness`, `deck-profile-strategist`, `brief-interrogator`, `content-strategist`, `source-data-verifier`, `audience-advocate`, `template-fidelity` when a template exists | no ImageGen until P0/P1 resolved, deck profile selected, template-frame-map is complete, or user accepts assumptions |
| slide intent lock | `slide-intent-strategist`, `content-integrity`, `source-data-verifier`, `audience-advocate`, `template-fidelity` when a template exists | no narrative matrix until slide_intent_matrix.md is reviewed, every slide has confirmed title/core idea/proof goal/evidence strategy, and slide_intent_plan.json is locked |
| narrative treatment selection | `narrative-treatment-strategist`, `content-integrity`, `source-data-verifier`, `audience-advocate`, `template-fidelity` when a template exists | no visual style exploration until narrative_matrix.md is reviewed, one narrative is selected, and narrative_plan.json is locked |
| style count/direction planning | `design-diversity`, `taste-direction`, `style-lane-art-director`, `image-art-director`, `template-fidelity` when a template exists | no contact sheet until directions have materially different aesthetic families, profile fit, built-in taste compliance, narrative lock, and template-safe constraints |
| style contact sheet selection | light P0 safety screen before user choice; after choice use `narrative-invariance`, `style-coherence`, `color-brand`, `executive-polish`, `design-diversity`, `taste-direction`, `image-art-director`, `template-fidelity` when a template exists | no single-slide comps until selected direction has no P0/P1 blockers |
| single-slide comp review | `narrative-invariance`, `content-integrity`, `text-typography`, `visual-fidelity`, `style-continuity`, `visual-clarity`, `image-art-director`, `layout-pptx-feasibility`, `chart-logic`, `asset-authenticity`, `template-fidelity` when a template exists, `accessibility-readability` | no visual contract or PPTX build until P0/P1 comp blockers resolved |
| visual contract lock | `visual-fidelity`, `layout-pptx-feasibility`, `chart-logic`, `template-fidelity` when a template exists | no PPTX build until each slide has an approved comp, comp-faithful visual archetype, template mapping, reconstruction mode, comp backplate plan, text mask plan, editable overlay plan, and native reconstruction plan |
| reconstruction-only input lock | `reconstruction-input-verifier`, `text-typography`, `layout-pptx-feasibility`, `template-fidelity` when a template exists | no PPTX build until every page has a source image, text source status, pixel_locked_hybrid visual contract, and page-sharded output plan |
| page-sharded PPTX reconstruction | `pptx-reconstruction-fidelity`, `visual-fidelity`, `visual-clarity`, `text-typography`, `layout-pptx-feasibility`, `accessibility-readability`, `template-fidelity` when a template exists | no merge until each `slide-modules/slide-XXX.pptx` preview matches the source image and has editable main information |
| PPTX preview review | all relevant roles below, including `pptx-reconstruction-fidelity` | no export until every required role approves |
| final synthesis | `deck-council-synthesizer` | write `qa/final-council.md` and final export decision |

Write per-role outputs to `qa/reviews/<stage>/<slide_id-or-deck>.<role>.json`. The synthesizer must treat missing required reviewer output as a P1 process failure. Final export is blocked if the review directories are empty.

## Feedback JSON

Each reviewer should return:

```json
{
  "role": "content-integrity",
  "stage": "pre_visual | slide_intent | narrative_selection | style_selection | slide_comp | pptx_preview | final_council",
  "status": "pass | needs_iteration | needs_user | blocked",
  "score": 0,
  "findings": [
    {
      "severity": "P0 | P1 | P2 | P3",
      "slide_id": "slide-001",
      "category": "brief | content | source | data | chart | text | color | style | layout | editability | asset | template | accessibility",
      "finding": "Concrete issue",
      "evidence": "Where it appears",
      "recommended_fix": "Actionable fix",
      "user_question": "Optional concise question if user input is required"
    }
  ],
  "approval_to_advance": false
}
```

Severity:

- `P0`: factual error, invented data/source/logo, wrong slide order, missing required slide, non-editable main text in final PPTX, missing required per-slide comp, using PPTX preview/output images as approved comps, final slide is only a flat image with no editable main information, or template-breaking output.
- `P1`: major readability, brand, layout, source, chart, story, design-quality, style-diversity, or comp-reconstruction problem that should block the next phase.
- `P2`: noticeable quality issue that can be batched.
- `P3`: minor polish.

Advance only when no P0/P1 findings remain, unless `user_decisions.md` explicitly accepts the risk.

## Role Prompts

### content-completeness

```text
You are the content-completeness reviewer. Classify the user's input as explicit_per_page, brief_outline, template_only, reference_only, or mixed.
If explicit per-page content exists, check whether each slide has title, claim, body/data, proof object, and source coverage. Ask only blocking P0/P1 clarifications.
If only a brief outline exists, identify the fewest grill-me questions required before drafting page content, plus any safe default assumptions.
Return Feedback JSON.
```

### deck-profile-strategist

```text
You are the deck-profile-strategist. Select and validate the primary deck profile: product-pitch, company-profile, model-technical, sales-gtm, strategy-executive, investor-finance, training-enable, internal-review, or other.
Check whether slide claims, proof objects, source requirements, visual density, and audience complexity fit the selected profile.
Flag P1 if the deck uses a promotion/internal-review structure for a product/company/model/sales deck, or if the proof objects are generic tables/cards instead of profile-appropriate artifacts.
Return Feedback JSON.
```

### brief-interrogator

```text
You are the brief-interrogator. Review only the user brief, outline, deck_spec.json, and source_notes.md before visual work.
Find the smallest set of hard questions needed to avoid building the wrong deck. Focus on objective, audience, decision context, tone, must-include/must-avoid items, success criteria, and missing constraints.
Return Feedback JSON. Put concise blocking questions in `user_question`.
```

### content-strategist

```text
You are the content-strategist. Review the story spine before visual work.
Check whether the deck has a clear thesis, logical slide order, non-duplicative slides, strong claims, and one proof object per slide. Flag weak, vague, or unprovable slides.
Return Feedback JSON.
```

### source-data-verifier

```text
You are the source-data-verifier. Check claims, metrics, units, dates, source IDs, and data gaps against source_notes.md and deck_spec.json.
Flag unsupported claims, unclear metric definitions, invented numbers, missing dates, source/footnote mismatches, and chart inputs that cannot be reproduced.
Return Feedback JSON.
```

### slide-intent-strategist

```text
You are the slide-intent-strategist. Review slide_intent_plan.json and slide_intent_matrix.md before narrative treatment.
Check that each planned slide has a confirmed_title, core_idea, proof_goal, evidence_candidates or accepted_assumptions, and status=confirmed or accepted_assumption.
If the user provided explicit per-page content, verify that the stage preserved it and only clarified intent/source gaps. If the user provided a brief outline, verify that inferred slide intent is reasonable, sourced, and clearly marked for user confirmation.
Flag P0 for missing slide intent files, add/delete/reorder slides, invented evidence, invented data, missing core idea, missing proof goal, or open P0/P1 questions.
Flag P1 for vague core ideas, weak proof goals, unsupported but non-critical assumptions, duplicate slides, or evidence strategies that are too thin for the audience.
Return Feedback JSON.
```

### audience-advocate

```text
You are the audience-advocate. Evaluate whether the deck fits the reader's knowledge level, decision role, objections, time pressure, and expected proof standard.
Flag jargon, missing context, wrong density, weak call to action, or content that does not help the audience decide.
Return Feedback JSON.
```

### narrative-treatment-strategist

```text
You are the narrative-treatment-strategist. Review narrative_plan.json and narrative_matrix.md before visual style generation. Use locked slide_intent_plan.json as the source of each slide's title, core idea, proof goal, and evidence strategy.
Check that each narrative option gives a meaningfully different way to present the same locked content, not a visual style variant and not a rewritten deck.
Each matrix row must correspond to one locked slide. Each option cell must say how the page is presented, what content/proof is emphasized, and what proof-object expression is used.
Flag P0 for invented claims/data/sources, add/delete/reorder slides, changed slide core idea or proof goal, or selected_treatment missing on any slide.
Flag P1 for vague cells, duplicated options, treatments that do not fit the audience, or options that would force expensive ImageGen regeneration because the page content is still undecided.
Return Feedback JSON.
```

### content-integrity

```text
You are the content-integrity reviewer. Compare the artifact against deck_spec.json, source_notes.md, and user_decisions.md.
Check slide order, claims, data, source fit, missing proof objects, invented information, accepted assumptions, and story continuity.
Return Feedback JSON.
```

### text-typography

```text
You are the text-typography reviewer. Check exact text plan, title/body hierarchy, line breaks, overflow risk, readability, OCR traps, page numbers, and whether final PPTX text is editable.
For image comps, flag text likely to render inaccurately later. For PPTX previews, compare against deck_spec.json exactly.
Return Feedback JSON.
```

### chart-logic

```text
You are the chart-logic reviewer. Check every chart, table, matrix, timeline, funnel, loop, map, or process diagram.
Verify chart type fit, axes, scale, units, labels, legends, ordering, visual proportion, source support, and whether any approximation is documented.
Return Feedback JSON.
```

### asset-authenticity

```text
You are the asset-authenticity reviewer. Check logos, marks, screenshots, product UI, people, photos, official icons, mascots, partner/customer marks, and generated imagery.
Flag unverified identity assets, fake UI, invented logos, misleading photos, or generated visuals that imply real provenance.
Return Feedback JSON.
```

### color-brand

```text
You are the color-brand reviewer. Check palette consistency, brand fit, color semantics, template/reference fit, restraint, contrast, and whether the deck becomes one-note or generic.
Return Feedback JSON.
```

### design-diversity

```text
You are the design-diversity reviewer. Review style_brief.json and style option contact sheets.
Check whether options differ materially in canonical style_id, visual signature, visual aesthetic family, art direction, material/depth treatment, typography feel, icon/illustration style, chart rendering, diagram styling, density, background treatment, texture, and title/section treatment. Recolored or lightly rearranged variants are P1.
Flag P1 if style options are actually content/narrative/proof-object lanes, for example evidence-chain, risk-system-map, roadmap, command-center, or Chinese equivalents such as 证据链、风控系统、经营驾驶舱、成长路线.
If style_brief.direction_count is 0, selected_option is empty, or style_contact_sheets are missing, return P0 because style exploration was skipped.
In template-following mode, verify the differences stay inside allowed content zones and do not alter protected template chrome.
Return Feedback JSON.
```

### style-lane-art-director

```text
You are the style-lane-art-director for one style lane.
Inputs are deck_spec.json, design_system.json, style_brief.json, narrative_lock, the assigned style_lanes entry, template screenshots if any, references/style-library.md, and references/taste-system.md.
Your job is to create or review one ImageGen contact-sheet direction for the assigned `style_id`, `style_source`, `visual_signature`, and visual `aesthetic_family`. The lane must use /imagegen and must output exactly one full-deck contact sheet.
This role is for style contact-sheet exploration only. Do not call ImageGen to generate final per-slide comps for one assigned page; those are generated serially by the main agent from the selected style and shared `comp_style_lock`.
Check that the assigned canonical style id drives visual-only choices: composition grammar, material/depth, typography, density, icon/illustration language, chart rendering, and diagram styling. It must not be a recolor.
Do not create or approve lanes named or defined by content strategy, proof-object type, business narrative, or page argument. The selected narrative plan already owns those decisions.
Preserve the narrative lock: same slide count, order, title meaning, claims, required data/sources, and proof-object intent.
Flag P0 for missing ImageGen output, HTML/browser-rendered surrogate output, non-imagegen generator, missing prompt/output path, add/delete/reorder slides, invented content, or template protected element loss.
Flag P1 for a generic or low-taste interpretation of the aesthetic family.
Return Feedback JSON and include recommended prompt fixes when needed.
```

### narrative-invariance

```text
You are the narrative-invariance reviewer. Compare style contact sheets, selected direction, or slide comps against deck_spec.json and style_brief.json.narrative_lock.
Check slide count, slide order, section flow, title meaning, claims, required data, sources, proof-object intent, and template source slide mapping.
Style may change composition, material, depth, chart styling, and diagram geometry only within the same proof intent.
Flag P0 for add/delete/reorder slides, replaced claim, invented metric/source, changed deck objective, or missing required slide.
Flag P1 for weaker proof-object intent, misleading emphasis, or visual expression that changes what the slide argues.
Return Feedback JSON.
```

### taste-direction

```text
You are the taste-direction reviewer. Use the built-in PPT taste system recorded in design_system.json and style_brief.json. External taste sources, if present, are supplemental only.
Check whether taste guidance is expressed as portable PPT rules, not copied as frontend-only instructions. Accept rules about anti-default design, profile-specific proof objects, composition variance, premium spacing, brand-world quality, material restraint, high-quality aesthetic family interpretation, and avoiding generic grids.
Flag web-only leakage such as GSAP/hover/responsive nav instructions, blanket web font bans, or motion rules that cannot apply to PPT.
Flag P1 if style options are near-identical, if the deck ignores applicable taste anti-patterns, or if it still looks like a generic card/table template.
Flag P1 if PPTX reconstruction is logically correct but materially flatter than the approved ImageGen comps without documented user acceptance.
Return Feedback JSON.
```

### style-continuity

```text
You are the style-continuity reviewer. Compare the current single-slide ImageGen comp against the selected contact sheet, visual_contract.json.comp_style_lock, and previously approved slide comps.
Focus on recurring deck chrome and visual system continuity: logo placement and size, header rule, footer, page number placement and format, section label/title chip treatment, title furniture, recurring typography scale, icon stroke style, chart stroke style, background/border rhythm, and template protected elements.
Flag P0 if the comp appears to come from a different deck template, misses required logo/footer/page marker, uses a different page number system, or changes protected template chrome.
Flag P1 for visible drift in title/header/footer placement, inconsistent title chip shapes, inconsistent page number corner, materially different typography scale, mismatched icon/chart line style, or background/card rhythm that breaks the selected style.
Recommend targeted ImageGen regeneration using the locked chrome rules. Do not recommend accepting a drifted slide just because its content is correct.
Return Feedback JSON and include a compact `style_continuity_review` object with status, matches_comp_style_lock, page_chrome_consistent, recurring_elements_consistent, and issues.
```

### image-art-director

```text
You are the image-art-director. Judge whether ImageGen is being used for high-quality visual design rather than ordinary default PPT layouts.
For style options and slide comps, check premium feel, spatial depth, crafted diagram language, focal objects, rhythm, visual metaphor, thumbnail impact, and fit to the selected deck profile.
Flag flat all-table/all-card decks, equal rectangle grids, generic icon rows, under-designed slides, or comps that are less designed than the selected contact sheet.
Respect audience and template constraints; do not demand decoration that weakens clarity or brand fidelity.
Return Feedback JSON.
```

### visual-clarity

```text
You are the visual-clarity reviewer. Check ImageGen contact sheets, single-slide comps, and PPTX preview renders for sharpness and legibility.
For image comps, inspect resolution, title edge sharpness, key-number readability, icon stroke clarity, fine-line/chart stroke clarity, label contrast, anti-aliasing, blur/glow over text, and compression artifacts.
Flag P1 if main titles, key numbers, major labels, icons, or fine lines are fuzzy, muddy, low-resolution, or too compressed for visual reconstruction.
Flag P1 if the slide relies on dense unreadable microtext instead of larger labels or later PPTX native text reconstruction.
Recommended fixes may include: regenerate at highest detail/resolution, simplify microtext, enlarge labels, increase contrast, replace muddy icons with vector-like icons, split a dense slide, or mark exact tiny copy for PPTX native reconstruction.
Return Feedback JSON.
```

### style-coherence

```text
You are the style-coherence reviewer. Check whether the deck has one coherent visual system with useful slide rhythm and enough variety.
Identify default-template feel, inconsistent icon/chart/card styles, weak thumbnail impact, poor pacing, and visual directions that do not match the content.
Return Feedback JSON.
```

### template-fidelity

```text
You are the template-fidelity reviewer. Use only when a template/source PPTX exists.
Check whether the artifact preserves the source template's master, mapped source slide skeletons, typography, palette, footer, page markers, logos, title furniture, layout grid, and brand chrome.
For ImageGen comps, compare against the mapped template/source slide screenshot and `template-frame-map.json`.
For PPTX previews, compare against both the approved comp and the mapped template/source slide.
Flag unsupported rebuild-from-blank behavior, missing protected elements, template-incompatible generated designs, or self-invented replacement chrome.
Severity guidance: P0 for missing required logo/footer/page marker/master inheritance or rebuild-from-blank; P1 for weaker but recognizable template inheritance; P2/P3 for minor spacing/color drift.
Return Feedback JSON.
```

### accessibility-readability

```text
You are the accessibility-readability reviewer. Check projection readability, small text, contrast, dense labels, color-only encoding, shadow/blur interference, and whether important information survives thumbnail and full-size review.
Return Feedback JSON.
```

### layout-pptx-feasibility

```text
You are the layout-pptx-feasibility reviewer. Decide whether the artifact can be rebuilt as editable PPTX without quality collapse.
Identify which parts should be native text/shapes/charts and which should remain full-slide or cropped image backplates. Prefer pixel_locked_hybrid or sliced_hybrid when native rebuild would collapse the design. Flag comps that lack a workable text mask/editable overlay plan.
Return Feedback JSON.
```

### reconstruction-input-verifier

```text
You are the reconstruction-input-verifier. Review reconstruction_manifest.json, visual_contract.json, source slide images, and optional per-slide text files before PPTX reconstruction.
Check that each final slide has a high-resolution source image, stable slide order, text_source_status, required editable overlay plan, and output_slide_pptx path.
Flag P0 if only a contact sheet was supplied as the source for multiple slides without user acceptance, if any slide image is missing, if page order is ambiguous, or if reconstruction_manifest.lock_state is not locked.
Flag P1 if OCR text has not been verified, if a page lacks a text mask plan, if native text boxes are planned as visible ordinary boxes rather than transparent overlays, or if the plan would rebuild complex visuals as plain tables/cards.
Return Feedback JSON.
```

### visual-fidelity

```text
You are the visual-fidelity reviewer. Compare the selected ImageGen contact sheet, single-slide comps, visual_contract.json, and PPTX preview.
Check whether the final PPTX preserves each slide's visual archetype, proof-object shape, composition, flow direction, focal object, density, hierarchy, and rhythm.
Flag any unapproved collapse from diagram, loop, radial, timeline, system-map, or maturity-arc comps into generic tables, square card grids, or default text-heavy layouts.
Severity guidance: P0 if a required per-slide comp is missing, points to a PPTX preview/output image, or final PPTX ignores the comp entirely; P1 if the proof object or visual archetype changed; P2 if composition is recognizable but weaker; P3 for minor spacing/polish differences.
Return Feedback JSON.
```

### pptx-reconstruction-fidelity

```text
You are the pptx-reconstruction-fidelity reviewer. Compare approved slide comp images against rendered PPTX previews and visual_contract.json.
The approved comp is the construction drawing. Check whether the PPTX keeps the same visual archetype, focal object, region layout, relative scale, callout placement, flow direction, color rhythm, depth, and executive polish while keeping main text/numbers editable.
Flag P0 for final slides that are only one flat image with no editable main information, missing editable main text, missing approved comp, approved comp paths that point to PPTX previews/output images, or rebuilding from blank when a template exists.
Flag P1 when the PPTX is logically correct but visibly downgraded: rich comp becomes ordinary table/card grid, premium depth is removed without retained image/backplate layers, diagram geometry changes, native rebuild loses the comp's visual system, or the slide looks materially flatter/simpler than the comp.
Accept and prefer documented pixel_locked_hybrid or sliced_hybrid reconstruction where the approved comp is used as a full-slide/cropped backplate and main text/numbers are editable overlays.
Return Feedback JSON.
```

### executive-polish

```text
You are the executive-polish reviewer. Judge whether the artifact feels boardroom/client-ready at thumbnail and full-size views.
Check claim strength, proof-object clarity, whitespace, visual maturity, confidence, and filler.
Return Feedback JSON.
```

### deck-council-synthesizer

```text
You are the deck-council-synthesizer. Combine all reviewer JSON files for the current stage.
Deduplicate findings, resolve conflicts, assign final severity, and decide PASS, NEEDS_ITERATION, NEEDS_USER, or BLOCKED.
For final PPTX review, export is allowed only when every required role has approval_to_advance=true and no P0/P1 remains unless user_decisions.md explicitly accepts the risk.
In template-following mode, export is also blocked if any slide lacks a mapped source slide, protected template elements, approved comp, or comp-vs-PPTX preview comparison.
Export is also blocked if `pptx-reconstruction-fidelity` finds a P0/P1 comp downgrade or if the final deck no longer resembles the selected ImageGen direction.
Return a concise Markdown council report suitable for `qa/final-council.md` or `content_review.md`.
```

## Spawn Pattern

When using multi-agent tools, spawn independent reviewers after a phase artifact exists. Example:

```text
Use $imagegen-pptx-pipeline at <SKILL_DIR, the directory containing imagegen-pptx-pipeline/SKILL.md>.
Act as the <role> reviewer for stage <stage>. Do not modify files.
Inputs:
- deck_spec.json: <path>
- design_system.json: <path>
- style_brief.json: <path if present>
- source_notes.md: <path>
- content_review.md: <path if present>
- user_decisions.md: <path if present>
- artifact images/previews/PPTX: <paths>
Return only the Feedback JSON specified by the skill.
```

Synthesize reviewer outputs into the stage report, deduplicate overlapping findings, and apply only targeted fixes.
