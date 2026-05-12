cmake_minimum_required(VERSION 3.8)
project(common_resources)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(DIRECTORY
  data
  DESTINATION share/${PROJECT_NAME}/
)

install(DIRECTORY
  config
  DESTINATION share/${PROJECT_NAME}/
)

# Install mesh files into their Gazebo model directories
install(FILES data/object_files/pipe1.obj DESTINATION share/${PROJECT_NAME}/data/object_files/pipe)
install(FILES data/object_files/pipe2.png DESTINATION share/${PROJECT_NAME}/data/object_files/pipe)
install(FILES data/aruco_tags/aruco-19.png DESTINATION share/${PROJECT_NAME}/data/object_files/pipe)
install(FILES data/object_files/structure.obj DESTINATION share/${PROJECT_NAME}/data/object_files/structure)

ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/common_resources.dsv.in")

ament_package()
