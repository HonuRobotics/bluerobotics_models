cmake_minimum_required(VERSION 3.14)
project(blueboat_gazebo)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)
find_package(blueboat_description REQUIRED)
find_package(bluerobotics_parts REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so model://blueboat_gazebo
# (the composed model below) resolves in Gazebo.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

install(DIRECTORY
  launch
  worlds
  DESTINATION share/${PROJECT_NAME})

# ros_gz bridge config is GENERATED from the vehicle config plus the
# assembled URDF (whose <assembly_part> manifest lists the resolved parts,
# defaults included), so bridge topics always match the fitted sensors.
# Re-runs when the config, the URDF or the generator changes.
set(vehicle_config ${blueboat_description_DIR}/../config/blueboat.yaml)
set(desc_urdf ${blueboat_description_DIR}/../urdf/blueboat.urdf)
set(bridge_yaml ${CMAKE_CURRENT_BINARY_DIR}/ros_gz_bridge.yaml)
add_custom_command(
  OUTPUT ${bridge_yaml}
  COMMAND Python3::Interpreter
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_bridge_config.py
          ${vehicle_config} ${desc_urdf} ${bridge_yaml}
  DEPENDS ${vehicle_config} ${desc_urdf}
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_bridge_config.py
  COMMENT "Generating ros_gz_bridge.yaml from blueboat.yaml and blueboat.urdf")
add_custom_target(${PROJECT_NAME}_bridge_yaml ALL DEPENDS ${bridge_yaml})
install(FILES ${bridge_yaml} DESTINATION share/${PROJECT_NAME}/config)

# Composed simulation model. model.sdf is GENERATED from model.sdf.xacro at build
# time (reads blueboat_description/config/blueboat.yaml, adds the Gazebo plugins).
# xacro_add_files (no DESTINATION) installs it to share/${PROJECT_NAME}/model.sdf,
# next to the static model.config. The config dependency is EXPLICIT: the
# configure time xacro --deps snapshot cannot resolve $(find) and fails with
# only a warning, leaving the rule without deps.
xacro_add_files(model.sdf.xacro DEPENDS ${vehicle_config} TARGET model_raw)

# Stamp model.sdf with the same model specs comment the installed URDF
# carries (the numbers come from that URDF, the loadout from the config).
set(stamper
  ${blueboat_description_DIR}/../../../lib/blueboat_description/stamp_model_specs.py)
set(raw_sdf ${CMAKE_CURRENT_BINARY_DIR}/model.sdf)
set(stamped_sdf ${CMAKE_CURRENT_BINARY_DIR}/stamped/model.sdf)
add_custom_command(
  OUTPUT ${stamped_sdf}
  COMMAND Python3::Interpreter ${stamper}
          --vehicle blueboat
          --urdf ${desc_urdf}
          --config ${vehicle_config}
          --stamp ${raw_sdf}
          --out ${stamped_sdf}
  DEPENDS ${raw_sdf} ${desc_urdf} ${vehicle_config} ${stamper}
  COMMENT "Stamping model.sdf with model specs")
add_custom_target(${PROJECT_NAME}_model_specs ALL DEPENDS ${stamped_sdf})
install(FILES ${stamped_sdf} DESTINATION share/${PROJECT_NAME})
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
  # NOCAPTURE so the sim output printed at teardown reaches the test logs
  # even when every assertion passes; the runtime behavior tests watch the
  # vehicle for several seconds each.
  ament_add_pytest_test(test_gz_launch test/test_gz_launch.py TIMEOUT 420
    NOCAPTURE)
  ament_add_pytest_test(test_ros_launch test/test_ros_launch.py TIMEOUT 300
    NOCAPTURE)
endif()

ament_package()
