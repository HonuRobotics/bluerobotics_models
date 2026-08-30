# Running the BlueROV2 simulation

```bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

The launch generates every artifact of the full simulation at start
(URDF, composed model, bridge config, into directory under `$ROS_HOME`),
spawns the model as `bluerov2` into the pool world and starts the
ROS bridge. The vehicle should settle just under the surface at its
declared trim. A custom loadout file is passed with `config_file:=`;
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

Without ROS:

```bash
gz sim $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_playground.sdf
```

runs the default vehicle in the same pool scene (the playground world is the
pool world with `model://bluerov2` included).
The camera, ping360 and stereo camera are rendered sensors and need a GPU.
To see the model in RViz:

```bash
ros2 launch bluerov2_description display.launch.xml
```

```{admonition} RViz shows a part posed differently than Gazebo?
:class: tip

Both render the same URDF, generated fresh at every launch, so they cannot
genuinely disagree. An RViz session left open across a rebuild keeps the
`robot_description` it received when its RobotModel display loaded; restart
RViz (or toggle the RobotModel display) after rebuilding or switching
branches.
```
