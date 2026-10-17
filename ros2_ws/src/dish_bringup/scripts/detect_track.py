#!/usr/bin/env python3
"""Detect, track and classify colonies in synthetic dish images; score against ground truth."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

CFG = dict(med_k=41, blur_sigma=1.0, thr=3.0, min_area=5, max_r_mm=5.0, max_aspect=2.0,
           match_px=4.0, grow_ratio=1.2, grow_abs_px=1.0, min_obs=3, static_obs=3,
           gt_match_px=6.0, need_bright=False,
           max_gap_h=6.0, mono_tol=1.0, base_mode='min', merge_frac=1.0, diff_ref=True)


def detect(rgb, ppm, dish_r_mm, cfg, ref=None):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if ref is None:
        bg = cv2.medianBlur(gray, cfg['med_k']).astype(np.float32)
    else:
        bg = cv2.GaussianBlur(ref.astype(np.float32), (0, 0), cfg['blur_sigma'])
    res = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), cfg['blur_sigma']) - bg
    h, w = gray.shape
    yy, xx = np.mgrid[0:h, 0:w]
    inside = np.hypot(xx - w / 2.0, yy - h / 2.0) <= (dish_r_mm - 1.5) * ppm
    mask = ((np.abs(res) > cfg['thr']) & inside).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    dets = []
    for i in range(1, n):
        x0, y0, bw, bh, area = (int(v) for v in stats[i])
        if area < cfg['min_area']:
            continue
        r = float(np.sqrt(area / np.pi)) + 0.5
        if r > cfg['max_r_mm'] * ppm:
            continue
        sub = lab[y0:y0 + bh, x0:x0 + bw] == i
        ys, xs = np.nonzero(sub)
        cov = np.cov(np.vstack([xs, ys]).astype(np.float64))
        ev = np.linalg.eigvalsh(cov) + 1.0 / 12.0
        aspect = float(np.sqrt(ev[1] / ev[0]))
        if aspect > cfg['max_aspect']:
            continue
        sign = 1 if res[y0:y0 + bh, x0:x0 + bw][sub].mean() > 0 else -1
        dets.append(dict(x=float(cents[i][0]), y=float(cents[i][1]), r=r, sign=sign))
    return dets


def sustained(tr, cfg):
    """True if the last min_obs observations are consecutive and non-decreasing (within tolerance)."""
    recent = tr['obs'][-cfg['min_obs']:]
    if cfg['max_gap_h'] is not None:
        ts = [t for t, _ in recent]
        if any(b - a > cfg['max_gap_h'] for a, b in zip(ts, ts[1:])):
            return False
    if cfg['mono_tol'] is not None:
        rr = [r for _, r in recent]
        if any(b < a - cfg['mono_tol'] for a, b in zip(rr, rr[1:])):
            return False
    return True


def baseline(rs, cfg):
    """Reference radius for the growth test."""
    if cfg['base_mode'] == 'min':
        return min(rs[:-1])
    head = sorted(rs[:max(1, len(rs) // 2)])
    return head[(len(head) - 1) // 2]


def classify(tr, cfg):
    if tr['status'] == 'colony':
        return
    rs = [r for _, r in tr['obs']]
    tr['status'] = 'new'
    if len(rs) >= cfg['min_obs'] and (tr['sign'] > 0 or not cfg['need_bright']):
        base = baseline(rs, cfg)
        if (rs[-1] >= cfg['grow_ratio'] * base and rs[-1] - base >= cfg['grow_abs_px']
                and sustained(tr, cfg)):
            tr['status'] = 'colony'
            tr['confirm_t'] = tr['obs'][-1][0]
            return
    if len(rs) >= cfg['static_obs'] and max(rs) - min(rs) < cfg['grow_abs_px']:
        tr['status'] = 'artifact'


def update(tracks, dets, t, cfg):
    cand = []
    for ti, tr in enumerate(tracks):
        for di, d in enumerate(dets):
            dist = float(np.hypot(tr['x'] - d['x'], tr['y'] - d['y']))
            if dist <= cfg['match_px']:
                cand.append((dist, ti, di))
    cand.sort()
    t_used, d_used = set(), set()
    for dist, ti, di in cand:
        if ti in t_used or di in d_used:
            continue
        t_used.add(ti)
        d_used.add(di)
        tr, d = tracks[ti], dets[di]
        tr['obs'].append((t, d['r']))
        tr['x'], tr['y'] = d['x'], d['y']
    for di, d in enumerate(dets):
        if di not in d_used:
            tracks.append(dict(x=d['x'], y=d['y'], sign=d['sign'], obs=[(t, d['r'])],
                               status='new', confirm_t=None))
    for tr in tracks:
        classify(tr, cfg)


def score(gt, tracks, cfg):
    ppm = gt['px_per_mm']
    c0 = gt['size_px'] / 2.0
    gcol = [(c0 + c['x_mm'] * ppm, c0 + c['y_mm'] * ppm, c) for c in gt['colonies']]
    arts = [(c0 + a['x_mm'] * ppm, c0 + a['y_mm'] * ppm, a['type']) for a in gt['artifacts']
            if a['type'] in ('debris', 'bubble', 'reflection_spot')]
    matched = {}
    fp = []
    for tr in tracks:
        if tr['status'] != 'colony':
            continue
        best = None
        for gx, gy, c in gcol:
            d = float(np.hypot(tr['x'] - gx, tr['y'] - gy))
            if d <= cfg['gt_match_px'] and (best is None or d < best[0]):
                best = (d, c['id'], c)
        if best and best[1] not in matched:
            matched[best[1]] = tr['confirm_t'] - best[2]['appear_h']
        elif best:
            fp.append('duplicate')
        else:
            src = 'none'
            for ax, ay, ty in arts:
                if np.hypot(tr['x'] - ax, tr['y'] - ay) <= cfg['gt_match_px']:
                    src = ty
                    break
            fp.append(src)
    missed = [c for _, _, c in gcol if c['id'] not in matched]
    return dict(n_gt=len(gcol), tp=len(matched), fn=len(missed),
                fn_early=sum(1 for c in missed if c['appear_h'] <= 48),
                fp=len(fp), fp_src=fp, delays=list(matched.values()))


def overlay(img, tracks):
    out = img.copy()
    colors = {'colony': (0, 200, 0), 'artifact': (0, 0, 220), 'new': (0, 200, 220)}
    for tr in tracks:
        cv2.circle(out, (int(round(tr['x'])), int(round(tr['y']))),
                   int(round(tr['obs'][-1][1])) + 3, colors[tr['status']], 1, cv2.LINE_AA)
    return out


def merge_duplicates(tracks, frac=1.0):
    """Merge a track into a larger one if its centre lies inside the larger track's circle."""
    def rmax(tr):
        return max(r for _, r in tr['obs'])

    kept = []
    for tr in sorted(tracks, key=rmax, reverse=True):
        host = None
        for k in kept:
            if np.hypot(tr['x'] - k['x'], tr['y'] - k['y']) <= frac * rmax(k):
                host = k
                break
        if host is None:
            kept.append(tr)
        elif tr['status'] == 'colony':
            if host['status'] == 'colony':
                host['confirm_t'] = min(host['confirm_t'], tr['confirm_t'])
            else:
                host['confirm_t'] = tr['confirm_t']
            host['status'] = 'colony'
    return kept


def run_seed(seed, root, cond, cfg):
    sdir = root / ('seed_%04d' % seed)
    gt = json.loads((sdir / 'labels.json').read_text())
    tracks = []
    last = None
    ref = None
    if cfg['diff_ref']:
        ref = cv2.cvtColor(cv2.imread(str(sdir / cond / ('t_%03d.png' % gt['times_h'][0]))),
                           cv2.COLOR_BGR2GRAY)
    for t in gt['times_h']:
        bgr = cv2.imread(str(sdir / cond / ('t_%03d.png' % t)))
        dets = detect(bgr[..., ::-1].copy(), gt['px_per_mm'], gt['r_dish_mm'], cfg, ref)
        update(tracks, dets, t, cfg)
        last = bgr
    tracks = merge_duplicates(tracks, cfg['merge_frac'])
    return gt, tracks, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cond', default='open')
    ap.add_argument('--seed-start', type=int, default=0)
    ap.add_argument('--seed-count', type=int, default=10)
    ap.add_argument('--data', default='../../data/synth')
    ap.add_argument('--out', default='../../data/eval')
    args = ap.parse_args()
    root, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tot = dict(n_gt=0, tp=0, fn=0, fn_early=0, fp=0)
    delays, fp_src = [], []
    print('seed  gt  tp  fn  fn(<=48h)  fp')
    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        gt, tracks, last = run_seed(seed, root, args.cond, CFG)
        s = score(gt, tracks, CFG)
        print('%4d %3d %3d %3d %6d %8d' % (seed, s['n_gt'], s['tp'], s['fn'], s['fn_early'], s['fp']))
        for k in tot:
            tot[k] += s[k]
        delays += s['delays']
        fp_src += s['fp_src']
        if seed == args.seed_start:
            cv2.imwrite(str(out / ('overlay_%s_seed%04d.png' % (args.cond, seed))),
                        overlay(last, tracks))
    print('-' * 40)
    print('total', tot)
    if delays:
        print('delay h: median %.1f, mean %.1f, max %.1f (n=%d)' % (
            np.median(delays), np.mean(delays), np.max(delays), len(delays)))
    print('false positive sources:', {k: fp_src.count(k) for k in sorted(set(fp_src))})


if __name__ == '__main__':
    main()
