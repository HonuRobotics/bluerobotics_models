# Driving the BlueBoat

The boat is driven by thrust commands, in newtons, to its two outboard
motors. Equal thrust drives ahead; differential thrust yaws (more starboard
thrust turns to port and vice versa).

## ROS topics

| Topic | Type | Notes |
|---|---|---|
| `/blueboat/thrusters/port/thrust` | `std_msgs/msg/Float64` | newtons, clamped to the T200 limits (about +51 / -40 N) |
| `/blueboat/thrusters/stbd/thrust` | `std_msgs/msg/Float64` | same |
| `/joint_states` | `sensor_msgs/msg/JointState` | `motor_port_joint`, `motor_stbd_joint` speeds, for RViz |

```bash
ros2 topic pub /blueboat/thrusters/port/thrust std_msgs/msg/Float64 "data: 20.0" -1 &
ros2 topic pub /blueboat/thrusters/stbd/thrust std_msgs/msg/Float64 "data: 20.0" -1 &
wait
```

Commands **latch**: each motor holds its last command until a new one
arrives. Command both motors together (the `&` + `wait` above publishes in
parallel); bringing them up one command at a time applies a differential
wrench while the second command is in flight and yaws the boat off its
heading. Controllers that publish continuously are unaffected. Stop with
`data: 0.0` to both.

## Gazebo transport (no ROS)

| gz topic | Type | Direction |
|---|---|---|
| `/model/blueboat/joint/motor_<side>_joint/cmd_thrust` | `gz.msgs.Double` | command (what the bridge maps the ROS topics to) |
| `/model/blueboat/joint/motor_<side>_joint/ang_vel` | `gz.msgs.Double` | propeller speed feedback, rad/s |

```bash
gz topic -t /model/blueboat/joint/motor_port_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /model/blueboat/joint/motor_stbd_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```

The topic namespace (`blueboat`) and the per sensor topic names are set in
the loadout config; see [Topics](../../reference/topics.md).
