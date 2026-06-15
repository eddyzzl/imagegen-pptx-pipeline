# ImageGen PPTX Pipeline

[![CI](https://github.com/eddyzzl/imagegen-pptx-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/eddyzzl/imagegen-pptx-pipeline/actions/workflows/ci.yml)

An agent skill for producing editable PowerPoint decks from outlines, templates, reference decks, data, brand assets, generated slide comps, or user-supplied final slide images.

The pipeline uses ImageGen/Image2 as the visual design engine, then converts approved slide images into faithful editable PPTX with a strict measured converter: `slidelib.py`, `iconcut3.py` with HD icon enhancement, `qa_gate.py`, and at least 10 real render-compare-fix rounds backed by distinct exported render files.

`reconstruction-only` remains a compatibility mode name for direct slide-image conversion. The implementation path is `conversion_manifest.json` plus the strict converter.

## What It Is For

- Product, company, model/technical, sales, strategy, investor, training, and internal review decks
- Decks that need multiple materially different visual directions before authoring
- Decks that must preserve a supplied PowerPoint template
- Workflows where users may pause to confirm content, page intent, narrative, and visual style
- Slide images, screenshots, or mockups that must become faithful editable PPTX
- CJK-heavy slides where text wrapping, icon clipping, and visual drift matter

## Core Workflow

1. Read the user brief, template, historical decks, sources, and assets.
2. Lock `deck_spec.json` as the content source of truth.
3. Confirm each slide's title, core idea, proof goal, and evidence strategy in `slide_intent_matrix.md`.
4. Confirm narrative treatment in `narrative_matrix.md`.
5. Generate materially different ImageGen contact-sheet directions using concrete style IDs from `references/style-library.md`.
6. Let the user choose one or multiple visual directions unless full automation was explicit.
7. Generate one independent high-resolution ImageGen comp for every slide in each selected style.
8. Review comps for content, style continuity, visual clarity, template fidelity, and PPTX feasibility.
9. Lock `visual_contract.json` and `conversion_manifest.json`.
10. Convert slide images into editable PPTX using measured 1920x1080 basis coordinates, strict HD icon extraction/enhancement, native `slidelib.py` shapes/text, and 10+ real render-compare-fix rounds verified by `qa_gate.py`.
11. Run final council review before export.

For direct image conversion, content/narrative/style generation is skipped. User-supplied per-slide images are registered in `conversion_manifest.json` and converted with the same strict converter.

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
    slidelib.py
    iconcut3.py
    qa_gate.py
    PITFALLS.md
    agents/openai.yaml
    references/
    scripts/
  examples/
  tests/
```

The installable skill is the inner `imagegen-pptx-pipeline/` directory.

## Installation

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

Direct image conversion:

```text
Use $imagegen-pptx-pipeline to convert these final slide images into a faithful editable PPTX.
Use strict HD icon extraction and run at least 10 render-compare rounds, each with a new exported render file.
```

## Required Capabilities

The full workflow expects:

- ImageGen/Image2-style image generation for contact sheets and per-slide comps
- Python 3 with `Pillow`, `numpy`, and `python-pptx`
- LibreOffice `soffice`
- Poppler `pdftoppm`
- image viewing for paired crops and icon contact sheets
- optional `markitdown` for text QA
- optional subagents for role review

Without ImageGen, the skill can still run direct slide-image conversion from user-supplied images. Without LibreOffice/Poppler or image viewing, it cannot complete the strict render-compare loop.

## Validation

Run smoke tests:

```bash
python -m unittest discover -s tests
```

Run the gate checker manually:

```bash
python imagegen-pptx-pipeline/scripts/check_pipeline_gates.py \
  --workspace /path/to/workspace \
  --stage before-pptx
```

## Local Codex Sync

Treat this repository as the source of truth. For local development, prefer a symlink:

```bash
mkdir -p ~/.codex/skills
ln -sfn "$PWD/imagegen-pptx-pipeline" ~/.codex/skills/imagegen-pptx-pipeline
```

For runtimes that do not support symlinked skills:

```bash
tools/sync-to-codex.sh --dry-run
tools/sync-to-codex.sh
```

## Design Principles

- Generated images are visual targets, not the source of truth for text or data.
- Final text and numbers come from `deck_spec.json`.
- User-supplied templates are hard constraints.
- Style options must differ by visual system, not just color.
- ImageGen prompts should request crisp text, sharp icons, clean fine lines, and the highest available detail.
- Blurry titles, unreadable key numbers, muddy icons, soft fine lines, or compression artifacts are blockers unless accepted by the user.
- PPTX conversion uses measurement, not eyeballing.
- Full-slide and large region image layers are not the conversion path.
- Text, numbers, labels, cards, lines, charts, arrows, tables, and page chrome should be native editable PowerPoint objects.
- Complex icons are extracted and HD-enhanced with `iconcut3.py`; ClipError means fix the measurement, not bypass the extractor.
- Every extracted icon needs both a 4-edge alpha audit and a visual contact-sheet audit.
- Multi-line CJK text and mixed-size numeric runs should be split into absolute text boxes.
- Final decks require at least 10 render-compare-fix rounds with distinct render files, paired crops, real region metrics, and passing `qa_gate.py` media/round/metric audits.
- Every user pause is stateful through `pipeline_state.json`.
