# BlueRobotics Models

Simulation ready models of the [Blue Robotics](https://bluerobotics.com)
vehicles for **ROS 2** and **Gazebo**. Each vehicle is assembled from a
shared library of parts (hulls, thrusters, propellers, brackets, sensors),
ships as a complete default model that needs no configuration, and can be
reconfigured from one YAML file when you want the exact loadout.

- **BlueBoat**: twin hull differential drive USV with the Ping2 echosounder
  fitted by default: [BlueBoat manual](vehicles/blueboat/index.md)
- **BlueROV2**: vectored six or eight thruster ROV with camera, sonar, DVL and
  manipulator accessories: [BlueROV2 manual](vehicles/bluerov2/index.md)
  (being moved onto the parts pipeline; its pages still describe the
  previous accessory system)

## Quick start

```bash
mkdir -p ~/ws/src
cd ~/ws/src && git clone https://github.com/HonuRobotics/bluerobotics_models.git
cd ~/ws && rosdep update && rosdep install --from-paths src --ignore-packages-from-source --default-yes
colcon build --merge-install
source install/setup.bash
ros2 launch blueboat_gazebo sim.launch.xml
```

Press play in Gazebo: the BlueBoat floats at its waterline, the propellers
take thrust commands and the echosounder streams ranges. Nothing to
configure; [First simulation](getting-started/first-simulation.md) walks
through it, [Configuring the BlueBoat](vehicles/blueboat/configuration.md)
shows how to change the loadout, and [Design](design/index.md) explains how
parts, slots and the generated models fit together.

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
