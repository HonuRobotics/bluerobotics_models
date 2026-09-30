# Tuning of closed-loop response for BlueROV2

This walkthrough is to confirm that ArduSub's inner control loops (stabilization layer) drive the simulated BlueROV2 the way the hardware behaves. `STABILIZE` holds heading, `ALT_HOLD` adds depth.

[Verify the SITL connection (ROV)](verify-sitl-rov.md) checks the wiring — each stick moves the axis it names. This page checks the numbers.

```{note}
OUTLINE. The expected figures are blank until the hydrodynamic
identification is done; each is filled in from a published source or from a
trial. Nothing on this page has been run yet.
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

TBD — which `GCS_PID_MASK` bits ArduSub uses, and the `graph` expressions for the yaw rate loop and the depth loop. Unlike the boat, the demand and achieved values here come from loops with an integrator, so what to watch is the transient rather than a standing offset.

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

TBD — a short table mapping each symptom to the layer that owns it: no motion on an axis the frame does not mix, a response too slow or too fast being damping, saturation being thrust limits, and oscillation being a gain meeting the wrong plant.
