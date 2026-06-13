# -*- coding: utf-8 -*-
"""Mechanical QA gates for slide-image -> editable PPTX.

These gates read REAL data (the actual render, the actual .pptx, the actual render
log). They cannot be satisfied with a hand-written number. Run them and paste their
output verbatim into the final report. If a gate prints FAIL, the work is NOT done.

CLI:
  python qa_gate.py metrics SRC.png RENDER.jpg [--threshold 40] [--regions regions.json]
  python qa_gate.py audit OUT.pptx [--icons icons_manifest.json]
  python qa_gate.py rounds render_log.json
  python qa_gate.py all SRC.png RENDER.jpg OUT.pptx render_log.json icons_manifest.json

Manifests (you author these as you work):
  render_log.json  -> list of rounds, one object each:
    {"round":1,"render":"r1.jpg","timestamp":"2026-06-13T10:00:00",
     "max_metric":52.0,"issues":"band y off","fix":"shift band +14px","recheck":"band 22"}
  icons_manifest.json -> {"extracted":[{"name":"target","box":[x0,y0,x1,y1]}, ...],
                          "exceptions":[{"region":[x0,y0,x1,y1],"why_not_extractable":"...",
                                         "near_text":true,"native_replacement":"oval+free",
                                         "review":"approved"}]}
"""
import os, sys, json, zipfile, io
import numpy as np
from PIL import Image

# XML hardening: prefer defusedxml; otherwise reject any DOCTYPE/ENTITY (PPTX XML
# never legitimately contains one) before handing bytes to the stdlib parser.
# This blocks XXE and billion-laughs without adding a hard dependency.
try:
    from defusedxml.ElementTree import fromstring as _xml_fromstring  # type: ignore
except Exception:
    from xml.etree.ElementTree import fromstring as _stdlib_fromstring

    def _xml_fromstring(data):
        head = (data[:4096] if isinstance(data, bytes) else data[:4096].encode('utf-8', 'ignore')).lower()
        if b'<!doctype' in head or b'<!entity' in head:
            raise ValueError("refusing XML with DOCTYPE/ENTITY (possible XXE/billion-laughs)")
        return _stdlib_fromstring(data)

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'


# ---------- gate 1: real region metrics ----------
def region_metrics(src_png, render_path, regions=None, basis=(1920, 1080)):
    S = Image.open(src_png).convert('RGB').resize(basis)
    R = Image.open(render_path).convert('RGB')
    SC = R.width / basis[0]
    if not regions:
        regions = []
        cols, rows = 6, 4
        for r in range(rows):
            for c in range(cols):
                regions.append((f"r{r}c{c}", c*basis[0]//cols, r*basis[1]//rows,
                                (c+1)*basis[0]//cols, (r+1)*basis[1]//rows))
    out, mx = [], 0.0
    for nm, x0, y0, x1, y1 in regions:
        a = np.asarray(S.crop((x0, y0, x1, y1)).resize((300, 150))).astype(int)
        b = np.asarray(R.crop((int(x0*SC), int(y0*SC), int(x1*SC), int(y1*SC))).resize((300, 150))).astype(int)
        d = float(np.abs(a - b).mean()); out.append((nm, d)); mx = max(mx, d)
    return out, mx


def gate_metrics(src_png, render_path, threshold=40.0, regions=None):
    rows, mx = region_metrics(src_png, render_path, regions)
    print(f"[metrics] REAL max region mean-abs = {mx:.2f}  (threshold {threshold})")
    for nm, d in sorted(rows, key=lambda r: -r[1])[:5]:
        print(f"    worst {nm:10s} {d:.1f}")
    ok = mx < threshold
    print(f"[metrics] {'PASS' if ok else 'FAIL'} — this is the actual computed max; "
          f"no hand-written 'blocking value' may replace it.")
    return ok, mx


# ---------- gate 2: pptx internal media audit ----------
def _slides(z):
    return sorted(n for n in z.namelist()
                  if n.startswith('ppt/slides/slide') and n.endswith('.xml'))


def media_audit(pptx_path, expected_icons=None, fullpage_frac=0.7):
    z = zipfile.ZipFile(pptx_path)
    # slide size in EMU
    pres = _xml_fromstring(z.read('ppt/presentation.xml'))
    sz = pres.find(f'{{{P}}}sldSz')
    sw, sh = int(sz.get('cx')), int(sz.get('cy'))
    media = [n for n in z.namelist() if n.startswith('ppt/media/')]
    pics, texts, fullpage = 0, 0, []
    for sl in _slides(z):
        root = _xml_fromstring(z.read(sl))
        for pic in root.iter(f'{{{P}}}pic'):
            pics += 1
            ext = pic.find(f'.//{{{A}}}ext')
            if ext is not None:
                cx, cy = int(ext.get('cx')), int(ext.get('cy'))
                if cx >= fullpage_frac*sw and cy >= fullpage_frac*sh:
                    fullpage.append((sl, cx/sw, cy/sh))
        texts += sum(1 for t in root.iter(f'{{{A}}}t') if (t.text or '').strip())
    print(f"[media] media files={len(media)}  placed pictures={pics}  text runs={texts}")
    ok = True
    if fullpage:
        ok = False
        for sl, fw, fh in fullpage:
            print(f"    FAIL near-full-page image on {sl}: {fw:.0%}x{fh:.0%} of slide "
                  f"(banned background — Iron Rule 1)")
    if expected_icons is not None:
        if pics != expected_icons:
            ok = False
            print(f"    FAIL picture count {pics} != icon manifest count {expected_icons} "
                  f"(missing/extra/duplicated icon)")
        else:
            print(f"    ok picture count matches manifest ({pics})")
    if texts < 8:
        ok = False
        print(f"    FAIL only {texts} text runs — text was likely rasterized, not native")
    print(f"[media] {'PASS' if ok else 'FAIL'}")
    return ok


# ---------- gate 3: render-log integrity (a round == a new render file) ----------
def check_rounds(log_path, min_rounds=10):
    rounds = json.load(open(log_path))
    errs, seen = [], set()
    for r in rounds:
        f = r.get('render')
        if not f or not os.path.exists(f):
            errs.append(f"round {r.get('round')}: render file missing -> {f}")
        else:
            key = os.path.realpath(f)
            if key in seen:
                errs.append(f"round {r.get('round')}: reuses an earlier render ({f}); "
                            f"a round REQUIRES a new export")
            seen.add(key)
        for k in ('round', 'max_metric', 'issues', 'fix', 'recheck'):
            if k not in r:
                errs.append(f"round {r.get('round')}: missing field '{k}'")
    print(f"[rounds] logged rounds={len(rounds)}  unique render files={len(seen)}  "
          f"required>={min_rounds}")
    for e in errs:
        print("    FAIL", e)
    ok = (not errs) and len(seen) == len(rounds) and len(rounds) >= min_rounds
    print(f"[rounds] {'PASS' if ok else 'FAIL'} — claimed rounds must equal distinct render files.")
    return ok


def _load_icons(path):
    if not path:
        return None
    m = json.load(open(path))
    extracted = m.get('extracted')
    if isinstance(extracted, list):
        return len(extracted)
    icons = m.get('icons')
    if isinstance(icons, list):
        return len(icons)
    return 0


def main(argv):
    if not argv:
        print(__doc__); return 2
    cmd = argv[0]
    if cmd == 'metrics':
        regions = json.load(open(argv[argv.index('--regions')+1])) if '--regions' in argv else None
        th = float(argv[argv.index('--threshold')+1]) if '--threshold' in argv else 40.0
        ok, _ = gate_metrics(argv[1], argv[2], th, regions); return 0 if ok else 1
    if cmd == 'audit':
        exp = _load_icons(argv[argv.index('--icons')+1]) if '--icons' in argv else None
        return 0 if media_audit(argv[1], exp) else 1
    if cmd == 'rounds':
        return 0 if check_rounds(argv[1]) else 1
    if cmd == 'all':
        src, ren, pptx, log = argv[1], argv[2], argv[3], argv[4]
        icons = argv[5] if len(argv) > 5 else None
        g1, _ = gate_metrics(src, ren)
        g2 = media_audit(pptx, _load_icons(icons))
        g3 = check_rounds(log)
        allok = g1 and g2 and g3
        print(f"\n=== OVERALL: {'PASS' if allok else 'FAIL'} ===")
        return 0 if allok else 1
    print(__doc__); return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
