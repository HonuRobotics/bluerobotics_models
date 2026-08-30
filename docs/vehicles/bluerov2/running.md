# Running the simulation

```bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

Launches the vehicle in its default configuration: every artifact of the
full simulation is generated at start (URDF, composed model, bridge
config, into a directory under `$ROS_HOME`), the model is spawned as
`bluerov2` into the pool world and the ROS bridge comes up with it.

To run a custom vehicle instead, pass its config with `config_file:=`;
the [configuration page](configuration.md) lists the slots and
[Change the fitted parts](../../how-to/change-parts.md) walks through writing one.

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

Starts `robot_state_publisher`, `joint_state_publisher_gui` (sliders to
spin the propellers) and RViz with the packaged config, showing the model
and its frames (parts, slots, the camera and sonar frames). It takes the
same `config_file:=` argument, and the xacro is expanded at launch time,
so a custom config needs no rebuild. Running next to `sim.launch.xml`,
`/joint_states` arrives over the bridge and RViz animates the propellers.
