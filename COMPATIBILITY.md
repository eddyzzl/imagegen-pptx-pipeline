# Compatibility

This skill is written for agent runtimes that can:

- Load local skills from a directory containing `SKILL.md`
- Generate images through an ImageGen/Image2-like capability for full deck design
- Run Python 3 with `Pillow`, `numpy`, and `python-pptx`
- Run LibreOffice `soffice`
- Run Poppler `pdftoppm`
- View generated images, paired crops, and icon contact sheets

## Codex

Codex can run the intended workflow when the `imagegen` skill is available and the local runtime has the conversion toolchain.

Expected support:

- Stateful workflow files
- Gate checker scripts
- ImageGen contact-sheet generation
- Per-slide ImageGen comps
- Strict slide-image conversion through `slidelib.py`, HD-enhancing `iconcut3.py`, and `qa_gate.py`
- 4-edge and contact-sheet icon audits
- LibreOffice/Poppler preview rendering
- 10+ render-compare-fix rounds with paired crops, distinct exported render files, and mechanical metric/media/round gates
- Optional multi-agent or role-based review

The Presentations plugin may help with template inspection or preview rendering, but it is not the conversion method for approved slide images.

## Claude Or Other Agents

Other agents can use the planning, schemas, prompts, and gate checker if they provide adapters for:

- image generation
- Python file execution
- PPTX creation through `python-pptx`
- preview rendering through LibreOffice/Poppler or equivalent
- image viewing for paired crops
- subagent orchestration, if parallel review is desired

Recommended adapter contract:

```text
image_adapter.generate(prompt, output_path, aspect_ratio="16:9")
python_adapter.run(script_path, cwd=workspace)
pptx_renderer.render_with_soffice_and_pdftoppm(pptx_path, preview_dir)
review_adapter.view_image(path)
review_adapter.run_roles(stage, artifacts, roles)
```

If no image adapter exists, direct conversion from user-supplied final slide images can still run. If no Python/PPTX/rendering stack exists, stop after `visual_contract.json` and `conversion_manifest.json`.

## Graceful Degradation

The skill should not pretend a complete PPTX was produced when required capabilities are missing.

Allowed partial outputs:

- `deck_spec.json`
- `slide_intent_matrix.md`
- `narrative_matrix.md`
- ImageGen prompts
- `visual_contract.json`
- `conversion_manifest.json`
- QA reports

Blocked outputs:

- Final PPTX export without the strict conversion, real render-compare loop, and `qa_gate.py` mechanical PASS
- Claimed ImageGen comps without real generated images
- Claimed icon success without strict extraction, HD enhancement, and contact-sheet audit
- Claimed review approval without role outputs or documented sequential self-review
