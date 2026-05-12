import os
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node

_WORLD = 'tacc_world'
_MODEL = 'bluerov2_heavy'


def _gz_img(link, sensor):
    return f'/world/{_WORLD}/model/{_MODEL}/link/{link}/sensor/{sensor}/image'


def generate_launch_description():
    pkg_bluerov2_gz = get_package_share_directory('bluerov2_gz')
    ardupilot_gz_lib = os.path.join(
        get_package_prefix('ardupilot_gazebo'), 'lib', 'ardupilot_gazebo'
    )
    world_file = os.path.join(pkg_bluerov2_gz, 'worlds', 'tacc.world')

    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.join(pkg_bluerov2_gz, 'models') + ':' +
              os.path.join(pkg_bluerov2_gz, 'worlds') + ':' +
              os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    )

    # Expose libArduPilotPlugin.so (and other ardupilot_gazebo plugins) to Gz
    gz_plugin_path = SetEnvironmentVariable(
        name='GZ_SIM_SYSTEM_PLUGIN_PATH',
        value=ardupilot_gz_lib + ':' +
              os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', '')
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': [world_file, ' -r']
        }.items()
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            f'/world/{_WORLD}/model/{_MODEL}/link/base_link/sensor/imu_sensor/imu'
            '@sensor_msgs/msg/Imu[gz.msgs.IMU',
            _gz_img('camera_zed_left',  'camera_zed_left')  + '@sensor_msgs/msg/Image[gz.msgs.Image',
            _gz_img('camera_zed_right', 'camera_zed_right') + '@sensor_msgs/msg/Image[gz.msgs.Image',
            _gz_img('camera_bottom',    'camera_bottom')    + '@sensor_msgs/msg/Image[gz.msgs.Image',
        ],
        remappings=[
            (_gz_img('camera_zed_left',  'camera_zed_left'),  '/sim/camera_zed/left/image_raw'),
            (_gz_img('camera_zed_right', 'camera_zed_right'), '/sim/camera_zed/right/image_raw'),
            (_gz_img('camera_bottom',    'camera_bottom'),    '/sim/camera_bottom'),
        ],
        output='screen'
    )

    return LaunchDescription([
        gz_resource_path,
        gz_plugin_path,
        gz_sim,
        bridge,
    ])
