# Teleoperate with a gamepad

`bluerobotics_teleop` drives either vehicle with a standard gamepad:
`joy_node` reads the pad, `teleop_twist_joy` maps the sticks to a
normalized `/cmd_vel`, and the `twist_to_thrust` mixer turns that Twist
into per thruster thrust commands through a per vehicle gain matrix. The
thrust topics it publishes are the ones documented in each vehicle's
Actuators page ([BlueBoat](../vehicles/blueboat/actuators.md),
[BlueROV2](../vehicles/bluerov2/actuators.md)), so the same launch works
against the simulation or a bridged real vehicle.

```{mermaid}
flowchart LR
  PAD(["gamepad"]) --> JOY["joy_node"]
  JOY -- "/joy<br/>sensor_msgs/Joy" --> TTJ["teleop_twist_joy_node"]
  TTJ -- "/cmd_vel<br/>geometry_msgs/Twist, normalized" --> MIX["twist_to_thrust"]
  JOY -- "/joy<br/>deadman, EPA" --> MIX
  CFG["per vehicle mixer.yaml<br/>gain matrix, thrust limits"] -.-> MIX
  MIX -- "one std_msgs/Float64 per thruster<br/>/blueboat/motor_*/thrust<br/>/bluerov2/thruster_*/thrust" --> OUT(["simulation or<br/>bridged vehicle"])
```

## Configure the gamepad mapping (optional)

A gamepad mapping ties the pad's controls, stick axes and buttons, to the vessel's controllable degrees of freedom: surge, sway, heave and yaw, plus the deadman button and the thrust ceiling (EPA).

The shipped mapping is two files in the package: [joystick.config.yaml](https://github.com/HonuRobotics/bluerobotics_models/blob/lyrical/bluerobotics_teleop/config/pad/joystick.config.yaml), which axis and button drive each motion, read by `teleop_twist_joy`; and [twist_to_thrust.yaml](https://github.com/HonuRobotics/bluerobotics_models/blob/lyrical/bluerobotics_teleop/config/pad/twist_to_thrust.yaml), the deadman button and the EPA axis, read by the mixer. It follows the SDL game controller layout, so it fits any pad that `joy_enumerate_devices` reports as `Mapped: true`. It was made with a Logitech F310 with the back switch on X, and reads:

- Deadman: RB
- Surge: left stick forward and back
- Sway: right stick left and right
- Heave: right stick up and down
- Yaw: left stick left and right

Edit those files by hand, or let `joy_map` write them: an interactive walkthrough in the terminal that captures a no touch baseline, then detects each stick and button as you move it, refusing double assignments.

```bash
ros2 run bluerobotics_teleop joy_map
```

If nothing is publishing `/joy`, the tool starts its own `joy_node`
(with the autorepeat the baseline capture needs) and stops it on exit,
however the walkthrough ends, so there is no background node to forget.
Running the walkthrough next to a live teleop session also works: its `joy_node`
is detected and reused.

One walkthrough maps every function (surge, sway, heave, yaw, deadman,
EPA) for every vehicle at once: the mapping describes the pad, not a
vehicle, and a vehicle without a motion zeroes it in its mixer gains.

Saving writes `$ROS_HOME/bluerobotics_teleop/pad/` (default
`~/.ros/...`): the mapping is user state, so it survives rebuilds and
works from a binary install. The teleop launch prefers it over the
defaults shipped with the package and logs which one it loaded; delete
the directory to fall back. To make a mapping the new shipped default,
copy the files into the repository at `bluerobotics_teleop/config/pad/`
and commit. The per vehicle mixer config (thruster topics and gains) is
model truth and is never touched by the mapping tool.

## Run

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

## Safety behavior

- **Deadman**: holding the deadman button (RB by default) is required for
  any output; releasing it zeroes every thruster immediately.
- **Command timeout**: a stale `/cmd_vel` zeroes every thruster.
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

Once the pad enumerates, confirm messages are flowing. With teleop running, or `ros2 run joy joy_node` on its own:

```bash
ros2 topic echo /joy
```

`axes` and `buttons` should change as you move the sticks. If they do, the pad and `joy_node` are fine and any remaining problem is downstream: the mapping, the deadman, or the mixer. If the pad enumerates but `/joy` stays silent, check that your user can read the device; `/dev/input/event*` is normally group `input`.
