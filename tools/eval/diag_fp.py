#!/usr/bin/env python3
"""List false-positive confirmed tracks with radius history and nearest artifact."""
import sys
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed

ROOT = Path('../../data/synth')
cond = sys.argv[1] if len(sys.argv) > 1 else 'pol'
seeds = [int(s) for s in sys.argv[2:]] or [9, 8]

for seed in seeds:
    gt, tracks, _ = run_seed(seed, ROOT, cond, CFG)
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    gcol = [(c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm, c['id']) for c in gt['colonies']]
    arts = [(c0 + a['x_mm'] * ppm, c0 + a['y_mm'] * ppm, a['type'])
            for a in gt['artifacts'] if 'x_mm' in a and 'y_mm' in a]
    matched = set()
    print('== seed %d cond %s ==' % (seed, cond))
    for tr in tracks:
        if tr['status'] != 'colony':
            continue
        best = None
        for gx, gy, cid in gcol:
            d = float(np.hypot(tr['x'] - gx, tr['y'] - gy))
            if d <= CFG['gt_match_px'] and (best is None or d < best[0]):
                best = (d, cid)
        if best and best[1] not in matched:
            matched.add(best[1])
            continue
        kind = 'duplicate' if best else 'none'
        na = min(((float(np.hypot(tr['x'] - ax, tr['y'] - ay)), ty) for ax, ay, ty in arts),
                 default=(-1.0, '-'))
        rc = float(np.hypot(tr['x'] - c0, tr['y'] - c0)) / ppm
        print('FP %s x=%.0f y=%.0f from_centre=%.1fmm sign=%+d confirm_t=%s nobs=%d nearest_art=%s(%.1fpx)' % (
            kind, tr['x'], tr['y'], rc, tr['sign'], tr['confirm_t'], len(tr['obs']), na[1], na[0]))
        print('    r(px):', ' '.join('%d:%.1f' % (t, r) for t, r in tr['obs']))
