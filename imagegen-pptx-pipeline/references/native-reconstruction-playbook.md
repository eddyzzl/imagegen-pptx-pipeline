# Native Trace PPTX Reconstruction Playbook

Use this playbook whenever converting a final slide image into editable PPTX. The approved image is a coordinate blueprint, not the final slide layer. The output must visibly resemble the source image while being built from native PowerPoint text, shapes, connectors, chart primitives, and processed transparent icon assets.

## Core Contract

- Do not insert the full source image as the visible final slide by default.
- Do not hide editable text behind the source image, off-canvas, in notes, or with full transparency.
- Rebuild the reader-facing slide structure as native PPT elements: titles, subtitles, labels, body text, key numbers, cards, dividers, circles, arrows, flows, tables, simple charts, page furniture, and connectors.
- Retain images only for complex icons, photos, texture, depth fields, detailed illustrations, official logos, or visual fragments that would degrade if redrawn.
- If the user explicitly accepts a less-editable pixel-locked backplate, record `native_trace_exception.user_accepted_risk=true`; otherwise a full-slide backplate fails the gate.

## Coordinate Method

1. Read the source image dimensions, for example `3840x2160`.
2. Set the PPT canvas to 16:9. For 13.333 x 7.5 in slides, use:
   - `scale_x = 13.333333 / source_width_px`
   - `scale_y = 7.5 / source_height_px`
3. Convert every traced box from pixel coordinates to inches:
   - `x = px_left * scale_x`
   - `y = px_top * scale_y`
   - `w = px_width * scale_x`
   - `h = px_height * scale_y`
4. Record this in `visual_contract.json.slides[].native_trace_plan.pixel_to_inch_mapping_recorded=true`.

## Build Order

1. Create the blank slide at the correct 16:9 size.
2. Rebuild the background with native fills, subtle gradients, ruled lines, or small retained image fragments. Do not place the full source as a base layer.
3. Rebuild page chrome: logo area, section chips, header rules, footer, page number, and recurring markers.
4. Rebuild major layout regions: panels, cards, matrix cells, flow containers, metric groups, diagram zones, timelines, and callout lanes.
5. Rebuild text as native editable text boxes, using the source image only for coordinates and visual hierarchy.
6. Rebuild simple icons natively when practical. Otherwise place processed transparent PNG icon assets at matching coordinates.
7. Rebuild connectors, arrows, loops, radial lines, and chart primitives as native shapes whenever possible.
8. Add retained image fragments only after recording them in the slide QA note.
9. Render, compare, repair, and repeat until the slide passes both visual fidelity and native density gates. A native-heavy slide that visually diverges from the comp still fails.

## Icon Asset Method

1. Identify each reusable or hard-to-draw icon in the source comp.
2. Crop generously around the icon. Include at least one clear padding ring around colored pixels.
3. Use `scripts/prepare_icon_assets.py --strict` to:
   - remove only edge-connected light backgrounds
   - keep connected alpha components that intersect the original icon core
   - trim to content
   - upscale/sharpen small icons
   - add transparent padding
   - fail if colored pixels touch the output edge
4. Insert only processed transparent PNGs into the PPTX.
5. Do not paste white-background icon crops unless the white tile is part of the original design.

## Density Targets

Dense business slides should usually contain dozens to hundreds of native elements. A simple title/thanks page can be lighter, but a normal content slide should not pass with only a full-slide picture plus a handful of text boxes.

The gate defaults are intentionally conservative:

- Content slide: at least 35 native elements, 8 visible editable text shapes, and 60 editable characters.
- Simple first/last slide: at least 10 native elements, 2 visible editable text shapes, and 10 editable characters.
- Large or full-slide raster images: 0 by default.

These are minimums, not a quality target. Rich slides often need far more native objects.

## Visual Fidelity Gate

Native density does not prove visual reconstruction. After rendering the PPTX, compare each preview against the approved comp and run:

```bash
python scripts/audit_visual_fidelity.py \
  --summary qa/manual-visual-diff/visual_diff_summary.json \
  --policy visual_contract.json \
  --output-pptx output/<deck>.pptx \
  --report qa/pptx-visual-fidelity-audit.json
```

The report must be `PASS` before final export. If the rendered PPTX changes the proof-object shape, removes dense diagram structure, shifts page chrome, collapses the page into generic cards/tables, or reads as a different visual system, iterate or block even if `audit_pptx_reconstruction.py` passes.

For multi-style output, audit every produced style lane. A passing audit for one selected lane cannot certify sibling PPTX files.

## Implementation Notes

- Prefer a small local slide-building helper layer with functions for rounded rectangles, circles, lines, arrows, text boxes, icon placement, and freeform paths.
- Use consistent font defaults and explicitly set East Asian fonts for Chinese text when the PPTX library permits it.
- Build one high-complexity calibration slide first, render it, then reuse its font sizes, icon sizes, line widths, card radii, and spacing rules across the remaining deck.
- For generated decks, the same owner should generate all pages within one selected style lane so slide chrome remains consistent.
- For reconstruction-only decks, build one slide module per page under `slide-modules/slide-XXX.pptx`, approve it, then merge modules.

## Required QA

After building PPTX:

1. Render the PPTX using LibreOffice/Presentations + poppler.
2. Compare rendered preview against the approved comp.
3. Fix title wrapping, overflow, missing text, icon clipping, wrong card gaps, wrong page chrome, and geometry drift.
4. Run at least 9 recorded render/compare/fix rounds for the final output style.
5. Run native reconstruction audit:

```bash
python scripts/audit_pptx_reconstruction.py --pptx output/<deck>.pptx --visual-contract visual_contract.json --report qa/pptx-reconstruction-audit.json
```

The report must be `PASS` before final export.
6. Run visual fidelity audit:

```bash
python scripts/audit_visual_fidelity.py --summary qa/manual-visual-diff/visual_diff_summary.json --policy visual_contract.json --output-pptx output/<deck>.pptx --report qa/pptx-visual-fidelity-audit.json
```

The report must also be `PASS` before final export and must bind to the current output PPTX by path and sha256. For multi-style output, pass `--output-pptx` once per final PPTX.
