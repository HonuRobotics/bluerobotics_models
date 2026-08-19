# Blue Robotics models

ROS 2 / Gazebo Sim model packages for Blue Robotics vehicles: the BlueROV2
underwater vehicle (standard and Heavy configurations) and the BlueBoat USV.
Targets **ROS 2 Lyrical + Gazebo Jetty** (the default pairing on Ubuntu 26.04),
via `ros_gz`.

**Documentation: <https://honurobotics.github.io/bluerobotics_models/>**

The site covers installation, driving each vehicle, accessory configuration,
the ROS interfaces and the design of the parts pipeline.

## Quick start

```bash
cd ~/ws/src && git clone https://github.com/HonuRobotics/bluerobotics_models.git
cd ~/ws
rosdep update
rosdep install --from-paths src --ignore-packages-from-source --default-yes
colcon build --merge-install
source install/setup.bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

## Contributing

Developer workflow (build, tests, pre-commit hooks, conventions):
see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0 (see [LICENSE](LICENSE)). Reused third-party meshes are credited in
[NOTICE](NOTICE) and `bluerov2_description/ASSETS.md`.
