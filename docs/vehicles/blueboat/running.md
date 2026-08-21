# Running the BlueBoat

## Full ROS bring up

```bash
ros2 launch blueboat_gazebo sim.launch.xml
```

Starts the Gazebo server (composed in one container with the ros_gz bridge
and `robot_state_publisher`), the Gazebo GUI, and spawns the boat into the
vehicle free water world. The simulation starts running.

| Argument | Default | Meaning |
|---|---|---|
| `config_file` | the package default | loadout YAML; every artifact is regenerated from it at launch |
| `world` | `blueboat_water.sdf` | a vehicle free world SDF to spawn into |
| `gui` | `true` | start the Gazebo GUI |
| `use_composition` | `true` | server, bridge and state publisher in one process |
| `name` | `blueboat` | model name to spawn as (the world's buoyancy and the bridge expect it) |
| `z` | `0.05` | spawn height; the default sits at the waterline |

A `[kdl_parser] root link ... inertia` warning from `robot_state_publisher`
is expected and harmless.

## Gazebo only, no ROS

The playground world includes the default composed model (started this way
the world comes up paused; press play):

```bash
gz sim $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_playground.sdf
```

## RViz only, no Gazebo

```bash
ros2 launch blueboat_description display.launch.xml          # config_file:= works here too
```

Shows the model and its frames (parts, slots, the Ping `beam`), with sliders
to spin the propellers.

## In your own world

Include `model://blueboat_gazebo` or spawn the generated model; see
[Run in your own world](../../how-to/own-world.md).
