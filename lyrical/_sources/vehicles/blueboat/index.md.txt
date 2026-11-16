# BlueBoat

The BlueBoat is a twin hull differential drive unmanned surface vessel. In
simulation it floats on graded buoyancy, is driven by thrust commands to its
two outboard motors, and carries the Ping2 echosounder.

To drive it under ArduRover start from [Drive the BlueBoat with ArduRover](../../quickstarts/sitl-blueboat.md); how its parameters were derived is in [BlueBoat parameters](parameters.md).

```{toctree}
:maxdepth: 1

running
actuators
sensors
configuration
```

## The default vehicle

The shipped config fits the chassis (pontoons, crossbeams, hatches and the outboard thruster bodies) and its two M200 weedless propellers, nothing else. With `slot_defaults: true` the slots fill with their own defaults as well: the flag on the aft crossbeam and the Ping2 echosounder on its integration kit bracket, face below the waterline. Everything else in the catalog can be fitted ([Configuration](configuration.md)).
