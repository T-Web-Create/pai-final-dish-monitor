#!/usr/bin/env python3
"""False suspicions / confirmations on colony-free dishes (seeds 200-229). Frozen detector, plan-6 definitions.
Suspicion = status 'new' with >= PEND_OBS observations; confirmation = status 'colony' (would open the lid)."""
import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from detect_track import CFG, detect, merge_duplicates, update

ROOT = Path('../../data/synth')
COND = sys.argv[1] if len(sys.argv) > 1 else 'lid'
SEEDS = range(200, 230)
PEND_OBS = 2

rows = []
for seed in SEEDS:
    sdir = ROOT / ('seed_%04d' % seed)
    gt = json.loads((sdir / 'labels.json').read_text())
    assert len(gt['colonies']) == 0, seed
    ppm = gt['px_per_mm']
    times = gt['times_h']
    ref = cv2.cvtColor(cv2.imread(str(sdir / COND / ('t_%03d.png' % times[0]))), cv2.COLOR_BGR2GRAY)
    tracks, nxt, pend, first_s, first_c = [], 0, {}, None, None
    for t in times:
        bgr = cv2.imread(str(sdir / COND / ('t_%03d.png' % t)))
        update(tracks, detect(bgr[..., ::-1].copy(), ppm, gt['r_dish_mm'], CFG, ref), t, CFG)
        for tr in tracks:
            if 'uid' not in tr:
                tr['uid'] = nxt
                nxt += 1
        m = merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])
        for tr in m:
            if tr['status'] == 'new' and len(tr['obs']) >= PEND_OBS:
                pend[tr['uid']] = pend.get(tr['uid'], 0) + 1
                first_s = t if first_s is None else first_s
            if tr['status'] == 'colony' and first_c is None:
                first_c = t
    final = {tr['uid']: tr['status'] for tr in merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])}
    rows.append(dict(seed=seed, n_s=len(pend), first_s=first_s, first_c=first_c,
                     dur=list(pend.values()), fate=[final.get(u, 'merged') for u in pend]))

n = len(rows)
print('cond %s, colony-free seeds %d-%d, %d dishes' % (COND, SEEDS[0], SEEDS[-1], n))
print('dishes with >=1 false suspicion: %d / %d' % (sum(1 for r in rows if r['n_s']), n))
print('false suspicions per dish (distinct tracks): mean %.2f max %d' % (
    np.mean([r['n_s'] for r in rows]), max(r['n_s'] for r in rows)))
print('dishes with a false CONFIRM (plan 6 would open the lid): %d / %d' % (
    sum(1 for r in rows if r['first_c'] is not None), n))
fs = [r['first_s'] for r in rows if r['first_s'] is not None]
if fs:
    print('time of first false suspicion (h): median %.1f min %d max %d' % (np.median(fs), min(fs), max(fs)))
dur = [d for r in rows for d in r['dur']]
if dur:
    print('snapshots a false suspicion stayed pending (x6 h): median %.1f max %d' % (np.median(dur), max(dur)))
fate = [f for r in rows for f in r['fate']]
print('fate at 72 h: ' + str({k: fate.count(k) for k in sorted(set(fate))}))
for r in rows:
    if r['n_s'] or r['first_c'] is not None:
        print('  seed %d: suspicions %d, first %s h, confirm %s h, fates %s' % (
            r['seed'], r['n_s'], r['first_s'], r['first_c'], r['fate']))
