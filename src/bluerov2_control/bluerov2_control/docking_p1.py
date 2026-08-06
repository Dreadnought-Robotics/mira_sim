import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from custom_msgs.msg import Commands

from cv_bridge import CvBridge
import cv2
import time
import math
from ultralytics import YOLO
from ament_index_python import get_package_share_directory


# -------------------- sim_master interface --------------------
PWM_NEUTRAL = 1500
PWM_RANGE = 400.0
MAX_THRUST = 20.0
PWM_MIN = 1100
PWM_MAX = 1900


def force_to_pwm(force):
    """Convert a thruster-force intent into a PWM value sim_master understands.

    sim_master does pwm_to_force(pwm) = (pwm - 1500) / 400 * 20, so this is
    the exact inverse. Result is clamped to a safe PWM range.
    """
    pwm = PWM_NEUTRAL + force / MAX_THRUST * PWM_RANGE
    return int(max(PWM_MIN, min(PWM_MAX, pwm)))


class DepthYawVisionController(Node):

    def __init__(self):
        super().__init__('depth_yaw_vision_controller')

        # -------------------- Publishers --------------------
        # Goes through sim_master (/master/commands -> /bluerov2/thrusters)
        self.cmd_pub = self.create_publisher(
            Commands,
            '/master/commands',
            10
        )

        # -------------------- Subscribers --------------------
        self.odom_sub = self.create_subscription(
            Odometry,
            '/bluerov2/odometry',
            self.odom_cb,
            10
        )

        self.image_sub = self.create_subscription(
            Image,
            '/bluerov2/left/image_color',
            self.image_cb,
            10
        )

        # -------------------- Phase 2 handoff --------------------
        self.stopped = False
        self.phase2_sub = self.create_subscription(
            Bool,
            '/docking_phase2',
            self.phase2_cb,
            10
        )

        # -------------------- Vision --------------------
        self.bridge = CvBridge()
        model_path = get_package_share_directory("bluerov2_control") + "/best.pt"
        self.model = YOLO(model_path)

        # -------------------- State --------------------
        self.current_depth = None
        self.current_yaw = None
        self.target_yaw = None
        self.target_depth = 1.3  # FIXED depth target

        # -------------------- Gains --------------------
        self.depth_Kp = 45.0
        self.depth_Kd = 25.0

        self.yaw_Kp = 40.0
        self.yaw_Kd = 0.0

        # -------------------- Motion intent --------------------
        self.surge = 0.0
        self.yaw_cmd = 0.0
        self.heave = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.sway = 0.0   # Always zero now

        # -------------------- PID State --------------------
        self.prev_depth_error = 0.0
        self.prev_yaw_error = 0.0
        self.prev_time = time.time()

        self.start_time = None

        self.get_logger().info("Depth + Yaw + Vision Controller Started (via sim_master)")

        self.control_timer = self.create_timer(0.1, self.control_loop)

    # ==========================================================
    # ODOMETRY
    # ==========================================================

    def odom_cb(self, msg):
        self.current_depth = msg.pose.pose.position.z

        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)

        self.current_yaw = -math.atan2(siny_cosp, cosy_cosp)

        if self.target_yaw is None:
            self.target_yaw = self.current_yaw
            self.start_time = time.time()
            self.get_logger().info(
                f"Yaw locked at {self.target_yaw:.3f} rad"
            )

    # ==========================================================
    # IMAGE CALLBACK (VISION DISPLAY ONLY)
    # ==========================================================

    def phase2_cb(self, msg):
        """ArUco detected by Phase 2 perception -> shut Phase 1 down entirely."""
        if msg.data and not self.stopped:
            self.stopped = True
            cmd = Commands()
            cmd.mode = "MANUAL"
            cmd.arm = False
            cmd.forward = PWM_NEUTRAL
            cmd.lateral = PWM_NEUTRAL
            cmd.thrust = PWM_NEUTRAL
            cmd.yaw = PWM_NEUTRAL
            cmd.pitch = PWM_NEUTRAL
            cmd.roll = PWM_NEUTRAL
            self.cmd_pub.publish(cmd)
            self.get_logger().info("Phase 1 shutting down - handing off to Phase 2")
            # Fully shut down the node; rclpy.spin() will return.
            rclpy.shutdown()

    def image_cb(self, msg):
        if self.stopped:
            return

        if self.current_depth is None:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w, _ = frame.shape

        frame_center_x = w // 2
        top_line = int(0.7 * h)
        bottom_line = int(0.8 * h)

        results = self.model(frame, conf=0.5)

        sway_text = "NONE"
        heave_text = "HOLD"

        k_heave = 0.001
        k_sway = 0.30

        # Reset sway every frame
        self.sway = 0.0

        for r in results:
            boxes = r.boxes
            if boxes is not None and len(boxes) > 0:

                box = boxes[0]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                dock_center_x = int((x1 + x2) / 2)
                dock_center_y = int((y1 + y2) / 2)

                cv2.rectangle(frame,
                            (int(x1), int(y1)),
                            (int(x2), int(y2)),
                            (0, 255, 0), 2)

                cv2.circle(frame,
                        (dock_center_x, dock_center_y),
                        5,
                        (0, 0, 255), -1)

                # ---------------------------------------------------
                # AFTER 17 SECONDS → ENABLE HEAVE + SWAY CONTROL
                # ---------------------------------------------------
                if self.start_time is not None:
                    elapsed = time.time() - self.start_time

                    if elapsed > 17.0:

                        # ---------------- HEAVE ----------------
                        if dock_center_y < top_line:
                            error_pixels = top_line - dock_center_y
                            self.target_depth -= k_heave * error_pixels
                            heave_text = "UP"

                        elif dock_center_y > bottom_line:
                            error_pixels = dock_center_y - bottom_line
                            self.target_depth += k_heave * error_pixels
                            heave_text = "DOWN"

                        else:
                            heave_text = "HOLD"

                        # Clamp target depth to maximum 2.5 meters
                        if self.target_depth > 2.5:
                            self.target_depth = 2.5


                        # ---------------- SWAY (PROPORTIONAL) ----------------
                        offset_x = dock_center_x - frame_center_x

                        self.sway = -k_sway * offset_x

                        if offset_x < -40:
                            sway_text = "LEFT"
                        elif offset_x > 40:
                            sway_text = "RIGHT"
                        else:
                            sway_text = "CENTERED"

                    else:
                        heave_text = "HOLD"
                        sway_text = "NONE"

                break

        # Guide lines
        cv2.line(frame, (frame_center_x, 0),
                (frame_center_x, h), (255, 0, 0), 2)

        cv2.line(frame, (0, top_line),
                (w, top_line), (255, 255, 0), 2)

        cv2.line(frame, (0, bottom_line),
                (w, bottom_line), (255, 255, 0), 2)

        cv2.putText(frame, f"sway: {sway_text}",
                    (40, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255), 2)

        cv2.putText(frame, f"heave: {heave_text}",
                    (40, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255), 2)

        cv2.imshow("Dock Alignment", frame)
        cv2.waitKey(1)


    # ==========================================================
    # CONTROL LOOP (UNCHANGED LOGIC)
    # ==========================================================

    def control_loop(self):

        if self.stopped:
            return

        if self.current_depth is None or self.current_yaw is None:
            return

        now = time.time()
        dt = now - self.prev_time
        self.prev_time = now

        # ---------------- Depth PD ----------------
        depth_error = self.current_depth - self.target_depth
        depth_derivative = (
            (depth_error - self.prev_depth_error) / dt
            if dt > 0.0 else 0.0
        )
        self.prev_depth_error = depth_error

        depth_output = (
            self.depth_Kp * depth_error +
            self.depth_Kd * depth_derivative
        )

        # ---------------- Yaw PD ----------------
        yaw_error = self.angle_error(
            self.target_yaw,
            self.current_yaw
        )

        yaw_derivative = (
            (yaw_error - self.prev_yaw_error) / dt
            if dt > 0.0 else 0.0
        )
        self.prev_yaw_error = yaw_error

        yaw_output = (
            self.yaw_Kp * yaw_error +
            self.yaw_Kd * yaw_derivative
        )

        # ---------------- Surge logic ----------------
        elapsed = time.time() - self.start_time
        surge_command = 0.0 if elapsed < 17.0 else 5.0

        # ---------------- Clamp ----------------
        depth_output = self.clamp(depth_output, 20.0)
        yaw_output = self.clamp(yaw_output, 10.0)
        surge_command = self.clamp(surge_command, 15.0)

        # ---------------- Assign ----------------
        self.surge = surge_command
        self.yaw_cmd = yaw_output
        self.heave = depth_output

        self.publish_commands()

    # ==========================================================

    def angle_error(self, target, current):
        e = target - current
        while e > math.pi:
            e -= 2.0 * math.pi
        while e < -math.pi:
            e += 2.0 * math.pi
        return e

    def clamp(self, value, limit):
        return max(-limit, min(limit, value))

    def publish_commands(self):
        cmd = Commands()
        cmd.mode = "MANUAL"
        cmd.arm = True

        cmd.forward = force_to_pwm(self.surge)
        cmd.thrust = force_to_pwm(self.heave)
        cmd.yaw = force_to_pwm(self.yaw_cmd)
        # sim_master internally negates lateral, so pass -sway to keep
        # the same direction as the old direct thruster mix.
        cmd.lateral = force_to_pwm(-self.sway)
        cmd.pitch = PWM_NEUTRAL
        cmd.roll = PWM_NEUTRAL

        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = DepthYawVisionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        cv2.destroyAllWindows()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
