#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from nav_msgs.msg import Odometry
from custom_msgs.msg import Commands, Telemetry

MAX_THRUST = 20.0
PWM_NEUTRAL = 1500
PWM_RANGE = 400.0


def pwm_to_force(pwm):
    return (pwm - PWM_NEUTRAL) / PWM_RANGE * MAX_THRUST


def clamp(v, lim=MAX_THRUST):
    return max(-lim, min(lim, v))


class SimBridge(Node):
    def __init__(self):
        super().__init__('sim_master')

        self.armed = False
        self.depth = 0.0

        self.thruster_pub = self.create_publisher(Float64MultiArray, '/bluerov2/thrusters', 10)
        self.telemetry_pub = self.create_publisher(Telemetry, '/master/telemetry', 10)

        self.create_subscription(Commands, '/master/commands', self.commands_cb, 10)
        self.create_subscription(Odometry, '/bluerov2/odometry', self.odom_cb, 10)

        self.create_timer(0.05, self.publish_telemetry)  # 20 Hz

        self.get_logger().info("sim_master bridge ready: /master/commands -> /bluerov2/thrusters")

    def odom_cb(self, msg: Odometry):
        self.depth = msg.pose.pose.position.z

    def commands_cb(self, msg: Commands):
        self.armed = msg.arm

        if not msg.arm:
            self._publish_zeros()
            return

        surge = pwm_to_force(msg.forward)
        sway  = -pwm_to_force(msg.lateral)
        heave = pwm_to_force(msg.thrust)
        yaw   = pwm_to_force(msg.yaw)
        pitch = pwm_to_force(msg.pitch)
        roll  = pwm_to_force(msg.roll)

        # Same 8-thruster mix as docking_p2.py
        out = Float64MultiArray()
        out.data = [
            clamp(+surge + yaw + sway),
            clamp(+surge - yaw - sway),
            clamp(-surge - yaw + sway),
            clamp(-surge + yaw - sway),
            clamp(heave + pitch + roll),
            clamp(heave + pitch - roll),
            clamp(heave - pitch + roll),
            clamp(heave - pitch - roll),
        ]
        self.thruster_pub.publish(out)

    def _publish_zeros(self):
        out = Float64MultiArray()
        out.data = [0.0] * 8
        self.thruster_pub.publish(out)

    def publish_telemetry(self):
        msg = Telemetry()
        msg.arm = self.armed
        msg.external_pressure = float(1013.25 + self.depth * 100.0)  # rough approximation
        self.telemetry_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SimBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
