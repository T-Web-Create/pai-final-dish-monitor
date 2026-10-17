#!/usr/bin/env python3
"""Median background vs t=0 reference difference, all conditions (tuning seeds 0-9 only)."""
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed, score

ROOT = Path('../../data/synth')
SETTINGS = (('median', False, 4.5), ('diff', True, 3.0), ('diff', True, 4.5), ('diff', True, 6.0))

for cond in ('open', 'lid', 'pol'):
    for name, diff, thr in SETTINGS:
        cfg = dict(CFG, diff_ref=diff, thr=thr)
        tp = fn = fp = dup = 0
        delays = []
        for seed in range(0, 10):
            gt, tracks, _ = run_seed(seed, ROOT, cond, cfg)
            s = score(gt, tracks, cfg)
            tp += s['tp']
            fn += s['fn']
            fp += s['fp']
            dup += s['fp_src'].count('duplicate')
            delays += s['delays']
        print('%-4s %-6s thr %.1f tp %3d fn %3d fp %3d (dup %3d) delay median %.1f' % (
            cond, name, thr, tp, fn, fp, dup, np.median(delays) if delays else float('nan')))
