# Releasing to the ROS buildfarm

Runbook for bloom-releasing `bluerov2_description` + `bluerov2_gazebo` into a
ROS 2 distro (target: **Lyrical**). The packages themselves are release-ready
(manifests with version/maintainer/license/urls, per-package `CHANGELOG.rst`,
uniform versions, no network access at build time, tests headless-safe); what
remains is process.

## One-time prerequisites

1. **Public source repo**: push this repo to
   `https://github.com/HonuRobotics/bluerobotics_models` (branch `lyrical`) and get CI
   green on the target distro.
2. **Release repo**: create an empty
   `https://github.com/HonuRobotics/bluerobotics_models-release` (bloom populates it).
3. **Hold until the final meshes land** (project decision): don't publish the
   placeholder-mesh model to apt; the artist's glTF assets replace them first
   (and shrink the 24 MB heavy-frame `.dae`, which matters for deb size).
4. **Dependency availability in the target distro**: all ROS deps must be
   released in Lyrical: `xacro`, `ros_gz_*`, `robot_state_publisher`,
   `joint_state_publisher_gui`, `rviz2`, `marine_acoustic_msgs` (released in
   Rolling, flows forward), `ament_*`. The rosdistro PR's automated checks
   verify this; system keys (`python3-yaml`, `python3-pytest`) already resolve
   via rosdep.
5. **Name check**: confirm no `bluerov2*` package/repo entry already exists in
   [ros/rosdistro](https://github.com/ros/rosdistro) (collision would block the
   PR).

## Per-release steps

1. Finalize the changelogs + version and tag (from a clean `lyrical` branch):
   ```bash
   catkin_generate_changelog   # folds new commits into CHANGELOG.rst (review!)
   catkin_prepare_release      # sets versions, replaces "Forthcoming", tags
   ```
   All packages in the repo must share one version (bloom enforces this).
2. Bloom (first time creates the track and can open the rosdistro PR for you;
   needs a GitHub token):
   ```bash
   bloom-release --rosdistro lyrical --track lyrical bluerobotics_models --edit
   # upstream:  https://github.com/HonuRobotics/bluerobotics_models.git   (branch lyrical)
   # release:   https://github.com/HonuRobotics/bluerobotics_models-release.git
   ```
3. Wait for the [ros/rosdistro](https://github.com/ros/rosdistro) PR review +
   merge, then the buildfarm builds `ros-lyrical-bluerov2-description` /
   `ros-lyrical-bluerov2-gazebo` and they reach the testing repo → sync → main
   apt repo.

## Buildfarm notes

- Binary (deb) jobs build without running tests; devel/PR jobs run the full
  `colcon test` suite, which is headless-safe by design (the gz load test needs no
  GPU; the camera render test skips where software GL is unavailable).
- The deb-install configuration story (baked default artifacts, overlay or
  runtime regeneration for custom loadouts) is documented in each package
  README under "Binary (deb) installs".
- Consider also releasing into **Rolling** so the packages flow into future
  distros automatically.
