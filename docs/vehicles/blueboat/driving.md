# Driving the BlueBoat

The boat is driven by thrust commands, in newtons, to its two propellers.
Equal thrust drives ahead; differential thrust yaws (more starboard thrust
turns to port and vice versa). Each propeller part in the loadout gets a
thrust topic named after it, `/<namespace>/<name>/thrust`; the default
loadout fits `motor_port` and `motor_stbd`.

## ROS topics

| Topic | Type | Notes |
|---|---|---|
| `/blueboat/motor_port/thrust` | `std_msgs/msg/Float64` | newtons, clamped to the propeller's limits (about +51 / -40 N) |
| `/blueboat/motor_stbd/thrust` | `std_msgs/msg/Float64` | same |
| `/joint_states` | `sensor_msgs/msg/JointState` | `motor_port_joint`, `motor_stbd_joint` speeds, for RViz |

```bash
ros2 topic pub /blueboat/motor_port/thrust std_msgs/msg/Float64 "data: 20.0" -1 &
ros2 topic pub /blueboat/motor_stbd/thrust std_msgs/msg/Float64 "data: 20.0" -1 &
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
| `/blueboat/motor_<side>/thrust` | `gz.msgs.Double` | command (the same name the bridge exposes on ROS) |
| `/blueboat/motor_<side>/thrust/ang_vel` | `gz.msgs.Double` | propeller speed feedback, rad/s |

```bash
gz topic -t /blueboat/motor_port/thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /blueboat/motor_stbd/thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```

The topic namespace (`blueboat`) and the per part topic names are set in
the loadout config; see [Topics](../../reference/topics.md). Fit a
different propeller, rename it or leave a motor slot empty and the thrust
topics follow the loadout.
