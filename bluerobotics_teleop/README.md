# bluerobotics_teleop

Gamepad teleoperation for the BlueROV2 and the BlueBoat.

Pipeline: `joy_node` reads the pad, `teleop_twist_joy` maps sticks to a
normalized `/cmd_vel`, and `twist_to_thrust` mixes that Twist into per
thruster commands through a per vehicle gain matrix. Safety behavior:
holding the deadman button (RB by default) is required for any output,
stale commands time out to zero thrust, and the thrust ceiling starts at
20% and is stepped with the D pad (EPA), so full thrust is opt in.

## Run

Start a simulation, then:

```bash
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=bluerov2
ros2 launch bluerobotics_teleop teleop.launch.py vehicle:=blueboat
```

Left stick: surge and yaw. Right stick (BlueROV2): sway and heave.

## Calibrate a different gamepad

```bash
ros2 run bluerobotics_teleop joy_calibrate --vehicle bluerov2
```

The tool starts its own joy_node (with the autorepeat the baseline
capture needs) when nothing is publishing `/joy`, and stops it on exit —
there is no background node to forget, which used to break the next
teleop session. Calibrating next to a running teleop session also works:
its joy_node is detected and reused.

The walkthrough detects each control against a no touch baseline and
rewrites `config/<vehicle>/joystick.config.yaml` and
`twist_to_thrust.yaml`. The mixer config (thruster topics and gains) is
model truth and is never touched by calibration.
