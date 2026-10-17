#!/usr/bin/env python3
"""Notice analysis for 'suspected' (pending) tracks on lid-on images, held-out seeds 100-129.
A suspicion = track with status 'new' and >= PEND_OBS observations (after duplicate merging).
True suspicion = a colony that has already appeared lies within gt_match_px of the track."""
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
PEND_OBS = 2


def analyse(seed):
    sdir = ROOT / ('seed_%04d' % seed)
    gt = json.loads((sdir / 'labels.json').read_text())
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    cols = [(c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm, c['id'], c['appear_h']) for c in gt['colonies']]
    times = gt['times_h']
    ref = cv2.cvtColor(cv2.imread(str(sdir / COND / ('t_%03d.png' % times[0]))), cv2.COLOR_BGR2GRAY)
    tracks, snaps, pend, last_status, nxt = [], [], {}, {}, 0
    for t in times:
        bgr = cv2.imread(str(sdir / COND / ('t_%03d.png' % t)))
        update(tracks, detect(bgr[..., ::-1].copy(), ppm, gt['r_dish_mm'], CFG, ref), t, CFG)
        for tr in tracks:
            if 'uid' not in tr:
                tr['uid'] = nxt
                nxt += 1
        merged = merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])
        last_status = {tr['uid']: tr['status'] for tr in merged}
        kinds, has_col = set(), False
        for tr in merged:
            is_pend = tr['status'] == 'new' and len(tr['obs']) >= PEND_OBS
            is_col = tr['status'] == 'colony'
            if not (is_pend or is_col):
                continue
            has_col = has_col or is_col
            best = None
            for gx, gy, cid, ah in cols:
                if ah <= t:
                    d = float(np.hypot(tr['x'] - gx, tr['y'] - gy))
                    if d <= CFG['gt_match_px'] and (best is None or d < best[0]):
                        best = (d, cid)
            kind = 'true' if best else 'false'
            kinds.add(kind)
            if is_pend:
                p = pend.setdefault(tr['uid'], dict(t0=t, kind=kind, snaps=0))
                p['snaps'] += 1
        snaps.append(dict(t=t, kinds=kinds, col=has_col))
    first_appear = min(c[3] for c in cols)
    fa = next((s for s in snaps if s['kinds']), None)
    ft = next((s['t'] for s in snaps if 'true' in s['kinds']), None)
    fc = next((s['t'] for s in snaps if s['col']), None)
    out = dict(
        first_any_t=fa['t'] if fa else None,
        first_any_kinds=fa['kinds'] if fa else set(),
        d_any=(fa['t'] - first_appear) if fa else None,
        d_true=(ft - first_appear) if ft is not None else None,
        d_conf=(fc - first_appear) if fc is not None else None,
        n_true=sum(1 for p in pend.values() if p['kind'] == 'true'),
        n_false=sum(1 for p in pend.values() if p['kind'] == 'false'),
        false_before_true=any(p['kind'] == 'false' and (ft is None or p['t0'] < ft) for p in pend.values()),
        fates=[last_status.get(u, 'merged') for u, p in pend.items() if p['kind'] == 'false'],
        dur=[p['snaps'] for p in pend.values() if p['kind'] == 'false'],
    )
    return out


def stat(v):
    v = [x for x in v if x is not None]
    return 'median %.1f mean %.1f min %.1f max %.1f (n=%d)' % (
        np.median(v), np.mean(v), np.min(v), np.max(v), len(v))


R = [analyse(s) for s in SEEDS]
print('cond %s, seeds %d-%d, %d dishes' % (COND, SEEDS[0], SEEDS[-1], len(R)))
print('-- delay from first colony appearing (h), same definitions as policy_sim')
print('first suspicion or confirm (any):    ' + stat([r['d_any'] for r in R]))
print('first confirm:                       ' + stat([r['d_conf'] for r in R]))
print('-- delay counting only suspicions near a TRUE colony')
print('first true suspicion:                ' + stat([r['d_true'] for r in R]))
only_false = sum(1 for r in R if r['first_any_kinds'] == {'false'})
both = sum(1 for r in R if r['first_any_kinds'] == {'false', 'true'})
only_true = sum(1 for r in R if r['first_any_kinds'] == {'true'})
none_ = sum(1 for r in R if not r['first_any_kinds'])
print('-- what was the very first notice? true only %d / false only %d / both %d / none %d' % (
    only_true, only_false, both, none_))
print('dishes with a false suspicion before the first true one: %d / %d' % (
    sum(1 for r in R if r['false_before_true']), len(R)))
print('-- suspicions per dish over 72 h (distinct tracks): true mean %.1f, false mean %.2f (total false %d)' % (
    np.mean([r['n_true'] for r in R]), np.mean([r['n_false'] for r in R]), sum(r['n_false'] for r in R)))
fates = [f for r in R for f in r['fates']]
print('-- fate of false suspicions at the last snapshot: ' + str({k: fates.count(k) for k in sorted(set(fates))}))
dur = [d for r in R for d in r['dur']]
if dur:
    print('snapshots a false suspicion stayed pending (x6 h): median %.1f max %d' % (np.median(dur), max(dur)))
