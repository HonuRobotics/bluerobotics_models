cmake_minimum_required(VERSION 3.14)
project(blueboat_description)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into it
# (the generated URDF that blueboat_gazebo merge-includes) resolve
# in Gazebo. RViz resolves package:// on its own through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

# Expand the xacro into a concrete URDF at *build* time and install it. The
# config yaml (accessories) is passed as the config_file arg; xacro's --deps
# reports the xacro includes AND the load_yaml'd config, so editing the config
# or any xacro re-triggers this on the next colcon build.
xacro_add_files(
  urdf/blueboat.urdf.xacro
    REMAP config_file:=${CMAKE_CURRENT_SOURCE_DIR}/config/blueboat.yaml
    INSTALL DESTINATION urdf
)

install(DIRECTORY
  meshes
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
endif()

ament_package()
