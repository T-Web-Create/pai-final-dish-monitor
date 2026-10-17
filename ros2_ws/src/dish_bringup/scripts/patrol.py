#!/usr/bin/env python3
"""Patrol: per observation time T, capture the lid-on image, open the lid with suction,
capture the open image, close. Both image plates are pre-placed so that only one
service call (removing the lid plate) happens inside the open window."""
import json
import os
import signal
import subprocess
import sys
import time

import cv2
import numpy as np
import rclpy
from sensor_msgs.msg import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lid_cycle import LidCycle

MODELS = os.path.expanduser('~/ros2_ws/src/dish_description/models')
OUT = os.path.expanduser('~/recordings/patrol')


def run_group(cmd, timeout):
    """Run cmd in its own process group; kill the whole group on timeout. Returns exit code or None."""
    pr = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          start_new_session=True)
    try:
        return pr.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(pr.pid, signal.SIGKILL)
        pr.wait()
        return None


class Patrol(LidCycle):
    def __init__(self):
        super().__init__()
        self.last = None
        self.create_subscription(Image, '/dish_camera/image', self._on_img, 10)

    def _on_img(self, msg):
        self.last = msg

    def remove(self, name):
        subprocess.run(['gz', 'service', '-s', '/world/empty/remove', '--reqtype', 'gz.msgs.Entity',
                        '--reptype', 'gz.msgs.Boolean', '--timeout', '2000', '--req',
                        'name: "%s" type: MODEL' % name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def create(self, cond, t, z):
        name = 'plate_' + cond
        model = os.path.join(MODELS, 'img_%s_t%03d' % (cond, t), 'model.sdf')
        for attempt in range(3):
            self.remove(name)
            time.sleep(0.5)
            rc = run_group(['ros2', 'run', 'ros_gz_sim', 'create', '-file', model, '-name', name,
                            '-x', '0.30', '-y', '0.0', '-z', str(z)], 20)
            if rc == 0:
                return
            print('create %s failed (rc=%s), retry %d' % (name, rc, attempt + 1), flush=True)
        raise RuntimeError('create failed: ' + name)

    def grab(self, path, settle=0.6):
        after = self.sim + settle
        t0 = time.time()
        while True:
            rclpy.spin_once(self, timeout_sec=0.05)
            m = self.last
            if m is not None and m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 > after:
                break
            if time.time() - t0 > 15:
                raise RuntimeError('no fresh frame for ' + path)
        img = np.frombuffer(m.data, dtype=np.uint8).reshape(m.height, m.width, 3)
        cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    def observe(self, t):
        os.makedirs(OUT, exist_ok=True)
        self.create('open', t, 0.027)
        self.create('lid', t, 0.034)
        self.suction('/suction/detach')
        self.move('HIGH', 3.0)
        self.hold(0.5)
        self.grab(os.path.join(OUT, 'lid_t%03d.png' % t))
        self.move('DOWN', 3.0)
        t_attach = self.sim
        self.suction('/suction/attach')
        self.hold(0.5)
        self.move('LIFT', 1.5)
        self.remove('plate_lid')
        self.move('RETRACT', 2.0)
        self.grab(os.path.join(OUT, 'open_t%03d.png' % t))
        self.move('LIFT', 2.0)
        self.move('DOWN', 1.5)
        self.suction('/suction/detach')
        t_detach = self.sim
        self.hold(0.5)
        self.move('HIGH', 3.0)
        self.remove('plate_open')
        self.remove('plate_lid')
        return t_attach, t_detach


def main():
    times = [int(a) for a in sys.argv[1:]] or list(range(0, 73, 6))
    rclpy.init()
    node = Patrol()
    node.wait_clock()
    os.makedirs(os.path.expanduser('~/data'), exist_ok=True)
    for t in times:
        ta, td = node.observe(t)
        print('t=%2dh  open time (sim) %.2f s' % (t, td - ta), flush=True)
        with open(os.path.expanduser('~/data/patrol_log.jsonl'), 'a') as f:
            f.write(json.dumps({'t_h': t, 't_attach': ta, 't_detach': td, 'open_time': td - ta}) + '\n')
    node.remove('plate_lid')
    node.remove('plate_open')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
