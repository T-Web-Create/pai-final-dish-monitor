#!/usr/bin/env python3
"""Scan a raw Gazebo recording (or one image) for desktop intrusions.
Checks per frame: (1) near-white pixels (all channels >= 250), (2) colour tint G-(R+B)/2 versus the
running median (+-0.5 s), (3) change of the right-edge strip (x 1040-1200, never visited by the robot)
versus its median over the recording.
Usage: scan_raw.py VIDEO_OR_PNG [OUT_JSON]"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

src = Path(sys.argv[1])
if src.suffix.lower() == '.png':
    f = cv2.imread(str(src))
    white = int((f.min(axis=2) >= 250).sum())
    tint = float((f[..., 1].astype(np.float32) - (f[..., 0].astype(np.float32) + f[..., 2]) / 2.0).mean())
    print('image %s: near-white pixels %d, tint %.2f' % (src.name, white, tint))
    sys.exit(1 if white > 0 else 0)

cap = cv2.VideoCapture(str(src))
whites, tints, strips = [], [], []
while True:
    ok, f = cap.read()
    if not ok:
        break
    whites.append(int((f.min(axis=2) >= 250).sum()))
    ff = f.astype(np.float32)
    tints.append(float((ff[..., 1] - (ff[..., 0] + ff[..., 2]) / 2.0).mean()))
    strips.append(cv2.resize(f[60:900, 1040:1200], (40, 210)).astype(np.float32))
n = len(tints)
t = np.array(tints)
med = np.array([np.median(t[max(0, i - 15):i + 16]) for i in range(n)])
tdev = np.abs(t - med)
st = np.stack(strips)
sdev = np.abs(st - np.median(st, axis=0)).mean(axis=(1, 2, 3))
bad = sorted({i for i in range(n) if whites[i] > 0 or tdev[i] > 0.8 or sdev[i] > 5})
spans, cur = [], None
for i in bad:
    if cur and i - cur[1] <= 3:
        cur[1] = i
    else:
        cur = [i, i]
        spans.append(cur)
print('frames %d (%.1f s): max white %d, max tint dev %.2f, max strip dev %.2f' % (
    n, n / 30.0, max(whites), float(tdev.max()), float(sdev.max())))
print('intrusion spans: %d' % len(spans))
for a, b in spans:
    print('    %.2f - %.2f s (%d frames): white %d, tint %.2f, strip %.2f' % (
        a / 30.0, b / 30.0, b - a + 1, max(whites[a:b + 1]), float(tdev[a:b + 1].max()),
        float(sdev[a:b + 1].max())))
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(dict(spans=spans)))
