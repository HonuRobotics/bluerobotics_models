cmake_minimum_required(VERSION 3.14)
project(bluerov2_description)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into it
# (the meshes, and the generated URDF that bluerov2_gazebo merge-includes) resolve
# in Gazebo. RViz resolves package:// on its own through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

# Expand the xacro into a concrete URDF at *build* time and install it. The
# config yaml (accessories + variant) is passed as the config_file arg; xacro's
# --deps reports the xacro includes AND the load_yaml'd config, so editing the
# config or any xacro re-triggers this on the next colcon build.

# Validate the battery loadout before generating: slots, fit, offsets, counts
# and buoyancy_trim, with readable messages. Errors fail the build here rather
# than producing a silently wrong vehicle.
set(battery_stamp ${CMAKE_CURRENT_BINARY_DIR}/battery_config.validated)
add_custom_command(
  OUTPUT ${battery_stamp}
  COMMAND Python3::Interpreter
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/validate_battery_config.py
          --vehicle bluerov2
          --config ${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
          --catalog ${CMAKE_CURRENT_SOURCE_DIR}/config/batteries.yaml
  COMMAND ${CMAKE_COMMAND} -E touch ${battery_stamp}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
          ${CMAKE_CURRENT_SOURCE_DIR}/config/batteries.yaml
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/validate_battery_config.py
  COMMENT "Validating bluerov2 battery loadout")
add_custom_target(${PROJECT_NAME}_battery_validation ALL DEPENDS ${battery_stamp})

xacro_add_files(
  urdf/bluerov2.urdf.xacro
    REMAP config_file:=${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
          batteries_file:=${CMAKE_CURRENT_SOURCE_DIR}/config/batteries.yaml
    INSTALL DESTINATION urdf
)

install(DIRECTORY
  meshes
  urdf
  rviz
  launch
  config
  DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/validate_battery_config.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_description test/test_description.py TIMEOUT 180)
  ament_add_pytest_test(test_batteries test/test_batteries.py TIMEOUT 180)
endif()

ament_package()
