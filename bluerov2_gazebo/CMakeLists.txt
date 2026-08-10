cmake_minimum_required(VERSION 3.14)
project(bluerov2_gazebo)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)
find_package(bluerov2_description REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so model://bluerov2_gazebo
# (the composed model below) resolves in Gazebo.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

install(DIRECTORY
  launch
  worlds
  DESTINATION share/${PROJECT_NAME})

# ros_gz bridge config is GENERATED from the vehicle config (same source the
# model generation reads), so bridge topics always match the configured
# accessories. Re-runs when the config or the generator changes.
set(vehicle_config ${bluerov2_description_DIR}/../config/bluerov2.yaml)
set(bridge_yaml ${CMAKE_CURRENT_BINARY_DIR}/ros_gz_bridge.yaml)
add_custom_command(
  OUTPUT ${bridge_yaml}
  COMMAND Python3::Interpreter
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_bridge_config.py
          ${vehicle_config} ${bridge_yaml}
  DEPENDS ${vehicle_config}
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_bridge_config.py
  COMMENT "Generating ros_gz_bridge.yaml from bluerov2.yaml")
add_custom_target(${PROJECT_NAME}_bridge_yaml ALL DEPENDS ${bridge_yaml})
install(FILES ${bridge_yaml} DESTINATION share/${PROJECT_NAME}/config)

# Composed simulation model. model.sdf is GENERATED from model.sdf.xacro at build
# time: it reads bluerov2_description/config/bluerov2.yaml (variant -> thruster
# count) and adds the Gazebo plugins. xacro_add_files (no DESTINATION) installs it
# to share/${PROJECT_NAME}/model.sdf, next to the static model.config. The config
# dependency is EXPLICIT: the configure time xacro --deps snapshot cannot resolve
# $(find) and fails with only a warning, leaving the rule without deps.
xacro_add_files(model.sdf.xacro DEPENDS ${vehicle_config} INSTALL)
install(FILES
  model.config
  model.sdf.xacro
  DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/generate_bridge_config.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_bridge_generator test/test_bridge_generator.py
    TIMEOUT 60)
  ament_add_pytest_test(test_model_generation test/test_model_generation.py
    TIMEOUT 180)
  # Headless gz server integration test (render assertions skip on CPU-only
  # hosts); includes the buoyancy-rise and surge behavior checks, which watch
  # the vehicle for several seconds each; see test/test_gz_launch.py.
  # NOCAPTURE so the sim output printed at teardown reaches the test logs even
  # when every assertion passes (pytest captures stdout of passing tests).
  ament_add_pytest_test(test_gz_launch test/test_gz_launch.py TIMEOUT 420
    NOCAPTURE)
  # Headless ROS bring-up test: container + bridge + robot_state_publisher
  # through sim.launch.xml; see test/test_ros_launch.py.
  ament_add_pytest_test(test_ros_launch test/test_ros_launch.py TIMEOUT 300
    NOCAPTURE)
endif()

ament_package()
