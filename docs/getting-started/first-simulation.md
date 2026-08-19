# First simulation

Bring up the BlueROV2 with the full ROS stack (Gazebo server, bridge,
robot_state_publisher and the GUI):

```bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

The world starts **paused** — press play. The near-neutral vehicle drifts up
very slowly until it floats essentially awash at the surface.

In a second terminal (also sourced), watch the camera:

```bash
ros2 topic echo /bluerov2/camera/camera_info --once
```

Next: [drive it](../vehicles/bluerov2/driving.md).
