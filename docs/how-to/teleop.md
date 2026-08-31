# Teleoperate with a gamepad

`bluerobotics_teleop` drives either vehicle with a standard gamepad:
`joy_node` reads the pad, `teleop_twist_joy` maps the sticks to a
normalized `/cmd_vel`, and the `twist_to_thrust` mixer turns that Twist
into per thruster thrust commands through a per vehicle gain matrix. The
thrust topics it publishes are the ones documented in each vehicle's
Actuators page ([BlueBoat](../vehicles/blueboat/actuators.md),
[BlueROV2](../vehicles/bluerov2/actuators.md)), so the same launch works
against the simulation or a bridged real vehicle.

## Run

Start a simulation, then:

```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=bluerov2   # or blueboat
```

Left stick: surge and yaw. Right stick (BlueROV2): sway and heave.

## Safety behavior

- **Deadman**: holding the deadman button (RB by default) is required for
  any output; releasing it zeroes every thruster immediately.
- **Command timeout**: a stale `/cmd_vel` zeroes every thruster.
- **EPA (end point adjustment)**: the thrust ceiling starts at 20% and is
  stepped in 10% increments from the D pad, so full thrust is opt in.
- **50 Hz republish**: latched commands downstream can never go stale.

## Map a different gamepad

The shipped mapping matches the pad it was last mapped with. For a
different pad, run the mapping walkthrough: a terminal screen that
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
Saving rewrites `config/pad/joystick.config.yaml` and
`twist_to_thrust.yaml` in the package's installed share (with a symlink
install that is the repository copy: commit it to keep the mapping).
The per vehicle mixer config (thruster topics and gains) is model truth
and is never touched by the mapping tool.
