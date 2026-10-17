#!/usr/bin/env python3
"""Warp Gazebo captures to top-down images laid out like data/synth, so detect_track.py runs unchanged.
usage: warp_series.py [SEED] [CAPTURE_DIR] [OUT_ROOT]   (plate height differs per condition)"""
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path('/mnt/llm-storage/pai-final')
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 100
CAP = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'recordings' / 'gz_series'
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / 'data' / 'gz'
CAM = np.array([0.50, 0.0, 0.30])
PITCH, FOV, PX, PPM, N = 0.95, 0.7, 0.30, 6.5, 640
PZ = {'lid': 0.034, 'open': 0.027}

f = (1280 / 2.0) / np.tan(FOV / 2.0)
fwd = np.array([-np.cos(PITCH), 0.0, -np.sin(PITCH)])
right = np.array([0.0, 1.0, 0.0])
up = np.array([-np.sin(PITCH), 0.0, np.cos(PITCH)])
a, b = np.meshgrid(np.arange(N), np.arange(N))
c0 = (N - 1) / 2.0


def maps(pz):
    wy = (a - c0) / PPM / 1000.0
    wx = PX + (b - c0) / PPM / 1000.0
    d = np.stack([wx - CAM[0], wy - CAM[1], np.full_like(wx, pz - CAM[2])], axis=-1)
    depth = d @ fwd
    mx = ((1280 - 1) / 2.0 + f * (d @ right) / depth).astype(np.float32)
    my = ((960 - 1) / 2.0 - f * (d @ up) / depth).astype(np.float32)
    return mx, my


dst = OUT / ('seed_%04d' % SEED)
dst.mkdir(parents=True, exist_ok=True)
shutil.copy(ROOT / 'data' / 'synth' / ('seed_%04d' % SEED) / 'labels.json', dst / 'labels.json')
n = 0
for cond in ('lid', 'open'):
    mx, my = maps(PZ[cond])
    (dst / cond).mkdir(exist_ok=True)
    for t in range(0, 73, 6):
        cam = cv2.imread(str(CAP / ('%s_t%03d.png' % (cond, t))))
        assert cam is not None, (cond, t)
        w = np.ascontiguousarray(np.rot90(cv2.remap(cam, mx, my, cv2.INTER_LINEAR), 1))
        cv2.imwrite(str(dst / cond / ('t_%03d.png' % t)), w)
        n += 1
print('warped', n, 'images ->', dst)
