#!/usr/bin/env python3
"""Find frames of the raw Gazebo recording with a desktop overlay (sudden colour tint).
Metric per frame: mean of G - (R+B)/2 over the whole frame, compared with the running median (+-0.5 s)."""
import json
from pathlib import Path

import cv2
import numpy as np

VID = Path('/mnt/llm-storage/pai-final/recordings/video')
RAW = VID / 'gazebo_raw_v5.mp4'
FPS = 30.0
TH = 0.8

cap = cv2.VideoCapture(str(RAW))
vals = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    f = f.astype(np.float32)
    vals.append(float((f[..., 1] - (f[..., 0] + f[..., 2]) / 2.0).mean()))
v = np.array(vals)
n = len(v)
med = np.array([np.median(v[max(0, i - 15):i + 16]) for i in range(n)])
dev = v - med
bad = [i for i in range(n) if abs(dev[i]) > TH]
print('frames %d, typical |dev| %.3f, max |dev| %.2f at %.2f s' % (
    n, float(np.median(np.abs(dev))), float(np.abs(dev).max()), int(np.abs(dev).argmax()) / FPS))
spans, cur = [], None
for i in bad:
    if cur and i - cur[1] <= 3:
        cur[1] = i
    else:
        cur = [i, i]
        spans.append(cur)
print('flagged frames %d in %d spans (threshold %.1f):' % (len(bad), len(spans), TH))
for a, b in spans:
    print('    recording %.2f - %.2f s  (%d frames, peak dev %.2f)' % (
        a / FPS, b / FPS, b - a + 1, float(np.abs(dev[a:b + 1]).max())))
full = sorted({i for a, b in spans for i in range(a, b + 1)})
(VID / 'bad_frames.json').write_text(json.dumps(dict(frames=full, spans=spans, threshold=TH)))
print('wrote', VID / 'bad_frames.json')
