# Verify the SITL connection (Boat)

This walkthrough is to confirm that ArduRover in SITL is driving the simulated BlueBoat correctly. 

## Prerequisites

* Setup and run the drydock + source development environment: [installation_drydock.md](../../getting-started/installation_drydock.md)
* [ArduPilot SITL setup](../../getting-started/ardupilot_setup.md); (the rest of this page assumes the Iris smoke test passed.)


## Walkthrough

You will start two shells. Both need the colcon workspace and then the ArduPilot environment, in that order.  All commands are issued within the drydock dev container.

First, the simulation:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v3 -r $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_sitl.sdf
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

```{note}
Gazebo prints `ArduPilot controller has reset` once shortly after SITL
connects and then roughly once a minute. It is expected and nothing is
reset: `ardupilot_gazebo` keeps ArduPilot's 32-bit frame counter in a
`uint16_t`, so it wraps about every 66 seconds at 1000 Hz and the plugin
reads the wrap as a restart. The fix is open upstream as
[ardupilot_gazebo#174](https://github.com/ArduPilot/ardupilot_gazebo/pull/174);
see the troubleshooting notes in [ArduPilot SITL setup](../../getting-started/ardupilot_setup.md).
```

### Verify that the boat drives in the correct directions and polarity.  

At the MAVProxy prompt, drive the USV forward (surge):

```
mode manual
arm throttle
rc 3 1700
```

| Command | Expected | 
|---|---|---|
| `rc 3 1700` | +surge, both thrusters equal | 
| `rc 1 1700`  | spins to starboard on the spot (pivot turn)
| `rc 1 1300`  | spins to port on the spot (pivot turn)
| `rc 3 1300` | drives astern | 
| `rc all 1500` | stops | 

To see what the autopilot is actually commanding while you move the sticks, echo the same topics:

```bash
gz topic -e -t /blueboat/motor_port/cmd
gz topic -e -t /blueboat/motor_stbd/cmd
```


