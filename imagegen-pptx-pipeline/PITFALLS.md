# Trap Catalog — every pitfall hit in production, with the proven fix

All coordinates below are basis-px (1920×1080) unless noted. `hd` = original-resolution image, `scale = hd.width/1920`.

## A. Icon extraction

| # | Trap | Symptom | Fix |
|---|------|---------|-----|
| A1 | Naive bbox crop / manual alpha keying | Half-cropped icons shipped silently (the original client complaint) | Only `iconcut3.strict_cut3` — it raises `ClipError` instead of shipping a clipped icon |
| A2 | Silent fallback extractor | Bad icons pass because a lenient path ran when strict failed | Never add a fallback. On failure, adjust inputs and re-run strict |
| A3 | `clear_rects` amputates the icon, cut edge is transparent so edge-check passes | Icon missing a side, no error | iconcut3's clear-boundary abutment check catches this; if it fires, move the clear or shrink the box — don't delete the check |
| A4 | Dashed ring / surrounding decoration intersects core box | `ClipError: content touches crop edge` repeatedly | **Inscribed core**: shrink core box to sit fully inside the ring; drop clears that don't intersect the core (component-keep handles neighbors) |
| A5 | Adjacent elements anti-aliased together (gap < 3px) | Components merge; impossible to split | Extract the whole row/group as ONE strip asset, place as one pic |
| A6 | Glyph fused with colored background; white details inside solid glyph | Strict cut leaves holes (white details become transparent) or can't separate | **Feathered opaque slice**: `hd.crop(full_bounds)`, 8–12px linear alpha ramp on all 4 edges, native underlay fill = sampled source bg |
| A7 | Opaque slice shows square seam | Visible rectangle around icon | (a) sample the real bg color at flat spots and use it for the native fill underneath (off-by-#05 in one channel is visible); (b) feather edges; (c) slice generous bounds covering the whole decorative circle |
| A8 | Slice cut through the icon's halo/lower half because bbox came from a partial scan window | Badge/circle bottom missing | Measure the FULL element extent with a color mask in a window larger than you think you need; scan windows clip silently — check whether extents hit window edges |
| A9 | Background min-channel exactly at threshold (e.g. 235) keeps giant background components | Huge icon PNG with baked background | `white_min` is a per-job option — lower/raise it per icon |
| A10 | Text glyphs inside extraction box | Icon PNG contains baked label fragments | Column-profile scan to find the true gap between icon and text (icon\|gap\|text), end box before the gap |
| A11 | Re-running jobs doesn't regenerate | Fixed coords but same bad PNG placed | `run_jobs` skips existing files — delete the bad PNG first (by explicit path) |
| A12 | **Box placed on a text label → whole label extracted as a clean "icon"** (a weak model picks the wrong box; e.g. captures a card title "角色定位" instead of the pictogram beside it) | Passes the 4-edge audit, passes ClipError, passes everything — the asset is just *text*. Only a contact-sheet glance catches it | Icon-vs-text audit is **mandatory and separate** from the 4-edge audit. Look at every cell; any Chinese/latin characters = wrong box. Programmatic pre-flag: `aspect=max(w,h)/min(w,h) > 2.5` → probably a text strip (unless it's a deliberate A5 row-strip). The pictogram sits adjacent to the label — re-measure its true box; the label becomes a native text box in Phase 3. This is the #1 way a capable model still ships a wrong deck through this skill |
| A13 | **All-vector redraw — agent skips extraction and draws every icon with native shapes / `slidelib` glyph helpers** (common with vector-loving models like GPT/Codex, which read the bundled `shield()/target()/gear()` as the intended path) | PPTX has zero extracted icon PNGs; icons look like generic geometric approximations, not the source artwork. "Looks editable" but fails 1:1 fidelity = generic deck | EXTRACT is the default (Iron Rule 1b, Phase 2). Native redraw is only for bare primitives (dots/rings/chevrons/checks/bars). The glyph helpers are placeholders, NOT a fidelity path — their docstring says so. A good skill must converge every agent on extraction; if one went all-vector, the extract-vs-redraw rule was too soft (now hardened) |
| A14 | Sharpening a feathered opaque slice with `alpha_crisp=True` | Square seam returns around badges/fused art after HD enhancement | List slice names in `enhance_dir(..., feathered=(...))` or call `enhance_icon(..., alpha_crisp=False)` for those assets; strict transparent line-art icons should keep `alpha_crisp=True` |

## B. Measurement & reading images

| # | Trap | Symptom | Fix |
|---|------|---------|-----|
| B1 | Reading positions from a full-page view | Coords off by 10–40px, systematically | The viewer downsamples; use magnified crops (≤800px) with coordinate gridlines + px labels burnt in |
| B2 | Transcribing text from thumbnails | Wrong characters in near-identical CJK (增强 vs 加强, 主动 vs 业务) | Full-resolution narrow strips per text block; transcribe from those only |
| B3 | Scan window clips the element | Extent reported = window edge; element actually bigger | If `min`/`max` equals the window bound, re-scan with a wider window |
| B4 | Trusting a stale thumbnail of the source | Layout doesn't match scans at all | Regenerate measure copies from the actual source file; verify `src.png` diff ≈ 0 against a fresh resize |
| B5 | Guessing colors | Tinted cards/slices visibly off | Sample pixels at flat spots; for tint fills sample multiple points |
| B6 | Display-scale confusion (thumb px vs basis px) | Whole sections placed at ~73% or ~137% of true position | Convert ONCE: `basis = thumb_coord × (1920 / thumb_width)`; sanity-check against a scan |

## C. python-pptx / slidelib

| # | Trap | Symptom | Fix |
|---|------|---------|-----|
| C1 | `S.oval(..., dash=)` | `TypeError` | `S.shape_(MSO_SHAPE.OVAL, ..., dash='dash')` |
| C2 | `S.free(pts)` for a polyline | Phantom straight line closing the path | `close=False` |
| C3 | Arc angles | Arc sweeps the wrong way | `S.arc`: degrees CCW from +x axis, screen y-down |
| C4 | Gradient stop positions | LibreOffice ignores them; text zone unreadable | Add an opaque underlay rect of the dominant color beneath critical text |
| C5 | Shadow on every autoshape | Render subtly darker than source | slidelib disables `shadow.inherit` everywhere — keep that when extending |
| C6 | `pic()` aspect mismatch | Icon smaller than the box you wrote | `pic` contain-fits and centers; box aspect ≠ image aspect → margins. Use measured aspect |

## D. LibreOffice text rendering

| # | Trap | Symptom | Fix |
|---|------|---------|-----|
| D1 | CJK + `/` or latin runs | Extra spacing, unexpected wrap ("收获 / 总结") | Accept cosmetic spacing, or shrink 0.5pt / widen box; never let it wrap |
| D2 | Mixed-size runs in one box | Wrap exactly at the run boundary ("2.4" \| "万+维") | Separate absolute text boxes per run, positioned by measurement |
| D3 | Multi-line paragraph with `wrap=True` | Line breaks differ from source | One absolute text box per source line, breaks copied from the source image |
| D4 | Vertical CJK labels via line_spacing | Characters drift/cluster | One text box per character at measured pitch (`for k,ch in enumerate("三条主线")`) |
| D5 | Centered text in tight box | Off-center vs source | Make the box symmetric around the measured text center, wider than needed |
| D6 | Font pt from ink height | Sizes ~15% small | CJK: pt ≈ ink_height/1.7; verify with advance: pt ≈ width/(2×nchars) |

## E. Render loop & environment

| # | Trap | Symptom | Fix |
|---|------|---------|-----|
| E1 | `rm p3/dir/*.png` with zsh | `no matches found` aborts the WHOLE command, stale files survive | Delete explicit paths, or `setopt NULL_GLOB`, or `rm -f` each file |
| E2 | Shell cwd resets between tool calls | Scripts read/write wrong dirs | `cd <workspace>` at the start of every command block, or absolute paths |
| E3 | `soffice` conversion silently fails | pdftoppm renders an old PDF | Delete old PDFs first; check the PPTX mtime vs PDF mtime |
| E4 | Comparing at mismatched scales | Everything looks shifted | Render at known width (e.g. `-scale-to-x 2001`), use `SC = render_width / 1920` everywhere |
| E5 | One mega-fix round | Regressions hide among fixes | One cluster of related fixes per round; re-render; metrics before/after |
| E6 | Calling it done at "looks right" | Client finds icon/text defects | Exit criteria: paired crops clean + all region diffs ≤ ~35 + markitdown shows all text + icon audit passes + ≥10 rounds logged |

## F. Region diff calibration (300×150 resized crops, mean abs diff)

- 10–25: excellent match (flat regions, well-aligned)
- 15–35: normal font-rendering delta for text-dense regions — acceptable
- 35–45: suspicious — pull paired crops, usually a sub-element offset or wrong weight/color
- \>45: real defect — missing element, big offset, wrong fill, or wrong text

A metric that "improved only modestly" after a fix usually means a SECOND defect in the same region — keep pulling paired crops until the number lands in band.

## G. QA honesty / anti-fabrication gates (run `qa_gate.py`)

The skill's verification is only worth something if it reads REAL artifacts. Every trap here is a way self-reported QA drifts from reality; every fix is a mechanical gate.

| # | Trap | Symptom | Fix |
|---|------|---------|-----|
| G1 | "Rounds" counted as review notes, not exports | Report says 10 rounds; disk has 4 render files | A round = one new `soffice` export logged in `render_log.json`. `qa_gate.py rounds` fails unless distinct render files == rounds and ≥10 |
| G2 | Gate compares against a hand-written threshold value, not the real metric | Manifest shows `blocking=39.5` next to `actual_max=48.42` and "passes" | `qa_gate.py metrics` recomputes the max from the actual render; the written number is ignored. Keep fixing until the real max < threshold |
| G3 | Full-page or large raster background slips in | Looks 1:1 but it's a picture, not native shapes | `qa_gate.py audit` flags any picture placed at ≥70% slide W and H (EMU from the drawing XML, not pixel size). Hard FAIL |
| G4 | Icon manifest drifts from the actual deck | Manifest lists 15 icons; pptx has 21 pictures (or 9) | media-audit compares `icons_manifest.json` extracted count to real `<p:pic>` count; mismatch = FAIL |
| G5 | Text silently rasterized | Crisp-looking deck, but text isn't editable / not present | media-audit counts `<a:t>` runs; an implausibly low count (<8) FAILs. Also cross-check with `markitdown` |
| G6 | Native-rebuild exceptions undocumented | Can't tell which regions were redrawn vs extracted, or whether reviewed | Every non-extracted region is an `exceptions[]` entry: `region`, `why_not_extractable`, `near_text`, `native_replacement`, `review`. Forces a justification per exception |
| G7 | Final report inflates/omits | User misled by QA numbers | Iron Rule 6: paste `qa_gate.py` output verbatim — real render count, rounds, max metric, media summary, accepted risks |

**XML safety:** `qa_gate.py` parses the pptx XML with defusedxml when available, else rejects any `DOCTYPE`/`ENTITY` before parsing (PPTX never contains one) — blocks XXE / billion-laughs on untrusted decks.
