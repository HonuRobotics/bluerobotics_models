# Tuning of closed-loop response for BlueROV2

This walkthrough is to confirm that ArduSub's inner control loops (stabilization layer) drive the simulated BlueROV2 the way the hardware behaves. `STABILIZE` holds heading, `ALT_HOLD` adds depth.

[Verify the SITL connection (ROV)](verify-sitl-rov.md) checks the wiring — each stick moves the axis it names. This page checks the numbers.

```{note}
The expected figures on this page are blank until the hydrodynamic identification is done, because what a correct response looks like depends on the damping being identified. Each is filled in from a published source or from a trial, and nothing here has been run yet.
```

## Prerequisites

* Setup and run the drydock + source development environment: [installation_drydock.md](../../getting-started/installation_drydock.md)
* [ArduPilot SITL setup](../../getting-started/ardupilot_setup.md); (the rest of this page assumes the Iris smoke test passed.)
* [Verify the SITL connection (ROV)](verify-sitl-rov.md) passes.

## What these modes actually hold

`STABILIZE` names roll, pitch and yaw, but on the standard six-thruster vehicle only yaw is closed:

| Axis | Closed? | Why |
|---|---|---|
| roll | no | `ATC_ANG_RLL_P` is 0 — Blue Robotics' shipped value. Two verticals give little roll authority; the Heavy, with four, is the variant that closes it |
| pitch | no | the `Vectored` frame mixes no pitch at all, so there is nothing to close a loop with |
| yaw | yes | `ATC_ANG_YAW_P` above `ATC_RAT_YAW_*` |
| depth | in `ALT_HOLD` | `PSC_D_POS_P` → `PSC_D_VEL_P` → `PSC_D_ACC_*` |

So heading and depth are the objectives. A stick that produces no motion is not necessarily a defect here — see the pitch row.

Heading is two loops, and which one you are testing depends on the stick. Deflected, the yaw stick commands a **rate**, closed by `ATC_RAT_YAW_*`. Released, ArduSub waits 250 ms for the vehicle to slow, latches the heading it then has, and holds that **bearing** through `ATC_ANG_YAW_P`. That latch matters when judging: heading hold is against the bearing at release, not the one you started from.

## Walkthrough

All commands are issued within the drydock dev container. Two shells, as in the verification walkthrough.

First, the simulation:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v4 -r $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_sitl.sdf
```

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
connects and then roughly once a minute. This is annoying, but not of concern.
(The fix is open upstream as
[ardupilot_gazebo#174](https://github.com/ArduPilot/ardupilot_gazebo/pull/174).)
```

### Graph the autopilot internals

`GCS_PID_MASK` selects which loop the autopilot reports on. ArduSub's bits are not the boat's, and one of them is not in ArduPilot's parameter documentation:

| Bit | Value | Loop reported |
|---|---|---|
| 0 | 1 | roll rate |
| 1 | 2 | pitch rate |
| 2 | 4 | yaw rate |
| 3 | 8 | depth, as the vertical acceleration loop |

Bit 3 is read by `GCS_MAVLink_Sub.cpp` in `send_pid_tuning`, but the parameter's own `@Bitmask` metadata in `ArduSub/Parameters.cpp` lists only roll, pitch and yaw — so the depth loop cannot be found from the published parameter reference. That is an upstream documentation gap, not a local one.

Set one bit at a time. Every enabled loop sends `PID_TUNING` on the same message, so with two bits set the graph interleaves two loops and neither reads cleanly.

For the yaw rate loop:

```
param set GCS_PID_MASK 4
module load graph
graph PID_TUNING.desired PID_TUNING.achieved
```

For the depth loop:

```
param set GCS_PID_MASK 8
graph PID_TUNING.desired PID_TUNING.achieved
```

Both are degrees per second for yaw and m/s² for depth; the depth loop's achieved value is the earth-frame vertical acceleration with gravity removed, not a depth.

Depth itself is easier read directly, and it is what the checks below are judged on:

```
graph VFR_HUD.alt
```

Unlike the boat, what to watch is the transient rather than a standing offset. Both loops carry an integrator, which drives steady-state error to zero whether or not the plant is right — so a loop that settles on target says little, and the settling time and overshoot on the way there say everything.

### Verify heading hold

```
arm throttle
mode stabilize
```

TBD — hold the yaw stick, release it, and judge against the bearing at release.

| Check | Command | Expect | Measured |
|---|---|---|---|
| yaw rate | yaw stick deflected | TBD | |
| heading hold | stick released | TBD — holds the bearing at release | |
| heading disturbance | pushed off and left | TBD — returns, with what overshoot | |

### Verify depth hold

```
mode alt_hold
```

TBD — a step in commanded depth, then a disturbance.

| Check | Command | Expect | Measured |
|---|---|---|---|
| depth step | heave stick, then release | TBD | |
| depth disturbance | pushed off depth and left | TBD — returns, with what overshoot | |

For each row the quantities to judge are time to reach the demand, overshoot and settling time. Steady-state error is not the measure here: both loops carry an integrator, so it is driven to zero whether or not the plant is right. A wrong plant shows up as the shape of the response.

```{important}
The gains are not ours to move. Blue Robotics publish none for these loops,
so the reference is ArduSub's own firmware defaults, written out explicitly
in the parameter file — see
[Parameters](parameters.md). If a row only passes with a gain changed, the
actuator model or the hydrodynamics is wrong.
```

## If a row is wrong

Each symptom belongs to a layer, and the point of the table is to send you to the right one rather than to the gains.

| Symptom | Layer that owns it | Where to look |
|---|---|---|
| No motion at all on an axis | the frame, not a fault | `Vectored` mixes no pitch, and roll has no angle gain. Confirm the axis is one the vehicle closes before treating it as broken — see [Parameters](parameters.md) |
| Response settles, but too slowly | damping too high | `nRabsR` for yaw, `zWabsW` for heave |
| Response overshoots and rings | damping too low | the same two coefficients, from the other side |
| Demand is met but the vehicle is sluggish reaching it | thrust limits | the `drive` endpoints on `t200_prop_cw` / `t200_prop_ccw`. If `PID_TUNING` shows the output pinned, the loop is asking for thrust the model does not have |
| Oscillation that grows | a gain meeting the wrong plant | not the gain. A plant this far off is a damping or thrust error large enough to find in an open-loop trial, so go back to those |
| Depth drifts steadily | buoyancy, not the loop | the vehicle should be neutrally buoyant; `test_gz_launch.py::test_vehicle_neutrally_buoyant` asserts it |
| Heading wanders with no stick input | the IMU frame | the sensor is rolled 180° about x so it reports FRD, which is what `ArduPilotPlugin` requires. A yaw rate of the wrong sign makes the loop correct the way that makes it worse |

The last row is worth checking first when something is inexplicable rather than merely wrong. It is what the boat spent the longest on: `MANUAL` drove correctly while the stabilized mode spun, because the plugin takes the gyro straight from the IMU message without rotating it.
