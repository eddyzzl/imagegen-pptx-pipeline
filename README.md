# ImageGen PPTX Pipeline

An agent skill for producing editable PowerPoint decks from outlines, templates, reference decks, data, and brand assets.

The pipeline uses image generation as the primary visual design engine, then reconstructs approved slide images into editable PPTX slides with hard gates for content, slide intent, narrative, style selection, visual review, and final export.

It can also run in `reconstruction-only` mode when you already have final per-slide images and only want to convert those images into an editable PPTX.

## What It Is For

- Product, company, model or technical, sales, strategy, investor, training, and internal review decks
- Decks that need multiple materially different visual directions before authoring
- Decks that must preserve a supplied PowerPoint template
- Workflows where users may pause to confirm content, page intent, narrative, and visual style
- Agent-assisted review of slide text, color, charts, style, content, and PPTX reconstruction fidelity

## Core Workflow

1. Read the user brief, template, historical decks, sources, and assets.
2. Lock `deck_spec.json` as the content source of truth.
3. Produce `slide_intent_matrix.md` so the user can confirm every slide's title, core idea, proof goal, and evidence strategy.
4. Produce `narrative_matrix.md` so the user can select how each page should present the confirmed content.
5. Ask for or infer the requested number of visual style directions.
6. Generate materially different ImageGen contact-sheet directions.
7. Let the user choose one style direction unless full automation was explicitly requested.
8. Generate one independent ImageGen comp for every slide.
9. Review and iterate slide comps before PPTX work.
10. Reconstruct approved comps as editable PowerPoint slides.
11. Run final council review before export.

For `reconstruction-only`, steps 1-6 are skipped. User-supplied per-slide images are registered as approved comps, then each slide is reconstructed as an independent PPTX module and merged after review.

## Repository Layout

```text
imagegen-pptx-pipeline/
  README.md
  LICENSE
  COMPATIBILITY.md
  CONTRIBUTING.md
  CHANGELOG.md
  SECURITY.md
  imagegen-pptx-pipeline/
    SKILL.md
    agents/openai.yaml
    references/
    scripts/
  examples/
  tests/
```

The installable skill is the inner `imagegen-pptx-pipeline/` directory that contains `SKILL.md`.

## Installation

For Codex-style local skill directories:

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R imagegen-pptx-pipeline "$CODEX_HOME/skills/imagegen-pptx-pipeline"
```

If `CODEX_HOME` is not set, use the skill directory supported by your agent runtime.

## Minimal Usage

```text
Use $imagegen-pptx-pipeline to create a 10-slide product launch deck.

Inputs:
- Brief: ...
- Audience: executive product review
- Template: attached PPTX
- References: attached historical deck
- Style directions: 4

First confirm slide_intent_matrix.md, then narrative_matrix.md, then generate ImageGen style options.
```

## Required Capabilities

The full workflow expects:

- An ImageGen/Image2-style image generation capability for contact sheets and per-slide comps
- A Presentations/PPTX capability for editable slide construction, preview rendering, and export
- Optional subagents for parallel role review

Without those capabilities, the skill can still produce content plans, prompts, schemas, and gate checks, but it cannot complete image generation or PPTX reconstruction end to end. See `COMPATIBILITY.md`.

## Validation

Run the bundled smoke tests:

```bash
python -m unittest discover -s tests
```

Run the gate checker manually:

```bash
python imagegen-pptx-pipeline/scripts/check_pipeline_gates.py \
  --workspace /path/to/workspace \
  --stage slide-intent-lock
```

## Sync To Local Codex

Treat this repository as the source of truth. After editing the skill here, sync the installable skill directory to local Codex:

```bash
tools/sync-to-codex.sh --dry-run
tools/sync-to-codex.sh
```

By default this syncs to `$CODEX_HOME/skills/imagegen-pptx-pipeline` or `~/.codex/skills/imagegen-pptx-pipeline`.

To sync to a custom Codex home:

```bash
tools/sync-to-codex.sh --codex-home /path/to/.codex
```

## Design Principles

- Generated images are visual construction drawings, not the source of truth for text or data.
- Final text and numbers come from `deck_spec.json`.
- User-supplied templates are hard constraints.
- Style options must differ by visual system, not just color.
- PPTX reconstruction defaults to pixel-locked hybrid fidelity: approved comps may be used as full-slide or sliced visual backplates, with editable text/numbers/simple shapes overlaid.
- The workflow does not promise that every complex visual becomes native editable PPT geometry; it preserves complex visuals as image layers when that is required for visual fidelity.
- PPTX reconstruction must not downgrade rich comps into generic tables or card grids.
- Reconstruction-only uses page-sharded modules: `slide-modules/slide-XXX.pptx` is reviewed before merging into the final deck.
- Every user pause is stateful through `pipeline_state.json`.
