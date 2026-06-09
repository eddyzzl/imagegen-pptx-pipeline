# Built-In PPT Taste System

This file is the default design-quality baseline for the ImageGen PPTX pipeline. It is bundled with the skill so the workflow does not depend on external taste, brand, frontend, or high-end design skills.

External taste/design skills or documents may be used only as optional supplements. Start from this file, then translate any extra guidance into portable PPT rules.

## Universal Bar

A successful deck should feel intentionally art-directed, not like a default presentation template. ImageGen should be used to explore composition, diagram language, depth, and visual metaphor. PPTX reconstruction should preserve that visual grammar instead of collapsing it into plain tables, equal card grids, and generic rectangles.

Default anti-patterns:

- Flat table-only decks when the content can be shown as process, system, timeline, maturity, loop, funnel, radial, or dashboard logic.
- Equal-card grids repeated across many slides with only titles and icons changed.
- Generic AI gradients, random glow, decorative blobs, or depth that does not support the claim.
- One-note palettes, especially undifferentiated blue-purple tech, beige corporate, or all-red/all-blue slides without neutral balance.
- Text and metrics floating without a proof object or visual relationship.
- Icons used as decoration instead of labels, state, movement, ownership, or evidence.
- Overdense small text that looks plausible in an image but cannot be rebuilt as readable editable PPT.
- Template-following output that preserves the logo/footer but discards the selected comp's visual expression.

## Composition Rules

Use a different visual archetype when the slide claim changes:

- Status or KPI: scorecard, dashboard, metric stack, gauge/ring, bridge, or variance map.
- Method or workflow: process chain, swimlane, pipeline, decision tree, loop, or operating system map.
- Growth or maturity: maturity arc, timeline, stair-step, compound curve, phase path, or capability ladder.
- Cause and effect: funnel, flywheel, radial influence map, causal chain, or issue tree.
- Comparison: before/after, option matrix, tradeoff map, competitive quadrant, or capability gap.
- Architecture or model: layered stack, data lineage, system map, control plane, topology, or lifecycle.
- Executive decision: thesis board, options map, risk/return matrix, roadmap, or decision dashboard.

Keep one dominant proof object per slide. Use secondary modules as labels, callouts, or evidence, not as competing focal areas.

Prefer asymmetric but controlled composition inside the template frame. Use whitespace as hierarchy, not leftover space.

Design at two distances:

- Thumbnail: slide purpose, focal object, and section rhythm must be recognizable.
- Full size: title, key numbers, main labels, and source-critical details must be readable.

## Visual Ambition Levels

- `restrained`: formal, clean, low-risk. Still requires proof objects and rhythm; not plain boxes.
- `polished`: executive-ready, with crafted diagrams, refined spacing, and strong hierarchy.
- `premium`: richer depth, custom charts, higher visual specificity, and distinctive slide archetypes.
- `cinematic-business`: high-impact cover/section/commercial decks; use sparingly for formal reports.

Default to `polished` or `premium` unless the user asks for plain compliance output.

## Profile-Specific Guidance

### product-pitch

Show product value through user journey, before/after state, feature-to-benefit mapping, product surface, adoption proof, and roadmap. Avoid abstract capability cards without product evidence.

### company-profile

Build a brand world: mission, capability map, trust proof, milestone timeline, ecosystem, operating scale, and differentiators. Avoid pages that read like a company registration form.

### model-technical

Use architecture maps, data lineage, model lifecycle, experiment dashboards, validation matrices, risk controls, and monitoring loops. Avoid burying the model logic in prose tables.

### sales-gtm

Map customer pain to solution fit, value bridge, implementation journey, ROI proof, case evidence, and next steps. Avoid internally focused feature lists that do not answer buyer objections.

### strategy-executive

Use thesis, options, tradeoffs, decision maps, operating rhythm, milestones, and risk controls. Avoid generic 2x2s unless the axes create a real decision.

### investor-finance

Keep metric discipline high: bridges, cohorts, waterfall, sensitivity, unit economics, runway, source footnotes, and definition clarity. Visual polish cannot obscure numbers.

### training-enable

Use learning paths, SOP flows, scenario maps, checklists, examples, and comprehension hierarchy. Avoid decorative training pages that hide sequence and action.

### internal-review

Use evidence spine, contribution map, capability comparison, growth arc, lessons loop, future roadmap, and commitment plan. Avoid self-evaluation pages made only of text boxes.

## Style Direction Diversity

When generating multiple directions, each option must differ by more than color:

- aesthetic family
- composition grammar
- proof-object family
- density and pacing
- title/section treatment
- background and depth treatment
- chart/diagram language
- material and texture treatment

Examples of genuinely different options:

- Template-faithful executive evidence: restrained, formal, strong source hierarchy.
- Technical architecture system: layered maps, pipelines, control loops, dense but organized.
- Narrative growth arc: larger focal graphics, maturity curves, story rhythm, warmer pacing.
- Data-story dashboard: scorecards, bridges, deltas, and decision summaries.
- Premium editorial: stronger visual moments, asymmetry, refined image/diagram interplay.

Near-identical options are a P1 failure even if they look polished.

## Aesthetic Family Taxonomy

`aesthetic_family` is not a decoration label. It must drive composition grammar, proof-object treatment, material/depth, typography, density, and known failure modes while preserving the same deck story.

### premium-flat

Use refined flat hierarchy, custom diagrams, strong typography, exact spacing, and clean executive evidence modules. This is not default PPT flatness.

Forbid: default cards, table-only layouts, generic icon rows, bland white boxes, and low-effort consulting templates.

### motion-inspired

Use static directional rhythm: staged flow, keyframe-like progression, path composition, numbered reveals, arcs, trails, timelines, and movement cues. The slide should feel like a frozen moment from a thoughtful animation, not a motion spec.

Forbid: web animation instructions as PPT requirements, noisy arrows everywhere, fake UI transitions, and story changes masquerading as movement.

### skeuomorphic-material

Use tactile evidence modules, subtle dimensionality, physical controls, object-like panels, soft shadows, paper/metal/glass surfaces, and carefully modeled proof objects.

Forbid: cartoonish fake hardware, heavy drop shadows, plastic toy UI, uncontrolled 3D, and decorative objects unrelated to the claim.

### glassmorphism-blur

Use restrained translucency, blurred backplates, layered depth, frosted panels, fine highlights, and high-contrast text. Glass must support grouping and depth, not hide information.

Forbid: low-legibility glow, blurry text, overused blue-purple panels, bokeh decoration, and weak contrast.

### tech-systems

Use architecture maps, data lineage, control planes, nodes/edges, pipelines, telemetry, system stacks, and disciplined luminous accents.

Forbid: cyberpunk/neon decoration, fake code, meaningless circuit lines, and technical visuals that obscure source proof.

### editorial-literary

Use publication-like typography, narrative pacing, elegant whitespace, essay rhythm, quote/image interplay, and strong section moments. Good for reflective, company, brand, strategy, or narrative review decks.

Forbid: magazine prettiness that weakens proof, oversized decorative type in dense business slides, and vague poetic copy.

### data-command-center

Use executive dashboards, scorecards, deltas, bridges, operational maps, and high-density but organized control surfaces.

Forbid: illegible microtext, metric wallpaper, unsupported numbers, and visual density without decision hierarchy.

### brand-world

Use a strong product/company visual world with verified assets, authentic brand cues, distinctive color/material choices, and content-specific imagery.

Forbid: invented logos, fake product UI, stock-like filler, generic brand mood boards, and brand chrome that violates a supplied template.

## ImageGen Prompting Rules

Prompts should ask for the slide's visual archetype, not only its topic. Name the proof object and the reader takeaway.

For contact sheets, require distinct direction premises and thumbnail-level recognizability.

For single-slide comps, preserve the selected contact sheet's visual system and make the chosen archetype obvious. Do not let the slide become a wireframe or a plain data table unless that is the intentional proof object.

If a template exists, the prompt must explicitly include the mapped source slide screenshot and protected template elements. Explore inside allowed zones only.

## PPTX Reconstruction Rules

The comp is a construction drawing. Rebuild main titles, body text, numbers, footers, and page markers as editable PPT text. Rebuild simple geometry natively. Retain cropped image layers when needed for complex backgrounds, texture, depth, illustrations, or diagram backplates.

Do not deliver a final slide as only one flat image with no editable main information unless the user explicitly accepts non-editable output. A whole-slide comp backplate is acceptable when editable text/numbers/simple shapes are overlaid.

Do not replace a rich ImageGen comp with a generic table, card grid, or default layout because it is easier to author. If native reconstruction would lose the premium feel, retain the complex visual layer from the comp and overlay editable text/shapes.

## Optional External Taste Inputs

External taste skills may add vocabulary or inspiration, but they are not dependencies. When used:

- Record them in `source_notes.md` and `taste_guidance.sources`.
- Translate them into static PPT rules.
- Ignore web-only rules such as hover, scroll, GSAP, responsive breakpoints, nav patterns, CSS class names, and web-only font constraints.
- Never let them override source truth, a hard template, accessibility, or editability.
