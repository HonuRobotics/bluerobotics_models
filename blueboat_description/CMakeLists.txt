cmake_minimum_required(VERSION 3.14)
project(blueboat_description)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into it
# (the generated URDF that blueboat_gazebo merge-includes) resolve
# in Gazebo. RViz resolves package:// on its own through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

# Expand the xacro into a concrete URDF at *build* time. The config yaml is
# passed as the config_file arg. Dependencies are listed EXPLICITLY: the
# configure time `xacro --deps` snapshot only warns on failure and is not
# refreshed until the next reconfigure, so on its own a config or include
# edit can silently fail to regenerate the URDF.
xacro_add_files(
  urdf/blueboat.urdf.xacro
    REMAP config_file:=${CMAKE_CURRENT_SOURCE_DIR}/config/blueboat.yaml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/config/blueboat.yaml
    TARGET urdf_raw
)

# Stamp the generated URDF with a model specs comment (total mass, centers of
# mass and buoyancy, net buoyancy, accessories) and install the stamped copy
# under the same urdf/ name every consumer resolves.
set(raw_urdf ${CMAKE_CURRENT_BINARY_DIR}/urdf/blueboat.urdf)
set(stamped_urdf ${CMAKE_CURRENT_BINARY_DIR}/stamped/blueboat.urdf)
add_custom_command(
  OUTPUT ${stamped_urdf}
  COMMAND Python3::Interpreter
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/stamp_model_specs.py
          --vehicle blueboat
          --urdf ${raw_urdf}
          --config ${CMAKE_CURRENT_SOURCE_DIR}/config/blueboat.yaml
          --stamp ${raw_urdf}
          --out ${stamped_urdf}
  DEPENDS ${raw_urdf}
          ${CMAKE_CURRENT_SOURCE_DIR}/config/blueboat.yaml
          ${CMAKE_CURRENT_SOURCE_DIR}/scripts/stamp_model_specs.py
  COMMENT "Stamping blueboat.urdf with model specs")
add_custom_target(${PROJECT_NAME}_model_specs ALL DEPENDS ${stamped_urdf})
install(FILES ${stamped_urdf} DESTINATION share/${PROJECT_NAME}/urdf)

install(DIRECTORY
  urdf
  rviz
  launch
  config
  DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/stamp_model_specs.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_description test/test_description.py TIMEOUT 180)
  ament_add_pytest_test(test_model_specs test/test_model_specs.py TIMEOUT 60)
endif()

ament_package()
