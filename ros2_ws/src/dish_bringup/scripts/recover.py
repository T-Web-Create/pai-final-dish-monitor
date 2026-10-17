#!/usr/bin/env python3
"""Recover from an interrupted patrol: release suction and go back to HIGH."""
import os
import sys

import rclpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lid_cycle import LidCycle

rclpy.init()
node = LidCycle()
node.wait_clock()
node.suction('/suction/detach')
node.hold(0.5)
node.move('HIGH', 3.0)
print('recovered: detached, at HIGH')
node.destroy_node()
rclpy.shutdown()
