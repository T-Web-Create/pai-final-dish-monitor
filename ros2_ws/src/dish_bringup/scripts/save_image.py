#!/usr/bin/env python3
# Save one frame from /dish_camera/image as PNG.
import sys

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class Saver(Node):
    def __init__(self, path):
        super().__init__('image_saver')
        self.path = path
        self.done = False
        self.create_subscription(Image, '/dish_camera/image', self.cb, 10)

    def cb(self, msg):
        img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        cv2.imwrite(self.path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        self.done = True


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'frame.png'
    rclpy.init()
    node = Saver(path)
    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.5)
    print('saved', path)
    node.destroy_node()
    rclpy.shutdown()


main()
