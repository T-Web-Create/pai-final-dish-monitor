#!/usr/bin/env python3
# Lid open/close cycle with suction (DetachableJoint). Logs open time in sim time.
import json
import os
import subprocess
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from rosgraph_msgs.msg import Clock
from trajectory_msgs.msg import JointTrajectoryPoint

JOINTS = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
          'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']

POSES = {
    'HIGH':    [-0.4521, -0.9476, 0.9829, 1.5355, 1.5708, 1.1187],
    'DOWN':    [-0.4521, -0.6589, 1.3620, 0.8677, 1.5708, 1.1187],
    'LIFT':    [-0.45208, -0.77977, 1.32733, 1.02323, 1.57080, 1.11872],
    'RETRACT': [-0.07605, -1.28707, 2.02582, 0.83204, 1.57080, 1.49475],  # out of fixed-camera view; suction tip (0.15, 0.12, 0.11)
    'RETRACT_OLD': [0.06224, -0.62547, 1.02201, 1.17426, 1.57080, 1.63304],  # wrist visible to the fixed camera
}


class LidCycle(Node):
    def __init__(self):
        super().__init__('lid_cycle')
        self.sim = None
        self.create_subscription(Clock, '/clock', self._on_clock, 10)
        self.client = ActionClient(
            self, FollowJointTrajectory,
            '/scaled_joint_trajectory_controller/follow_joint_trajectory')

    def _on_clock(self, msg):
        self.sim = msg.clock.sec + msg.clock.nanosec * 1e-9

    def wait_clock(self):
        while self.sim is None:
            rclpy.spin_once(self, timeout_sec=0.1)

    def move(self, name, sec):
        self.client.wait_for_server()
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = JOINTS
        pt = JointTrajectoryPoint()
        pt.positions = list(POSES[name])
        pt.velocities = [0.0] * 6
        pt.time_from_start = Duration(sec=int(sec), nanosec=int((sec % 1) * 1e9))
        goal.trajectory.points = [pt]
        fut = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        handle = fut.result()
        if not handle.accepted:
            raise RuntimeError('goal rejected: ' + name)
        res = handle.get_result_async()
        rclpy.spin_until_future_complete(self, res)
        if res.result().result.error_code != 0:
            raise RuntimeError('move failed: ' + name)

    def hold(self, sec):
        target = self.sim + sec
        while self.sim < target:
            rclpy.spin_once(self, timeout_sec=0.05)

    def suction(self, topic):
        subprocess.run(['gz', 'topic', '-t', topic, '-m', 'gz.msgs.Empty', '-p', ' '],
                       check=True, stdout=subprocess.DEVNULL)


def main():
    capture_sec = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    rclpy.init()
    node = LidCycle()
    node.wait_clock()

    node.suction('/suction/detach')
    node.move('HIGH', 5.0)
    node.move('DOWN', 3.0)

    t_attach = node.sim
    node.suction('/suction/attach')
    node.hold(0.5)
    node.move('LIFT', 1.5)
    node.move('RETRACT', 2.0)
    node.hold(capture_sec)
    node.move('LIFT', 2.0)
    node.move('DOWN', 1.5)
    node.suction('/suction/detach')
    t_detach = node.sim
    node.hold(0.5)
    node.move('HIGH', 3.0)

    open_time = t_detach - t_attach
    print('open time (sim) = %.2f s (capture %.1f s)' % (open_time, capture_sec))

    log_dir = os.path.expanduser('~/data')
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, 'lid_cycle_log.jsonl'), 'a') as f:
        f.write(json.dumps({'t_attach': t_attach, 't_detach': t_detach,
                            'open_time': open_time, 'capture_sec': capture_sec}) + '\n')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
