#!/usr/bin/env python3
"""For unconfirmed colonies: print track sign and detected vs true radius (px)."""
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed

ROOT = Path('../../data/synth')
SHOW_T = (0, 12, 24, 36, 48, 60, 72)

for seed in range(0, 10):
    gt, tracks, _ = run_seed(seed, ROOT, 'open', CFG)
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    times = gt['times_h']
    matched = set()
    for tr in tracks:
        if tr['status'] != 'colony':
            continue
        best = None
        for c in gt['colonies']:
            d = np.hypot(tr['x'] - (c0 + c['x_mm'] * ppm), tr['y'] - (c0 + c['y_mm'] * ppm))
            if d <= CFG['gt_match_px'] and (best is None or d < best[0]):
                best = (d, c['id'])
        if best:
            matched.add(best[1])
    for c in gt['colonies']:
        if c['id'] in matched:
            continue
        cx, cy = c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm
        near = [tr for tr in tracks if np.hypot(tr['x'] - cx, tr['y'] - cy) <= CFG['gt_match_px']]
        print('seed %d id %d %s appear %.1fh r_max %.2fmm tracks=%d' % (
            seed, c['id'], c['color'], c['appear_h'], c['r_max_mm'], len(near)))
        true = ' '.join('%5.1f' % (c['radius_mm_by_time'][times.index(t)] * ppm) for t in SHOW_T)
        print('    true r(px) at', SHOW_T, ':', true)
        for tr in near:
            od = dict(tr['obs'])
            det = ' '.join(('%5.1f' % od[t]) if t in od else '    -' for t in SHOW_T)
            print('    track sign=%+d status=%s obs=%d det r(px):   %s' % (
                tr['sign'], tr['status'], len(od), det))
