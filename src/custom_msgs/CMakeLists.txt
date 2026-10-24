cmake_minimum_required(VERSION 3.8)
project(custom_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

# Mirrored from the mira real-robot custom_msgs package so sim and
# real-robot controllers share an identical message interface.
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Object2D.msg"
  "msg/Commands.msg"
  "msg/CommandsNormalized.msg"
  "msg/Telemetry.msg"
  "msg/EmergencyKill.msg"
  "msg/Depth.msg"
  "msg/Heading.msg"
  "msg/ArucoPose.msg"
  "msg/ConfidenceLevel.msg"
  DEPENDENCIES sensor_msgs std_msgs geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime sensor_msgs std_msgs geometry_msgs)
ament_package()
