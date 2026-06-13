---
name: imagegen-pptx-pipeline
description: End-to-end stateful workflow for designing and generating editable PowerPoint decks from a brief outline, template PPTX, historical/reference decks, brand assets, and data by using ImageGen/Image2 for materially different visual directions, mandatory reviewed per-slide visual comps, built-in PPT taste/design guidance, and strict slide-image-to-editable-PPTX conversion. Use for product decks, company decks, model/AI/technical decks, sales or GTM decks, strategy/executive decks, investor/board decks, training decks, internal review or defense decks, and any PPT/PPTX automation task that needs pause/resume questions, multiple distinct visual styles, generated or user-supplied slide images converted into faithful fully editable PPTX, strict icon extraction, CJK text placement control, render-compare-fix rounds, hard template preservation, or multi-agent/subagent review of slide images, text accuracy, color, design quality, style, layout, content, and PPTX fidelity before exporting PowerPoint.
---

# ImageGen PPTX Pipeline

Build an editable PPTX deck through a controlled pipeline, or convert user-supplied final slide images into a faithful editable PPTX.

Generated slide images are visual construction targets, not content truth. `deck_spec.json` owns final text, numbers, slide order, claims, and source provenance.

The PPTX conversion phase is now the bundled **strict slide-image converter**:

- `slidelib.py`: native PowerPoint builder in source-pixel coordinates.
- `iconcut3.py`: strict transparent icon extractor with amputation guards, HD supersampling/sharpening, and no silent fallback.
- `qa_gate.py`: mechanical QA gates that read real renders, real PPTX XML/media, real icon manifests, and real render logs.
- `PITFALLS.md`: required trap catalog for icon extraction, measurement, python-pptx, LibreOffice rendering, and render-compare loops.

Do not use any legacy audit-script image-to-PPTX path. Do not use full-slide or region-image layers as the main output. The approved comp or supplied slide image is a measurement target; the PPTX must be rebuilt from native text, shapes, connectors, charts, tables, and only validated icon/art assets.

## Hard Invariants

- **Stateful pauses are mandatory:** before any user question, write `pipeline_state.json`. On "continue/resume/继续", read `pipeline_state.json`, `deck_spec.json`, and `user_decisions.md` before doing anything else.
- **"帮我做 PPT" is not full automation consent:** only explicit wording such as "全自动", "不用问我", "你自己决定", or a recorded user answer may skip user style selection.
- **Template is a hard constraint:** if a template/source PPTX is supplied, preserve master/layout inheritance, typography, palette, logos, footer/page markers, title furniture, and protected brand chrome unless the user explicitly asks to restyle away from it.
- **ImageGen owns visual design:** generated images are not loose mood boards. After style selection, each page image is the approved construction target for conversion.
- **Content, slide intent, and narrative are locked before visual work:** confirm slide titles/core ideas/proof goals, then narrative treatment, then style options.
- **Style lanes are visual skins, not story lanes:** style options may differ by art direction only. They must not change slide count, order, claims, data, proof object intent, or selected narrative treatment.
- **No HTML/browser surrogate comps:** do not create HTML/CSS/SVG/React/canvas screenshots as `styles/*contact-sheet.png` or `slides/slide-XXX-comp.png`. Comps must come from ImageGen/Image2 or from user-supplied final slide images.
- **Per-slide comps are required:** a full-deck contact sheet alone is never enough for PPTX conversion.
- **Final single-slide ImageGen comps are serial within each style lane:** parallelize across selected styles if needed, but do not shard final pages across page-owning agents unless the user accepts style drift risk in `user_decisions.md`.
- **Image clarity is a hard gate:** request the highest available ImageGen detail. Try 4K 16:9 first, fall back only to a deck-wide 2K or 1080p tier after bounded failures, and record the fallback.
- **Strict converter owns PPTX output:** use measurement, strict HD icon extraction/enhancement, native build, and at least 10 render-compare-fix rounds. Do not ship a generic deck that merely resembles the content.
- **No full-image or region-image backgrounds:** headings, body text, numbers, labels, card titles, flow nodes, buttons, lines, arrows, charts, tables, cards, and color blocks must be native. Only complex icon artwork, photos, official marks, or inseparable art slices may remain images.
- **Icons fail closed:** every transparent icon must pass `iconcut3.strict_cut3` and a 4-edge alpha audit. On `ClipError`, fix the box or clear rects and rerun. Never hand-crop or alpha-key around the failure.
- **Real source icons must be extracted, not redrawn:** if a pictogram can be named (target, shield, database, briefcase, person, building, light bulb, cube, chart, people, etc.), treat it as source artwork and extract it with `iconcut3`. Do not use `slidelib` glyph helpers such as `shield()`, `target()`, `person()`, `bars()`, or `trend()` as a fidelity path for real source icons; those helpers are placeholder scaffolding for trivial primitives or temporary layout only. A PPTX with zero extracted icons when the source contains recognizable pictograms is a failed generic redraw.
- **Icons must be HD-enhanced before placement:** `iconcut3.strict_cut3` supersamples and sharpens strict line-art icons to at least 256px minimum dimension by default. If reusing an existing extracted-icon folder, run `iconcut3.enhance_dir(outdir, feathered=(...))` before building. Feathered opaque slices must be listed in `feathered` or processed with `alpha_crisp=False` so seam-hiding alpha is preserved.
- **Icon content audit is separate:** every extracted asset must be checked in a contact sheet. If an asset contains Chinese characters, Latin words, or a text label, re-measure the real pictogram and rebuild the text natively.
- **Never rely on automatic wrapping for multi-line text:** split CJK/mixed-size/multi-line text into absolute text boxes per source line or run.
- **Render-compare-fix means 10+ real export rounds:** each counted round must produce a new LibreOffice/Poppler render file. Looking at the same render multiple times is still one round. Keep a strict `render_log.json` list with one object per round: `round`, `render`, `timestamp`, `max_metric`, `issues`, `fix`, and `recheck`.
- **Mechanical gates read real artifacts:** do not satisfy conversion QA with hand-written metrics, rounded-down blocking values, or review notes. `qa_gate.py` must recompute the real max region diff from the latest render, inspect the PPTX media/text XML, and verify distinct render files. If the real max diff is over the threshold, fix the slide rather than writing a lower value into a manifest.
- **Final reports disclose real numbers:** paste or summarize the actual `qa_gate.py` output: real render count, distinct render files, real max region diff, picture/media count, text-run count, icon-manifest count, and any explicitly accepted risk.

## Required Tools And Skills

Use the `imagegen` skill for generated bitmap style options and per-slide comps.

Use the bundled converter files in this skill directory for PPTX conversion:

```bash
cp "$SKILL_DIR/slidelib.py" "$WORKSPACE/slidelib.py"
cp "$SKILL_DIR/iconcut3.py" "$WORKSPACE/iconcut3.py"
cp "$SKILL_DIR/qa_gate.py" "$WORKSPACE/qa_gate.py"
cp "$SKILL_DIR/PITFALLS.md" "$WORKSPACE/PITFALLS.md"
```

Runtime requirements:

- Python 3
- `Pillow`, `numpy`, `python-pptx`
- LibreOffice `soffice`
- Poppler `pdftoppm`
- `markitdown` optional for text QA
- an image-viewing path for paired crops and contact sheets

Use the Presentations plugin only as an optional helper for template inspection or preview rendering. It is not the PPTX conversion method for approved slide images.

## Deterministic Gate Checks

Use the gate checker:

```bash
SKILL_DIR=<directory containing this SKILL.md>
python "$SKILL_DIR/scripts/check_pipeline_gates.py" \
  --workspace <workspace> \
  --stage <content-lock|slide-intent-lock|narrative-lock|style-selection|conversion-lock|before-pptx|final>
```

Run it after:

- content lock: `--stage content-lock`
- slide-intent confirmation: `--stage slide-intent-lock`
- narrative selection: `--stage narrative-lock`
- style selection: `--stage style-selection`
- conversion-only input registration: `--stage conversion-lock`
- visual contract and converter plan are ready: `--stage before-pptx`
- final export: `--stage final`

If the checker returns `FAIL`, fix the listed artifacts and rerun. Do not work around the checker by writing prose that says unperformed work happened.

## Interaction And Resume Contract

Normal pause points are content lock, slide-intent confirmation, narrative treatment selection, design-direction count/brief, visual style selection, and finished-comp style-set selection for PPTX conversion.

Before asking the user, update `pipeline_state.json`:

- `skill`: `imagegen-pptx-pipeline`
- `workspace`: absolute workspace path
- `current_stage`: one of `content_gate`, `slide_intent_lock`, `narrative_selection`, `style_count`, `style_selection`, `single_slide_comps`, `multi_style_comp_selection`, `slide_comp_review`, `conversion_input_lock`, `visual_contract`, `pptx_conversion`, `final_review`
- `awaiting_user`: `true`
- `required_user_reply`: exact question or decision needed
- `next_action`: first action after the user replies
- `last_completed_artifacts`: latest valid artifacts
- `resume_instructions`: "Read pipeline_state.json, deck_spec.json, user_decisions.md, then continue this stage; do not restart unless the user requests a restart."

End the user-facing question with a concise resume promise: "回复后我会继续用 `$imagegen-pptx-pipeline` 从 `pipeline_state.json` 继续。"

On resume, set `awaiting_user=false`, append the answer to `user_decisions.md`, and continue from `next_action`.

## Workflow

### 0. Resume Or Continue

If a workspace exists or the user says "继续", "resume", "用新的 skill 继续", or similar:

1. Read `pipeline_state.json`, `deck_spec.json`, `design_system.json`, `user_decisions.md`, and the stage's required artifacts.
2. Confirm the state belongs to `imagegen-pptx-pipeline`.
3. Continue from `current_stage` and `next_action`.
4. Do not repeat completed parsing, style exploration, or slide generation unless the state marks them invalid.

### 1. Set Workspace

Create a workspace:

```bash
SKILL_DIR=<directory containing this SKILL.md>
python "$SKILL_DIR/scripts/init_pipeline_workspace.py" \
  --slug <task-slug> \
  --title "<deck title>" \
  --mode <create|template-following|targeted-edit|reconstruction-only|repair-existing-pptx>
```

Use `reconstruction-only` when the user already has final per-slide images and wants direct image-to-PPTX conversion. This is a legacy mode name for compatibility; the implementation path is the strict converter.

Immediately copy `slidelib.py`, `iconcut3.py`, `qa_gate.py`, and `PITFALLS.md` into the workspace before any PPTX conversion work.

### 2. Read Inputs

Classify inputs:

- **Brief outline:** content seed; expand only where the user allows.
- **Template PPTX:** hard constraint for source slide skeletons, master/layout inheritance, typography, palette, footer, logos, title furniture, page markers, and brand chrome.
- **Historical/reference PPTX:** soft reference for taste, pacing, density, chart language, and image treatment.
- **Data/source files:** truth source for metrics and charts.
- **Brand/media assets:** verified source assets; do not invent logos, product UI, official marks, or people.
- **Final slide images:** direct conversion targets; skip content/narrative/style generation unless the user asks to redesign.

For every PPTX input, render previews/contact sheets and extract slide text before using it.

When a template/source PPTX exists, write:

- `template-audit.md`
- `template-frame-map.json`
- `deviation-log.md`

### 2A. Conversion-Only Fast Path

Use this path when the user supplies final slide images and asks to convert them to PPTX. Do not rerun content planning, narrative selection, style exploration, or ImageGen unless an image is missing/invalid and the user asks to regenerate it.

Required inputs:

- one high-resolution 16:9 image per final slide, preferably ordered as `slide-001`, `slide-002`, etc.
- exact text per slide, or permission to OCR and verify text before PPTX conversion
- optional template/source PPTX for logos, footer, page markers, or corporate chrome

Write and lock:

- `conversion_manifest.json`: source image path, text source status, basis image path, measurement status, icon extraction status, render-compare status, strict render-log path, per-slide output path, QA-gate output path, and merge status.
- minimal `deck_spec.json`: slide count, slide IDs, exact text when known, and editability targets. Set `deck.lock_state="locked"` after text is provided, OCR is verified, or the user accepts image text.
- `visual_contract.json`: each supplied image becomes an approved conversion target with `conversion_method="strict_slide_image_to_editable_pptx"`.

If the user provides only a contact sheet, stop and ask for individual high-resolution slide images unless they explicitly accept lower fidelity.

### 3. Produce Draft Truth Files

Before ImageGen, write:

- `pipeline_state.json`
- `deck_spec.json`
- `design_system.json`
- `slide_intent_plan.json`
- `slide_intent_matrix.md`
- `narrative_plan.json`
- `narrative_matrix.md`
- `style_brief.json`
- `conversion_manifest.json`
- `template-frame-map.json` when a template/source PPTX exists
- `source_notes.md`
- `content_review.md`
- `user_decisions.md`

Read `references/schemas.md` when drafting structures.

Read `references/taste-system.md` before style exploration. Read `references/style-library.md` when selecting concrete style IDs.

### 4. Grill And Lock Content

Before ImageGen, run content review. Ask only P0/P1 clarification questions unless the user explicitly requested full automation.

Do not proceed to ImageGen until:

- `deck_spec.json.deck.lock_state` is `locked`
- each slide has a title, claim, proof object, and editability target
- P0/P1 content findings are resolved or explicitly accepted
- unsupported metrics/sources/assets are removed
- `check_pipeline_gates.py --stage content-lock` passes

Read `references/subagent-rubrics.md` for pre-visual role prompts.

### 5. Propose And Lock Slide Intent

Write `slide_intent_plan.json` and `slide_intent_matrix.md`.

The matrix rows are slides. Columns are page number, proposed title, core idea, proof goal, evidence/data candidates, content gaps/user questions, and confidence.

If the user did not request full automation, ask them to confirm or edit the proposed titles/core ideas.

Do not proceed until:

- `slide_intent_plan.json.lock_state` is `locked`
- every slide has a confirmed title, core idea, proof goal, and evidence strategy
- `slide_intent_matrix.md` exists
- `check_pipeline_gates.py --stage slide-intent-lock` passes

### 6. Propose And Lock Narrative Treatment

Write `narrative_plan.json` and `narrative_matrix.md`.

Narrative options may change framing and emphasis, but may not invent claims, data, logos, sources, products, results, slide count, or slide order.

Do not proceed until:

- `narrative_plan.json.lock_state` is `locked`
- `narrative_plan.json.selected_narrative_id` is set
- every slide has a selected narrative cell
- `narrative_matrix.md` exists
- `check_pipeline_gates.py --stage narrative-lock` passes

### 7. Explore And Select Visual Directions

If the user did not specify a count and did not request full automation, ask for the number of directions and any style preference. If full automation is explicit, default to 4 directions.

Use ImageGen to create materially different full-deck contact-sheet style options from locked content/narrative files. Use concrete `style_id` values from `references/style-library.md` where possible.

Require each direction to preserve:

- slide count and order
- titles and claims
- data and source meaning
- proof-object intent
- selected narrative treatment
- template frame, if any

Show all contact sheets unless full automation was explicit. Record selected options in `style_brief.json.selected_options`.

Do not proceed until `check_pipeline_gates.py --stage style-selection` passes.

### 8. Generate Single-Slide Visual Comps

For each selected style, generate one complete set of per-slide comps. Keep generation serial within each style lane so page chrome, footer, logo, page number, and title furniture stay consistent.

Each output must be a high-resolution 16:9 slide image:

- raw ImageGen return under `slides/raw/`
- downstream comp under `slides/slide-XXX-comp.png` or `slides/<style-lane-id>/slide-XXX-comp.png`
- prompt under `prompts/`
- dimensions, source type, review status, and clarity status recorded in `deck_spec.json` and `visual_contract.json`

Review comps before PPTX conversion. Fix P0/P1 findings by targeted ImageGen regeneration, not by hiding defects in PPTX.

### 9. Lock The Conversion Contract

Before writing PPTX code, translate approved comps into `visual_contract.json` and `conversion_manifest.json`.

For each slide record:

- approved comp path
- source image dimensions and basis image path
- exact text source status
- visual archetype
- measurement plan and status
- native elements required
- icon extraction jobs and audit status
- text line-splitting plan
- build script path
- output slide/module PPTX path
- preview path
- render-compare rounds status
- unresolved accepted risks

Reject any approved comp path that points to `preview/`, `output/`, template-starter preview images, or browser/HTML output.

Do not proceed to PPTX build until:

- every slide has an approved `slide-XXX-comp.png` or user-supplied final image
- `conversion_manifest.json.lock_state` is `locked`
- `visual_contract.json.conversion_policy.method` is `strict_slide_image_to_editable_pptx`
- `slidelib.py`, `iconcut3.py`, `qa_gate.py`, and `PITFALLS.md` are copied into the workspace
- every slide has a measurement plan, text split plan, and converter output path
- icon assets either pass strict extraction, HD enhancement, and contact-sheet audit, or `not_applicable` is backed by an explicit source-icon inventory stating no recognizable source pictograms exist
- `check_pipeline_gates.py --stage before-pptx` passes

### 10. Convert Slide Images To Editable PPTX

Read `PITFALLS.md` before writing conversion code.

Work in 1920x1080 basis coordinates. Keep the original high-resolution image open as `hd` and use `scale = hd.width / 1920` for extraction.

Use the strict converter workflow:

1. **Measure:** resize the source to `src.png` at 1920x1080. Use numpy scans for edges, text rows, column runs, color masks, and exact sampled colors. For ambiguous regions, create magnified labeled grid crops with burnt-in coordinates.
2. **Extract and HD-enhance icons:** default to extraction for every recognizable source pictogram. Use `iconcut3.run_jobs` or `iconcut3.strict_cut3` for line-art/glyph icons; `strict_cut3` supersamples and sharpens to a 256px minimum dimension before adding transparent padding. On `ClipError`, fix coordinates/clears and rerun. If icons already exist, run `iconcut3.enhance_dir(outdir, feathered=(...))` before placing them. For inseparable art, use feathered opaque slices with sampled native underlay color, document the exception, and keep `alpha_crisp=False` for those slice names. Only bare primitives such as plain dots, rings, chevrons, checkmarks, bars, and dividers may be native. Do not use `slidelib` composite glyph helpers to redraw real source icons.
3. **Audit icons:** run 4-edge alpha audit and visual contact-sheet audit after HD enhancement. Text labels are never icon assets.
4. **Build natively:** use `SB(1920,1080,bg)` from `slidelib.py`. Build text, cards, lines, circles, arrows, charts, tables, page chrome, and simple glyphs as native elements. Split multi-line CJK and mixed-size runs into absolute boxes.
5. **Render:** use LibreOffice and Poppler:

```bash
soffice --headless --convert-to pdf --outdir pdf out.pptx
pdftoppm -jpeg -r 150 -scale-to-x 2001 -scale-to-y -1 pdf/out.pdf r
```

6. **Compare and fix:** each round must include a fresh full-page render, full-page side-by-side, paired source/render crops for suspect regions, and region diff metrics. Fix one issue cluster per round.
7. **Log real rounds:** append one object to `qa/render-compare/render_log.json` for every real export round. The `render` path must point to a distinct existing render file. Do not backfill review notes as rounds.
8. **Run mechanical gates:** after the latest render, run:

```bash
python qa_gate.py all SRC.png LATEST_RENDER.jpg out.pptx qa/render-compare/render_log.json icons/icon_jobs.json
```

The output is the truth for max region diff, media audit, and render-round integrity. A failing gate blocks completion.
9. **Stop only after 10+ real export rounds:** all paired crops must match closely, the real region diff must be below the blocking threshold, text QA should pass or be explicitly accepted, icon audits must still pass, and `qa_gate.py all` must print PASS.

For multi-slide decks, build page modules under `slide-modules/slide-XXX.pptx` or build a combined deck with one builder script that records per-slide rounds. Merge only pages with no unresolved P0/P1 conversion defects.

### 11. Final Review And Export

Render final PPTX previews and compare them to approved comps/source images. Run a final council review on rendered previews, final contact sheet, `deck_spec.json`, `design_system.json`, `visual_contract.json`, `conversion_manifest.json`, `source_notes.md`, and `qa_report.md`.

Final council roles:

- `content-integrity`
- `text-typography`
- `source-data-verifier`
- `chart-logic`
- `asset-authenticity`
- `template-fidelity` when a template/source deck exists
- `color-brand`
- `style-coherence`
- `visual-clarity`
- `accessibility-readability`
- `layout-pptx-feasibility`
- `visual-fidelity`
- `pptx-conversion-fidelity`
- `executive-polish`
- `taste-direction`
- `narrative-invariance`

Blocking QA:

- final slide count and order match `deck_spec.json`
- all main text and numbers are visible and editable
- no full-slide or region-image layer is used as the primary slide
- every retained icon asset passed strict extraction plus HD enhancement, or has a documented art-slice exception with feathered alpha preserved
- every named source pictogram is extracted or has a documented inseparable-art exception; all-vector icon redraws are blocking defects
- every slide/output deck has at least 10 real render-compare-fix rounds backed by distinct render files
- `qa_gate.py all` passes for the latest render and PPTX, and its real metrics support the fidelity claim
- paired crops and region diff metrics support the fidelity claim without substituting hand-written blocking values
- no obvious typo, overflow, missing page number, malformed chart, or fake source remains
- final council roles have `approval_to_advance=true`
- no P0/P1 final council findings remain unless accepted in `user_decisions.md`

Before final response, run `check_pipeline_gates.py --stage final`. If it fails, report the blocker or iterate.

Deliver:

- final editable `.pptx`
- preview contact sheet or rendered previews
- concise QA report with retained-image/art-slice exceptions, real `qa_gate.py` numbers, and any accepted text/data risks

Keep final deliverables under `output/`; keep internal prompts, measurements, crops, icon sheets, and render rounds in the workspace.

## Reference Files

- `PITFALLS.md`: required converter trap catalog.
- `qa_gate.py`: required mechanical QA gate for real render metrics, PPTX media/text audit, and distinct render-round audit.
- `references/schemas.md`: required intermediate JSON/Markdown files.
- `references/prompt-templates.md`: ImageGen, conversion-contract, and final-review prompts.
- `references/subagent-rubrics.md`: reviewer roles and feedback schema.
- `references/taste-system.md`: bundled PPT taste system and anti-generic rules.
- `references/style-library.md`: concrete style IDs for visual exploration.
- `references/taste-integration.md`: optional external taste-source supplement rules.

## Boundaries

- Do not invent metrics, sources, logos, product screenshots, or official marks.
- Do not let ImageGen OCR output override the structured slide spec.
- Do not skip rendering previews before claiming the PPTX is finished.
- Do not ignore a supplied template or replace its visible system with self-designed layouts.
- Do not use subagents without explicit user authorization or a clear user request for collaborative/multi-agent review.
