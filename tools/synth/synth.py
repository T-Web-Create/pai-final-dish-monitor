#!/usr/bin/env python3
"""Synthetic top-down dish images with ground truth (simulated, not real photos)."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

SIZE = 640
CX = CY = SIZE / 2.0
PX_PER_MM = 6.5
R_DISH_MM = 43.5
R_VIS_MM = 0.30
TIMES = list(range(0, 121, 6))

COLORS = {
    'white': ((238, 236, 228), 1.0),
    'cream': ((228, 218, 180), 1.0),
    'translucent': ((205, 205, 180), 0.55),
}
CONDS = {
    'open': dict(glare=0.0, contrast=1.0, noise=2.0),
    'lid': dict(glare=1.0, contrast=0.85, noise=2.5),
    'pol': dict(glare=0.25, contrast=0.93, noise=2.5),
}


def mm2px(x, y):
    return CX + x * PX_PER_MM, CY + y * PX_PER_MM


def logistic(t, r_max, k, t_mid):
    return r_max / (1.0 + np.exp(-k * (t - t_mid)))


def rand_in_dish(rng, margin):
    rad = (R_DISH_MM - margin) * np.sqrt(rng.uniform())
    ang = rng.uniform(0, 2 * np.pi)
    return float(rad * np.cos(ang)), float(rad * np.sin(ang))


def sample_colonies(rng, n):
    cols = []
    for _ in range(4000):
        if len(cols) >= n:
            break
        r_max = float(rng.uniform(0.7, 3.0))
        x, y = rand_in_dish(rng, r_max + 1.0)
        if any(np.hypot(x - c['x_mm'], y - c['y_mm']) < r_max + c['r_max_mm'] + 0.5 for c in cols):
            continue
        k = float(rng.uniform(0.08, 0.20))
        t_mid = float(rng.uniform(20, 90))
        appear = t_mid - np.log(r_max / R_VIS_MM - 1.0) / k
        if not 6.0 <= appear <= 100.0:
            continue
        cols.append(dict(id=len(cols), x_mm=x, y_mm=y, r_max_mm=r_max, k_per_h=k,
                         t_mid_h=t_mid, color=str(rng.choice(list(COLORS), p=[0.4, 0.4, 0.2])),
                         appear_h=float(appear)))
    return cols


def sample_artifacts(rng):
    arts = []
    gx, gy = (float(v) for v in rng.uniform(-18, 18, 2))
    arts.append(dict(type='glare', x_mm=gx, y_mm=gy, w_mm=float(rng.uniform(15, 30)),
                     h_mm=float(rng.uniform(10, 22)), angle_deg=float(rng.uniform(0, 180))))
    a0 = float(rng.uniform(0, 360))
    arts.append(dict(type='rim_glare', start_deg=a0, end_deg=a0 + float(rng.uniform(40, 90))))
    for _ in range(int(rng.integers(2, 6))):
        sx, sy = gx + float(rng.uniform(-8, 8)), gy + float(rng.uniform(-6, 6))
        if np.hypot(sx, sy) > R_DISH_MM - 1.0:
            continue
        arts.append(dict(type='reflection_spot', x_mm=sx, y_mm=sy, r_mm=float(rng.uniform(0.3, 0.6))))
    for _ in range(int(rng.integers(3, 9))):
        x, y = rand_in_dish(rng, 2.0)
        arts.append(dict(type='debris', x_mm=x, y_mm=y, r_mm=float(rng.uniform(0.2, 0.5))))
    for _ in range(int(rng.integers(2, 7))):
        x, y = rand_in_dish(rng, 3.0)
        arts.append(dict(type='bubble', x_mm=x, y_mm=y, r_mm=float(rng.uniform(0.5, 1.4))))
    for _ in range(int(rng.integers(0, 3))):
        x, y = rand_in_dish(rng, 15.0)
        pts = [[x, y]]
        ang = float(rng.uniform(0, 2 * np.pi))
        for _ in range(int(rng.integers(5, 10))):
            ang += float(rng.normal(0, 0.6))
            x += 2.0 * float(np.cos(ang))
            y += 2.0 * float(np.sin(ang))
            pts.append([x, y])
        arts.append(dict(type='stroke', points_mm=pts))
    return arts


def make_base(seed):
    rng = np.random.default_rng(seed + 10_000_000)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    d = np.hypot(xx - CX, yy - CY)
    low = cv2.GaussianBlur(rng.normal(0, 1, (SIZE, SIZE)).astype(np.float32), (0, 0), 40)
    low = low / (low.std() + 1e-6) * 5.0
    vign = 1.0 - 0.12 * np.clip(d / (R_DISH_MM * PX_PER_MM), 0, 1) ** 3
    agar = np.array([190, 182, 140], np.float32)
    img = np.full((SIZE, SIZE, 3), 30.0, np.float32)
    inside = d <= R_DISH_MM * PX_PER_MM
    img[inside] = agar * vign[inside, None] + low[inside, None]
    rim = np.clip(1.0 - np.abs(d - (R_DISH_MM + 1.6) * PX_PER_MM) / (1.2 * PX_PER_MM), 0, 1)
    img = img * (1 - 0.5 * rim[..., None]) + 75.0 * rim[..., None]
    return img


def draw_disc(img, cx, cy, r, color, alpha, ring=0.0, shade=True):
    if r < 0.3:
        return
    x0, x1 = int(max(cx - r - 3, 0)), int(min(cx + r + 4, SIZE))
    y0, y1 = int(max(cy - r - 3, 0)), int(min(cy + r + 4, SIZE))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.hypot(xx - cx, yy - cy)
    a = np.clip(r - d + 0.5, 0, 1) * alpha
    s = np.ones_like(d)
    if shade:
        hl = np.clip(1 - np.hypot(xx - (cx - 0.3 * r), yy - (cy - 0.3 * r)) / (0.6 * r), 0, 1)
        s = 1.0 - 0.18 * np.clip(d / r, 0, 1) ** 2 + 0.10 * hl
    if ring > 0:
        a = np.maximum(a, np.clip(1 - np.abs(d - r), 0, 1) * ring)
    rgb = np.array(color, np.float32)[None, None, :] * s[..., None]
    reg = img[y0:y1, x0:x1]
    img[y0:y1, x0:x1] = reg * (1 - a[..., None]) + rgb * a[..., None]


def render(base, scene, t, cond, nrng):
    cfg = CONDS[cond]
    img = base.copy()
    for c in scene['colonies']:
        r = logistic(t, c['r_max_mm'], c['k_per_h'], c['t_mid_h']) * PX_PER_MM
        col, al = COLORS[c['color']]
        draw_disc(img, *mm2px(c['x_mm'], c['y_mm']), r, col, al)
    for a in scene['artifacts']:
        if a['type'] == 'debris':
            draw_disc(img, *mm2px(a['x_mm'], a['y_mm']), a['r_mm'] * PX_PER_MM, (90, 90, 85), 0.8)
        elif a['type'] == 'bubble':
            draw_disc(img, *mm2px(a['x_mm'], a['y_mm']), a['r_mm'] * PX_PER_MM,
                      (235, 232, 215), 0.3, ring=0.6, shade=False)
        elif a['type'] == 'stroke':
            mask = np.zeros((SIZE, SIZE), np.uint8)
            pts = np.array([mm2px(x, y) for x, y in a['points_mm']], np.float32)
            cv2.polylines(mask, [np.round(pts).astype(np.int32)], False, 255, 1, cv2.LINE_AA)
            m = (mask.astype(np.float32) / 255.0 * 0.3)[..., None]
            img = img * (1 - m) + np.array([70, 70, 60], np.float32) * m
    s = cfg['glare']
    if s > 0:
        yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
        lid_mask = (np.hypot(xx - CX, yy - CY) <= (R_DISH_MM + 2.5) * PX_PER_MM).astype(np.float32)
        rect_layer = np.zeros((SIZE, SIZE), np.float32)
        rim_layer = np.zeros((SIZE, SIZE), np.float32)
        for a in scene['artifacts']:
            if a['type'] == 'glare':
                rect = (mm2px(a['x_mm'], a['y_mm']),
                        (a['w_mm'] * PX_PER_MM, a['h_mm'] * PX_PER_MM), a['angle_deg'])
                cv2.fillConvexPoly(rect_layer, cv2.boxPoints(rect).astype(np.int32), 55.0)
            elif a['type'] == 'rim_glare':
                tmp = np.zeros((SIZE, SIZE), np.uint8)
                axes = (int((R_DISH_MM + 1.0) * PX_PER_MM),) * 2
                cv2.ellipse(tmp, (int(CX), int(CY)), axes, 0, a['start_deg'], a['end_deg'], 255, 5)
                rim_layer += cv2.GaussianBlur(tmp.astype(np.float32) / 255.0 * 45.0, (0, 0), 3)
        rect_layer = cv2.GaussianBlur(rect_layer, (0, 0), 6)
        img = img + (rect_layer + rim_layer)[..., None] * s * lid_mask[..., None]
        for a in scene['artifacts']:
            if a['type'] == 'reflection_spot':
                draw_disc(img, *mm2px(a['x_mm'], a['y_mm']), a['r_mm'] * PX_PER_MM,
                          (245, 245, 240), min(1.0, 0.9 * s))
    img = 150.0 + (img - 150.0) * cfg['contrast']
    img = img + nrng.normal(0, cfg['noise'], img.shape).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed-start', type=int, default=0)
    ap.add_argument('--seed-count', type=int, default=1)
    ap.add_argument('--out', default='../../data/synth')
    args = ap.parse_args()
    out = Path(args.out)
    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        rng = np.random.default_rng(seed)
        scene = dict(seed=seed, times_h=TIMES, px_per_mm=PX_PER_MM, size_px=SIZE,
                     r_dish_mm=R_DISH_MM, r_vis_mm=R_VIS_MM,
                     colonies=sample_colonies(rng, int(rng.integers(3, 41))))
        scene['artifacts'] = sample_artifacts(rng)
        for c in scene['colonies']:
            c['radius_mm_by_time'] = [float(logistic(t, c['r_max_mm'], c['k_per_h'], c['t_mid_h']))
                                      for t in TIMES]
        base = make_base(seed)
        sdir = out / ('seed_%04d' % seed)
        for ci, cond in enumerate(CONDS):
            (sdir / cond).mkdir(parents=True, exist_ok=True)
            for ti, t in enumerate(TIMES):
                img = render(base, scene, t, cond, np.random.default_rng((seed, ci, ti)))
                cv2.imwrite(str(sdir / cond / ('t_%03d.png' % t)), img[..., ::-1])
        with open(sdir / 'labels.json', 'w') as f:
            json.dump(scene, f, indent=1)
        rows = []
        for cond in CONDS:
            cells = []
            for t in (0, 48, 96, 120):
                im = cv2.imread(str(sdir / cond / ('t_%03d.png' % t)))
                im = cv2.resize(im, (320, 320))
                cv2.putText(im, '%s t=%dh' % (cond, t), (8, 22), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 1, cv2.LINE_AA)
                cells.append(im)
            rows.append(np.hstack(cells))
        cv2.imwrite(str(sdir / 'preview.png'), np.vstack(rows))
        print('seed', seed, 'colonies', len(scene['colonies']))


if __name__ == '__main__':
    main()
