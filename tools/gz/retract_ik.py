#!/usr/bin/env python3
"""UR3e FK/IK for a new RETRACT pose that keeps the wrist and the held lid out of the fixed camera's view."""
import numpy as np

D = [0.15185, 0.0, 0.0, 0.13105, 0.08535, 0.0921]
A = [0.0, -0.24355, -0.2132, 0.0, 0.0, 0.0]
AL = [np.pi / 2, 0.0, 0.0, np.pi / 2, -np.pi / 2, 0.0]
SUCTION = 0.04
LID_R = 0.048
POSES = {
    'HIGH':    [-0.4521, -0.9476, 0.9829, 1.5355, 1.5708, 1.1187],
    'DOWN':    [-0.4521, -0.6589, 1.3620, 0.8677, 1.5708, 1.1187],
    'LIFT':    [-0.45208, -0.77977, 1.32733, 1.02323, 1.57080, 1.11872],
    'RETRACT': [0.06224, -0.62547, 1.02201, 1.17426, 1.57080, 1.63304],
}
CAM = np.array([0.50, 0.0, 0.30])
PITCH = 0.95
F = (1280 / 2.0) / np.tan(0.35)
FWD = np.array([-np.cos(PITCH), 0.0, -np.sin(PITCH)])
RIGHT = np.array([0.0, 1.0, 0.0])
UP = np.array([-np.sin(PITCH), 0.0, np.cos(PITCH)])


def dh(th, d, a, al):
    ct, st, ca, sa = np.cos(th), np.sin(th), np.cos(al), np.sin(al)
    return np.array([[ct, -st * ca, st * sa, a * ct],
                     [st, ct * ca, -ct * sa, a * st],
                     [0.0, sa, ca, d],
                     [0.0, 0.0, 0.0, 1.0]])


def frames(q, s):
    T = np.diag([s, s, 1.0, 1.0])
    out = [T.copy()]
    for i in range(6):
        T = T @ dh(q[i], D[i], A[i], AL[i])
        out.append(T.copy())
    return out


def contact(T):
    return T[:3, 3] + SUCTION * T[:3, 2]


def visible_count(q, s):
    fr = frames(q, s)
    pts = []
    for i in range(2, 6):
        p0, p1 = fr[i][:3, 3], fr[i + 1][:3, 3]
        for a in np.linspace(0.0, 1.0, 8):
            c = p0 + a * (p1 - p0)
            pts.append(c)
            for v in np.eye(3):
                pts.append(c + 0.045 * v)
                pts.append(c - 0.045 * v)
    c = contact(fr[6])
    for z in (0.0, -0.005):
        for ang in np.linspace(0.0, 2 * np.pi, 16, endpoint=False):
            pts.append(c + np.array([LID_R * np.cos(ang), LID_R * np.sin(ang), z]))
        pts.append(c + np.array([0.0, 0.0, z]))
    n = 0
    for p in pts:
        d = p - CAM
        depth = d @ FWD
        if depth <= 0.05:
            continue
        u = 639.5 + F * (d @ RIGHT) / depth
        v = 479.5 - F * (d @ UP) / depth
        if 0 <= u < 1280 and 0 <= v < 960:
            n += 1
    return n, len(pts)


s = 1.0 if contact(frames(POSES['DOWN'], 1.0)[6])[0] > 0 else -1.0
print('base sign', s)
print('%-8s %-26s %-26s %s' % ('pose', 'tool0 xyz', 'contact xyz', 'visible pts'))
for name, q in POSES.items():
    T = frames(q, s)[6]
    n, tot = visible_count(q, s)
    print('%-8s %-26s %-26s %d/%d' % (name, np.round(T[:3, 3], 3), np.round(contact(T), 3), n, tot))

T_lift = frames(POSES['LIFT'], s)[6]
R_t = T_lift[:3, :3]
p_t = np.array([0.15, 0.12, contact(T_lift)[2] + 0.03])
print('target contact', np.round(p_t, 3))


def err(q):
    T = frames(q, s)[6]
    R = T[:3, :3]
    ep = p_t - contact(T)
    er = 0.5 * sum(np.cross(R[:, k], R_t[:, k]) for k in range(3))
    return np.concatenate([ep, er])


q = np.array(POSES['RETRACT'], float)
for it in range(3000):
    e = err(q)
    if np.linalg.norm(e) < 1e-8:
        break
    J = np.zeros((6, 6))
    for j in range(6):
        dq = np.zeros(6)
        dq[j] = 1e-6
        J[:, j] = (err(q + dq) - e) / 1e-6
    lam = 1e-3
    q = q - J.T @ np.linalg.solve(J @ J.T + lam * lam * np.eye(6), e)
print('IK iterations %d, residual %.2e' % (it, np.linalg.norm(err(q))))
q = (q + np.pi) % (2 * np.pi) - np.pi
print('NEW_RETRACT = [%s]' % ', '.join('%.5f' % v for v in q))
T = frames(q, s)[6]
n, tot = visible_count(q, s)
print('new retract: tool0 %s contact %s visible %d/%d' % (np.round(T[:3, 3], 3), np.round(contact(T), 3), n, tot))

qa = np.array(POSES['LIFT'])
zmin, rmin, vmax = 9.0, 9.0, 0
for a in np.linspace(0.0, 1.0, 41):
    qq = qa + a * (q - qa)
    c = contact(frames(qq, s)[6])
    zmin = min(zmin, c[2])
    rmin = min(rmin, float(np.hypot(c[0], c[1])))
print('path LIFT->NEW: min contact z %.3f, min horizontal distance from base axis %.3f' % (zmin, rmin))
qo = np.array(POSES['RETRACT'])
print('joint change from old RETRACT (rad):', np.round(q - qo, 3))
