# Teleoperate with a gamepad

`bluerobotics_teleop` drives either vehicle with a standard gamepad:
`joy_node` reads the pad, `teleop_twist_joy` maps the sticks to a
normalized `cmd_vel`, and the `twist_to_thrust` mixer turns that Twist
into per thruster thrust commands through a per vehicle gain matrix. The
stack binds to one vehicle instance, `<name>`: its three nodes and their
topics run under `/<name>`, and the mixer's thruster topics, relative in
its config, land on `/<name>/motor_port/cmd` and the like. Those are the
topics documented in each vehicle's Actuators page
([BlueBoat](../vehicles/blueboat/actuators.md),
[BlueROV2](../vehicles/bluerov2/actuators.md)), so the same launch works
against the simulation or a bridged real vehicle.

```{mermaid}
flowchart LR
  PAD(["gamepad"]) --> JOY["joy_node"]
  JOY -- "/&lt;name&gt;/joy<br/>sensor_msgs/Joy" --> TTJ["teleop_twist_joy_node"]
  TTJ -- "/&lt;name&gt;/cmd_vel<br/>geometry_msgs/Twist, normalized" --> MIX["twist_to_thrust"]
  JOY -- "/&lt;name&gt;/joy<br/>deadman, EPA" --> MIX
  CFG["per vehicle mixer.yaml<br/>gain matrix, command envelope"] -.-> MIX
  MIX -- "one std_msgs/Float64 per thruster<br/>/&lt;name&gt;/motor_*/cmd (boat)<br/>/&lt;name&gt;/thruster_*/cmd (ROV)" --> OUT(["the instance &lt;name&gt;:<br/>simulation or bridged vehicle"])
```

## Configure the gamepad mapping (optional)

A gamepad mapping ties the pad's controls, stick axes and buttons, to the vessel's controllable degrees of freedom: surge, sway, heave and yaw, plus the deadman button and the thrust ceiling (EPA).

The shipped mapping is two files in the package: [joystick.config.yaml](https://github.com/HonuRobotics/bluerobotics_models/blob/lyrical/bluerobotics_teleop/config/pad/joystick.config.yaml), which axis and button drive each motion, read by `teleop_twist_joy`; and [twist_to_thrust.yaml](https://github.com/HonuRobotics/bluerobotics_models/blob/lyrical/bluerobotics_teleop/config/pad/twist_to_thrust.yaml), the deadman button and the EPA control, read by the `twist_to_thrust` mixer. The current version is for a Logitech F310 with the back switch on X and the Mode LED off (lit, it swaps the left stick and the D pad), and follows the ArduSub and QGroundControl layout:

- Deadman: RB
- Heave: left stick up and down (BlueROV2)
- Yaw: left stick left and right
- Surge: right stick up and down
- Sway: right stick left and right (BlueROV2)
- EPA: D pad up and down, 10% per click

Edit those files by hand, or let `joy_map` write them: an interactive walkthrough in the terminal that captures a no touch baseline, then detects each stick and button as you move it, refusing double assignments. Map in the state you will drive in; the walkthrough warns when a stick lands on the D pad's axes.

```bash
ros2 run bluerobotics_teleop joy_map
```

If nothing is publishing Joy messages, the tool starts its own `joy_node`
(with the autorepeat the baseline capture needs) and stops it on exit,
however the walkthrough ends, so there is no background node to forget.
Running the walkthrough next to a live teleop session also works: its
`joy_node` publishes on `/<name>/joy`, and the tool finds and reads that
topic instead of starting a second one.

One walkthrough maps every function (surge, sway, heave, yaw, deadman,
EPA) for every vehicle at once: the mapping describes the pad, not a
vehicle, and a vehicle without a motion zeroes it in its mixer gains.

Saving writes `$ROS_HOME/bluerobotics_teleop/pad/` (default
`~/.ros/...`): the mapping is user state, so it survives rebuilds and
works from a binary install. The teleop launch prefers it over the
defaults shipped with the package and logs which one it loaded; delete
the directory to fall back. The per vehicle mixer config (thruster
topics and gains) is model truth and is never touched by the mapping
tool.

## Run

Hold RB to drive. The thrust ceiling starts at 20%, so the vehicle is sluggish until you press D pad up, 10% per click.

| Argument | Default | What |
|---|---|---|
| `vehicle` | `bluerov2` | Which mixer to load: `bluerov2`, `bluerov2_heavy` or `blueboat` |
| `name` | the vehicle's own name | The instance to drive, the name it was spawned under; the stack runs under `/<name>` |
| `device_id` | `0` | The gamepad `joy_node` opens; a second stack takes a second pad |

Without `name:=`, the stack drives the instance the vehicle's own
`sim.launch.xml` spawns: `blueboat`, or `bluerov2` for both ROV loadouts.

### BlueBoat

Start the simulation ([options](../vehicles/blueboat/running.md)):

```bash
ros2 launch blueboat_gazebo sim.launch.xml
```

Launch teleop:

```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=blueboat
```

### BlueROV2

Start the simulation ([options](../vehicles/bluerov2/running.md)):

```bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

Launch teleop:

```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=bluerov2
```

### A named instance, or two

An instance spawned under another name
([Several vehicles](namespaces.md#a-second-instance-in-the-same-world))
takes `name:=`. Two boats on one ocean, `boat_a` and `boat_b`, get one
stack each, on two gamepads:

```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=blueboat name:=boat_a
```

```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=blueboat name:=boat_b device_id:=1
```

Each stack publishes only under its name, so the pads never cross:

```bash
ros2 topic list | grep cmd
```

```text
/boat_a/cmd_vel
/boat_a/motor_port/cmd
/boat_a/motor_stbd/cmd
/boat_b/cmd_vel
/boat_b/motor_port/cmd
/boat_b/motor_stbd/cmd
```

## Safety behavior

- **Deadman**: holding the deadman button (RB by default) is required for
  any output; releasing it zeroes every thruster immediately.
- **Command timeout**: a stale `/<name>/cmd_vel` zeroes every thruster.
- **EPA (end point adjustment)**: the thrust ceiling starts at 20% and is
  stepped in 10% increments from the D pad, so full thrust is opt in.
- **50 Hz republish**: latched commands downstream can never go stale.

## Troubleshooting

Confirm `joy_node` can see the pad at all.

```bash
ros2 run joy joy_enumerate_devices
```

which lists the pad:

```text
ID : GUID                             : GamePad : Mapped : Joystick Device Name
-------------------------------------------------------------------------------
 0 : 030005ff6d0400001dc2000014400000 :    true :   true : Logitech F310 Gamepad (XInput)
```

If the table is empty, check that the host sees the pad:

```bash
ls /dev/input/by-id/ | grep -i joystick
```

Once the pad enumerates, confirm messages are flowing. With teleop running, on the instance's topic (`/joy` for a bare `ros2 run joy joy_node`):

```bash
ros2 topic echo /blueboat/joy
```

`axes` and `buttons` should change as you move the sticks. If they do, the pad and `joy_node` are fine and any remaining problem is downstream: the mapping, the deadman, or the mixer. If the pad enumerates but `/joy` stays silent, check that your user can read the device; `/dev/input/event*` is normally group `input`.
