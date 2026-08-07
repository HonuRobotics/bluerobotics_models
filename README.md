# Blue Robotics models

ROS 2 / Gazebo Sim model packages for Blue Robotics vehicles: the BlueROV2
underwater vehicle (standard and Heavy configurations) and the BlueBoat USV.

| Package | Purpose |
|---------|---------|
| [`bluerov2_description`](bluerov2_description/) | URDF/xacro, meshes, RViz; pure description, no simulator code |
| [`bluerov2_gazebo`](bluerov2_gazebo/) | Composed Gazebo model (thrusters, hydrodynamics, sensors, grippers), world, launch and ros_gz bridge |
| [`blueboat_description`](blueboat_description/) | BlueBoat URDF/xacro, primitive visuals, RViz; no simulator code |
| [`blueboat_gazebo`](blueboat_gazebo/) | Composed BlueBoat model (twin thrusters, hydrodynamics, echosounder), surface-water world, launch and ros_gz bridge |

Targets **ROS 2 Lyrical + Gazebo Jetty** (the default pairing on Ubuntu 26.04),
via `ros_gz`.

## Quick start

From source (binary `apt install ros-<distro>-bluerov2-*` packages are planned;
see each README's binary-install section for how configuration works there):

```bash
cd ~/ws/src && git clone https://github.com/HonuRobotics/bluerobotics_models.git
cd ~/ws
rosdep update
rosdep install --from-paths src --ignore-packages-from-source --default-yes
colcon build --merge-install
source install/setup.bash
ros2 launch bluerov2_gazebo sim.launch.xml     # Gazebo
```

In a second terminal (also sourced):

```bash
ros2 launch bluerov2_description display.launch.xml   # RViz
```

`rosdep update` refreshes the dependency database; skipping it in fresh
containers is the usual cause of "Cannot locate rosdep definition" errors.
The project standard is `colcon build --merge-install` (one deb style prefix,
the layout users get from binary installs). The default isolated layout also
works if you prefer it.

Each package README documents configuration (variant + accessory loadout),
ROS topics and how to include the model in an existing Gazebo world.

## Development

Optional but recommended: install the pre-commit hooks. They mirror the ament
linters that CI runs (plus basic file hygiene), so a passing pre-commit means a
passing lint stage.

```bash
pip install pre-commit
pre-commit install              # from the repo root; runs on every git commit
```

To check manually at any time:

```bash
pre-commit run --all-files      # everything, staged or not
pre-commit run                  # staged files only
pre-commit run ament_flake8 --all-files   # a single hook
```

The `ament_*` hooks need a sourced ROS environment; some hooks fix files in
place (trailing whitespace, end of file), so re-stage and re-run after a
failure that says "files were modified by this hook".

## License

Apache-2.0 (see [LICENSE](LICENSE)). Reused third-party meshes are credited in
[NOTICE](NOTICE) and `bluerov2_description/ASSETS.md`.
