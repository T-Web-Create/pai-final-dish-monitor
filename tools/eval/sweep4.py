#!/usr/bin/env python3
"""Merge radius fraction x condition (tuning seeds 0-9 only)."""
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed, score

ROOT = Path('../../data/synth')

for cond in ('open', 'lid', 'pol'):
    for frac in (1.0, 0.5, 0.3, 0.15):
        cfg = dict(CFG, merge_frac=frac)
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
        print('%-4s frac %.2f tp %3d fn %3d fp %3d (dup %3d) delay median %.1f' % (
            cond, frac, tp, fn, fp, dup, np.median(delays) if delays else float('nan')))
