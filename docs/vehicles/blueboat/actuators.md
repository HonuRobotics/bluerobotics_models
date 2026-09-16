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
topics is bridged to ROS and named after its motor, under the instance
name, `<name>`: `blueboat` for the default instance, which the commands
below use, or whatever the boat was spawned as
([Several vehicles](../../how-to/namespaces.md)).

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/motor_port/cmd` | Normalized thrust command in [-1, 1]: +1 full ahead, -1 full astern, 0 stop | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |
| `/<name>/motor_stbd/cmd` | Normalized thrust command in [-1, 1]: +1 full ahead, -1 full astern, 0 stop | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |

The command is a fraction of the propeller's own limits, which the model
takes from the part's drive table - 51.5 N ahead and -40.2 N astern for a
T200 at 16 V. The two directions scale independently, so +0.5 and -0.5 are
equal command and unequal force. Values outside [-1, 1] are clamped.

Equal command drives ahead; differential command yaws (more starboard
turns to port and vice versa). To manually send thruster commands via ROS:

```bash
ros2 topic pub /blueboat/motor_port/cmd std_msgs/msg/Float64 "data: 0.4" -1 &
ros2 topic pub /blueboat/motor_stbd/cmd std_msgs/msg/Float64 "data: 0.4" -1 &
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
| `/<name>/motor_<side>/cmd` | Normalized thrust command in [-1, 1] | `gz.msgs.Double` |
| `/<name>/motor_<side>/cmd/ang_vel` | Propeller speed feedback (rad/s) | `gz.msgs.Double` |

```bash
gz topic -t /blueboat/motor_port/cmd -m gz.msgs.Double -p 'data: 0.2' &
gz topic -t /blueboat/motor_stbd/cmd -m gz.msgs.Double -p 'data: 0.2' &
wait
```

A command topic follows the part's own name: fit a different propeller,
rename it or leave a motor slot empty and the topics follow the fitted
parts ([Configuration](configuration.md)).
