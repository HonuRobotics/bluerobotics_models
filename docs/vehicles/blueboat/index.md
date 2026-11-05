# BlueBoat

The BlueBoat is a twin hull differential drive unmanned surface vessel. In
simulation it floats on graded buoyancy, is driven by thrust commands to its
two outboard motors, and carries the Ping2 echosounder.

```{toctree}
:maxdepth: 1

running
actuators
sensors
configuration
parameters
verify-sitl-boat
tune-sitl-boat
mission-sitl-boat
visual_asset_commission
```

## The default vehicle

The shipped config fits the chassis (pontoons, crossbeams, hatches and the outboard thruster bodies) and its two M200 weedless propellers, nothing else. With `slot_defaults: true` the slots fill with their own defaults as well: the flag on the aft crossbeam and the Ping2 echosounder on its integration kit bracket, face below the waterline. Everything else in the catalog can be fitted ([Configuration](configuration.md)).
