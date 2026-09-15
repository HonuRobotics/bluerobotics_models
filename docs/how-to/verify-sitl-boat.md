# Verify the SITL connection (Boat)

Confirm that ArduRover in SITL is driving the simulated BlueBoat in `MANUAL` mode, which means throttle and steering commands are provided via RC channels and ArduRover mixes them into the two thruster commands.

## Prereqs

* Setup for ArduPilot itself is in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md).
* The workspace is built and sourced. See [Installation](../getting-started/installation.md).
* The steps below were run in the [drydock](https://github.com/HonuRobotics/drydock) container, started with `drydock run maritime`. They should work on a host set up per [Requirements](../getting-started/requirements.md) as well.  Currently untested.

## Two shells: sim and autopilot

### The simulation

Start the boat sim

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v4 -r $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_sitl.sdf
```

If successful, you should see Gazebo start with the boat floating at its waterline.

### The autopilot (SITL)

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
AP=$HOME/maritime_ws/thirdparty/ardupilot/Tools/autotest
sim_vehicle.py -v Rover -f rover-skid --model JSON --console -w \
  --add-param-file=$AP/default_params/rover.parm \
  --add-param-file=$(ros2 pkg prefix --share blueboat_gazebo)/params/blueboat_sitl.params
```

```{note}
Gazebo prints `ArduPilot controller has reset` once shortly after SITL
connects and then roughly once a minute.  This is annoying, but not of concern. (The fix is open upstream as
[ardupilot_gazebo#174](https://github.com/ArduPilot/ardupilot_gazebo/pull/174).)
See troubleshooting notes in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md).
```

## Verification

One axis at a time, at the MAVProxy prompt in the autopilot shell.

Throttle ahead...
```
mode manual
arm throttle
rc 3 1700
```

`rc <channel> <microseconds>` overrides one RC input. Channel 3 is throttle and channel 1 is steering, which are ArduRover's ordinary assignments - none of ArduSub's channel remapping applies to the boat. Both span 1100 to 1900; 1500 is neutral.

Send `rc all 1500` between checks.

Directions are in the vehicle's own frame, [REP 103](https://www.ros.org/reps/rep-0103.html): x forward, y left, z up. "Turns to starboard" and "negative yaw" describe the same motion.

| Command | Axis | Expected |
|---|---|---|
| `rc 3 1700` | surge | drives straight ahead, both thrusters equal |
| `rc 3 1300` | surge | drives astern |
| `rc 1 1700` | yaw | spins to starboard on the spot, clockwise seen from above |
| `rc 1 1300` | yaw | spins to port, mirroring the line above |
| `rc all 1500` | — | stops |

```{important}
The check passes when each RC channel, commanded on its own, produces the
motion named above and no other. Work through every row: which channel
carries which axis, and which way positive points, are conventions rather
than standards, and they have to agree between the simulation and ArduRover
for the boat to answer the stick it is given. Nothing errors when they
disagree - the boat arms, drives, and does the wrong thing.
```

Two failures are worth naming because they look alike from the helm. Turning on the spot when you asked for throttle means one thruster is reversed. Spinning the wrong way when you asked for steering means the port and starboard channels are swapped. And if the two steering directions do not mirror each other, the thrusters are not scaled alike.

Unlike the ROV, the commands here are a half of full stick rather than a few percent, and the boat still responds more briskly than a real one would. Nothing has been tuned yet: the hull's hydrodynamic damping coefficients have never been identified. That is a later phase of the plan and out of scope here - this page is only checking that the wiring is correct.

## Background

The walkthrough ends here. What follows explains how a stick position (RC channel) becomes thrust.  It is worth reading if a check above did not do what it should, or if you are changing the model, the frame or the parameter file and need to know which layer owns what.  Also helpful for agents to read and share.  This is the background we needed to (re)learn while developing this walkthrough.

### What the autopilot is doing with those commands

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
gz topic -e -t /blueboat/motor_port/cmd
gz topic -e -t /blueboat/motor_stbd/cmd
```

Equal positive numbers for throttle alone, equal and opposite for steering alone. 
### What this does not check

Magnitudes. The thruster scales each direction on its own limit, so the T200's asymmetry — roughly 51.5 N ahead against 40.2 N astern — is represented. The hull is not: the hydrodynamic damping coefficients are placeholders awaiting identification. Speeds and accelerations are therefore not meaningful yet, and a boat that reaches the wrong speed at full throttle is expected rather than a defect.

### The parameter files are not optional

Both `--add-param-file` arguments are required, for the reason described in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md): recent ArduPilot resolves frame defaults from the SITL binary's embedded `vehicleinfo.json` keyed by `--model`, not by the `-f` frame name. With `--model JSON` nothing matches and no frame defaults are applied at all.

Order matters, and so does what is left out:

- `rover.parm` first. It carries the SITL side — accelerometer calibration so pre-arm passes, `SIM_PIN_MASK`, the mode slots — but also sets `SERVO1/3_MIN/MAX` to 1000/2000.
- `blueboat_sitl.params` last, so the shipped boat's 1100/1900 range and its throttle assignment win.
- **Not** `rover-skid.parm`. It sets `SERVO1_FUNCTION 73` and `SERVO3_FUNCTION 74`, which is the reverse of the shipped BlueBoat and would swap the thrusters.
