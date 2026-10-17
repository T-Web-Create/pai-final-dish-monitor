#!/usr/bin/env python3
"""Warp the Gazebo camera image of the textured plate to top-down and compare with the source texture."""
import sys

import cv2
import numpy as np

CAM = np.array([0.50, 0.0, 0.30])
PITCH = 0.95
FOV = 0.7
PLATE = np.array([0.30, 0.0, 0.033])
PPM = 6.5
N = 640

cam_path = sys.argv[1] if len(sys.argv) > 1 else '../../recordings/tex_test.png'
src_path = sys.argv[2] if len(sys.argv) > 2 else '../../data/synth/seed_0000/open/t_072.png'
out_path = sys.argv[3] if len(sys.argv) > 3 else '../../data/eval/warp_check.png'

cam = cv2.imread(cam_path)
src = cv2.imread(src_path)
assert cam is not None and src is not None and src.shape[:2] == (N, N)
h, w = cam.shape[:2]
f = (w / 2.0) / np.tan(FOV / 2.0)
fwd = np.array([-np.cos(PITCH), 0.0, -np.sin(PITCH)])
right = np.array([0.0, 1.0, 0.0])
up = np.array([-np.sin(PITCH), 0.0, np.cos(PITCH)])

a, b = np.meshgrid(np.arange(N), np.arange(N))
c0 = (N - 1) / 2.0
wy = (a - c0) / PPM / 1000.0
wx = PLATE[0] + (b - c0) / PPM / 1000.0
d = np.stack([wx - CAM[0], wy - CAM[1], np.full_like(wx, PLATE[2] - CAM[2])], axis=-1)
depth = d @ fwd
mx = (w - 1) / 2.0 + f * (d @ right) / depth
my = (h - 1) / 2.0 - f * (d @ up) / depth
warped = cv2.remap(cam, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)

warped = np.ascontiguousarray(np.rot90(warped, 1))
wg = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY).astype(np.float32)
mask = np.hypot(a - c0, b - c0) / PPM <= 38.0


def z(img):
    v = img[mask]
    return (v - v.mean()) / (v.std() + 1e-6)


res = []
for flip in (False, True):
    base = src[:, ::-1] if flip else src
    for k in range(4):
        v = np.ascontiguousarray(np.rot90(base, k))
        g = cv2.cvtColor(v, cv2.COLOR_BGR2GRAY).astype(np.float32)
        res.append((float((z(g) * z(wg)).mean()), 'rot%d%s' % (k * 90, '+flip' if flip else ''), v, g))
res.sort(key=lambda r: -r[0])
for r in res:
    print('%-14s corr %+.3f' % (r[1], r[0]))
best = res[0]
print('best:', best[1])
sm, wm = best[3][mask], wg[mask]
print('mean src %.1f warped %.1f ratio %.2f | std src %.1f warped %.1f ratio %.2f' % (
    sm.mean(), wm.mean(), wm.mean() / sm.mean(), sm.std(), wm.std(), wm.std() / sm.std()))
cv2.imwrite(out_path, np.hstack([best[2], warped]))
print('saved', out_path)
