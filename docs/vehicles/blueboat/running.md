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

To run a custom vehicle instead, pass its config with `config_file:=`;
the [configuration page](configuration.md) lists the slots and
[Change the fitted parts](../../how-to/change-parts.md) walks through writing one.

## Launch arguments

| Argument | Default | Meaning |
|---|---|---|
| `config_file` | the shipped config | Vehicle config, expanded at launch. |
| `name` | `blueboat` | Instance name: the Gazebo model name and the topic namespace (`/<name>/...`). Give each copy of the vehicle in one world its own; see [Several vehicles](../../how-to/namespaces.md). |
| `x`, `y`, `z` | `0`, `0`, the water default | Spawn position (m); the default sits at the waterline. |
| `roll`, `pitch`, `yaw` | `0` | Spawn orientation (rad). |
| `world` | the water world | Vehicle free world SDF to spawn into. |
| `gui` | `true` | Launch the Gazebo GUI. |
| `use_composition` | `true` | Run the server, the bridge and `robot_state_publisher` in one process. |

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

Starts `robot_state_publisher`, `joint_state_publisher_gui` (sliders to
spin the propellers) and RViz with the packaged config, showing the model
and its frames (parts, slots, the Ping `beam`). It takes the same
`config_file:=` argument, and the xacro is expanded at launch time, so a
custom config needs no rebuild. In a simulation the frames carry the instance name (`blueboat/base_link`)
and joint states arrive as `/blueboat/joint_states`, so RViz next to
`sim.launch.xml` needs its fixed frame, its RobotModel TF prefix and its
joint states pointed at the instance.
