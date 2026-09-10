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

## (Optional) Configure gamepad mapping (optional)

 The project includes a standalone utility program, written as a ROS node, to interactively configure a gamepad mapping via a curses walkthrough.  The gamepad mapping describes the connection between the gamepad functions (joystick axes, buttons, etc.) to the controllable degrees of freedom of a maritime vessel (surge, sway, heave; yaw). 

The shipped mapping % CLAUDE: what is the shipped mapping?  link to the file or files  if it is in this repo
is for a Logitech Gamepad 310 (with back selector switch on 'X') with the following convention:
- Deadman: RB
- Surge: Left stick fwd/rev
- Sway: Right stick left/right
- Heave: Right stick up/down
- Yaw: Left stick left/right

The mapping is expressed in the two config files % CLAUDE: link here
As an alternative to manual editing the files, the standalone `joy_map` utility 
is an interative curses walkthrough to write these files to user-space (e.g., `~/.ros/...`).
The utility runs in a terminal screen that
captures a no touch baseline, then detects each stick and button as you
move it, refusing double assignments.

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

## Run teleop examples

### BlueBoat

[Run the simulation](../vehicles/blueboat/running.md)
```bash
ros2 launch blueboat_gazebo sim.launch.xml
```

Launch teleop
```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=blueboat
```

### BlueROV

[Run the simulation](../vehicles/bluerov2/running.md)
```bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

Launch teleop
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



## Troubleshooting gamepad

Confirm `joy_node` can see the pad at all. 

```bash
ros2 run joy joy_enumerate_devices
```

Which should identify your device, similar to this
```
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

`axes` and `buttons` should change as you move the sticks. A pad that enumerates but publishes nothing is connected, so the problem is downstream: the mapping, the deadman, or the mixer.