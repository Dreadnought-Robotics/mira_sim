cmake_minimum_required(VERSION 3.8)
project(sauvc_sim)

find_package(
  ament_cmake REQUIRED
  ament_cmake_python REQUIRED
  rclcpp REQUIRED
  rclpy REQUIRED
	gazebo_ros REQUIRED
  ros_gz_interfaces REQUIRED
)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  scripts/teleop.py
  scripts/teleop25.py
  scripts/entity_spawner.py  
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  models
  worlds
  meshes
  DESTINATION share/${PROJECT_NAME}
)

# Install shared drum mesh into each drum model directory so model:// URIs resolve
install(FILES meshes/drum.obj DESTINATION share/${PROJECT_NAME}/models/blue_drum)
install(FILES meshes/drum.obj DESTINATION share/${PROJECT_NAME}/models/red_drum)

ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/${PROJECT_NAME}.dsv.in")

ament_package()
