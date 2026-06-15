# Changelog

## 0.1.0

- Initial open-source package.
- Includes stateful content, slide-intent, narrative, style, comp-review, strict PPTX conversion, and final-review workflow.
- Includes deterministic gate checker and workspace initializer.
- Includes built-in PPT taste guidance so external taste skills are optional.
- Replaces the previous image-to-PPTX implementation with `slidelib.py`, `iconcut3.py`, `qa_gate.py`, `PITFALLS.md`, `conversion_manifest.json`, and 10+ render-compare-fix rounds.
- Adds mechanical anti-fabrication gates for real render metrics, PPTX media/text audit, and distinct render-file round counting.
- Adds automatic HD enhancement for extracted icons, including supersampling/sharpening and feathered-slice alpha preservation.
- Adds GitHub Actions smoke-test CI and public repository metadata.
