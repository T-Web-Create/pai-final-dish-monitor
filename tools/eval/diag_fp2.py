#!/usr/bin/env python3
"""For pol false positives with no colony within gt_match_px: nearest true colony."""
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed

ROOT = Path('../../data/synth')
for seed in range(0, 10):
    gt, tracks, _ = run_seed(seed, ROOT, 'pol', CFG)
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    gcol = [(c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm, c) for c in gt['colonies']]
    matched = set()
    for tr in tracks:
        if tr['status'] != 'colony':
            continue
        ds = [(float(np.hypot(tr['x'] - gx, tr['y'] - gy)), c) for gx, gy, c in gcol]
        d0, c0_ = min(ds, key=lambda v: v[0])
        if d0 <= CFG['gt_match_px'] and c0_['id'] not in matched:
            matched.add(c0_['id'])
            continue
        if d0 <= CFG['gt_match_px']:
            continue
        print('seed %d FP x=%.0f y=%.0f last_r=%.1f | nearest colony id %d d=%.1fpx r_true=%.1fpx matched_by_other=%s' % (
            seed, tr['x'], tr['y'], tr['obs'][-1][1], c0_['id'], d0,
            c0_['radius_mm_by_time'][-1] * ppm, c0_['id'] in matched))
