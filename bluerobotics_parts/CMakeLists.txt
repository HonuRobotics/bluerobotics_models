cmake_minimum_required(VERSION 3.14)
project(bluerobotics_parts)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Put this package's share dir on GZ_SIM_RESOURCE_PATH so package:// URIs into
# models/ resolve in Gazebo. RViz resolves package:// through the ament index.
ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh.in")

# models/ carries the delivered meshes (and the modeler's SDF they came
# with); urdf/ carries the parts, one macro file each, the parts level
# library that includes them and the assembly dispatcher.
install(DIRECTORY
  models
  urdf
  worlds
  DESTINATION share/${PROJECT_NAME})

# The Python side: the assembly manifest reader and the config check that
# vehicle builds and launches run (bluerobotics_parts.assembly).
ament_python_install_package(${PROJECT_NAME})

# Tooling run by a person, never by the build: sdf_to_part.py bootstraps a
# part macro from a modeler's model.sdf, gltf_to_yup.py fixes a Z-up glTF
# delivery, parts_check_world.py regenerates worlds/parts_check.sdf, and
# check_assembly.py is the config check as a CLI, and
# stamp_model_specs.py writes the specs comment the builds stamp.
install(PROGRAMS
  scripts/sdf_to_part.py
  scripts/parts_check_world.py
  scripts/gltf_to_yup.py
  scripts/gltf_bake_basecolor.py
  scripts/check_assembly.py
  scripts/stamp_model_specs.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_parts test/test_parts.py TIMEOUT 180)
endif()

ament_package()
