#!/usr/bin/env python3
"""List missed colonies for a condition: colour, size, track status, nearest artifact."""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed

ROOT = Path('../../data/synth')
cond = sys.argv[1] if len(sys.argv) > 1 else 'lid'
miss, total = Counter(), Counter()
for seed in range(0, 10):
    gt, tracks, _ = run_seed(seed, ROOT, cond, CFG)
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    arts = [(c0 + a['x_mm'] * ppm, c0 + a['y_mm'] * ppm, a['type'])
            for a in gt['artifacts'] if 'x_mm' in a and 'y_mm' in a]
    matched = set()
    for tr in tracks:
        if tr['status'] != 'colony':
            continue
        best = None
        for c in gt['colonies']:
            d = float(np.hypot(tr['x'] - (c0 + c['x_mm'] * ppm), tr['y'] - (c0 + c['y_mm'] * ppm)))
            if d <= CFG['gt_match_px'] and (best is None or d < best[0]):
                best = (d, c['id'])
        if best:
            matched.add(best[1])
    for c in gt['colonies']:
        total[c['color']] += 1
        if c['id'] in matched:
            continue
        miss[c['color']] += 1
        cx, cy = c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm
        near = [tr for tr in tracks if np.hypot(tr['x'] - cx, tr['y'] - cy) <= CFG['gt_match_px']]
        tr = max(near, key=lambda t: len(t['obs'])) if near else None
        na = min(((float(np.hypot(cx - ax, cy - ay)), ty) for ax, ay, ty in arts), default=(-1.0, '-'))
        print('seed %d id %2d %-11s appear %5.1fh r_max %.2fmm status=%-8s nobs=%2d nearest_art=%s(%.0fpx)' % (
            seed, c['id'], c['color'], c['appear_h'], c['r_max_mm'],
            tr['status'] if tr else 'no_track', len(tr['obs']) if tr else 0, na[1], na[0]))
print({k: '%d/%d' % (miss[k], total[k]) for k in total})
