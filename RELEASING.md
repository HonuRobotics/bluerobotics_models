# Releasing

Maintainer runbook, deliberately outside the user documentation site.
Covers releasing the packages into a ROS 2 distro through the ROS
build farm (target: **Lyrical**; releasing into **Rolling** first makes the
packages flow into later distros automatically).

## One time prerequisites

1. **Release repository**: an empty
   `https://github.com/HonuRobotics/bluerobotics_models-release`; bloom
   populates it.
2. **Dependencies released** in the target distro: `xacro`, `ros_gz_*`,
   `robot_state_publisher`, `joint_state_publisher_gui`, `rviz2`,
   `ament_*`; system keys (`python3-yaml`, `python3-pytest`) resolve via
   rosdep. The rosdistro PR's checks verify this.
3. **Name check**: no colliding package names in
   [ros/rosdistro](https://github.com/ros/rosdistro).
4. **Credentials**: a GitHub token for bloom (to fork rosdistro and open the
   PR); push access to the release repo. The build farm needs nothing from
   us: it builds and signs the debs itself.

## Per release

1. From a clean distro branch, finalize changelogs and version:
   ```bash
   catkin_generate_changelog   # folds new commits into each CHANGELOG.rst (review!)
   catkin_prepare_release      # sets versions, replaces "Forthcoming", tags
   ```
   All packages in the repo share one version (bloom enforces this).
2. Bloom (the first time creates the track and opens the rosdistro PR):
   ```bash
   bloom-release --rosdistro lyrical --track lyrical bluerobotics_models --edit
   ```
3. Wait for the rosdistro PR review and merge; the build farm builds the
   debs, which reach the testing repo, then sync to main.

## Notes

- Binary jobs build without running tests; devel/PR jobs run `colcon test`,
  which is headless safe by design.
- From debs, the default vehicle is baked in; custom configs are a
  `config_file:=` away ([Configure an installed vehicle](docs/how-to/installed-vehicle.md)).
- The build farm runs `rosdoc2` per package; packages without a `doc/`
  folder get an auto generated stub at `docs.ros.org/en/<distro>/p/<pkg>`.
  Before the first release, add a minimal per package `doc/` that links
  here.
- Meshes: the artist's glTF assets are delivered per part; the placeholder
  heavy meshes of the previous design are gone from the BlueBoat.
