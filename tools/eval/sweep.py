#!/usr/bin/env python3
"""Compare detection thresholds on the tuning seeds (0-9) only."""
from collections import Counter
from pathlib import Path

import numpy as np

from detect_track import CFG, run_seed, score

ROOT = Path('../../data/synth')

for thr in (3.0, 4.5, 6.0):
    cfg = dict(CFG, thr=thr)
    tot = dict(n_gt=0, tp=0, fn=0, fp=0)
    delays, src = [], []
    for seed in range(0, 10):
        gt, tracks, _ = run_seed(seed, ROOT, 'open', cfg)
        s = score(gt, tracks, cfg)
        for k in tot:
            tot[k] += s[k]
        delays += s['delays']
        src += s['fp_src']
    print('thr=%.1f %s delay median %.1f mean %.1f fp_src %s' % (
        thr, tot, np.median(delays), np.mean(delays), dict(Counter(src))))
