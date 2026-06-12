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
6. Select concrete visual style ids from the built-in style library, then generate materially different ImageGen contact-sheet directions.
7. Let the user choose one or multiple style directions unless full automation was explicitly requested.
8. Generate one independent ImageGen comp for every slide in each selected style. Parallelism is allowed across style lanes; each style lane still generates its pages serially to keep chrome consistent.
9. Save raw ImageGen returns, normalize every approved comp to uniform 4K (`3840x2160`) locally, then review and iterate slide comps before PPTX work.
10. Let the user choose one or multiple completed style sets for PPTX conversion.
11. Prepare retained icons as padded transparent PNG assets, reconstruct approved comps as editable PowerPoint slides, and run at least 9 render/compare/fix rounds.
12. Run final council review before export.

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

## Local Codex Sync

Treat this repository as the source of truth. For local development, prefer a symlink so edits in this repo are immediately visible to Codex:

```bash
mkdir -p ~/.codex/skills
ln -sfn "$PWD/imagegen-pptx-pipeline" ~/.codex/skills/imagegen-pptx-pipeline
```

For runtimes that do not support symlinked skills, copy/sync instead:

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
- Style options should use canonical `style_id` values from `imagegen-pptx-pipeline/references/style-library.md`, such as `mckinsey-consulting-report`, `enterprise-annual-report`, `apple-keynote-white`, `notion-workspace-clean`, `swiss-international`, and `classical-european`, instead of vague labels like flat/3D/tech.
- ImageGen prompts request the highest available clarity/detail by default. Raw single-slide comps request true 4K 16:9 (`3840x2160`) first with bounded 2K/1080p fallback; every accepted downstream comp is then normalized locally to uniform 4K before PPTX reconstruction.
- Blurry titles, unreadable key numbers, muddy icons, soft fine lines, low-resolution comps, or compression artifacts are P1 blockers unless the user explicitly accepts the risk.
- Local 4K normalization improves uniform dimensions and edge clarity, but it does not recover unreadable source text or missing icon detail. Visual-clarity review still decides whether to regenerate.
- Retained icons should be processed into transparent PNGs with padding before being placed into PPTX.
- PPTX reconstruction defaults to native trace hybrid fidelity: approved comps are pixel coordinate blueprints, while main visible structure is rebuilt from native PPT text, shapes, connectors, chart primitives, and processed transparent icon assets.
- Full-slide comp backplates are downgrade exceptions, not the default. Use them only when the user explicitly accepts limited editability or when a documented retained-image exception is unavoidable.
- The workflow does not promise that every complex visual becomes native editable PPT geometry; it preserves complex icons, photos, texture, official marks, and hard visual fragments as cropped image layers when that is required for visual fidelity.
- Hidden text boxes, speaker notes, off-canvas text, transparent text, or text placed behind a full-slide image do not count as editable reconstruction.
- For image-to-editable-slide work, `native_trace_hybrid` is the default: the source image becomes a coordinate reference, while major cards, text, arrows, icons, charts, and connectors are rebuilt as native PPT elements and verified by render/fix loops.
- PPTX reconstruction must not downgrade rich comps into generic tables or card grids.
- Final decks must pass at least 9 render/compare/fix rounds against the approved normalized comps.
- Final decks must pass `scripts/audit_pptx_reconstruction.py`, which rejects image-only, image-dominant, or non-native-trace PPTX output.
- Final decks must also pass `scripts/audit_visual_fidelity.py`, which rejects native-heavy rebuilds that no longer visually resemble the approved slide comps. The PASS report must include sha256 bindings for the current source comparison summary and current output PPTX.
- Reconstruction-only uses page-sharded modules: `slide-modules/slide-XXX.pptx` is reviewed before merging into the final deck.
- Every user pause is stateful through `pipeline_state.json`.
