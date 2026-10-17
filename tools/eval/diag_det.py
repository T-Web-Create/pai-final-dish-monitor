#!/usr/bin/env python3
"""Why are colonies missed? (1) merge on/off, (2) detection probe at the last time."""
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from detect_track import CFG, detect, merge_duplicates, score, update

ROOT = Path('../../data/synth')
cond = sys.argv[1] if len(sys.argv) > 1 else 'lid'
cfg = CFG


def probe(bgr, gt, c):
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    cx, cy = c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm
    r_true = c['radius_mm_by_time'][-1] * ppm
    gray = cv2.cvtColor(bgr[..., ::-1].copy(), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    bg = cv2.medianBlur(gray, cfg['med_k']).astype(np.float32)
    res = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), cfg['blur_sigma']) - bg
    yy, xx = np.mgrid[0:h, 0:w]
    inside = np.hypot(xx - w / 2.0, yy - h / 2.0) <= (gt['r_dish_mm'] - 1.5) * ppm
    mask = ((np.abs(res) > cfg['thr']) & inside).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    d = np.hypot(xx - cx, yy - cy)
    res_c = float(res[d <= 3.0].mean())
    ring = (d >= r_true - 1.5) & (d <= r_true + 1.5)
    res_e = float(res[ring].mean()) if ring.any() else float('nan')
    disk = d <= max(3.0, r_true + 2.0)
    out = []
    for i in sorted(set(int(v) for v in np.unique(lab[disk]) if v > 0)):
        x0, y0, bw, bh, area = (int(v) for v in stats[i])
        r = float(np.sqrt(area / np.pi)) + 0.5
        aspect = 1.0
        if area >= 3:
            ys, xs = np.nonzero(lab[y0:y0 + bh, x0:x0 + bw] == i)
            ev = np.linalg.eigvalsh(np.cov(np.vstack([xs, ys]).astype(np.float64))) + 1.0 / 12.0
            aspect = float(np.sqrt(ev[1] / ev[0]))
        if area < cfg['min_area']:
            why = 'small'
        elif r > cfg['max_r_mm'] * ppm:
            why = 'big'
        elif aspect > cfg['max_aspect']:
            why = 'aspect'
        else:
            why = 'ok'
        dist = float(np.hypot(cents[i][0] - cx, cents[i][1] - cy))
        out.append((area, r, aspect, why, dist))
    if not out:
        cat = 'no_comp'
    elif any(o[3] == 'ok' and o[4] <= cfg['gt_match_px'] for o in out):
        cat = 'det_ok'
    elif any(o[3] == 'ok' for o in out):
        cat = 'ok_offset'
    elif any(o[3] == 'big' for o in out):
        cat = 'big'
    elif any(o[3] == 'aspect' for o in out):
        cat = 'aspect'
    else:
        cat = 'small'
    return r_true, res_c, res_e, cat, out


fn_on = fn_off = 0
cats = Counter()
for seed in range(0, 10):
    sdir = ROOT / ('seed_%04d' % seed)
    gt = json.loads((sdir / 'labels.json').read_text())
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    tracks = []
    bgr = None
    for t in gt['times_h']:
        bgr = cv2.imread(str(sdir / cond / ('t_%03d.png' % t)))
        update(tracks, detect(bgr[..., ::-1].copy(), ppm, gt['r_dish_mm'], cfg), t, cfg)
    fn_off += score(gt, tracks, cfg)['fn']
    merged = merge_duplicates(tracks)
    fn_on += score(gt, merged, cfg)['fn']
    matched = set()
    for tr in merged:
        if tr['status'] != 'colony':
            continue
        best = None
        for c in gt['colonies']:
            dd = float(np.hypot(tr['x'] - (c0 + c['x_mm'] * ppm), tr['y'] - (c0 + c['y_mm'] * ppm)))
            if dd <= cfg['gt_match_px'] and (best is None or dd < best[0]):
                best = (dd, c['id'])
        if best:
            matched.add(best[1])
    for c in gt['colonies']:
        if c['id'] in matched:
            continue
        r_true, res_c, res_e, cat, out = probe(bgr, gt, c)
        cats[cat] += 1
        comps = ' ; '.join('%s a=%d r=%.1f asp=%.1f d=%.0f' % (o[3], o[0], o[1], o[2], o[4])
                           for o in sorted(out, reverse=True)[:3]) or '-'
        print('seed %d id %2d %-11s r_true %5.1fpx | res_c %+6.1f res_edge %+6.1f | %-9s | %s' % (
            seed, c['id'], c['color'], r_true, res_c, res_e, cat, comps))
print('cond %s: misses with merge %d / without merge %d' % (cond, fn_on, fn_off))
print('categories at last time:', dict(cats))
