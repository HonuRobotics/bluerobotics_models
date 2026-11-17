# BlueROV2

The BlueROV2 is a vectored thruster ROV, assembled from the
`bluerobotics_parts` library in its standard (6 thruster) and heavy
(8 thruster) configurations, with camera, sonar, DVL and manipulator
parts.

To dive it under ArduSub start from [Dive the BlueROV2 with ArduSub](../../quickstarts/sitl-bluerov2.md); how its parameters were derived is in [BlueROV2 parameters](parameters.md).

```{toctree}
:maxdepth: 1

running
actuators
sensors
configuration
```

## The default vehicle

The default configuration is the standard chassis with its six T200 propellers
and the exploreHD camera, trimmed 2 g positively buoyant. The chassis
visual is the delivered art; the heavy chassis still uses a placeholder
mesh.
