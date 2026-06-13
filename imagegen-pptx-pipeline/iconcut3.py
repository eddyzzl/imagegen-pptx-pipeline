# -*- coding: utf-8 -*-
"""Strict icon extractor v3 — no silent fallback, clear-boundary amputation detection.

Pipeline per user spec:
  1. crop box+pad from HD source (coords in basis px, scale=HD/basis)
  2. remove light background via corner flood fill (BFS, tolerance to local bg)
  3. wipe clear_rects (absolute basis coords)
  4. keep only connected components intersecting the core box
  5. VALIDATE:
     a. kept pixels must not come within EDGE_GAP px of the padded-crop edge
        -> ClipError "enlarge box/pad"
     b. kept pixels must not abut any clear_rect boundary (within EDGE_GAP px)
        -> ClipError "clear_rect amputates icon; move clear or shrink box"
  6. tight-crop to alpha bbox
  7. supersample/sharpen so min(w,h) >= target_min for crisp PPTX placement
  8. pad uniform transparent border
  9. assert all 4 edges have zero non-transparent pixels
No fallback exists. On failure the caller must adjust box/clears and retry.
"""
import numpy as np
from PIL import Image, ImageFilter

EDGE_GAP = 3


class ClipError(Exception):
    pass


def _flood_bg(rgb, tol=42):
    """mask of background pixels reachable from the 4 corners through light/near-uniform colors."""
    h, w, _ = rgb.shape
    bg = np.zeros((h, w), bool)
    # seed: all light pixels on the border
    light = rgb.min(axis=2) > 215
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if light[y, x] and not bg[y, x]:
                bg[y, x] = True
                stack.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if light[y, x] and not bg[y, x]:
                bg[y, x] = True
                stack.append((y, x))
    if not stack:
        return bg
    ref = rgb[bg].mean(axis=0)
    # BFS: expand into pixels close to local neighbour (gradient-tolerant) and lightish
    rgbf = rgb.astype(np.int16)
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx]:
                p = rgbf[ny, nx]
                q = rgbf[y, x]
                if abs(int(p[0]) - int(q[0])) + abs(int(p[1]) - int(q[1])) + abs(int(p[2]) - int(q[2])) <= tol \
                        and p.min() > 170:
                    bg[ny, nx] = True
                    stack.append((ny, nx))
    return bg


def _components(mask):
    """label connected components (4-conn) via BFS; returns label array and count."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    for sy in range(h):
        for sx in range(w):
            if mask[sy, sx] and lab[sy, sx] == 0:
                cur += 1
                stack = [(sy, sx)]
                lab[sy, sx] = cur
                while stack:
                    y, x = stack.pop()
                    if y > 0 and mask[y-1, x] and lab[y-1, x] == 0:
                        lab[y-1, x] = cur; stack.append((y-1, x))
                    if y < h-1 and mask[y+1, x] and lab[y+1, x] == 0:
                        lab[y+1, x] = cur; stack.append((y+1, x))
                    if x > 0 and mask[y, x-1] and lab[y, x-1] == 0:
                        lab[y, x-1] = cur; stack.append((y, x-1))
                    if x < w-1 and mask[y, x+1] and lab[y, x+1] == 0:
                        lab[y, x+1] = cur; stack.append((y, x+1))
    return lab, cur


def enhance_icon(im, target_min=256, sharpen=True, alpha_crisp=True,
                 unsharp=(1.4, 150, 2), max_factor=None):
    """Sharpen / HD-ize a soft extracted icon before it goes into the deck.

    Small icons cut from a screenshot are inherently soft. Supersampling gives
    the PPTX renderer headroom, UnsharpMask restores edge micro-contrast, and
    alpha_crisp steepens the silhouette for strict line-art icons.

    Use alpha_crisp=False for feathered opaque slices; their soft edge hides
    seams and should not be hardened. `max_factor` is optional for callers that
    prefer to fail/re-measure pathological tiny crops instead of fully reaching
    target_min. Returns RGBA with no border added.
    """
    im = im.convert('RGBA')
    r, g, b, a = im.split()
    w, h = im.size
    if min(w, h) < target_min:
        f = target_min / float(min(w, h))
        if max_factor is not None:
            f = min(max_factor, f)
        nw, nh = max(1, round(w * f)), max(1, round(h * f))
        rgb = Image.merge('RGB', (r, g, b)).resize((nw, nh), Image.LANCZOS)
        a = a.resize((nw, nh), Image.LANCZOS)
    else:
        rgb = Image.merge('RGB', (r, g, b))
    if sharpen:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=unsharp[0], percent=unsharp[1],
                                                 threshold=unsharp[2]))
    if alpha_crisp:
        an = np.asarray(a).astype(np.float32) / 255.0
        an = np.clip((an - 0.5) * 1.6 + 0.5, 0.0, 1.0)
        an = np.power(an, 0.7)
        a = Image.fromarray((an * 255.0).astype(np.uint8))
    return Image.merge('RGBA', (*rgb.split(), a))


def strict_cut3(hd, box, out, scale=2.0, pad=16, clear_rects=None, min_dim=110,
                border=10, name='', tol=42, white_min=235,
                sharpen=True, target_min=256, alpha_crisp=True):
    """Extract icon at basis-coord box=(x0,y0,x1,y1) from HD image (scale x basis)."""
    x0, y0, x1, y1 = box
    S = scale
    px0, py0 = int((x0 - pad) * S), int((y0 - pad) * S)
    px1, py1 = int((x1 + pad) * S), int((y1 + pad) * S)
    px0, py0 = max(px0, 0), max(py0, 0)
    px1, py1 = min(px1, hd.width), min(py1, hd.height)
    crop = hd.crop((px0, py0, px1, py1)).convert('RGB')
    rgb = np.asarray(crop)
    h, w, _ = rgb.shape

    bg = _flood_bg(rgb, tol=tol)
    keepable = ~bg
    # also drop near-white leftovers (enclosed light zones barely different)
    keepable &= ~(rgb.min(axis=2) > white_min)

    # clear rects (absolute basis coords) — record their boundaries inside crop
    clear_edges = []  # list of (axis, pos, lo, hi) lines in crop coords
    if clear_rects:
        for cx0, cy0, cx1, cy1 in clear_rects:
            rx0, ry0 = int(cx0 * S) - px0, int(cy0 * S) - py0
            rx1, ry1 = int(cx1 * S) - px0, int(cy1 * S) - py0
            ix0, iy0 = max(rx0, 0), max(ry0, 0)
            ix1, iy1 = min(rx1, w), min(ry1, h)
            if ix0 >= ix1 or iy0 >= iy1:
                continue
            keepable[iy0:iy1, ix0:ix1] = False
            if 0 < rx0 < w:
                clear_edges.append(('v', rx0, iy0, iy1))
            if 0 < rx1 < w:
                clear_edges.append(('v', rx1, iy0, iy1))
            if 0 < ry0 < h:
                clear_edges.append(('h', ry0, ix0, ix1))
            if 0 < ry1 < h:
                clear_edges.append(('h', ry1, ix0, ix1))

    if not keepable.any():
        raise ClipError(f"{name}: empty content; check box {box}")

    lab, n = _components(keepable)
    # core box in crop coords
    cx0, cy0 = int(x0 * S) - px0, int(y0 * S) - py0
    cx1, cy1 = int(x1 * S) - px0, int(y1 * S) - py0
    core = np.zeros((h, w), bool)
    core[max(cy0, 0):min(cy1, h), max(cx0, 0):min(cx1, w)] = True
    keep_ids = np.unique(lab[(lab > 0) & core])
    if len(keep_ids) == 0:
        raise ClipError(f"{name}: no component intersects core box {box}")
    kept = np.isin(lab, keep_ids)

    ys, xs = np.where(kept)
    # 5a: padded-crop edge check
    if ys.min() < EDGE_GAP or xs.min() < EDGE_GAP or ys.max() >= h - EDGE_GAP or xs.max() >= w - EDGE_GAP:
        side = []
        if xs.min() < EDGE_GAP: side.append('left')
        if xs.max() >= w - EDGE_GAP: side.append('right')
        if ys.min() < EDGE_GAP: side.append('top')
        if ys.max() >= h - EDGE_GAP: side.append('bottom')
        raise ClipError(f"{name}: content touches crop edge ({','.join(side)}); enlarge box/pad {box}")
    # 5b: clear-boundary abutment check (amputation guard)
    for axis, pos, lo, hi in clear_edges:
        if axis == 'v':
            for px_ in range(max(pos - EDGE_GAP, 0), min(pos + EDGE_GAP, w)):
                seg = kept[max(lo, 0):min(hi, h), px_]
                if seg.any():
                    raise ClipError(f"{name}: content abuts clear_rect v-edge x={px_/S + px0/S:.0f}; "
                                    f"clear amputates icon — adjust clears/box {box}")
        else:
            for py_ in range(max(pos - EDGE_GAP, 0), min(pos + EDGE_GAP, h)):
                seg = kept[py_, max(lo, 0):min(hi, w)]
                if seg.any():
                    raise ClipError(f"{name}: content abuts clear_rect h-edge y={py_/S + py0/S:.0f}; "
                                    f"clear amputates icon — adjust clears/box {box}")

    # build RGBA
    alpha = np.zeros((h, w), np.uint8)
    alpha[kept] = 255
    rgba = np.dstack([rgb, alpha])
    im = Image.fromarray(rgba, 'RGBA')
    # soften alpha edge 1px
    a = im.getchannel('A').filter(ImageFilter.MaxFilter(3))
    im.putalpha(a)
    bb = im.getchannel('A').getbbox()
    im = im.crop(bb)
    # 7: supersample + sharpen (HD-ize the soft extraction)
    tgt = max(min_dim, target_min) if sharpen else min_dim
    im = enhance_icon(im, target_min=tgt, sharpen=sharpen, alpha_crisp=alpha_crisp)
    # 8: uniform transparent border
    fin = Image.new('RGBA', (im.width + border * 2, im.height + border * 2), (0, 0, 0, 0))
    fin.paste(im, (border, border), im)
    # 9: hard assert edges empty
    fa = np.asarray(fin.getchannel('A'))
    assert fa[0, :].max() == 0 and fa[-1, :].max() == 0 and fa[:, 0].max() == 0 and fa[:, -1].max() == 0, \
        f"{name}: edge pixels present after border pad (bug)"
    fin.save(out)
    return fin.size


def run_jobs(hd, jobs, outdir, scale=2.0, **kw):
    """jobs: {name: (box, clear_rects_or_None, extra_kw_dict_optional)} → returns list of failures."""
    import os
    os.makedirs(outdir, exist_ok=True)
    fails = []
    for nm, spec in jobs.items():
        box, cl = spec[0], spec[1]
        extra = spec[2] if len(spec) > 2 else {}
        out = os.path.join(outdir, nm + '.png')
        if os.path.exists(out):
            continue
        try:
            sz = strict_cut3(hd, box, out, scale=scale, clear_rects=cl, name=nm, **{**kw, **extra})
            w, h = sz
            aspect = max(w, h) / max(min(w, h), 1)
            flag = "  <-- WIDE: probably a TEXT label, eyeball it (pitfall A12)" if aspect > 2.5 else ""
            print(f"  [ok] {nm} {sz} aspect={aspect:.1f}{flag}")
        except ClipError as e:
            fails.append((nm, str(e)))
            print(f"  [FAIL] {e}")
    print("REMINDER: 4-edge audit is NOT enough. Build a contact sheet and confirm every "
          "asset is a pictogram, not boxed text (pitfall A12).")
    return fails


def enhance_dir(outdir, feathered=(), target_min=256, sharpen=True, border=10):
    """Batch-sharpen every PNG in outdir in place before the build.

    Use this to HD-ize icons that were already extracted without re-running
    extraction. Names listed in `feathered` get alpha_crisp=False so seam-hiding
    alpha ramps survive. Re-asserts 4-edge transparency after processing.
    """
    import glob
    import os
    done = []
    for f in sorted(glob.glob(os.path.join(outdir, '*.png'))):
        nm = os.path.splitext(os.path.basename(f))[0]
        im = Image.open(f)
        alpha_crisp = nm not in feathered
        en = enhance_icon(im, target_min=target_min, sharpen=sharpen, alpha_crisp=alpha_crisp)
        fin = Image.new('RGBA', (en.width + border * 2, en.height + border * 2), (0, 0, 0, 0))
        fin.paste(en, (border, border), en)
        fa = np.asarray(fin.getchannel('A'))
        assert fa[0, :].max() == 0 and fa[-1, :].max() == 0 and fa[:, 0].max() == 0 and fa[:, -1].max() == 0, \
            f"{nm}: edge pixels after enhance (bug)"
        fin.save(f)
        mode = 'feathered' if not alpha_crisp else 'crisp'
        done.append((nm, fin.size, mode))
        print(f"  [enhanced] {nm} -> {fin.size} ({mode})")
    return done
