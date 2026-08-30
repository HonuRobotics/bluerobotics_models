# Actuators

Actuators are parts fitted into slots, exactly like the sensors. The
concepts live in [Slots and assembly](../../design/slots.md), the
vehicle's slots and their accepted types in the
[configuration page](configuration.md), and new parts can be added
following the [Add a part](../../how-to/add-part.md) guide.

## Available actuators

| Actuator | Part | Slot | Fitted by default |
|---|---|---|---|
| T200 thrusters, vectored horizontals | `t200_prop_ccw` / `t200_prop_cw` | `thruster_1` .. `thruster_4` | yes |
| T200 thrusters, verticals | `t200_prop_ccw` / `t200_prop_cw` | `thruster_5`, `thruster_6` | yes |
| T200 thrusters, verticals (heavy variant only) | `t200_prop_ccw` / `t200_prop_cw` | `thruster_7`, `thruster_8` | heavy only |
| Newton gripper | `newton_gripper` | `gripper` | no |
| Sediment sampler | `sediment_sampler` | `gripper` | no |

## Actuators ROS API

### Thrusters (`thruster_<n>` slots)

```{figure} images/thrusters.png
:alt: Thruster numbering on the standard vehicle and the heavy variant, top view

Thruster numbering, top view.
```

Each thruster plugin subscribes to a gz transport topic. Each of those gz
topics is bridged to ROS and indexed by number, starting at 1:

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/thruster_<n>/thrust` | Thrust command in newtons, clamped to the propeller's limits | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |

```bash
ros2 topic pub /bluerov2/thruster_1/thrust std_msgs/msg/Float64 "data: -10.0" -1
```

The horizontal thrusters (1-4) are vectored at 45 degrees, so single-axis
motion needs a mix with these signs:

| motion | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|--------|----|----|----|----|----|----|----|----|
| surge +x (forward) | - | - | + | + | 0 | 0 | 0 | 0 |
| sway +y (left) | - | + | - | + | 0 | 0 | 0 | 0 |
| yaw +z (counterclockwise) | - | + | + | - | 0 | 0 | 0 | 0 |
| heave +z (up) | 0 | 0 | 0 | 0 | - | - | - | - |

On the heavy variant all four corner verticals share heave; differential
use of its verticals also gives it roll and pitch authority the standard
vehicle does not have.

```{admonition} Command all thrusters together
:class: warning

Bringing thrusters up one command at a time leaves the wrench unbalanced
while the remaining commands arrive, yawing the vehicle off its heading
before it translates. Controllers that publish continuously (teleop,
ArduPilot, MAVROS) are unaffected. Stop by publishing `data: 0.0` to all
thrusters.
```

### Grippers (`newton_gripper` / `sediment_sampler`, `gripper` slot)

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/gripper/cmd_pos` | Jaw angle command, 0 rad closed to 0.6 rad open (subscribed) | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |

## Gazebo transport API

The same topics exist on the Gazebo side (the bridge exposes them to ROS
under the same names), plus a speed feedback per thruster:

| gz Topic | Description | Message type |
|---|---|---|
| `/bluerov2/thruster_<n>/thrust` | Thrust command in newtons (subscribed) | `gz.msgs.Double` |
| `/bluerov2/thruster_<n>/thrust/ang_vel` | Propeller speed feedback (rad/s) | `gz.msgs.Double` |
| `/bluerov2/gripper/cmd_pos` | Jaw angle command (subscribed) | `gz.msgs.Double` |

Command the mix **together** (`&` + `wait` publishes in parallel):

```bash
# surge forward at ~28 N
gz topic -t /bluerov2/thruster_1/thrust -m gz.msgs.Double -p 'data: -10.0' &
gz topic -t /bluerov2/thruster_2/thrust -m gz.msgs.Double -p 'data: -10.0' &
gz topic -t /bluerov2/thruster_3/thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /bluerov2/thruster_4/thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```
