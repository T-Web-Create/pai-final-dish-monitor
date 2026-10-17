"""Vision side of the plan-6 patrol: warp the Gazebo camera image to top-down and run the
frozen detector (detect_track.py, an exact copy of tools/eval/detect_track.py) over the lid series."""
import copy

import cv2
import numpy as np

from detect_track import CFG, detect, merge_duplicates, update

CAM = np.array([0.50, 0.0, 0.30])
PITCH, FOV, PX, PPM, N = 0.95, 0.7, 0.30, 6.5, 640
PZ = {'lid': 0.034, 'open': 0.027}
R_DISH_MM = 43.5
PEND_OBS = 2

_f = (1280 / 2.0) / np.tan(FOV / 2.0)
_fwd = np.array([-np.cos(PITCH), 0.0, -np.sin(PITCH)])
_right = np.array([0.0, 1.0, 0.0])
_up = np.array([-np.sin(PITCH), 0.0, np.cos(PITCH)])
_a, _b = np.meshgrid(np.arange(N), np.arange(N))
_c0 = (N - 1) / 2.0
_maps = {}


def _get_maps(cond):
    if cond not in _maps:
        wy = (_a - _c0) / PPM / 1000.0
        wx = PX + (_b - _c0) / PPM / 1000.0
        d = np.stack([wx - CAM[0], wy - CAM[1], np.full_like(wx, PZ[cond] - CAM[2])], axis=-1)
        depth = d @ _fwd
        mx = ((1280 - 1) / 2.0 + _f * (d @ _right) / depth).astype(np.float32)
        my = ((960 - 1) / 2.0 - _f * (d @ _up) / depth).astype(np.float32)
        _maps[cond] = (mx, my)
    return _maps[cond]


def warp(img, cond):
    mx, my = _get_maps(cond)
    return np.ascontiguousarray(np.rot90(cv2.remap(img, mx, my, cv2.INTER_LINEAR), 1))


def lid_state(series):
    """series: list of (t_h, path to warped lid image), sorted by time, starting at t=0."""
    ref = cv2.cvtColor(cv2.imread(series[0][1]), cv2.COLOR_BGR2GRAY)
    tracks = []
    for t, path in series:
        bgr = cv2.imread(path)
        update(tracks, detect(bgr[..., ::-1].copy(), PPM, R_DISH_MM, CFG, ref), t, CFG)
    m = merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])
    n_col = sum(1 for tr in m if tr['status'] == 'colony')
    n_pend = sum(1 for tr in m if tr['status'] == 'new' and len(tr['obs']) >= PEND_OBS)
    return dict(n_col=n_col, n_pend=n_pend)
