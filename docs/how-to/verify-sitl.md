# Verify the SITL connection

Confirm that ArduRover in SITL is driving the simulated BlueBoat, and that it drives it the right way round. Setup for ArduPilot itself is in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md); this page assumes it is done and the Iris smoke test passed.

Two shells. Both need the colcon workspace and then the ArduPilot environment, in that order.

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

## Verify that the boat drives in the correct directions and polarity.  

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


