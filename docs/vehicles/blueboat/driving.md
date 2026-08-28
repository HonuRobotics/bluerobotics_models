# Driving the BlueBoat

The boat is driven per propeller. Equal commands drive ahead; differential
commands yaw (more starboard thrust turns to port and vice versa). Each
propeller part in the loadout gets its topics named after it,
`/<namespace>/<name>/...`; the default loadout fits `motor_port` and
`motor_stbd`.

The primary interface is the normalized throttle, the convention real
drivers and autopilots use (ArduPilot scales every motor output to -1..1;
an ESC cannot honor a force setpoint, since actual thrust depends on
battery voltage and propeller state). In simulation the -1..1 command maps
linearly onto the thrust limits the propeller part declares; note the real
thrust to throttle curve is not linear, so half throttle is more than half
real world thrust.

## ROS topics

| Topic | Type | Notes |
|---|---|---|
| `/blueboat/motor_<side>/throttle` | `std_msgs/msg/Float64` | normalized -1..1, mapped onto the part's limits (about +51 / -40 N); out of range clamps |
| `/blueboat/motor_<side>/thrust` | `std_msgs/msg/Float64` | low level: newtons, clamped to the propeller's limits |
| `/joint_states` | `sensor_msgs/msg/JointState` | `motor_port_joint`, `motor_stbd_joint` speeds, for RViz |

```bash
ros2 topic pub /blueboat/motor_port/throttle std_msgs/msg/Float64 "data: 0.4" -1 &
ros2 topic pub /blueboat/motor_stbd/throttle std_msgs/msg/Float64 "data: 0.4" -1 &
wait
```

Commands **latch**: each motor holds its last command until a new one
arrives. Command both motors together (the `&` + `wait` above publishes in
parallel); bringing them up one command at a time applies a differential
wrench while the second command is in flight and yaws the boat off its
heading. Controllers that publish continuously are unaffected. Stop with
`data: 0.0` to both. Throttle and thrust land on the same latched plugin
input, whichever was published last wins.

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
