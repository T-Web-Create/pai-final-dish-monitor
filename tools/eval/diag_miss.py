#!/usr/bin/env python3
"""List colonies that were not confirmed, with possible reasons."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed

ROOT = Path('../../data/synth')
rows = []
all_colors = Counter()

for seed in range(0, 10):
    gt, tracks, _ = run_seed(seed, ROOT, 'open', CFG)
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    for c in gt['colonies']:
        all_colors[c['color']] += 1
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
        near = None
        for tr in tracks:
            d = np.hypot(tr['x'] - cx, tr['y'] - cy)
            if d <= CFG['gt_match_px'] and (near is None or d < near[0]):
                near = (d, tr)
        gaps = [np.hypot(c['x_mm'] - o['x_mm'], c['y_mm'] - o['y_mm']) - c['r_max_mm'] - o['r_max_mm']
                for o in gt['colonies'] if o['id'] != c['id']]
        rows.append(dict(seed=seed, id=c['id'], color=c['color'], r_max=c['r_max_mm'],
                         appear=c['appear_h'], r72=c['radius_mm_by_time'][-1],
                         status=near[1]['status'] if near else 'no_track',
                         nobs=len(near[1]['obs']) if near else 0,
                         gap=min(gaps) if gaps else 99.0))

print('seed id color        r_max appear  r72  status    nobs  gap_mm')
for r in rows:
    print('%4d %2d %-11s %5.2f %6.1f %5.2f  %-9s %3d  %6.2f' % (
        r['seed'], r['id'], r['color'], r['r_max'], r['appear'], r['r72'],
        r['status'], r['nobs'], r['gap']))
print()
miss_colors = Counter(r['color'] for r in rows)
for k in all_colors:
    print('%-11s missed %d / %d' % (k, miss_colors[k], all_colors[k]))
print('status of missed:', dict(Counter(r['status'] for r in rows)))
