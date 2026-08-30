# BlueBoat

The BlueBoat is a twin hull differential drive unmanned surface vessel. In
simulation it floats on graded buoyancy, is driven by thrust commands to its
two outboard motors, and carries the Ping2 echosounder.

## The default vehicle

Launched with no configuration, the boat comes as it is most often run:

- the **hull**: both pontoons, the crossbeams and hatches, and the two
  outboard thruster bodies
- two **outboard propellers** (M200 weedless props, one per hull), spinning
  on their motor joints and driven by thrust commands
- the **flag** on the aft crossbeam
- the **Ping2 echosounder**, fitted with its integration kit bracket on the
  inner face of the starboard hull, face below the waterline, streaming
  ranges to the seabed

Everything else in the catalog (antenna mast, payload bracket, standard T200
propellers, side scan and multibeam sonars) is available, and the default
parts can be swapped or left off; see [Configuration](configuration.md).

```{toctree}
:maxdepth: 1

running
actuators
sensors
configuration
```
