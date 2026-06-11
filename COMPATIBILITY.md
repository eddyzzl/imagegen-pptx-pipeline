# Compatibility

This skill is written for agent runtimes that can:

- Load local skills from a directory containing `SKILL.md`
- Generate images through an ImageGen/Image2-like capability
- Build, render, and export PowerPoint files through a Presentations/PPTX capability
- Run Python with Pillow for local 4K comp normalization and transparent icon asset preparation

## Codex

Codex can run the full intended workflow when the `imagegen` skill and `Presentations` plugin are available.

Expected support:

- Stateful workflow files
- Gate checker scripts
- ImageGen contact-sheet generation
- Per-slide ImageGen comps
- Local post-processing of raw ImageGen returns into uniform 4K normalized comps
- Transparent padded icon-asset preparation before PPTX reconstruction
- Presentations-based PPTX reconstruction and preview rendering
- Optional multi-agent or role-based review

## Claude Or Other Agents

Other agents can use the planning, schemas, prompts, and gate checker, but need adapters for:

- Image generation
- PPTX creation
- PPTX preview rendering
- Subagent orchestration, if parallel review is desired

Recommended adapter contract:

```text
image_adapter.generate(prompt, output_path, aspect_ratio="16:9")
pptx_adapter.create_from_visual_contract(workspace, output_path)
pptx_adapter.render_previews(pptx_path, preview_dir)
image_postprocess.normalize_to_4k(raw_path, output_path)
icon_adapter.prepare_transparent_icons(icon_manifest_path)
review_adapter.run_roles(stage, artifacts, roles)
```

If no image adapter exists, stop after producing prompts and `style_brief.json`.

If no PPTX adapter exists, stop after `visual_contract.json` and approved slide comps.

## Graceful Degradation

The skill should not pretend a complete PPTX was produced when required capabilities are missing.

Allowed partial outputs:

- `deck_spec.json`
- `slide_intent_matrix.md`
- `narrative_matrix.md`
- Image generation prompts
- `visual_contract.json`
- QA reports

Blocked outputs:

- Final PPTX export without a PPTX adapter
- Claimed ImageGen comps without real generated images
- Claimed review approval without role outputs or documented sequential self-review
