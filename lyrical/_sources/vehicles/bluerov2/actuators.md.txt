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

### Thrusters

```{figure} images/thrusters.png
:alt: Thruster numbering on the standard vehicle and the heavy variant, top view

Thruster numbering, top view.
```

Each thruster plugin subscribes to a gz transport topic. Each of those gz
topics is bridged to ROS and indexed by number, starting at 1:

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/thruster_<n>/cmd` | Normalized thrust command in [-1, 1]: +1 full ahead, -1 full astern, 0 stop | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |

The command is a fraction of the propeller's own limits, which the model
takes from the part's drive table - 51.5 N ahead and -40.2 N astern for a
T200 at 16 V. The two directions scale independently, so +0.5 and -0.5 are
equal command and unequal force. Values outside [-1, 1] are clamped.

To manually send a thruster command via ROS:

```bash
ros2 topic pub /bluerov2/thruster_1/cmd std_msgs/msg/Float64 "data: -0.2" -1
```

The layout follows ArduSub's
[Vectored frame](https://ardupilot.org/sub/docs/sub-frames.html)
(Vectored-6DOF on the heavy variant); the numbering in simulation is the
figure above. The horizontal thrusters (1-4) are vectored at 45 degrees,
so single-axis motion needs a mix with these signs:

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

### Grippers

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/gripper/cmd_pos` | Jaw angle command, 0 rad closed to 0.6 rad open | [std_msgs/msg/Float64](https://docs.ros.org/en/rolling/p/std_msgs/interfaces/msg/Float64.html) |


To drive with a gamepad instead, a ready mixer for either vehicle is in
[Teleoperate with a gamepad](../../how-to/teleop.md).

## Gazebo transport API

The same topics exist on the Gazebo side (the bridge exposes them to ROS
under the same names), plus a speed feedback per thruster:

| gz Topic | Description | Message type |
|---|---|---|
| `/bluerov2/thruster_<n>/cmd` | Normalized thrust command in [-1, 1] | `gz.msgs.Double` |
| `/bluerov2/thruster_<n>/cmd/ang_vel` | Propeller speed feedback (rad/s) | `gz.msgs.Double` |
| `/bluerov2/gripper/cmd_pos` | Jaw angle command | `gz.msgs.Double` |

Command the mix **together** (`&` + `wait` publishes in parallel):

```bash
# surge forward at 20 percent command on the four horizontals
gz topic -t /bluerov2/thruster_1/cmd -m gz.msgs.Double -p 'data: -0.2' &
gz topic -t /bluerov2/thruster_2/cmd -m gz.msgs.Double -p 'data: -0.2' &
gz topic -t /bluerov2/thruster_3/cmd -m gz.msgs.Double -p 'data: 0.2' &
gz topic -t /bluerov2/thruster_4/cmd -m gz.msgs.Double -p 'data: 0.2' &
wait
```
