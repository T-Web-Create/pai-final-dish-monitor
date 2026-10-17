#!/usr/bin/env python3
"""Growth baseline x growth amount, all conditions (tuning seeds 0-9 only)."""
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed, score

ROOT = Path('../../data/synth')

for cond in ('open', 'lid', 'pol'):
    for mode in ('min', 'head'):
        for ab in (1.0, 1.5, 2.0):
            cfg = dict(CFG, base_mode=mode, grow_abs_px=ab)
            tp = fn = fp = 0
            delays = []
            for seed in range(0, 10):
                gt, tracks, _ = run_seed(seed, ROOT, cond, cfg)
                s = score(gt, tracks, cfg)
                tp += s['tp']
                fn += s['fn']
                fp += s['fp']
                delays += s['delays']
            print('%-4s %-4s abs%.1f tp %3d fn %3d fp %3d delay median %.1f' % (
                cond, mode, ab, tp, fn, fp, np.median(delays) if delays else float('nan')))
