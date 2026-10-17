#!/usr/bin/env python3
"""Are reflections static over time? Pixel difference away from colonies, per condition."""
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path('../../data/synth')


def load(sdir, cond, t):
    img = cv2.imread(str(sdir / cond / ('t_%03d.png' % t)))
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)


for cond in ('open', 'lid', 'pol'):
    rows = []
    for seed in range(0, 10):
        sdir = ROOT / ('seed_%04d' % seed)
        gt = json.loads((sdir / 'labels.json').read_text())
        ppm = gt['px_per_mm']
        size = gt['size_px']
        c0 = size / 2.0
        yy, xx = np.mgrid[0:size, 0:size]
        ok = np.hypot(xx - c0, yy - c0) <= (gt['r_dish_mm'] - 1.5) * ppm
        for c in gt['colonies']:
            r = c['radius_mm_by_time'][-1] * ppm + 4.0
            ok &= np.hypot(xx - (c0 + c['x_mm'] * ppm), yy - (c0 + c['y_mm'] * ppm)) > r
        ts = gt['times_h']
        a0, a1, aN = load(sdir, cond, ts[0]), load(sdir, cond, ts[1]), load(sdir, cond, ts[-1])
        d1 = np.abs(a1 - a0)[ok]
        dN = np.abs(aN - a0)[ok]
        rows.append((d1.mean(), np.percentile(d1, 99), dN.mean(), np.percentile(dN, 99)))
    m = np.mean(rows, axis=0)
    print('%-4s |t6-t0| mean %.2f p99 %.2f | |t72-t0| mean %.2f p99 %.2f' % ((cond,) + tuple(m)))
