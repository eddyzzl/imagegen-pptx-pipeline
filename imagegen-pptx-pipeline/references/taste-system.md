# Built-In PPT Taste System

This file is the default design-quality baseline for the ImageGen PPTX pipeline. It is bundled with the skill so the workflow does not depend on external taste, brand, frontend, or high-end design skills.

External taste/design skills or documents may be used only as optional supplements. Start from this file, then translate any extra guidance into portable PPT rules.

## Universal Bar

A successful deck should feel intentionally art-directed, not like a default presentation template. ImageGen should be used to explore composition, diagram language, depth, and visual metaphor. Strict PPTX conversion should preserve that visual grammar instead of collapsing it into plain tables, equal card grids, and generic rectangles.

Default anti-patterns:

- Flat table-only decks when the content can be shown as process, system, timeline, maturity, loop, funnel, radial, or dashboard logic.
- Equal-card grids repeated across many slides with only titles and icons changed.
- Multiple style options that keep the same visual skeleton and only swap icons, line treatments, accent colors, or small decorative modules.
- Off-profile style recommendations, such as promotion/interview/academic-defense styles for a company profile deck, generic consulting/system-dashboard styles for a product deck, or annual-report styles for a defense/interview deck unless the user explicitly asked for that framing.
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

### defense-promotion

Use achievement proof spine, capability ladder, role-scope map, milestone timeline, before/after impact, stakeholder evidence, interview-ready recommendation board, or academic argument structure according to the actual occasion. Avoid generic consulting loops, annual-report dashboards, or system-control panels unless the user requested that framing.

## Style Direction Diversity

When generating multiple directions, choose concrete `style_id` values from [style-library.md](style-library.md) before writing ImageGen prompts. Do not start from vague adjectives like "flat", "3D", "tech", "premium", or "minimal" unless they map to a canonical style id.

Common user requests map to style ids:

- McKinsey style: `mckinsey-consulting-report`
- Enterprise annual report style: `enterprise-annual-report` or `luxury-print-annual`
- Apple launch/keynote style: `apple-keynote-black` or `apple-keynote-white`
- Notion style: `notion-workspace-clean`
- Minimalist style: `swiss-international`, `lecture-minimal-white`, or `brand-proposal-minimal`
- Promotion defense style: `promotion-defense-evidence` or `personal-performance-review`
- Interview style: `interview-case-board`
- Rigorous academic style: `rigorous-academic-defense` or `thesis-defense-clean`
- Classical style: `classical-european` or `shareholder-letter-editorial`

Screenshot-inspired categories from Tosea-like template libraries are represented in `style-library.md`: workplace, company business, consulting research, finance/investor, industry solution, education/academic, creative brand, personal/resume, and lifestyle/event.

Before choosing among these styles, classify the deck profile. Reuse a previous task's preferred styles only if the current profile matches; for example, a company introduction should not inherit promotion-defense or academic options, and a promotion defense should not inherit company-profile options.

Each option must differ by more than color:

- aesthetic family
- canonical style id and style source
- deck-profile fit and audience fit
- layout archetype
- evidence presentation pattern
- composition grammar
- visual skin and material language
- density and pacing
- title/section treatment
- background and depth treatment
- chart/diagram language
- material and texture treatment

Examples of genuinely different visual options:

- `mckinsey-consulting-report`: white consulting grid, issue-tree logic, bridge/waterfall charts, sparse accent color.
- `enterprise-annual-report`: premium print rules, disciplined metrics, refined typography, polished photography.
- `apple-keynote-white`: large hero object, dramatic whitespace, oversized typography, decisive minimal copy.
- `notion-workspace-clean`: block rhythm, simple icons, light dividers, workspace/database clarity.
- `technical-schematic-premium`: precise grids, connectors, line icons, system diagrams, instrument annotations.
- `editorial-gallery-white`: gallery numerals, image/object panels, serif/sans contrast, publication whitespace.

Near-identical options are a P1 failure even if they look polished.

## Aesthetic Family Taxonomy

`aesthetic_family` is not a decoration label. It must drive visual-only choices: composition grammar, material/depth, typography, density, icon/illustration language, chart rendering, and known failure modes while preserving the same deck story, slide content, and proof object.

Prefer the concrete `style_id` catalog in `style-library.md`. The older aesthetic families below remain broad fallback families or secondary influences, not the preferred user-facing option names.

### premium-flat

Use refined flat hierarchy, custom diagram rendering, strong typography, exact spacing, and clean executive modules. This is not default PPT flatness.

Forbid: default cards, table-only layouts, generic icon rows, bland white boxes, and low-effort consulting templates.

### motion-inspired

Use static directional rhythm: staged flow, keyframe-like progression, path composition, numbered reveals, arcs, trails, timelines, and movement cues. The slide should feel like a frozen moment from a thoughtful animation, not a motion spec.

Forbid: web animation instructions as PPT requirements, noisy arrows everywhere, fake UI transitions, and story changes masquerading as movement.

### skeuomorphic-material

Use tactile material modules, subtle dimensionality, physical controls, object-like panels, soft shadows, and paper/metal/glass surfaces.

Forbid: cartoonish fake hardware, heavy drop shadows, plastic toy UI, uncontrolled 3D, and decorative objects unrelated to the claim.

### glassmorphism-blur

Use restrained translucency, blurred depth fields, layered panels, frosted surfaces, fine highlights, and high-contrast text. Glass must support grouping and depth, not hide information.

Forbid: low-legibility glow, blurry text, overused blue-purple panels, bokeh decoration, and weak contrast.

### technical-schematic

Use schematic drafting language, precise grids, measured connectors, instrument-like annotations, thin blue-gray construction lines, and disciplined luminous accents. This is a visual skin only; it must not change the locked proof object or story.

Forbid: cyberpunk/neon decoration, fake code, meaningless circuit lines, and technical visuals that obscure or rewrite locked content.

### editorial-literary

Use publication-like typography, narrative pacing, elegant whitespace, essay rhythm, quote/image interplay, and strong section moments. Good for reflective, company, brand, strategy, or narrative review decks.

Forbid: magazine prettiness that weakens proof, oversized decorative type in dense business slides, and vague poetic copy.

### luxury-print

Use high-end annual-report print language: crisp rules, refined typography, premium paper-like texture, restrained color accents, and deliberate hierarchy.

Forbid: illegible microtext, decorative print effects that weaken proof, unsupported numbers, and visual density without reader hierarchy.

### animated-illustration

Use polished static illustration language: simplified forms, expressive but controlled figures/objects, motion-frame composition, and vivid accents that remain business-readable.

Forbid: childish cartoons, fake people, mascot-heavy pages, motion instructions, and story changes masquerading as illustration.

### brand-world

Use a strong product/company visual world with verified assets, authentic brand cues, distinctive color/material choices, and content-specific imagery.

Forbid: invented logos, fake product UI, stock-like filler, generic brand mood boards, and brand chrome that violates a supplied template.

## ImageGen Prompting Rules

Prompts should ask for the slide's visual archetype, not only its topic. Name the proof object and the reader takeaway.

For contact sheets, require distinct direction premises and thumbnail-level recognizability.

For single-slide comps, preserve the selected contact sheet's visual system and make the chosen archetype obvious. Do not let the slide become a wireframe or a plain data table unless that is the intentional proof object.

Always request the highest available image detail and a crisp presentation-render look: sharp title edges, clean vector-like icons, clear chart strokes, readable key numbers, high-contrast labels, and no blur/compression artifacts. Do not apply glass blur, glow, depth of field, motion blur, or heavy texture over text, icons, line charts, axes, or small labels.

If a template exists, the prompt must explicitly include the mapped source slide screenshot and protected template elements. Explore inside allowed zones only.

## PPTX Conversion Rules

The comp is a measurement target, not a final slide layer. Rebuild main titles, body text, numbers, footers, page markers, cards, connectors, charts, tables, simple diagrams, and simple geometry as editable/native PPT elements using source-pixel coordinates.

Do not deliver a final slide as only one flat image with no editable main information unless the user explicitly accepts non-editable output. Full-slide or large region image layers are not the conversion path.

Do not replace a rich ImageGen comp with a generic table, card grid, or default layout because it is easier to author. Use `slidelib.py` for native geometry/text and `iconcut3.py` for strict icon extraction. Retain only complex pictograms, photos, official marks, textures, or inseparable art slices as documented image assets.

Every converted output needs a measured build and render-compare evidence: at least 10 real export rounds with distinct render files, paired source/render crops, real region metrics, and a passing `qa_gate.py` audit. If a region diff is over the blocking threshold, fix the slide instead of calling it a font-rendering difference.

## Optional External Taste Inputs

External taste skills may add vocabulary or inspiration, but they are not dependencies. When used:

- Record them in `source_notes.md` and `taste_guidance.sources`.
- Translate them into static PPT rules.
- Ignore web-only rules such as hover, scroll, GSAP, responsive breakpoints, nav patterns, CSS class names, and web-only font constraints.
- Never let them override source truth, a hard template, accessibility, or editability.
