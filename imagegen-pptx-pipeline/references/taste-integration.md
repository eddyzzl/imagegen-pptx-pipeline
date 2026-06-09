# Optional External Taste Integration

Start with `references/taste-system.md`. It is the built-in, required PPT taste baseline for this skill.

Use external taste skills, design documents, or brand-world references only as optional supplements for art direction and QA. The deck pipeline must still work without them, and they must never replace the built-in PPT taste system.

## When To Add External Inputs

- User asks for high-end, premium, polished, not-generic, design-forward, or strong visual taste.
- The task is a product, company, brand, GTM, or executive deck where visual differentiation matters.
- A previous attempt looked like flat tables, equal cards, default templates, or generic consulting slides.

## How To Distill External Guidance

Read only the relevant opening sections of local taste/design skills or supplied design documents. Convert them into portable PPT rules:

- composition variety
- intentional whitespace
- typography hierarchy
- premium but restrained texture/depth
- brand-world coherence
- anti-default patterns
- profile-appropriate density
- thumbnail impact

Ignore or explicitly translate frontend-only rules:

- GSAP, hover physics, scroll interactions, nav bars, breakpoints, CSS class names, web-only font bans, and responsive layout details.
- These may inspire "motion-like flow" or "spatial depth" in static slides, but they are not PPT requirements.

## Supplemental Mapping

- Brand/identity taste skills: use for company-profile, product-pitch, sales-gtm, brand-world, and marketing decks.
- Anti-slop/frontend taste skills: use as anti-generic QA for style options and slide comps.
- High-end visual design skills: use for visual ambition, spacing, hierarchy, depth, and premium restraint.

## Output Fields

Record supplemental guidance in addition to the built-in source:

- `design_system.json.taste_guidance`
- `style_brief.json.taste_guidance`
- `source_notes.md` under taste sources used

Never treat taste guidance as permission to invent sources, replace a hard template, reduce editability, or ignore accessibility.
