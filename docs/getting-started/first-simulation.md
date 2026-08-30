# First simulation

Bring up the BlueBoat with the full ROS stack (Gazebo server, ros_gz bridge,
robot_state_publisher and the Gazebo GUI):

```bash
ros2 launch blueboat_gazebo sim.launch.xml
```

The simulation starts running, with the camera a few meters off the boat's
port quarter. The boat is spawned at its static waterline and floats there:
two hulls, the two outboard propellers, the flag and the Ping2 echosounder
fitted under the starboard hull. That is the default loadout; no
configuration was involved.

In a second terminal (also sourced), watch the echosounder and spin the
propellers:

```bash
ros2 topic echo /blueboat/ping/range --once
ros2 topic pub /blueboat/motor_port/thrust std_msgs/msg/Float64 "data: 10.0" -1 &
ros2 topic pub /blueboat/motor_stbd/thrust std_msgs/msg/Float64 "data: 10.0" -1 &
wait
```

The BlueROV2 equivalent is `ros2 launch bluerov2_gazebo sim.launch.xml`,
which spawns the ROV hovering near the surface of its pool.

Next: [drive it](../vehicles/blueboat/actuators.md), then
[change what is fitted](../vehicles/blueboat/configuration.md). Each
vehicle's Running page
([BlueBoat](../vehicles/blueboat/running.md),
[BlueROV2](../vehicles/bluerov2/running.md)) covers worlds, custom
loadouts and RViz.
