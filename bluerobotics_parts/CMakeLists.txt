cmake_minimum_required(VERSION 3.14)
project(bluerobotics_parts)

find_package(ament_cmake REQUIRED)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into
# models/ resolve in Gazebo. RViz resolves package:// through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

install(DIRECTORY
  models
  DESTINATION share/${PROJECT_NAME})

# The import script (model.sdf collisions -> urdf.xacro) is not written yet.
# Add its install rule alongside the script itself:
#   install(PROGRAMS scripts/import_part.py DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
