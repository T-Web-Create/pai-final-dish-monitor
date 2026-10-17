#!/usr/bin/env python3
"""Which synthetic image does each patrol capture match? (checks plate switching)"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path('/mnt/llm-storage/pai-final')
T = int(sys.argv[1]) if len(sys.argv) > 1 else 72
SEED = 100
CAM = np.array([0.50, 0.0, 0.30])
PITCH, FOV, PX, PPM, N = 0.95, 0.7, 0.30, 6.5, 640
PZ = {'lid': 0.034, 'open': 0.027}

f = (1280 / 2.0) / np.tan(FOV / 2.0)
fwd = np.array([-np.cos(PITCH), 0.0, -np.sin(PITCH)])
right = np.array([0.0, 1.0, 0.0])
up = np.array([-np.sin(PITCH), 0.0, np.cos(PITCH)])
a, b = np.meshgrid(np.arange(N), np.arange(N))
c0 = (N - 1) / 2.0
mask = np.hypot(a - c0, b - c0) / PPM <= 38.0


def warp(img, pz):
    wy = (a - c0) / PPM / 1000.0
    wx = PX + (b - c0) / PPM / 1000.0
    d = np.stack([wx - CAM[0], wy - CAM[1], np.full_like(wx, pz - CAM[2])], axis=-1)
    depth = d @ fwd
    mx = ((1280 - 1) / 2.0 + f * (d @ right) / depth).astype(np.float32)
    my = ((960 - 1) / 2.0 - f * (d @ up) / depth).astype(np.float32)
    w = np.ascontiguousarray(np.rot90(cv2.remap(img, mx, my, cv2.INTER_LINEAR), 1))
    return cv2.cvtColor(w, cv2.COLOR_BGR2GRAY).astype(np.float32)


def z(g):
    v = g[mask]
    return (v - v.mean()) / (v.std() + 1e-6)


cands = {}
for cond in ('lid', 'open'):
    for t in (0, T):
        img = cv2.imread(str(ROOT / 'data' / 'synth' / ('seed_%04d' % SEED) / cond / ('t_%03d.png' % t)))
        cands['%s_t%03d' % (cond, t)] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
print('%-14s' % 'capture \\ source' + ' '.join('%10s' % k for k in cands))
for cond in ('lid', 'open'):
    cap = cv2.imread(str(ROOT / 'recordings' / 'patrol' / ('%s_t%03d.png' % (cond, T))))
    assert cap is not None, cond
    g = warp(cap, PZ[cond])
    row = {k: float((z(g) * z(v)).mean()) for k, v in cands.items()}
    best = max(row, key=row.get)
    print('%-14s' % ('%s_t%03d' % (cond, T)) + ' '.join('%10.3f' % row[k] for k in cands) + '   best: ' + best)
