# Walkthrough: Verify the SITL connection (Boat)

Confirm that ArduRover in SITL is driving the simulated BlueBoat in `MANUAL` mode, which means throttle and steering commands are provided via RC channels and ArduRover mixes them into the two thruster commands. (BlueBoat is diff drive, not propeller/rudder.)

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
rc 3 1600
```

`rc <channel> <microseconds>` overrides one RC input. Channel 3 is throttle and channel 1 is steering, which are ArduRover's ordinary assignments - none of ArduSub's channel remapping applies to the boat. Both span 1100 to 1900; 1500 is neutral.

Send `rc all 1500` between checks.

| Command | Axis | Expected |
|---|---|---|
| `rc 3 1600` | surge | drives straight ahead, both thrusters equal |
| `rc 3 1400` | surge | drives astern |
| `rc 1 1600` | yaw | spins to starboard on the spot, clockwise seen from above |
| `rc 1 1400` | yaw | spins to port, mirroring the line above |
| `rc all 1500` | — | stops |


The check passes when each RC channel, commanded on its own, produces the motion described above.

The sign convention on yaw can be confusing, because two body frames meet here and they disagree.

* ArduPilot uses x forward, y **right**, z down - FRD, as in MAVLink's [`MAV_FRAME_BODY_FRD`](https://mavlink.io/en/messages/common.html#MAV_FRAME_BODY_FRD), and stated in the source at `AP_AHRS.h` ("in result, x is forward, y is right"). Positive yaw is a turn to starboard.
* ROS uses x forward, y **left**, z up - FLU, per [REP 103](https://www.ros.org/reps/rep-0103.html). Positive yaw is a turn to port.

So `rc 1 1600` is a positive yaw command in ArduPilot and shows up as a *negative* yaw rate in ROS conventions.

To see what the autopilot is commanding while you move the sticks, echo the thruster topics:

```bash
gz topic -e -t /blueboat/motor_port/cmd
gz topic -e -t /blueboat/motor_stbd/cmd
```

Equal positive numbers for throttle alone, equal and opposite for steering alone.
