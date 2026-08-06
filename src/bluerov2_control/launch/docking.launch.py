import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    calib = os.path.join(
        get_package_share_directory('bluerov2_control'),
        'calibration_data.json'
    )

    return LaunchDescription([
        Node(
            package='bluerov2_control',
            executable='docking_p1',
            name='depth_yaw_vision_controller',
            output='screen',
        ),
        Node(
            package='bluerov2_control',
            executable='docking_p2_perception',
            name='underwater_docking_node',
            output='screen',
            parameters=[{
                'calibration_file': calib,
                'marker_size': 0.15,
                'enable_gui': True,
            }],
        ),
        Node(
            package='bluerov2_control',
            executable='docking_p2_controller',
            name='phase2_controls',
            output='screen',
        ),
    ])
