#!/usr/bin/env python3
"""Compare lid-opening policies with the frozen detector on lid-on images (held-out seeds 100-129).
Opening = taking an open image to attach to the notification. Verification by the open image is NOT modelled.
Policy parameters (PERIOD_H, PEND_OBS) are fixed before looking at results."""
import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from detect_track import CFG, detect, merge_duplicates, update

ROOT = Path('../../data/synth')
COND = sys.argv[1] if len(sys.argv) > 1 else 'lid'
SEEDS = range(100, 130)
OPEN_SEC = 8.92
PERIOD_H = 24
PEND_OBS = 2
POLICIES = ('P0', 'P1', 'P1f', 'P2', 'P3')


def snapshots(seed):
    sdir = ROOT / ('seed_%04d' % seed)
    gt = json.loads((sdir / 'labels.json').read_text())
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    gpos = [(c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm) for c in gt['colonies']]
    times = gt['times_h']
    ref = None
    if CFG['diff_ref']:
        ref = cv2.cvtColor(cv2.imread(str(sdir / COND / ('t_%03d.png' % times[0]))), cv2.COLOR_BGR2GRAY)
    tracks, snaps = [], []
    for t in times:
        bgr = cv2.imread(str(sdir / COND / ('t_%03d.png' % t)))
        update(tracks, detect(bgr[..., ::-1].copy(), ppm, gt['r_dish_mm'], CFG, ref), t, CFG)
        m = merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])
        n_col = sum(1 for tr in m if tr['status'] == 'colony')
        pend = [tr for tr in m if tr['status'] == 'new' and len(tr['obs']) >= PEND_OBS]
        pend_true = sum(1 for tr in pend
                        if any(np.hypot(tr['x'] - gx, tr['y'] - gy) <= CFG['gt_match_px'] for gx, gy in gpos))
        snaps.append(dict(t=t, n_col=n_col, n_pend=len(pend), n_pend_false=len(pend) - pend_true))
    first_true = min(c['appear_h'] for c in gt['colonies']) if gt['colonies'] else None
    return snaps, first_true


def opened_times(name, snaps):
    opened = [snaps[0]['t']]
    prev = snaps[0]['n_col']
    last = snaps[0]['t']
    first_done = prev > 0
    for s in snaps[1:]:
        new = s['n_col'] > prev
        if name == 'P0':
            o = True
        elif name == 'P1':
            o = new
        elif name == 'P1f':
            o = new and not first_done
        elif name == 'P2':
            o = new or s['n_pend'] > 0
        else:
            o = new or s['t'] - last >= PERIOD_H
        if o:
            opened.append(s['t'])
            last = s['t']
        if s['n_col'] > 0:
            first_done = True
        prev = max(prev, s['n_col'])
    return opened


res = {p: dict(opens=[], nonew=[]) for p in POLICIES}
conf_delay, susp_delay, final_cols, susp_false = [], [], 0, 0
for seed in SEEDS:
    snaps, first_true = snapshots(seed)
    final_cols += snaps[-1]['n_col']
    susp_false += sum(s['n_pend_false'] for s in snaps)
    newt = {s['t'] for i, s in enumerate(snaps[1:], 1) if s['n_col'] > max(x['n_col'] for x in snaps[:i])}
    for p in POLICIES:
        op = opened_times(p, snaps)
        res[p]['opens'].append(len(op))
        res[p]['nonew'].append(sum(1 for t in op[1:] if t not in newt))
    if first_true is not None:
        fc = next((s['t'] for s in snaps if s['n_col'] > 0), None)
        fs = next((s['t'] for s in snaps if s['n_col'] > 0 or s['n_pend'] > 0), None)
        if fc is not None:
            conf_delay.append(fc - first_true)
        if fs is not None:
            susp_delay.append(fs - first_true)

print('cond %s, seeds %d-%d, final confirmed colonies (sanity) %d' % (COND, SEEDS[0], SEEDS[-1], final_cols))
print('policy  opens/dish (mean, min-max)  opens w/o new confirm  open time/dish')
for p in POLICIES:
    o = np.array(res[p]['opens'])
    print('%-5s   %5.1f (%2d-%2d)              %5.1f                  %5.0f s' % (
        p, o.mean(), o.min(), o.max(), np.mean(res[p]['nonew']), o.mean() * OPEN_SEC))
print('first-colony notice delay (h): confirmed median %.1f mean %.1f | suspected median %.1f mean %.1f (n=%d)' % (
    np.median(conf_delay), np.mean(conf_delay), np.median(susp_delay), np.mean(susp_delay), len(conf_delay)))
print('pending-track snapshots not near a true colony (all seeds, all times): %d' % susp_false)
