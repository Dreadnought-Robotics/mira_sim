from launch_ros.substitutions import FindPackageShare
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():

    ardusim_patch = Node(
        package="dnt_simulator",
        namespace="bluerov2",
        executable="ardusim_patch.py",
        name="ardusim_patch",
        output="screen",
        emulate_tty="true",
    )

    joystick_node = Node(
        package="mira2_rov",
        namespace="bluerov2",
        executable="joystick_exe",
        name="joystick_node",
        output="screen",
        emulate_tty="true",
    )

    joy_node = Node(
        package="joy",
        namespace="bluerov2",
        executable="joy_node",
        name="joy_node",
        output="screen",
        emulate_tty="true",
    )

    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        PathJoinSubstitution(
                            [
                                FindPackageShare("stonefish_ros2"),
                                "launch",
                                "stonefish_simulator.launch.py",
                            ]
                        )
                    ]
                ),
                launch_arguments={
                    "simulation_data": PathJoinSubstitution(
                        [FindPackageShare("common_resources"), "data"]
                    ),
                    "scenario_desc": PathJoinSubstitution(
                        [FindPackageShare("dnt_simulator"), "scenarios", "TACC_DOCKING.scn"]
                    ),
                    "simulation_rate": "300.0",
                    # "parameter_file": "tacc_config.yaml",
                    "window_res_x": "1200",
                    "window_res_y": "800",
                    "rendering_quality": "high",
                }.items(),
            ),
            # joystick_node,
            # joy_node
            ardusim_patch,
        ]
    )
