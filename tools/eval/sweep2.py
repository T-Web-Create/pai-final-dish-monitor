#!/usr/bin/env python3
"""Compare persistence rules on all three conditions (tuning seeds 0-9 only)."""
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed, score

ROOT = Path('../../data/synth')
CONFIGS = [('base', None, None), ('gap6', 6.0, None), ('mono0.5', None, 0.5),
           ('gap6+mono0.5', 6.0, 0.5), ('gap6+mono1.0', 6.0, 1.0)]

for cond in ('open', 'lid', 'pol'):
    for name, gap, tol in CONFIGS:
        cfg = dict(CFG, max_gap_h=gap, mono_tol=tol)
        tp = fn = fp = 0
        delays = []
        for seed in range(0, 10):
            gt, tracks, _ = run_seed(seed, ROOT, cond, cfg)
            s = score(gt, tracks, cfg)
            tp += s['tp']
            fn += s['fn']
            fp += s['fp']
            delays += s['delays']
        print('%-4s %-13s tp %3d fn %3d fp %3d delay median %.1f' % (
            cond, name, tp, fn, fp, np.median(delays) if delays else float('nan')))
