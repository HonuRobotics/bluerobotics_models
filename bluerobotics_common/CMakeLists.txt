cmake_minimum_required(VERSION 3.14)
project(bluerobotics_common)

find_package(ament_cmake REQUIRED)

# Put the shared models dir on GZ_SIM_RESOURCE_PATH so model:// URIs into it
# (pool, deck) resolve in Gazebo for every consumer of this package.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

install(DIRECTORY
  models
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
