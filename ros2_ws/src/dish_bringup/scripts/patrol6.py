#!/usr/bin/env python3
"""Plan-6 patrol for one observation time T.
Lid-on capture every time -> detector over the lid series -> 'suspected' notice without opening.
The lid is opened only at t=0 (open reference) and at the first confirmation ('confirmed' notice)."""
import json
import os
import re
import sys

import cv2
import rclpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dish_vision import lid_state, warp
from patrol import Patrol

OUT = os.path.expanduser('~/recordings/patrol6')
WARP = os.path.join(OUT, 'warp')
NOTIFY = os.path.expanduser('~/data/notify_log.jsonl')
LOG = os.path.expanduser('~/data/patrol6_log.jsonl')


def sent_kinds():
    if not os.path.exists(NOTIFY):
        return set()
    with open(NOTIFY) as f:
        return {json.loads(line)['kind'] for line in f if line.strip()}


def append(path, rec):
    with open(path, 'a') as f:
        f.write(json.dumps(rec) + '\n')


def lid_series(t_max):
    s = []
    for name in os.listdir(WARP):
        m = re.fullmatch(r'lid_t(\d{3})\.png', name)
        if m and int(m.group(1)) <= t_max:
            s.append((int(m.group(1)), os.path.join(WARP, name)))
    return sorted(s)


def main():
    t = int(sys.argv[1])
    os.makedirs(WARP, exist_ok=True)
    os.makedirs(os.path.dirname(NOTIFY), exist_ok=True)
    rclpy.init()
    node = Patrol()
    node.wait_clock()

    node.create('lid', t, 0.034)
    node.suction('/suction/detach')
    node.move('HIGH', 3.0)
    node.hold(0.5)
    raw = os.path.join(OUT, 'lid_t%03d.png' % t)
    node.grab(raw)
    cv2.imwrite(os.path.join(WARP, 'lid_t%03d.png' % t), warp(cv2.imread(raw), 'lid'))

    st = lid_state(lid_series(t))
    sent = sent_kinds()
    rec = dict(t_h=t, n_pend=st['n_pend'], n_col=st['n_col'], opened=False)
    if t > 0 and st['n_pend'] + st['n_col'] > 0 and 'suspected' not in sent:
        append(NOTIFY, dict(t_h=t, kind='suspected', image=raw, **st))
        print('NOTICE t=%dh suspected (pending %d, confirmed %d)' % (t, st['n_pend'], st['n_col']), flush=True)

    if t == 0 or (st['n_col'] > 0 and 'confirmed' not in sent):
        node.create('open', t, 0.027)
        node.move('DOWN', 3.0)
        t_attach = node.sim
        node.suction('/suction/attach')
        node.hold(0.5)
        node.move('LIFT', 1.5)
        node.remove('plate_lid')
        node.move('RETRACT', 2.0)
        img_open = os.path.join(OUT, 'open_t%03d.png' % t)
        node.grab(img_open)
        node.move('LIFT', 2.0)
        node.move('DOWN', 1.5)
        node.suction('/suction/detach')
        t_detach = node.sim
        node.hold(0.5)
        node.move('HIGH', 3.0)
        rec.update(opened=True, open_time=t_detach - t_attach)
        if t > 0:
            append(NOTIFY, dict(t_h=t, kind='confirmed', image=img_open, **st))
            print('NOTICE t=%dh confirmed (confirmed %d)' % (t, st['n_col']), flush=True)

    node.remove('plate_lid')
    node.remove('plate_open')
    append(LOG, rec)
    print('t=%2dh pending %d confirmed %d opened %s%s' % (
        t, st['n_pend'], st['n_col'], rec['opened'],
        ' open time (sim) %.2f s' % rec['open_time'] if rec['opened'] else ''), flush=True)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
