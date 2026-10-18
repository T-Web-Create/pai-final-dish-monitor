#!/usr/bin/env python3
"""Per-seed timeline of plan 6 on lid-on images: first suspicion, first confirmation, final count.
Weekday mapping: t=0 is Fri 09:00. Candidates for the video: suspicion 12-30 h, confirmation 24-60 h, final 10-25."""
import copy
import json
from pathlib import Path

import cv2

from detect_track import CFG, detect, merge_duplicates, update

ROOT = Path('../../data/synth')
PEND_OBS = 2
DAYS = ['Fri', 'Sat', 'Sun', 'Mon']


def clock(t):
    return '%s %02d:00' % (DAYS[(9 + t) // 24], (9 + t) % 24)


print('seed  n_gt  first_suspect  first_confirm  final  confirm_by_day(Sat/Sun/Mon)  cand')
for seed in range(100, 130):
    sdir = ROOT / ('seed_%04d' % seed)
    gt = json.loads((sdir / 'labels.json').read_text())
    ppm = gt['px_per_mm']
    times = gt['times_h']
    ref = cv2.cvtColor(cv2.imread(str(sdir / 'lid' / ('t_%03d.png' % times[0]))), cv2.COLOR_BGR2GRAY)
    tracks, fs, fc, by_t = [], None, None, {}
    for t in times:
        bgr = cv2.imread(str(sdir / 'lid' / ('t_%03d.png' % t)))
        update(tracks, detect(bgr[..., ::-1].copy(), ppm, gt['r_dish_mm'], CFG, ref), t, CFG)
        m = merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])
        n_col = sum(1 for tr in m if tr['status'] == 'colony')
        n_pend = sum(1 for tr in m if tr['status'] == 'new' and len(tr['obs']) >= PEND_OBS)
        by_t[t] = n_col
        if t > 0 and fs is None and n_pend + n_col > 0:
            fs = t
        if t > 0 and fc is None and n_col > 0:
            fc = t
    final = by_t[72]
    cand = fs is not None and fc is not None and 12 <= fs <= 30 and 24 <= fc <= 60 and 10 <= final <= 25
    print('%4d  %4d  %3sh %-9s  %3sh %-9s  %5d  %3d/%3d/%3d  %s' % (
        seed, len(gt['colonies']), fs, clock(fs) if fs else '-', fc, clock(fc) if fc else '-',
        final, by_t[24], by_t[48], by_t[72], '*' if cand else ''))
