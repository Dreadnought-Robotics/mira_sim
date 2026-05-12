#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import sys
import termios
import tty
import select
from datetime import datetime
import os
from ament_index_python.packages import get_package_share_directory

# Movement instructions
INSTRUCTIONS = """
AUV Teleop Control
---------------------------
Moving around:
   w/s : forward/backward
   a/d : left/right (strafe)
   q/e : yaw left/right
   r/f : up/down

   i/k : increase/decrease linear speed
   j/l : increase/decrease angular speed

Recording controls:
   1/2/3 : toggle RealSense/Side/Bottom camera recording
   0     : start/stop ALL camera recordings
   
SPACE : stop all movement
CTRL-C : quit

Current speeds will be displayed
"""

class TeleopKeyboard(Node):
    def __init__(self):
        super().__init__('auv_teleop_keyboard')
        
        # Publisher for velocity commands
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Speed settings
        self.linear_speed = 0.5  # m/s
        self.angular_speed = 0.5  # rad/s
        self.speed_step = 0.1
        
        # Current velocities
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.wz = 0.0
        
        # Recording setup
        self.bridge = CvBridge()
        
        # Get the package directory and create recordings folder
        try:
            pkg_dir = get_package_share_directory('sauvc_sim')
            # Go up to package root (share directory is install/sauvc_sim/share/sauvc_sim)
            # We want to save in the source package directory instead
            self.recording_dir = os.path.join(os.getcwd(), 'src', 'sauvc_sim', 'recordings')
        except:
            # Fallback: try to find it relative to current directory
            self.recording_dir = os.path.join(os.getcwd(), 'recordings')
        
        os.makedirs(self.recording_dir, exist_ok=True)
        
        # Camera subscribers
        self.realsense_sub = self.create_subscription(
            Image, '/realsense/image', self.realsense_callback, 10)
        self.side_cam_sub = self.create_subscription(
            Image, '/side_cam', self.side_cam_callback, 10)
        self.bottom_cam_sub = self.create_subscription(
            Image, '/bottom_cam', self.bottom_cam_callback, 10)
        
        # Recording state
        self.cameras = {
            'realsense': {'enabled': False, 'recording': False, 'writer': None, 'latest_frame': None},
            'side': {'enabled': False, 'recording': False, 'writer': None, 'latest_frame': None},
            'bottom': {'enabled': False, 'recording': False, 'writer': None, 'latest_frame': None},
        }
        
        # Key bindings
        self.move_bindings = {
            'w': (1, 0, 0, 0),   # forward
            's': (-1, 0, 0, 0),  # backward
            'a': (0, 1, 0, 0),   # left
            'd': (0, -1, 0, 0),  # right
            'r': (0, 0, 1, 0),   # up
            'f': (0, 0, -1, 0),  # down
            'q': (0, 0, 0, 1),   # yaw left
            'e': (0, 0, 0, -1),  # yaw right
        }
        
        self.speed_bindings = {
            'i': (1, 0),   # increase linear
            'k': (-1, 0),  # decrease linear
            'j': (0, 1),   # increase angular
            'l': (0, -1),  # decrease angular
        }
        
        self.get_logger().info('AUV Teleop Keyboard initialized')
        self.get_logger().info(f'Recordings will be saved to: {self.recording_dir}')
        print(INSTRUCTIONS)
        self.print_current_speeds()
        self.print_recording_status()
    
    def get_key(self, timeout=0.1):
        """Get keyboard input with timeout"""
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            key = sys.stdin.read(1)
            return key
        return None
    
    def print_current_speeds(self):
        """Print current speed settings"""
        print(f"\nCurrent speeds - Linear: {self.linear_speed:.2f} m/s, Angular: {self.angular_speed:.2f} rad/s")
    
    def print_recording_status(self):
        """Print current recording status"""
        status = []
        for cam_name, cam_data in self.cameras.items():
            if cam_data['enabled']:
                state = "RECORDING" if cam_data['recording'] else "ENABLED"
                status.append(f"{cam_name}: {state}")
            else:
                status.append(f"{cam_name}: OFF")
        print(f"\nRecording status: {' | '.join(status)}")
    
    def realsense_callback(self, msg):
        """Callback for RealSense camera"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.cameras['realsense']['latest_frame'] = cv_image
            if self.cameras['realsense']['recording'] and self.cameras['realsense']['writer']:
                self.cameras['realsense']['writer'].write(cv_image)
        except Exception as e:
            self.get_logger().error(f'RealSense callback error: {e}')
    
    def side_cam_callback(self, msg):
        """Callback for side camera"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.cameras['side']['latest_frame'] = cv_image
            if self.cameras['side']['recording'] and self.cameras['side']['writer']:
                self.cameras['side']['writer'].write(cv_image)
        except Exception as e:
            self.get_logger().error(f'Side camera callback error: {e}')
    
    def bottom_cam_callback(self, msg):
        """Callback for bottom camera"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.cameras['bottom']['latest_frame'] = cv_image
            if self.cameras['bottom']['recording'] and self.cameras['bottom']['writer']:
                self.cameras['bottom']['writer'].write(cv_image)
        except Exception as e:
            self.get_logger().error(f'Bottom camera callback error: {e}')
    
    def start_recording(self, cam_name):
        """Start recording for a specific camera"""
        cam = self.cameras[cam_name]
        if cam['latest_frame'] is None:
            print(f"\n{cam_name} camera: No frames received yet, cannot start recording")
            return
        
        if cam['recording']:
            print(f"\n{cam_name} camera: Already recording")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.recording_dir, f"{cam_name}_{timestamp}.mov")
        
        height, width = cam['latest_frame'].shape[:2]
        # Use mp4v codec for .mov files (widely compatible)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        cam['writer'] = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))
        
        if cam['writer'].isOpened():
            cam['recording'] = True
            print(f"\n{cam_name} camera: Recording started -> {filename}")
        else:
            print(f"\n{cam_name} camera: Failed to start recording")
            cam['writer'] = None
    
    def stop_recording(self, cam_name):
        """Stop recording for a specific camera"""
        cam = self.cameras[cam_name]
        if not cam['recording']:
            print(f"\n{cam_name} camera: Not recording")
            return
        
        if cam['writer']:
            cam['writer'].release()
            cam['writer'] = None
        cam['recording'] = False
        print(f"\n{cam_name} camera: Recording stopped")
    
    def toggle_camera(self, cam_name):
        """Toggle camera recording on/off"""
        cam = self.cameras[cam_name]
        if cam['enabled']:
            # Disable and stop recording if active
            if cam['recording']:
                self.stop_recording(cam_name)
            cam['enabled'] = False
            print(f"\n{cam_name} camera: Disabled")
        else:
            # Enable and start recording
            cam['enabled'] = True
            print(f"\n{cam_name} camera: Enabled")
            self.start_recording(cam_name)
        self.print_recording_status()
    
    def toggle_all_cameras(self):
        """Toggle all cameras on/off"""
        # Check if any camera is currently recording
        any_recording = any(cam['recording'] for cam in self.cameras.values())
        
        if any_recording:
            # Stop all recordings
            for cam_name in self.cameras.keys():
                if self.cameras[cam_name]['recording']:
                    self.stop_recording(cam_name)
                self.cameras[cam_name]['enabled'] = False
            print("\nAll recordings stopped")
        else:
            # Start all recordings
            for cam_name in self.cameras.keys():
                self.cameras[cam_name]['enabled'] = True
                self.start_recording(cam_name)
            print("\nAll recordings started")
        self.print_recording_status()
    
    def publish_velocity(self):
        """Publish the current velocity command"""
        twist = Twist()
        twist.linear.x = self.vx
        twist.linear.y = self.vy
        twist.linear.z = self.vz
        twist.angular.z = self.wz
        self.publisher.publish(twist)
    
    def run(self):
        """Main control loop"""
        # Save terminal settings
        settings = termios.tcgetattr(sys.stdin)
        
        try:
            tty.setraw(sys.stdin.fileno())
            
            while rclpy.ok():
                key = self.get_key()
                
                if key:
                    # Check for quit
                    if key == '\x03':  # Ctrl-C
                        break
                    
                    # Check for stop
                    elif key == ' ':
                        self.vx = 0.0
                        self.vy = 0.0
                        self.vz = 0.0
                        self.wz = 0.0
                        print("\nStopped")
                    
                    # Check for movement
                    elif key in self.move_bindings:
                        dx, dy, dz, dw = self.move_bindings[key]
                        self.vx = dx * self.linear_speed
                        self.vy = dy * self.linear_speed
                        self.vz = dz * self.linear_speed
                        self.wz = dw * self.angular_speed
                        print(f"\rVel: x={self.vx:.2f} y={self.vy:.2f} z={self.vz:.2f} yaw={self.wz:.2f}", end='')
                    
                    # Check for speed adjustment
                    elif key in self.speed_bindings:
                        dl, da = self.speed_bindings[key]
                        self.linear_speed = max(0.1, min(2.0, self.linear_speed + dl * self.speed_step))
                        self.angular_speed = max(0.1, min(2.0, self.angular_speed + da * self.speed_step))
                        self.print_current_speeds()
                    
                    # Check for recording controls
                    elif key == '1':
                        self.toggle_camera('realsense')
                    elif key == '2':
                        self.toggle_camera('side')
                    elif key == '3':
                        self.toggle_camera('bottom')
                    elif key == '0':
                        self.toggle_all_cameras()
                    
                    # Publish velocity
                    self.publish_velocity()
                
                # Spin once to process callbacks
                rclpy.spin_once(self, timeout_sec=0)
        
        except Exception as e:
            print(f"\nError: {e}")
        
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            
            # Stop all recordings
            for cam_name in self.cameras.keys():
                if self.cameras[cam_name]['recording']:
                    self.stop_recording(cam_name)
            
            # Stop the AUV
            twist = Twist()
            self.publisher.publish(twist)
            print("\nShutting down teleop")


def main(args=None):
    rclpy.init(args=args)
    
    teleop = TeleopKeyboard()
    
    try:
        teleop.run()
    except KeyboardInterrupt:
        pass
    finally:
        teleop.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()