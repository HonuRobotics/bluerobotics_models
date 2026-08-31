cmake_minimum_required(VERSION 3.14)
project(bluerov2_description)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
# The parts library the xacro assembles from; a real build order dependency
# because $(find bluerobotics_parts) is resolved while expanding at build time.
find_package(bluerobotics_parts REQUIRED)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into
# it (the generated URDF that bluerov2_gazebo merge-includes) resolve in
# Gazebo. RViz resolves package:// on its own through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

# Expand the xacro into a concrete URDF at *build* time. The config yaml is
# passed as the config_file arg. Dependencies are listed EXPLICITLY: the
# configure time `xacro --deps` snapshot only warns on failure and is not
# refreshed until the next reconfigure, so on its own a config or include
# edit can silently fail to regenerate the URDF.
xacro_add_files(
  urdf/bluerov2.urdf.xacro
    REMAP config_file:=${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
    TARGET urdf_raw
)

set(stamper
  ${bluerobotics_parts_DIR}/../../../lib/bluerobotics_parts/stamp_model_specs.py)
# Stamp the generated URDF with a model specs comment (total mass, centers of
# mass and buoyancy, net buoyancy, accessories) and install the stamped copy
# under the same urdf/ name every consumer resolves.
set(raw_urdf ${CMAKE_CURRENT_BINARY_DIR}/urdf/bluerov2.urdf)
set(stamped_urdf ${CMAKE_CURRENT_BINARY_DIR}/stamped/bluerov2.urdf)
add_custom_command(
  OUTPUT ${stamped_urdf}
  COMMAND Python3::Interpreter ${stamper}
          --urdf ${raw_urdf}
          --config ${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
          --stamp ${raw_urdf}
          --out ${stamped_urdf}
  DEPENDS ${raw_urdf} ${stamper}
          ${CMAKE_CURRENT_SOURCE_DIR}/config/bluerov2.yaml
  COMMENT "Stamping bluerov2.urdf with model specs")
add_custom_target(${PROJECT_NAME}_model_specs ALL DEPENDS ${stamped_urdf})
install(FILES ${stamped_urdf} DESTINATION share/${PROJECT_NAME}/urdf)

install(DIRECTORY
  urdf
  rviz
  launch
  config
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_description test/test_description.py TIMEOUT 180)
  ament_add_pytest_test(test_model_specs test/test_model_specs.py TIMEOUT 60)
endif()

ament_package()
