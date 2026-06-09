---
name: imagegen-pptx-pipeline
description: End-to-end stateful workflow for designing and generating editable PowerPoint decks from a brief outline, template PPTX, historical/reference decks, brand assets, and data by using ImageGen/Image2 for materially different style directions, mandatory reviewed per-slide visual comps, built-in PPT taste/design guidance, and the Presentations plugin for comp-faithful PPTX export. Use for product decks, company decks, model/AI/technical decks, sales or GTM decks, strategy/executive decks, investor/board decks, training decks, internal review or defense decks, and any PPT/PPTX automation task that needs pause/resume questions, multiple distinct visual styles, generated slide images/comps converted into editable slides, hard preservation of a supplied PPTX template, built-in anti-generic visual QA, or multi-agent/subagent review of slide images, text accuracy, color, design quality, style, layout, content, and PPTX reconstruction fidelity before exporting PowerPoint.
---

# ImageGen PPTX Pipeline

Build an editable PPTX deck through a controlled pipeline, or reconstruct an editable deck directly from user-supplied final slide images.

1. Convert the user's outline, template, historical decks, data, and assets into structured truth files.
2. Persist workflow state so user-question pauses can resume without losing the skill context.
3. Grill and lock content before any visual generation.
4. Confirm each slide's title, core idea, proof goal, evidence candidates, and content gaps before narrative treatment.
5. Offer multiple narrative-treatment options as a per-slide Markdown matrix and lock the user's chosen narrative before visual work.
6. Use `imagegen` / Image2 as the primary design engine for materially different visual style options and mandatory approved single-slide visual comps.
7. Let the user choose a visual direction unless they explicitly requested full automation.
8. Use `Presentations` for comp-faithful editable PPTX reconstruction, render previews, and export.
9. Use stage-specific reviewer roles or subagents, then run a final all-role review council before export.

Do not treat generated images as the content source of truth. Generated images are visual blueprints; `deck_spec.json` owns final text, numbers, slide order, and claims.

Do not let editable PPTX reconstruction collapse ImageGen visual comps into generic tables, square card grids, or plain text layouts. The final PPTX must preserve the selected comp's visual grammar, proof-object shape, rhythm, density, hierarchy, and major diagram composition unless an explicit source, editability, or template constraint requires a documented deviation.

Default reconstruction mode is **pixel-locked hybrid**, not native-only redraw: use the approved slide comp as a full-slide or sliced visual backplate, mask/replace main text regions, and overlay editable native PPT text, numbers, labels, and simple shapes. A slide may use the whole comp as a visual backplate; it fails only if the final slide is just one flat image with no editable main information.

## Hard Invariants

- **Stateful pauses are mandatory:** any time the workflow asks the user a question, write `pipeline_state.json` first. On any "continue/resume/继续" message, read `pipeline_state.json`, `deck_spec.json`, and `user_decisions.md` before doing anything else.
- **"帮我做 PPT" is not full automation consent:** only explicit wording such as "全自动", "不用问我", "你自己决定", or a recorded user answer may skip user style selection. Do not record generic task delegation as permission to bypass questions.
- **Template is a hard constraint:** if the user supplies a template/source PPTX, preserve its master, source slide skeletons, typography, palette, logos, footer/page markers, title furniture, and brand chrome. Do not replace them with a self-invented design unless the user explicitly asks to restyle away from the template.
- **Image2/ImageGen owns the visual design:** generated images are not merely mood boards or loose style hints. After style selection, each page image is the approved visual construction drawing for that slide.
- **Slide intent is confirmed before narrative:** after content/source review, generate a `slide_intent_matrix.md` that proposes each slide's title, core idea, proof goal, available evidence, and unresolved gaps. Ask the user to confirm or edit it before narrative options.
- **Narrative is confirmed before visual style:** after content lock, generate a `narrative_matrix.md` with multiple narrative treatments as columns and slides as rows. Ask the user to choose or edit one treatment before any ImageGen style contact sheets.
- **Style options must be meaningfully different:** do not offer near-identical variants that only change color, title chips, or minor card spacing. Directions must differ primarily by aesthetic family, composition grammar, material/depth treatment, chart/diagram language, rhythm, and density while respecting any template frame.
- **Style does not rewrite the story:** all style options must preserve `deck_spec.json` and the selected narrative treatment: slide order, section flow, slide titles, claims, required data, sources, core proof objects, and per-slide narrative intent. A visual style lane may express the same narrative differently, but it must not change the deck's narrative logic.
- **Per-slide ImageGen comps are required:** after style selection, every output slide must have an approved `slides/slide-XXX-comp.png` generated as an independent 16:9 single-slide comp. A contact sheet alone is never enough to build the final PPTX.
- **Images are iterated before PPTX:** subagents/reviewer roles review each single-slide comp. P0/P1 findings must trigger targeted ImageGen regeneration of that slide before PPTX authoring.
- **PPTX is a pixel-locked hybrid reconstruction of the approved comp:** final slides must preserve the approved comp's appearance by default. Use full-slide or sliced comp backplates when native shape rebuilding would degrade the design, then overlay editable main text/numbers/simple shapes from `deck_spec.json`. Native-only redraw is allowed only when it visibly matches the comp or the user explicitly accepts a fidelity downgrade.
- **Editable does not mean fully native:** complex diagrams, depth fields, textures, glow, glass, illustrations, screenshots, dense icons, and generated visual systems may remain image layers. Required editability applies to main titles, claims, body text, key numbers, labels, footers, and simple callouts unless a user-approved exception is documented.
- **Reconstruction-only may skip planning, not fidelity:** when the user supplies final per-slide images, use `reconstruction-only` mode. Skip content/narrative/style generation, but still require per-slide image registration, exact text/OCR verification, visual contract, page-level reconstruction review, rendered previews, and final council.
- **Page-sharded reconstruction is preferred:** in reconstruction-only or repair mode, build each slide as an independent `slide-modules/slide-XXX.pptx`, review it against the source image, then merge approved slide modules. This isolates failures and prevents one bad page from degrading the deck.
- **No ordinary visual rebuild:** never replace an approved visual comp with a normal-looking table, card grid, default PPT text block, or square-box diagram. Native text boxes are allowed only as transparent/editable overlays that match the source typography and placement.
- **No self-certified comps:** never use final PPTX previews, template-starter previews, or output contact sheets as approved ImageGen comps. Approved comps must be independently generated files under `slides/slide-XXX-comp.png` or an explicitly documented equivalent comp path.
- **No silent downgrade:** do not switch to a style-inspired rebuild, blank-template rebuild, native-only redraw, table-only/card-only simplification, flat corporate grid, or generic PPT layout unless the user explicitly accepts that downgrade in `user_decisions.md`.
- **Advanced design bar:** unless the user asks for a plain compliance deck, visual comps should use richer slide-specific diagrams, layered composition, controlled depth, custom chart language, and executive polish. A deck made mostly of plain tables, equal rectangles, or default card grids fails this skill.

## Required Companion Skills

Use the `imagegen` skill for all generated bitmap visual drafts. Stay on its built-in tool path unless the user explicitly asks for CLI/API/model controls.

Use the `Presentations` skill for PPTX construction, preview rendering, QA, and export. Follow its workspace and artifact-tool contract, especially for template-following decks.

If either companion skill is unavailable, stop and explain which phase is blocked.

## General Deck Profiles

This is a general PPT design pipeline, not a defense-deck-only workflow. Select one primary `deck_profile` during content lock and record it in `deck_spec.json`; use it to choose proof objects, density, style directions, and reviewer emphasis.

- `product-pitch`: product overview, launch, roadmap, feature narrative, user journey, product strategy.
- `company-profile`: company introduction, capability deck, brand story, corporate overview, recruitment or partnership deck.
- `model-technical`: model, AI, data science, risk, engineering, architecture, methodology, validation, or platform decks.
- `sales-gtm`: sales pitch, solution proposal, customer value story, GTM/growth, market or segment deck.
- `strategy-executive`: board, management, operating review, transformation, planning, executive decision deck.
- `investor-finance`: fundraising, IR, finance, operating metrics, portfolio or investment committee deck.
- `training-enable`: training, SOP, onboarding, knowledge transfer, internal enablement deck.
- `internal-review`: promotion, performance, project review, postmortem, OKR, governance, or committee materials.

If the user supplies a template, `template-following` mode still controls the construction path; `deck_profile` only controls content, proof-object choices, and visual taste inside allowed template zones.

## Built-In PPT Taste System

Use `references/taste-system.md` as the default design-quality baseline for every non-trivial deck. This guidance is bundled with the skill so open-source users do not need separate taste skills to get strong ImageGen art direction, anti-generic QA, or profile-specific visual grammar.

Use taste guidance this way:

1. Read `references/taste-system.md` before style exploration and distill the relevant profile-specific rules into `design_system.json.taste_guidance` and `style_brief.json.taste_guidance`.
2. Keep `taste_guidance.enabled=true` unless the user explicitly asks for a plain compliance deck or non-designed output. Even then, keep the anti-regression rules that prevent unreadable, template-breaking, or table-only slides.
3. Apply the built-in anti-patterns during style direction planning, contact-sheet review, single-slide comp review, PPTX reconstruction, and final council review.
4. External taste/design skills or documents are optional supplements only. If used, translate them into static PPT rules and record them in `source_notes.md`; never require them for the pipeline to run.
5. Translate frontend-only rules into PPT equivalents. GSAP, hover physics, responsive breakpoints, web nav patterns, and web-only font bans are not PPT rules.

Taste guidance cannot override source truth, hard template constraints, brand authenticity, accessibility, or PPTX editability.

## Deterministic Gate Checks

Use the gate checker to prevent prose-only compliance from being bypassed:

```bash
SKILL_DIR=<directory containing this SKILL.md>
python "$SKILL_DIR/scripts/check_pipeline_gates.py" \
  --workspace <workspace> \
  --stage <content-lock|slide-intent-lock|narrative-lock|style-selection|reconstruction-lock|before-pptx|final>
```

Run it at these points:

- after content lock: `--stage content-lock`
- after user/automation slide-intent confirmation: `--stage slide-intent-lock`
- after user/automation narrative selection: `--stage narrative-lock`
- after user/automation style selection: `--stage style-selection`
- after reconstruction-only input registration and text/source-image lock: `--stage reconstruction-lock`
- before any PPTX construction code: `--stage before-pptx`
- before final response/export delivery: `--stage final`

If the checker returns `FAIL`, stop the current phase, fix the listed artifacts, and run it again. Do not work around the checker by editing `visual_contract.json`, `qa_report.md`, or `user_decisions.md` to describe steps that did not happen.

## Interaction And Resume Contract

This skill may stop to ask the user questions at five normal points: content lock, slide-intent confirmation, narrative treatment selection, design-direction count/brief, and visual style selection. Stopping is allowed; losing the workflow is not.

Before asking the user, update `pipeline_state.json` with:

- `skill`: `imagegen-pptx-pipeline`
- `workspace`: absolute workspace path
- `current_stage`: one of `content_gate`, `slide_intent_lock`, `narrative_selection`, `style_count`, `style_selection`, `single_slide_comps`, `slide_comp_review`, `reconstruction_input_lock`, `visual_contract`, `page_reconstruction`, `pptx_reconstruction`, `final_review`
- `awaiting_user`: `true`
- `required_user_reply`: exact question or decision needed
- `next_action`: first action to take after the user replies
- `last_completed_artifacts`: paths to the latest valid artifacts
- `resume_instructions`: "Read pipeline_state.json, deck_spec.json, user_decisions.md, then continue this stage; do not restart unless the user requests a restart."

End the user-facing question with a concise resume promise, for example: "回复后我会继续用 `$imagegen-pptx-pipeline` 从 `pipeline_state.json` 继续。"

On resume, first set `pipeline_state.json.awaiting_user=false`, append the user's answer to `user_decisions.md`, and continue from `next_action`. Do not reinitialize the workspace unless `pipeline_state.json` is missing or the user explicitly asks to start over.

## Workflow

### 0. Resume Or Continue

If a workspace already exists or the user says "继续", "resume", "用新的 skill 继续", or similar, search the current task output area for the most relevant `pipeline_state.json`. If found:

1. Read `pipeline_state.json`, `deck_spec.json`, `design_system.json`, `user_decisions.md`, and the stage's required artifacts.
2. Confirm the state belongs to `imagegen-pptx-pipeline`.
3. Continue from `current_stage` / `next_action`.
4. Do not repeat completed input parsing, style exploration, or slide generation unless the state marks them invalid.

### 1. Set Workspace

Create a Presentations-compatible workspace:

```bash
SKILL_DIR=<directory containing this SKILL.md>
python "$SKILL_DIR/scripts/init_pipeline_workspace.py" \
  --slug <task-slug> \
  --title "<deck title>" \
  --mode <create|template-following|targeted-edit|reconstruction-only|repair-existing-pptx>
```

Use the printed `workspace` path for all scratch files. Keep final deliverables under its `output/` directory unless the user supplied a destination.

Immediately update `pipeline_state.json` to `current_stage="input_reading"` and `awaiting_user=false`.

Mode selection:

- Use `template-following` whenever the user supplies a PPTX as a template, corporate template, source deck, or "follow this layout/style" deck.
- Use `create` when no deck/template is supplied.
- Use `targeted-edit` for small edits to an existing deck.
- Use `reconstruction-only` when the user already has final per-slide images and wants to convert them into an editable PPTX without rerunning content, narrative, style, or ImageGen phases.
- Use `repair-existing-pptx` when the user has a bad PPTX plus source images and wants to repair each slide to match the images.

### 2. Read Inputs

Classify inputs before design work:

- **Brief outline:** content seed; expand only where the user allows.
- **Template PPTX:** hard constraint for source slide skeletons, master/layout inheritance, typography, palette, footer, logos, title furniture, page markers, and brand chrome.
- **Historical/reference PPTX:** soft reference for taste, pacing, density, chart language, and image treatment.
- **Data/source files:** truth source for metrics and charts.
- **Brand/media assets:** verified source assets; do not invent logos, product UI, official marks, or people.

For every PPTX input, render previews/contact sheets and extract slide text before using it.

When a template/source PPTX exists, also write:

- `template-audit.md`: visible template elements, masters/layouts, reusable slide archetypes, fonts, colors, footer/page rules, and protected brand elements.
- `template-frame-map.json`: which template/source slide each target slide inherits from, which elements must be preserved, and which content zones may change.
- `deviation-log.md`: any user-approved template deviations. Empty is acceptable; missing is not.

### 2A. Reconstruction-Only Fast Path

Use this path when the user supplies final per-slide images and asks to convert them to PPTX. Do not rerun content planning, narrative selection, visual style exploration, or ImageGen unless a page image is missing/invalid and the user asks to regenerate it.

Required inputs:

- one high-resolution 16:9 image per final slide, preferably named or ordered as `slide-001`, `slide-002`, etc.
- exact text per slide, or permission to OCR and ask the user/agent reviewers to verify text before PPTX reconstruction
- optional template/source PPTX for logos, footer, page markers, or corporate chrome

Write and lock:

- `reconstruction_manifest.json`: source image path, text source status, reconstruction mode, per-slide output path, and page-sharding status.
- minimal `deck_spec.json`: slide count, slide IDs, exact overlay text when known, and editability targets. Set `deck.lock_state="locked"` after text is provided or OCR is verified/accepted.
- `visual_contract.json`: each supplied image becomes the approved comp with `reconstruction_mode="pixel_locked_hybrid"` unless explicitly overridden.

In this mode:

- `style_brief.json.selected_option` may be `user-supplied-final-images`.
- `visual_contract.json.contact_sheet` is optional; per-slide images are the source of truth.
- The gate checker may skip content, slide-intent, narrative, and style-selection gates, but it must still check `reconstruction_manifest.json`, `visual_contract.json`, per-slide preview review, and final export readiness.

Page-sharded build rules:

1. Build each slide independently as `slide-modules/slide-XXX.pptx`.
2. Use the source image as a full-slide or sliced backplate.
3. Mask/cover source-image text areas that will be editable.
4. Overlay editable native PPT text/numbers/labels/page markers.
5. Keep complex visuals as image layers. Do not redraw them as ordinary PPT tables, cards, or boxes.
6. Render `preview/slide-XXX-pptx.png` and compare against the source image before merging.
7. If a slide fails visual fidelity, repair only that slide module and rerender.
8. Merge approved slide modules into the final deck only after all page-level P0/P1 findings are resolved or explicitly accepted.

If the user provides only a contact sheet, stop and ask for individual high-resolution slide images unless they explicitly accept lower-fidelity reconstruction.

### 3. Produce Draft Truth Files

Write these files before calling ImageGen, but keep `deck_spec.json.lock_state` as `draft` or `needs_user_confirmation` until the next phase passes:

- `pipeline_state.json`: current stage, pause/resume status, required user reply, next action, and last completed artifacts.
- `deck_spec.json`: slide order, claims, exact text, numbers, proof objects, image needs, editability targets.
- `design_system.json`: template constraints, deck profile, palette, fonts, layout grid, chart grammar, asset rules, reference patterns, and built-in taste guidance.
- `slide_intent_plan.json`: user-confirmed slide titles, core ideas, proof goals, evidence candidates, material coverage, and unresolved gaps.
- `slide_intent_matrix.md`: user-facing Markdown table for confirming each slide's title and core idea.
- `narrative_plan.json`: narrative treatment options, selected treatment, slide-by-slide narrative cells, and lock status.
- `narrative_matrix.md`: user-facing Markdown table whose rows are slides and whose columns are narrative options.
- `style_brief.json`: requested number of design directions, direction names, diversity axes, visual ambition level, template constraints, built-in taste guidance, and option selection status.
- `reconstruction_manifest.json`: direct image-to-PPTX source manifest and per-slide module status, required in `reconstruction-only` and `repair-existing-pptx`.
- `template-frame-map.json`: required when a template/source PPTX exists; maps target slides to inherited source slides and preserved elements.
- `source_notes.md`: source provenance, missing inputs, assumptions, and asset authenticity notes.
- `content_review.md`: content critique, unresolved risks, and user-facing questions.
- `user_decisions.md`: confirmed decisions, accepted assumptions, and explicit user preferences.

Read `references/schemas.md` when drafting the structures.

Read `references/taste-system.md` and record the applicable built-in taste rules before style exploration. If the user supplied extra style/taste references, add them only as supplemental sources.

### 4. Grill And Lock Content

Before any ImageGen call, run a content-only review gate. Use reviewer roles or subagents when authorized; otherwise run the same roles sequentially.

First classify content completeness:

- **Explicit per-page content:** the user supplied titles/body/data or a detailed source deck for each page. Do not rewrite broadly. Run content review, ask only P0/P1 clarification questions, and lock exact slide text after resolution.
- **Brief outline only:** the user supplied a short outline, goal, or rough topic list. Ask grill-me style questions before designing unless the user explicitly requested full automation. Then draft the per-slide story, claims, proof objects, and exact text for confirmation.
- **Template-only/reference-only:** do not assume content from design structure. Ask for objective, audience, slide scope, and required claims before content generation.

Required pre-visual roles:

- `content-completeness`
- `deck-profile-strategist`: selects the deck profile and checks proof-object fit for that deck type.
- `brief-interrogator`: asks the fewest necessary hard questions about objective, audience, stakes, tone, constraints, and success criteria.
- `content-strategist`: checks story spine, slide order, claim strength, redundancy, and whether each slide has a proof object.
- `source-data-verifier`: checks source coverage, data gaps, metric definitions, units, dates, and unsupported claims.
- `audience-advocate`: checks whether the deck fits the actual reader's knowledge level, decision context, and objections.

Write the results into `content_review.md`. If there are blocking unknowns, ask the user concise questions before visual work. If the user wants full automation, record reasonable assumptions in `user_decisions.md` and mark them as accepted assumptions.

After content lock, record `deck_spec.json.deck.deck_profile`, `design_system.json.deck_profile`, and the applicable built-in taste guidance before style exploration.
Use the gate checker's `expected_deck_spec_fingerprint` output as `style_brief.json.narrative_lock.deck_spec_fingerprint` before generating style lanes.

When asking questions, write `pipeline_state.json` with `current_stage="content_gate"`, `awaiting_user=true`, and `next_action="apply user answers, update deck_spec.json, rerun content gate, then lock content"`.

Do not proceed to ImageGen until:

- `deck_spec.json.lock_state` is `locked`
- each slide has a title, claim, proof object, and editability target
- P0/P1 content findings are resolved or explicitly accepted by the user
- any invented or unsupported metric/source/asset risk is removed
- `check_pipeline_gates.py --stage content-lock` passes

Read `references/subagent-rubrics.md` for the pre-visual role prompts.

### 5. Propose And Lock Slide Intent

Before narrative treatment, confirm what each page is fundamentally trying to say. This stage lets the agent collect evidence from supplied materials even when the user cannot describe full slide content upfront.

Write:

- `slide_intent_plan.json`: machine-readable slide intent plan.
- `slide_intent_matrix.md`: user-facing table.

The table must use:

- rows: every planned slide in order
- columns: page number, proposed title, core idea, proof goal, evidence/data candidates from materials, content gaps/user questions, confidence

Rules:

- If the user supplied explicit per-page content, preserve the page structure and use this stage only to confirm title/core idea/proof goal and catch gaps.
- If the user supplied only a brief outline, the agent proposes slide titles/core ideas from the outline, template, references, and source materials, then asks the user to confirm or edit.
- Evidence candidates must come from supplied materials, verified sources, or clearly labeled assumptions. Do not invent numbers or sources.
- A slide may remain light on details if the core idea is confirmed and evidence can be extracted from materials later.
- Do not generate narrative options, images, or PPTX in this stage.

If the user did not request full automation, show `slide_intent_matrix.md` and ask them to confirm or edit the proposed titles/core ideas. Write `pipeline_state.json` with `current_stage="slide_intent_lock"`, `awaiting_user=true`, and `next_action="record slide intent edits, update slide_intent_plan.json and deck_spec.json, run slide-intent gate, then generate narrative matrix"`.

If the user explicitly requested full automation, lock the slide intent with accepted assumptions in `user_decisions.md`.

Do not proceed to narrative treatment until:

- `slide_intent_plan.json.lock_state` is `locked`
- every slide has a confirmed title, core idea, proof goal, and evidence strategy
- P0/P1 gaps are resolved or explicitly accepted
- `slide_intent_matrix.md` exists
- `check_pipeline_gates.py --stage slide-intent-lock` passes

Read `references/prompt-templates.md` for the slide-intent prompt.

### 6. Propose And Lock Narrative Treatment

Before asking for visual style count or generating any ImageGen output, produce narrative options for the whole deck. This stage reduces expensive visual regeneration by confirming exactly how each page should present the locked slide intent and content.

Write:

- `narrative_plan.json`: machine-readable narrative options and selected treatment.
- `narrative_matrix.md`: user-facing table.

The table must use:

- rows: every slide in locked page order
- columns: each narrative option
- cell content: how that slide would be presented, what content/proof is emphasized, what visual proof object is used, and what must stay unchanged

Example column families should be selected for the actual task, not reused mechanically:

- `evidence-first`: direct claims, strongest proof object, decision-oriented hierarchy.
- `story-arc`: context -> tension -> progress -> outcome -> next step.
- `technical-system`: architecture, mechanisms, process/control logic, validation.
- `executive-decision`: decision frame, tradeoffs, risks, options, recommendations.
- `customer-value`: pain, solution fit, impact, adoption, next action.
- `growth-maturity`: baseline, capability build, milestone arc, future commitment.

Rules:

- Narrative options may change per-slide framing, order of emphasis, proof-object expression, and what supporting content is foregrounded.
- Narrative options may not invent new claims, data, logos, sources, products, or results.
- Narrative options may not change the locked slide count or slide order unless the user explicitly asks to restructure the deck.
- Do not generate images in this stage.
- If the user has explicit per-page content, keep each slide's exact content and offer presentation treatments only.
- If the user gave a brief outline, use `slide_intent_plan.json` as the confirmed source for each page's title/core idea/proof goal.

If the user did not request full automation, show `narrative_matrix.md` and ask them to choose one narrative option or edit cells directly. Write `pipeline_state.json` with `current_stage="narrative_selection"`, `awaiting_user=true`, and `next_action="record selected narrative treatment, update narrative_plan.json, update style_brief narrative lock, then ask design count"`.

If the user explicitly requested full automation, select the strongest narrative with the reviewer rubric, record the reason in `user_decisions.md`, and lock `narrative_plan.json`.

Do not proceed to visual style count or ImageGen until:

- `slide_intent_plan.json.lock_state` is `locked`
- `narrative_plan.json.lock_state` is `locked`
- `narrative_plan.json.selected_narrative_id` is set
- every slide has a selected narrative cell
- `narrative_matrix.md` exists
- `check_pipeline_gates.py --stage narrative-lock` passes

Read `references/prompt-templates.md` for the narrative matrix prompt.

### 7. Ask Design Count And Explore Visual Directions

Before generating style options, determine how many directions the user wants:

- If the user specified a count, use it.
- If the user did not specify a count and did not request full automation, ask for a count and any style preference. Write `pipeline_state.json` with `current_stage="style_count"` and resume after the answer.
- If the user requested full automation, default to 4 directions.
- Recommended range: 3 to 6 directions. Fewer than 3 weakens exploration; more than 6 usually slows review.

Write `style_brief.json` with `direction_count`, `generation_mode`, `narrative_lock`, `selected_narrative_id`, `visual_ambition`, `diversity_axes`, `user_style_preferences`, `candidate_directions`, and `style_lanes`.

Style direction generation must be ImageGen-based. The preferred path is **parallel style lanes**:

1. Create one lane per option under `style_lanes`, each with a distinct `aesthetic_family`, design premise, prompt path, and expected output path.
2. When the user requested or approved subagent collaboration and subagent tools are available, spawn one `style-lane-art-director` subagent per lane. Each lane independently writes its prompt and calls ImageGen for exactly one full-deck contact sheet preview.
3. When subagents are unavailable, not approved, or cannot call ImageGen, run the same lanes sequentially yourself, but keep separate prompts and separate ImageGen calls. Do not collapse all directions into one generic multi-option prompt unless the runtime only supports that fallback.
4. Record each contact sheet in `style_brief.json.style_contact_sheets` with `generator="imagegen"`, `style_lane_id`, `aesthetic_family`, `prompt_path`, and `path`.

Recommended aesthetic families are task-dependent. Pick the best fit from the built-in taste system and the user's preference; examples include:

- `premium-flat`: refined flat editorial/business design, high hierarchy, no default-card feel.
- `motion-inspired`: static slides that borrow animation/keyframe rhythm, directional flow, kinetic paths, staged reveals, and motion-like composition.
- `skeuomorphic-material`: tactile material, subtle dimensionality, physical controls, object-like evidence modules.
- `glassmorphism-blur`: blurred glass, layered translucency, restrained depth, high contrast and readability.
- `tech-systems`: technical architecture, data lineage, control planes, luminous but disciplined system maps.
- `editorial-literary`: publication-like composition, narrative pacing, elegant typography, image/quote/essay rhythm.
- `data-command-center`: dense executive dashboards, scorecards, deltas, bridges, and operational control surfaces.
- `brand-world`: strong brand atmosphere, product/company identity, visual world-building with verified assets only.

Users may specify desired or forbidden aesthetic families. If they do not, the agent recommends families that fit the deck profile, audience, template, and source material. All selected families must still meet the premium taste bar; "flat", "tech", "glass", or "cartoon/animation-inspired" are not excuses for cheap, generic, or unreadable slides.

Use ImageGen to create the requested number of full-deck contact-sheet style options from `deck_spec.json`, `slide_intent_plan.json`, `narrative_plan.json`, `design_system.json`, and `style_brief.json`.

Require:

- all slides in correct order
- 16:9 slide thumbnails
- genuinely different visual systems, not recolors
- each direction has a named aesthetic family and design premise, for example "premium-flat executive evidence", "tech-systems architecture", "motion-inspired growth arc", "glassmorphism decision cockpit", "skeuomorphic material workflow", or "editorial-literary narrative"
- direction premises fit the selected `deck_profile`; for example, product decks need product/benefit/user-flow options, company decks need capability/brand/world-view options, and model/technical decks need architecture/methodology/validation options
- materially different visual style grammar: one option may emphasize refined flat structure, another glass depth and translucent layers, another motion-like flow paths, another tactile material modules, another technical systems maps, another editorial narrative pacing
- same narrative logic: every option must keep the same slide count, order, section flow, core title meaning, claims, sources, proof-object intent from `deck_spec.json`, and selected per-slide narrative treatment from `narrative_plan.json`
- richer design than a flat table/card deck: use custom diagrams, focal objects, controlled layering, depth, high-quality chart language, and slide-specific visual metaphors where appropriate
- no fake logos, fake UI, fake people, or invented metrics
- enough legibility to judge structure, not final copy accuracy
- when a template/source PPTX exists, attach the template contact sheet and require every option to keep the template's visible frame, title/footer/page system, typography feel, and brand chrome; explore only within the template's allowed content zones

If the user explicitly wants full automation, pick the best option with the style rubric and record the decision in `qa/style-selection.md`. Otherwise show all ImageGen contact sheets and ask the user to choose. Generic delegation like "帮我做一个 PPT" is not explicit full automation.

Read `references/prompt-templates.md` for the prompt.

### 8. Select Style, Then Review The Selected Direction

Do a light safety screen before showing options:

- remove or regenerate any option with P0 template/source violations, fake identity assets, missing slides, or wrong slide order
- do not spend review effort polishing all unselected options

If the user wants full automation, select the best option only after reviewer synthesis and write `qa/style-selection.md`. Otherwise show all options and ask the user to choose. Write `pipeline_state.json` with `current_stage="style_selection"`, `awaiting_user=true`, and `next_action="record selected style, run selected-style review, then generate single-slide comps"`.

After the user selects a direction, run the style-selection reviewer group on the selected contact sheet:

- `narrative-invariance`
- `style-coherence`
- `color-brand`
- `executive-polish`
- `taste-direction`
- `design-diversity`
- `image-art-director`
- `template-fidelity` when a template/source deck exists

Fix P0/P1 style findings before single-slide generation.

Do not proceed to single-slide comp generation until `check_pipeline_gates.py --stage style-selection` passes.

### 9. Generate Single-Slide Visual Comps

For the selected style, call ImageGen once per slide. This phase is mandatory. Each output is a high-resolution 16:9 visual comp:

- Use `deck_spec.json` as the content guide.
- Use `slide_intent_plan.json` as the slide title/core-idea/proof-goal guide.
- Use `narrative_plan.json` as the slide-by-slide presentation guide.
- Use the selected contact sheet as the visual system.
- In template-following mode, attach the mapped template/source slide screenshot from `template-frame-map.json` and require the comp to preserve that template frame.
- Keep slide numbers and major text visible, but do not rely on ImageGen for exact final text.
- Save files as `slides/slide-001-comp.png`, `slides/slide-002-comp.png`, etc.
- Save ImageGen prompts under `prompts/slide-001-comp.txt`, `prompts/slide-002-comp.txt`, etc. Record generated image file paths in `deck_spec.json` and `visual_contract.json`.
- Do not build PPTX until every target slide has a saved comp path, selected-style reference, template source slide if applicable, and review status.
- If ImageGen fails or returns a contact sheet/grid instead of one slide, retry with the single-slide prompt. If it still fails, block or ask the user; do not proceed with a generic editable slide.
- If the single-slide comp looks flatter, simpler, or less designed than the selected contact sheet direction, regenerate it. Do not accept "clean but generic" comps unless the selected direction itself is deliberately plain.

### 10. Review And Iterate Visual Comps

Run stage-specific reviewer roles on slide comps. If multi-agent tools are available and the user requested subagents or approved collaboration, spawn independent subagents for bounded review roles. Otherwise perform the same roles sequentially.

Visual-comp reviewer group:

- `narrative-invariance`: checks slide count/order context, claim meaning, data/source preservation, and proof-object intent against the locked deck spec.
- `content-integrity`: checks slide claims, data, source fit, and story completeness against `deck_spec.json`.
- `text-typography`: checks exact text plan, editability, hierarchy, line breaks, overflow risk, and OCR traps.
- `visual-fidelity`: checks that the comp matches the selected style and preserves the intended proof-object shape.
- `image-art-director`: checks whether the comp uses ImageGen's visual strength instead of default PPT boxes, and whether it has enough crafted design quality for the audience.
- `layout-pptx-feasibility`: checks whether the visual comp can be rebuilt as editable PPTX without quality collapse.
- `chart-logic`: checks chart type, units, labels, scale, data-to-visual fit, and whether approximations are acceptable.
- `asset-authenticity`: checks logos, screenshots, people, product UI, icons, and identity assets for provenance and non-fabrication.
- `template-fidelity`: required when a template/source PPTX exists; checks the comp preserves the mapped source slide frame and protected elements.
- `accessibility-readability`: checks contrast, projection readability, small text, visual noise, and color-only encoding.

Read `references/subagent-rubrics.md` for reviewer prompts and JSON feedback format.

Iteration rule:

- Fix all P0/P1 blockers before moving from contact sheets to slide comps or from slide comps to PPTX.
- Fix P0/P1 comp blockers by targeted ImageGen regeneration of that slide first. Do not patch around a failed comp directly in PPTX unless the finding is only exact text correction from `deck_spec.json`.
- Run at most 2 automated visual-comp iterations unless the user asks for more.
- Prefer targeted prompt edits over redesigning the whole deck.

### 11. Lock The Visual Reconstruction Contract

Before writing PPTX code, translate the selected contact sheet and single-slide comps into `visual_contract.json`.

For each slide record:

- approved comp path
- comp review status and unresolved accepted risks
- template/source slide inherited by this slide, if any
- protected template elements that must survive final PPTX reconstruction
- selected style option
- visual archetype: system map, maturity arc, loop, funnel, radial, timeline, swimlane, matrix, scorecard, dashboard, process chain, comparison, or other
- reconstruction mode: `pixel_locked_hybrid` by default, `sliced_hybrid` when text/diagram regions need separate editable overlays, or `native_rebuild` only with explicit fidelity evidence or user acceptance
- comp backplate plan: full-slide comp image or cropped comp layers that must be inserted before native overlays
- text mask plan: regions where comp-rendered text should be covered before adding editable PPT text
- must-preserve composition: key regions, flow direction, diagram geometry, focal object, whitespace, and visual hierarchy
- allowed simplifications for editability
- prohibited regressions, especially `table-only`, `square-card-only`, `default-template`, and `text-heavy` when the comp uses richer diagrams
- native reconstruction plan: which elements become editable text, shapes, connectors, charts, and tables
- retained image plan: which complex areas may remain images and why

Reject any visual contract entry whose approved comp path points to `preview/`, `output/`, `template-starter-preview/`, or a rendered PPTX preview. That is self-certification, not ImageGen review.

If ImageGen produced only a full-deck contact sheet and not per-slide comps, generate the missing single-slide comps. Downgrade to "style-inspired editable rebuild" only after explicitly telling the user the result will no longer be comp-faithful and recording the user's acceptance in `user_decisions.md`. Full automation or time pressure is not implied consent.

Do not proceed to PPTX build until:

- every slide has an approved `slide-XXX-comp.png`
- every slide has a reconstruction mode, comp backplate plan, editable overlay plan, and text mask plan
- every slide has a visual archetype and native reconstruction plan
- every template-following slide has a mapped source slide and protected template elements
- at least 60% of non-title slides use a non-table proof object when the selected style contains diagrams or visual systems
- no slide's planned proof object is weaker than `deck_spec.json.proof_object`
- visual-fidelity reviewer has no P0/P1 findings
- `check_pipeline_gates.py --stage before-pptx` passes

Read `references/schemas.md` for `visual_contract.json`.

### 12. Build Editable PPTX

Use `Presentations` and artifact-tool presentation JSX.

Treat the approved comp as the slide construction drawing and visual backplate. The default target is pixel-locked hybrid fidelity: the rendered PPTX preview should look like the approved comp at normal viewing size, while main information remains editable. A final slide that only preserves the text and template frame while discarding the comp's visual expression fails reconstruction.

Reconstruction modes:

- `pixel_locked_hybrid` (default): place the approved comp as a full-slide image backplate, cover/mask text areas that must become editable, then overlay native PPT text, key numbers, labels, simple shapes, and page furniture. This gives the highest visual fidelity.
- `sliced_hybrid`: crop the comp into stable visual layers or regions, omit/mask text-heavy regions, then rebuild those regions natively. Use this for dense slides where text editability is important.
- `native_rebuild`: rebuild with native shapes/charts only. Use only when it passes preview comparison or the user explicitly accepts that it will not be pixel-faithful.

For **template-following** mode:

- Duplicate/import the starter PPTX and edit copied slide elements in place.
- Start from the mapped source slide in `template-frame-map.json` or a clearly compatible source layout; never start from a blank slide when a template slide exists.
- Preserve source layout grammar, typography, palette, logos, footer/page markers, title furniture, and brand chrome.
- Do not rebuild from blank JSX, mutate OOXML directly, or use LibreOffice save-as.
- Treat ImageGen comps as the approved visual blueprint inside the inherited template canvas; the final deck must still inherit from duplicated template/source slides.
- Preserve the approved comp's proof-object archetype and composition inside the inherited template canvas. Template-following is not permission to replace a system map, loop, radial, maturity arc, or workflow comp with a generic table/card grid.
- Use pixel-locked hybrid reconstruction aggressively: insert the approved comp or sliced comp layers first, then rebuild main text and simple geometry as native PPT elements. Complex backgrounds, textures, depth, illustrations, and diagrams should remain image layers when native rebuilding would collapse the design.
- If the inherited template cannot support the approved comp's visual expression, split the slide, choose a more suitable source slide, regenerate the comp within the template frame, or document a P1 deviation and ask the user. Do not silently degrade the slide.

For **create** mode:

- Build slides from `deck_spec.json`, `slide_intent_plan.json`, `narrative_plan.json`, `design_system.json`, and approved visual comps.
- Insert the approved comp as a full-slide or sliced backplate before adding editable overlays, unless the slide is explicitly marked `native_rebuild` with evidence.
- Main text, numbers, footers, and page markers must be native editable PPT elements.
- Preserve complex visual assets as cropped high-quality images when rebuilding them as native shapes would degrade quality.

For **reconstruction-only** and **repair-existing-pptx** mode:

- Treat each user-supplied slide image as the approved comp.
- Build one independent PPTX module per slide under `slide-modules/slide-XXX.pptx`.
- Do not create ordinary-looking native tables/cards/text blocks as a substitute for the image design.
- Native text boxes are allowed only for editable overlays and must match the source image's typography, position, color, line breaks, and hierarchy.
- Keep complex visual design, diagrams, shadows, depth, icons, and background systems as full-slide or sliced image backplates.
- Render and approve each slide module before merging. Do not merge failed pages into the final deck.
- Merge approved slide modules into `output/<deck-name>.pptx` only after all page-level previews pass `pptx-reconstruction-fidelity`.

Never deliver a slide as only one flat image with no editable main information unless the user explicitly requests non-editable output. A whole-slide comp backplate is allowed and recommended when it is combined with editable overlays and documented retained-image areas.

After building each slide, render a preview and compare it against the approved comp before moving on. P1 visual-fidelity or template-fidelity failures require slide-level iteration before final deck review.

### 13. Final Deck Council Review And Export

Render PPTX previews and compare them to visual comps and `visual_contract.json`. Then run a final all-role review council on the rendered PPTX previews, final contact sheet, `deck_spec.json`, `design_system.json`, `visual_contract.json`, `source_notes.md`, and `qa_report.md`.

Final council roles:

- `content-integrity`
- `text-typography`
- `source-data-verifier`
- `chart-logic`
- `asset-authenticity`
- `template-fidelity` when a template/source deck exists
- `color-brand`
- `style-coherence`
- `accessibility-readability`
- `layout-pptx-feasibility`
- `visual-fidelity`
- `pptx-reconstruction-fidelity`
- `executive-polish`
- `taste-direction`
- `narrative-invariance`

Write results to `qa/final-council.md` and summarize them in the final `qa_report.md`.

Blocking QA:

- Final slide count and order match `deck_spec.json`.
- Every final slide has an approved per-slide ImageGen comp and PPTX preview comparison.
- Main text and numbers are editable and match `deck_spec.json`.
- No obvious typo, overflow, missing page number, malformed chart, or fake source.
- Preview preserves approved composition, color, density, and hierarchy.
- PPTX previews pass reconstruction-fidelity review against the approved comp; logical correctness without visual reconstruction is not enough.
- Final PPTX preserves `visual_contract.json` archetypes; no unapproved collapse to table-only/card-only/default layouts.
- Template-following decks pass source-template fidelity gates, preserve mapped template elements, and have no unapproved rebuild-from-blank slides.
- Every final council role has `approval_to_advance=true`.
- No P0/P1 final council findings remain unless the user explicitly accepts the risk in `user_decisions.md`.

Export only after blockers are resolved. Deliver:

- final editable `.pptx`
- preview contact sheet
- concise QA report with known image-retained areas and any data approximations

Before the final response, run `check_pipeline_gates.py --stage final`. If it fails, do not deliver the PPTX as final; report the blocker or iterate.

Keep only final deliverables in `output/`: the final PPTX, final preview contact sheet, and final QA report. Internal prompts, intermediate comps, layout JSON, reviewer scratch, and temporary previews should stay in the workspace and be cleaned according to the `Presentations` skill before the final response.

## Reference Files

- `references/schemas.md`: required intermediate JSON/Markdown files.
- `references/prompt-templates.md`: ImageGen and PPTX reconstruction prompts.
- `references/subagent-rubrics.md`: reviewer roles, feedback schema, and spawn guidance.
- `references/taste-system.md`: bundled PPT taste system, anti-generic rules, profile-specific visual guidance, and ImageGen/PPTX reconstruction taste constraints.
- `references/taste-integration.md`: optional external taste-source supplement rules.

## Boundaries

- Do not invent metrics, sources, logos, product screenshots, or official marks.
- Do not let ImageGen OCR output override the structured slide spec.
- Do not skip rendering previews before claiming the PPTX is finished.
- Do not ignore a supplied template or replace its visible system with self-designed layouts.
- Do not use subagents without explicit user authorization or a clear user request for collaborative/multi-agent review.
