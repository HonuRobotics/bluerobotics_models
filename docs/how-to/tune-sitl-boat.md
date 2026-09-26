# Closed-loop response (Boat)

This walkthrough is to confirm that ArduRover's inner control loops (stabilization layer) drive the simulated BlueBoat the way the real one behaves, under Blue Robotics' published gains. It uses `ACRO`, where the throttle stick commands a **speed** and the steering stick a **turn rate**.

```{note}
OUTLINE. The expected figures are blank until the hydrodynamic
identification is done; each is filled in from a published source or from a
trial. Nothing on this page has been run yet.
```

## Prerequisites

* Setup and run the drydock + source development environment: [installation_drydock.md](../getting-started/installation_drydock.md)
* [ArduPilot SITL setup](../getting-started/ardupilot_setup.md); (the rest of this page assumes the Iris smoke test passed.)
* [Verify the SITL connection (Boat)](verify-sitl-boat.md) passes.

## Walkthrough

All commands are issued within the drydock dev container. Two shells, as in the verification walkthrough.

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

### Test closed-loop 


#### surge

Graph the autopilot internals
```
param set GCS_PID_MASK 2
module load graph
graph PID_TUNING.desired PID_TUNING.achieved
```
Send full forward speed command
```
rc 3 1900
```
Results in
./images/surge_auto_1900.png


Sending command 
```
rc 3 1700
```
results in
./images/surge_auto_1700.png

#### yaw-rate


param set GCS_PID_MASK 1
module load graph
graph PID_TUNING.desired PID_TUNING.achieved


TBD — one paragraph: full throttle asks for `SPEED_MAX` and full steering for `ACRO_TURN_RATE`, so the demand is a parameter, not a stick position. Name which parameter sets which, so a reader can tell a wrong demand from a wrong response.

### Reading the response

TBD — how to measure from the Gazebo side rather than through MAVLink: model pose against the sim clock, and the command that prints them. Speed and yaw rate are then the vehicle's, not the autopilot's estimate of itself.

### Verify the closed-loop response

At the MAVProxy prompt, one step at a time. Send `rc all 1500` and let the boat come to rest between rows.

```
mode acro
arm throttle
rc 3 1900
```

| Command | Asks for | Expected | Measured |
|---|---|---|---|
| `rc 3 1900` | full speed | TBD, anchored to 3 m/s | |
| `rc 3 1700` | half speed | TBD | |
| `rc 1 1900`, throttle neutral | full turn rate | TBD, anchored to 45 °/s | |
| `rc 3 1900` and `rc 1 1700` | both | TBD — speed holds while turning | |

For each row the quantities to judge are time to reach the demand, overshoot, settling time, and steady-state error against the demand. TBD: the tolerance on each, and what distinguishes a failure from a boat that is simply slower than the real one.

```{important}
The gains are not ours to move. `ATC_SPEED_*` and `ATC_STR_RAT_*` are Blue
Robotics' published values, and this page checks that they work unmodified.
If a row only passes with a gain changed, the actuator model or the
hydrodynamics is wrong — see
[Parameters](../vehicles/blueboat/parameters.md).
```

### If a row is wrong

TBD — a short table mapping each symptom to the layer that owns it: a wrong demand is a parameter, a response too slow or too fast is damping, a response that is right until thrust saturates is the thrust limits, and oscillation is a gain meeting the wrong plant.
