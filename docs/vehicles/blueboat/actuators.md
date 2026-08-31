# Actuators

Actuators are parts fitted into slots, exactly like the sensors. The
concepts live in [Slots and assembly](../../design/slots.md), the
vehicle's slots and their accepted types in the
[configuration page](configuration.md), and new parts can be added
following the [Add a part](../../how-to/add-part.md) guide.

## Available actuators

| Actuator | Part | Slot | Fitted by default |
|---|---|---|---|
| M200 weedless propellers | `m200_weedless_prop_ccw` / `_cw` | `motor_port`, `motor_stbd` | yes |
| T200 propellers | `t200_prop_ccw` / `_cw` | `motor_port`, `motor_stbd` | no |

## Actuators ROS API

### Thrusters

Each thruster plugin subscribes to a gz transport topic. Each of those gz
topics is bridged to ROS and named after its motor:

| ROS Topic | Description | Message type |
|---|---|---|
| `/blueboat/motor_port/thrust` | Thrust command in newtons, clamped to the propeller's limits | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |
| `/blueboat/motor_stbd/thrust` | Thrust command in newtons, clamped to the propeller's limits | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |

Equal thrust drives ahead; differential thrust yaws (more starboard
thrust turns to port and vice versa). To manually send thruster commands
via ROS:

```bash
ros2 topic pub /blueboat/motor_port/thrust std_msgs/msg/Float64 "data: 20.0" -1 &
ros2 topic pub /blueboat/motor_stbd/thrust std_msgs/msg/Float64 "data: 20.0" -1 &
wait
```

```{admonition} Command both motors together
:class: warning

Commands **latch**: each motor holds its last command until a new one
arrives, and bringing the motors up one command at a time applies a
differential wrench while the second command is in flight, yawing the
boat off its heading. The `&` + `wait` above publishes in parallel;
controllers that publish continuously are unaffected. Stop with
`data: 0.0` to both.
```


To drive with a gamepad instead, a ready mixer for either vehicle is in
[Teleoperate with a gamepad](../../how-to/teleop.md).

## Gazebo transport API

The same topics exist on the Gazebo side (the bridge exposes them to ROS
under the same names), plus a speed feedback per motor:

| gz Topic | Description | Message type |
|---|---|---|
| `/blueboat/motor_<side>/thrust` | Thrust command in newtons | `gz.msgs.Double` |
| `/blueboat/motor_<side>/thrust/ang_vel` | Propeller speed feedback (rad/s) | `gz.msgs.Double` |

```bash
gz topic -t /blueboat/motor_port/thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /blueboat/motor_stbd/thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```

Topic bases follow `/<namespace>/<instance>/...`: fit a different
propeller, rename it or leave a motor slot empty and the thrust topics
follow the fitted parts.
