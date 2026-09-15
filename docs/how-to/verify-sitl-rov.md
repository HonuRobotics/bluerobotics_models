# Verify the SITL connection (ROV)

Confirm that ArduSub in SITL is driving the simulated BlueROV2 (standard configuration, not "heavy") in `MANUAL` mode, which means surge, yaw, sway and heave commands are provided via RC channels and ArduSub maps from commands in the body frame to individual thruster commands.  

## Prereqs

* Setup for ArduPilot itself is in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md). This page assumes it is done and that `./waf sub` has been built.
* The workspace is built and sourced: `colcon build --merge-install` from the workspace root, then `source install/setup.bash`. See [Installation](../getting-started/installation.md).
* The steps below were run in the [drydock](https://github.com/HonuRobotics/drydock) container, started with `drydock run maritime`. They work on a host set up per [Requirements](../getting-started/requirements.md) too; only the prerequisites differ.

First, the simulation:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v4 -r $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_sitl.sdf
```
If successful, you should see Gazebo sim start with the ROV spawned in a simple underwater environemnt. 


Then the autopilot:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
AP=$HOME/maritime_ws/thirdparty/ardupilot/Tools/autotest
sim_vehicle.py -v ArduSub -f gazebo-bluerov2 --model JSON --console -w \
  --add-param-file=$AP/default_params/sub.parm \
  --add-param-file=$(ros2 pkg prefix --share bluerov2_gazebo)/params/bluerov2_sitl.params
```

```{note}
Gazebo prints `ArduPilot controller has reset` once shortly after SITL
connects and then roughly once a minute. It is expected and nothing is
reset: `ardupilot_gazebo` keeps ArduPilot's 32-bit frame counter in a
`uint16_t`, so it wraps about every 66 seconds at 1000 Hz and the plugin
reads the wrap as a restart. The fix is open upstream as
[ardupilot_gazebo#174](https://github.com/ArduPilot/ardupilot_gazebo/pull/174);
see the troubleshooting notes in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md).
```

## The checks

One axis at a time. At the MAVProxy prompt:

```
mode manual
arm throttle
rc 6 1600
```

`rc <channel> <microseconds>` overrides one RC input. Channel 6 is surge, and the channel spans 1100 to 1900 about a 1500 neutral, so 1600 is a quarter of full stick ahead. In `MANUAL` that quarter passes through the mixer unscaled, so each of the four horizontal thrusters ends up at about a quarter of full command - roughly 13 N of the T200's 51.5 N, before the 45 degree vectoring takes its cosine. Full stick is 1900, and `rc 6 1500` returns to neutral.

The channels are not the ones you might guess, and ArduPilot's own parameter documentation is stale on this point — the comments in `AP_RCMapper.cpp` say forward is "normally channel 5" and lateral "channel 6", while the code defaults are 6 and 7. The code is what runs:

| Command | Axis | Expected | If not |
|---|---|---|---|
| `rc 6 1600` | surge | moves ahead, holds heading and depth | yawing means the four horizontals are not mixing evenly; sinking or rising means a vertical is being driven |
| `rc 6 1400` | surge | moves astern | |
| `rc 7 1600` | sway | crabs to starboard, nose stays put | a turn instead of a crab means two horizontals are swapped |
| `rc 4 1600` | yaw | turns to starboard on the spot | translating instead of turning means the diagonal pairs are wrong |
| `rc 3 1600` | heave | rises | sinking means both verticals are reversed; rolling means one of them is |
| `rc 3 1400` | heave | sinks | |
| `rc all 1500` | — | stops | |
| `rc clear` | — | releases the overrides | |

Each stick should produce its own axis and nothing else. A cross-coupled response means the thruster allocation is wrong; a reversed one means a thruster or a channel is.

`rc 1` and `rc 2` are roll and pitch. They do nothing on this vehicle and that is correct: the standard BlueROV2 has two vertical thrusters, enough for heave and roll, and ArduSub's `Vectored` frame mixes no pitch at all. The Heavy, with four verticals, is the variant that has the authority — it is not modelled yet.

## What the autopilot is doing with those commands

`MANUAL` on a sub is closer to passthrough than the boat's `MANUAL` is, but it is still a mix. `ModeManual::run()` takes the six normalized stick inputs and hands them straight to the motor mixer without any attitude loop:

```cpp
motors.set_forward(channel_forward->norm_input());
motors.set_lateral(channel_lateral->norm_input());
motors.set_throttle((channel_throttle->norm_input() + 1.0f) / 2.0f);
motors.set_yaw(channel_yaw->norm_input() * g.acro_yaw_p / ACRO_YAW_P);
```

`AP_Motors6DOF` then combines them with the per-motor factors its `FRAME_CONFIG` selects. For `FRAME_CONFIG 1` (Vectored), motors 1 to 4 are the horizontals and carry surge, sway and yaw; motors 5 and 6 are the verticals and carry heave and roll. Each motor's output is converted to PWM around a 1500 neutral — not around the minimum, which is why a disarmed ROV sits still rather than diving.

From there it is the same path as the boat: PWM over UDP to `ArduPilotPlugin`, whose `<control>` blocks map 1100–1900 onto [-1, 1] and publish that on each thruster's command topic. The thruster owns the newtons.

To see what the autopilot is actually commanding while you move the sticks:

```bash
gz topic -e -t /bluerov2/thruster_1/cmd
gz topic -e -t /bluerov2/thruster_5/cmd
```

Values are normalized, so anything outside [-1, 1] is a bug in the mapping rather than an aggressive command. Thruster 1 is a horizontal and should respond to surge, sway and yaw; thruster 5 is a vertical and should respond only to heave and roll.

## Which thruster is which

The channel a thruster answers to is not configured anywhere — ArduSub assigns Motor1 to Motor6 to SERVO1 to SERVO6 itself, from `FRAME_CONFIG`, and the model numbers its `<control>` blocks to match. That correspondence is a claim about where each thruster sits, and `bluerov2_gazebo/test/test_ardusub_frame.py` asserts it against the factors in ArduSub's own `AP_Motors6DOF.cpp`. If a slot ever moves, that test fails rather than the vehicle quietly answering the wrong stick.

## What this does not check

Magnitudes. The thruster limits are the T200 placeholders carried since before the interface was normalized, and the hull's hydrodynamic coefficients have never been identified, so speeds and accelerations are not meaningful yet. An ROV that reaches the wrong speed at full stick is expected rather than a defect. Phase 4 of the [SITL spec](../specs/SITL_SPEC.md) is where that gets settled.

Depth also comes for free here rather than from a sensor: the JSON protocol carries no pressure field, and ArduSub synthesizes depth from the position the plugin already reports.

## The parameter files are not optional

Both `--add-param-file` arguments are required, for the same reason as on the boat: recent ArduPilot resolves frame defaults from the SITL binary's embedded `vehicleinfo.json` keyed by `--model`, and with `--model JSON` nothing matches, so no frame defaults are applied at all.

Order matters, and so does what is left out:

- `sub.parm` first. It supplies the SITL side — fake accelerometer calibration so pre-arm passes, the joystick button map, the position controller gains.
- `bluerov2_sitl.params` last, so the vehicle's own frame and outputs win.
- Not `sub-6dof.parm`. It sets `FRAME_CONFIG 2` for the Heavy, which expects eight thrusters; this vehicle has six, and motors 7 and 8 would be mixed into nothing.
