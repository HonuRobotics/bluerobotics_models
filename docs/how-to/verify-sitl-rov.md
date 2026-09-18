# Verify the SITL connection (ROV)

Confirm that ArduSub in SITL is driving the simulated BlueROV2 (standard configuration, not "heavy") in `MANUAL` mode, which means surge, yaw, sway and heave commands are provided via RC channels and ArduSub maps from commands in the body frame to individual thruster commands.  

## Prereqs

* Setup for ArduPilot itself is in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md). 
* The workspace is built and sourced. See [Installation](../getting-started/installation.md).
* The steps below were run in the [drydock](https://github.com/HonuRobotics/drydock) container, started with `drydock run maritime`. They should work on a host set up per [Requirements](../getting-started/requirements.md) as well.  Currently untested. 

## Two shells: sim and autopilot

### The simulation

Start the ROV sim
 
```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v4 -r $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_sitl.sdf
```

If successful, you should see Gazebo sim start with the ROV spawned in a simple underwater environment. 


### The autopilot (SITL)

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
connects and then roughly once a minute.  This is annoying, but not of concern. (The fix is open upstream as
[ardupilot_gazebo#174](https://github.com/ArduPilot/ardupilot_gazebo/pull/174).)
See troubleshooting notes in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md).
```

## Verification - teleop via the autopilot. 

One axis at a time, at the MAVProxy prompt in the autopilot shell. 

Forward surge... 
```
mode manual
arm throttle
rc 5 1510
```

`rc <channel> <microseconds>` overrides one RC input. Channel 5 is surge, and the channel spans 1100 to 1900; 1500 is neutral.

Send `rc all 1500` between checks. 

The channel mapping is different from the usual ArduPilot one - of course it is.
`ArduSub/Parameters.h` overrides it for Sub.

| RCMAP | Channel | Axis |
|---|---|---|
| `RCMAP_PITCH` | 1 | pitch |
| `RCMAP_ROLL` | 2 | roll |
| `RCMAP_THROTTLE` | 3 | heave |
| `RCMAP_YAW` | 4 | yaw |
| `RCMAP_FORWARD` | 5 | surge |
| `RCMAP_LATERAL` | 6 | sway |

`param show RCMAP*` confirms.

Directions below are in the vehicle's own frame, [REP 103](https://www.ros.org/reps/rep-0103.html): x forward, y left, z up.

| Command | Axis | Expected |
|---|---|---|
| `rc 5 1510` | surge | moves ahead, holds heading and depth |
| `rc 5 1490` | surge | moves astern |
| `rc 6 1510` | sway | crabs to starboard (its own right, -y)|
| `rc 4 1510` | yaw | turns to starboard, clockwise seen from above |
| `rc 3 1510` | heave | rises |
| `rc 3 1490` | heave | sinks |
| `rc 1 1510` | pitch | no motion, and that is correct: on the six-thruster standard vehicle the four horizontals carry surge, sway and yaw and the two verticals carry heave and roll, so pitch is not actuated |
| `rc all 1500` | — | stops |


The verification passes when each RC channel, commanded on its own, produces the
motion described above.

The sign convention can be confusing, because two coordinate conventions do not agree:

* ArduPilot uses x forward, y **right**, z down - FRD, as in MAVLink's [`MAV_FRAME_BODY_FRD`](https://mavlink.io/en/messages/common.html#MAV_FRAME_BODY_FRD). 
* ROS uses x forward, y **left**, z up - FLU, per [REP 103](https://www.ros.org/reps/rep-0103.html).


The commands are deliberately tiny. 1510 about 2.5% of full stick and it is  enough to see the vehicle move. This is because the actuators and vehicle dynamics have not been tuned yet.  That will happen later in [the spec](../specs/SITL_SPEC.md)

To see what the autopilot is commanding while you move the sticks, echo the thruster topics:

```bash
gz topic -e -t /bluerov2/thruster_1/cmd
gz topic -e -t /bluerov2/thruster_5/cmd
```

