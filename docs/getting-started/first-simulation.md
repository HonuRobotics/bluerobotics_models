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

Or inspect the model and its frames in RViz, without Gazebo:

```bash
ros2 launch blueboat_description display.launch.xml
```

Next: [drive it](../vehicles/blueboat/driving.md), then
[change what is fitted](../vehicles/blueboat/configuration.md).
