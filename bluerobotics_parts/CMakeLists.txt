cmake_minimum_required(VERSION 3.14)
project(bluerobotics_parts)

find_package(ament_cmake REQUIRED)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into
# models/ resolve in Gazebo. RViz resolves package:// through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

# models/ carries the meshes, model.sdf and each part's macro; urdf/ carries the
# parts-level library that includes them.
install(DIRECTORY
  models
  urdf
  worlds
  DESTINATION share/${PROJECT_NAME})

# The import script (model.sdf + <part>.yaml -> urdf/<part>.urdf.xacro). Run
# by a person when the modeler delivers, never by the build.
install(PROGRAMS
  scripts/sdf_to_part.py
  scripts/parts_check_world.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
