# Verify the SITL connection

Confirm that ArduRover in SITL is driving the simulated BlueBoat, and that it drives it the right way round. Setup for ArduPilot itself is in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md); this page assumes it is done and the Iris smoke test passed.

Two shells. Both need the colcon workspace and then the ArduPilot environment, in that order: `setup-ardupilot.sh` appends to `GZ_SIM_RESOURCE_PATH`, so the workspace has to be on it first or the boat's meshes will not resolve.

First, the simulation:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v4 -r $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_sitl.sdf
```

Then the autopilot:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
AP=$HOME/maritime_ws/thirdparty/ardupilot/Tools/autotest
sim_vehicle.py -v Rover -f rover-skid --model JSON --console -w \
  --add-param-file=$AP/default_params/rover.parm \
  --add-param-file=$(ros2 pkg prefix --share blueboat_gazebo)/params/blueboat_sitl.params
```

## The checks

At the MAVProxy prompt:

```
mode manual
arm throttle
rc 3 1700
```

| Command | Expected | If not |
|---|---|---|
| `rc 3 1700` | drives straight ahead, both thrusters equal | turning on the spot means one thruster is reversed |
| `rc 1 1700` (no throttle) | spins to starboard on the spot | spinning to port means the port and starboard channels are swapped |
| `rc 1 1300` (no throttle) | spins to port on the spot | should mirror the line above exactly; if one direction spins faster than the other, the two thrusters are not scaled alike |
| `rc 3 1300` | drives astern | |
| `rc all 1500` | stops | |
| `rc clear` | releases the overrides | |



## What the autopilot is doing with those commands

`MANUAL` is not passthrough to the ESC. It bypasses the *controllers* — no speed/heading loops, none of the `ATC_` gains — but the *output mixer* still runs, because it has to. A skid-steer boat has no rudder: differential thrust is the only steering there is, so a steering stick must become a difference between two throttles. There is no frame-level meaning to "steer" that could go straight to one ESC.


**1. RC values, scaled to demand in body-frame** RC3 and RC1 values are not intended for individual PWM channels, but are sematically associated with scaled effort in the body frame with RC3 being trottle (forward effort) and RC1 steering (turn effort).  Each PWM value (0-1900) is scaled by their `RCn_MIN`/`TRIM`/`MAX` into a throttle demand  and a steering demand, still in units of PWM.

**2. Axes to motors,** in `AP_MotorsUGV::output_skid_steering`:

With skid steering enabled in the firmware, the mixing that maps the body-frame effort to 
```
motor_left  = throttle + steering
motor_right = throttle - steering
```

Consider the example,  `rc 3 1700` and `rc 1 1700` together:

Both sticks are 200 µs above center, so both have the the same fraction, so

```
motor_left  = 200 + 200 = 400
motor_right = 200 - 200 = 0
```

**3. Motors to outputs.** `left` is `SERVO3` (`ThrottleLeft`, port) and `right` is `SERVO1` (`ThrottleRight`, starboard), and each fraction becomes PWM through that channel's `SERVOn_MIN`/`TRIM`/`MAX`. With our 1100/1500/1900: port ≈ 1900, starboard = 1500.

**4. Outputs to thrust.** On the real boat those PWM values go down a wire to an ESC. In simulation they go over UDP to `ArduPilotPlugin`, whose `<control>` block maps 1100–1900 onto ±1 and scales to newtons — so the plugin is standing in for the ESC and the propeller together. Port ≈ +40 N, starboard 0 N.

Several parameters still act in `MANUAL`, which is the other half of why it is not passthrough: `MOT_THR_MIN`/`MAX` clip the demand, `MOT_SLEWRATE` rate-limits it, `MOT_STR_THR_MIX` decides who gives way when steering and throttle together would saturate an output, and `MOT_THST_ASYM` scales *negative* outputs up to compensate for a thruster that pushes harder ahead than astern.


To see what the autopilot is actually commanding while you move the sticks, echo the same topics:

```bash
gz topic -e -t /blueboat/motor_port/thrust
gz topic -e -t /blueboat/motor_stbd/thrust
```

Equal positive numbers for throttle alone, equal and opposite for steering alone. 
## What this does not check

Magnitudes. The simulated thruster maps a command symmetrically about stop, and a T200 is not symmetric — it makes roughly 51.5 N ahead against 40.2 N astern. Speeds and accelerations are therefore not meaningful yet, and a boat that reaches the wrong speed at full throttle is expected rather than a defect.

## The parameter files are not optional

Both `--add-param-file` arguments are required, for the reason described in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md): recent ArduPilot resolves frame defaults from the SITL binary's embedded `vehicleinfo.json` keyed by `--model`, not by the `-f` frame name. With `--model JSON` nothing matches and no frame defaults are applied at all.

Order matters, and so does what is left out:

- `rover.parm` first. It carries the SITL side — accelerometer calibration so pre-arm passes, `SIM_PIN_MASK`, the mode slots — but also sets `SERVO1/3_MIN/MAX` to 1000/2000.
- `blueboat_sitl.params` last, so the shipped boat's 1100/1900 range and its throttle assignment win.
- **Not** `rover-skid.parm`. It sets `SERVO1_FUNCTION 73` and `SERVO3_FUNCTION 74`, which is the reverse of the shipped BlueBoat and would swap the thrusters.
