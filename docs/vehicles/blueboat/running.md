# Running the simulation

```bash
ros2 launch blueboat_gazebo sim.launch.xml
```

Launches the vehicle in its default configuration: every artifact of the
full simulation is generated at start (URDF, composed model, bridge
config, into a directory under `$ROS_HOME`), the model is spawned as
`blueboat` into the water world and the ROS bridge comes up with it. A
`[kdl_parser] root link ... inertia` warning from `robot_state_publisher`
is expected and harmless.

To run a custom vehicle instead, pass a loadout file with `config_file:=`;
the [configuration page](configuration.md) lists the slots and
[Change the loadout](../../how-to/loadout.md) walks through writing one.

## Choosing the world

By default the boat is spawned into the open water world
(`blueboat_water.sdf`: graded buoyancy, a seabed at 3 m and a visual
surface). The `world:=` argument swaps the environment without changing
anything else about the simulation: pass any vehicle free world SDF
([Run in your own world](../../how-to/own-world.md)):

```bash
ros2 launch blueboat_gazebo sim.launch.xml world:=/path/my_world.sdf
```

## In RViz

To see the model in RViz:

```bash
ros2 launch blueboat_description display.launch.xml
```

Shows the model and its frames (parts, slots, the Ping `beam`), with
sliders to spin the propellers.
