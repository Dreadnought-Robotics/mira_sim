from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution
from ament_index_python import get_package_share_directory
import os
try:
    from dnt_simulator.perf_profiles import PROFILES, detect_profile
except ImportError:
    PROFILES = {"nogpu": {"simulation_rate": "60.0", "window_res_x": "640", "window_res_y": "480", "rendering_quality": "low"}, "low": {"simulation_rate": "80.0", "window_res_x": "800", "window_res_y": "600", "rendering_quality": "low"}, "medium": {"simulation_rate": "100.0", "window_res_x": "960", "window_res_y": "600", "rendering_quality": "low"}, "high": {"simulation_rate": "200.0", "window_res_x": "1280", "window_res_y": "720", "rendering_quality": "high"}}
    def detect_profile():
        env = os.environ.get("STONEFISH_PROFILE") or os.environ.get("PROFILE") or "auto"
        if env in PROFILES: return env
        return "medium" if os.path.exists("/dev/dri") else "nogpu"

def _create_actions(context, *args, **kwargs):
    profile = LaunchConfiguration("profile").perform(context)
    if profile == "auto": profile = detect_profile()
    cfg = PROFILES.get(profile, PROFILES["medium"])
    print(f"[stonefish] tank profile={profile} -> rate={cfg['simulation_rate']} res={cfg['window_res_x']}x{cfg['window_res_y']} quality={cfg['rendering_quality']}")
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([PathJoinSubstitution([FindPackageShare("stonefish_ros2"), "launch", "stonefish_simulator.launch.py"])]),
            launch_arguments={
                "simulation_data": PathJoinSubstitution([FindPackageShare("common_resources"), "data"]),
                "scenario_desc": PathJoinSubstitution([FindPackageShare("dnt_simulator"), "scenarios", "bluerov2_tank.scn"]),
                "simulation_rate": cfg["simulation_rate"],
                "window_res_x": cfg["window_res_x"],
                "window_res_y": cfg["window_res_y"],
                "rendering_quality": cfg["rendering_quality"],
            }.items(),
        ),
        Node(package="dnt_simulator", namespace="bluerov2", executable="ardusim_patch.py", name="ardusim_patch", output="screen", emulate_tty="true"),
    ]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("profile", default_value="auto", description="Perf profile: auto/nogpu/low/medium/high"),
        OpaqueFunction(function=_create_actions),
    ])