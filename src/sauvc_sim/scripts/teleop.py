#!/usr/bin/env python3
import time
import sys
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetEntityState, GetEntityState
from select import select
import termios
import tty
import threading


class KeyboardController(Node):

    def __init__(self):
        super().__init__('keyboard_ctrl')
        self.set = self.create_client(
            SetEntityState, 'sauvc_sim/set_entity_state')
        self.get = self.create_client(
            GetEntityState, 'sauvc_sim/get_entity_state')
        while not self.set.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('sauvc_sim/set_entity_state not available, waiting again...')
        while not self.get.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('sauvc_sim/get_entity_state not available, waiting again...')

        self.model_name = "orca"
        self.LIN_VEL_STEP = 0.1
        self.ANG_VEL_STEP = 0.1

        self.settings = termios.tcgetattr(sys.stdin)
        self.key_timeout = 0.5

        self.set_req = SetEntityState.Request()
        self.get_req = GetEntityState.Request()
        self.get_req.name = self.model_name

        self.get_logger().info("started successfully")

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select([sys.stdin], [], [], self.key_timeout)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def run(self):
        key = self.get_key()

        resp = self.get.call(self.get_req)
        state = resp.state

        if key == 'w':
            state.twist.linear.x = 0.0
            state.twist.linear.y = self.LIN_VEL_STEP
            state.twist.linear.z = 0.0
            self.get_logger().info("front")
        elif key == 'a':
            state.twist.linear.x = -self.LIN_VEL_STEP
            state.twist.linear.y = 0.0
            state.twist.linear.z = 0.0
            self.get_logger().info("left")
        elif key == 's':
            state.twist.linear.x = 0.0
            state.twist.linear.y = -self.LIN_VEL_STEP
            state.twist.linear.z = 0.0
            self.get_logger().info("back")
        elif key == 'd':
            state.twist.linear.x = self.LIN_VEL_STEP
            state.twist.linear.y = 0.0
            state.twist.linear.z = 0.0
            self.get_logger().info("right")
        elif key == 'k':
            state.twist.linear.x = 0.0
            state.twist.linear.y = 0.0
            state.twist.linear.z = self.LIN_VEL_STEP
            self.get_logger().info("up")
        elif key == 'j':
            state.twist.linear.x = 0.0
            state.twist.linear.y = 0.0
            state.twist.linear.z = -self.LIN_VEL_STEP
            self.get_logger().info("down")
        elif key == 'u':
            state.twist.angular.z = self.ANG_VEL_STEP
            self.get_logger().info("yaw_left")
        elif key == 'i':
            state.twist.angular.z = -self.ANG_VEL_STEP
            self.get_logger().info("yaw_right")
        elif key == 'q':
            state.twist.linear.x = 0.0
            state.twist.linear.y = 0.0
            state.twist.linear.z = 0.0
            self.get_logger().info("stop")
        else:
            state.twist.angular.x = 0.0
            state.twist.angular.y = 0.0
            state.twist.angular.z = 0.0

        self.set_req.state = state
        self.set_req.state.name = self.model_name
        return self.set.call(self.set_req)


if __name__ == "__main__":
    rclpy.init()
    node = KeyboardController()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,))
    spin_thread.start()

    rate = node.create_rate(5)
    while rclpy.ok():
        node.run()
        rate.sleep()

    node.destroy_node()
    rclpy.shutdown()
