# BlueRobotics Models

Simulation-ready models of the [Blue Robotics](https://bluerobotics.com)
vehicles for **ROS 2** and **Gazebo**: vehicle descriptions, sensors, thrust
interfaces, worlds and a config-driven accessory system.

- **BlueROV2** — vectored six or eight thruster ROV with camera, sonar, DVL and
  manipulator accessories: [BlueROV2 manual](vehicles/bluerov2/index.md)
- **BlueBoat** — twin-hull differential-drive USV with echosounder and survey
  accessories: [BlueBoat manual](vehicles/blueboat/index.md)

## Quick start

```bash
cd ~/ws/src && git clone https://github.com/HonuRobotics/bluerobotics_models.git
cd ~/ws && rosdep update && rosdep install --from-paths src --ignore-packages-from-source --default-yes
colcon build --merge-install
source install/setup.bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

These models target **ROS 2 Lyrical** and **Gazebo Jetty** on Ubuntu 26.04.
Use the version flyout (lower left) to switch documentation between ROS
distributions.

```{toctree}
:hidden:
:maxdepth: 4

Getting started <getting-started/index>
Vehicles <vehicles/index>
How-to guides <how-to/index>
Reference <reference/index>
Design <design/index>
Project <project/index>
```
