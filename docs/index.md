# BlueRobotics Models

Simulation ready models of the [Blue Robotics](https://bluerobotics.com)
vehicles for **ROS 2** and **Gazebo**. Each vehicle is assembled from a
shared library of parts (hulls, thrusters, propellers, brackets, sensors),
ships as a complete default model that needs no configuration, and can be
reconfigured from one YAML file when you want different parts.

- **BlueBoat**: twin hull differential drive USV with the Ping2 echosounder
  fitted by default: [BlueBoat manual](vehicles/blueboat/index.md)
- **BlueROV2**: vectored six or eight thruster ROV with camera, sonar, DVL and
  manipulator parts: [BlueROV2 manual](vehicles/bluerov2/index.md)

## Where to start

- Users: the [Quickstarts](quickstarts/index.md) take you from a clean machine to a running simulation, a boat driven by ArduRover and a ROV diving under ArduSub. The [Walkthroughs](walkthroughs/index.md) then take one capability at a time: tuning, a waypoint mission, changing the fitted parts, worlds, several vehicles, teleoperation.
- Reference: one manual per vehicle ([BlueBoat](vehicles/blueboat/index.md), [BlueROV2](vehicles/bluerov2/index.md)) with launch arguments, topics and configuration, and the [parts catalog](reference/parts-catalog.md).
- Developers: [design](developers/design/index.md), the SITL spec, vehicle parameter derivations, extending the parts library and [contributing](developers/contributing.md).

These models target **ROS 2 Lyrical** and **Gazebo Jetty** on Ubuntu 26.04, built from source in the drydock container.
Use the version flyout (lower left) to switch documentation between ROS
distributions.

```{toctree}
:hidden:
:caption: Users

Quickstarts <quickstarts/index>
Walkthroughs <walkthroughs/index>
Troubleshooting <walkthroughs/troubleshooting>
```

```{toctree}
:hidden:
:caption: Reference

Vehicles <vehicles/index>
Parts catalog <reference/index>
```

```{toctree}
:hidden:
:caption: Developers

Developers <developers/index>
```
