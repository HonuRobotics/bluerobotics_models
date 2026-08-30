# Running the BlueROV2 simulation

```bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

The launch generates every artifact of the full simulation at start
(URDF, composed model, bridge config, into directory under `$ROS_HOME`),
spawns the model as `bluerov2` into the pool world and starts the
ROS bridge. The vehicle should settle just under the surface at its
declared trim. The camera, ping360 and stereo camera are rendered
sensors and need a GPU. A custom loadout file is passed with `config_file:=`;
[Configuring the BlueROV2](configuration.md) lists the slots and
[Change the loadout](../../how-to/loadout.md) walks through writing one.

## Choosing the world

By default the vehicle is spawned into the pool world
(`bluerov2_pool.sdf`, a 25 m basin with its deck). The `world:=` argument
swaps the environment without changing anything else about the
simulation: pass any vehicle free world SDF, such as the packaged open
water one (unbounded water over a bare seabed, and the template for
[your own world](../../how-to/own-world.md)):

```bash
ros2 launch bluerov2_gazebo sim.launch.xml world:=$(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_water.sdf
```

## In RViz

To see the model in RViz:

```bash
ros2 launch bluerov2_description display.launch.xml
```
