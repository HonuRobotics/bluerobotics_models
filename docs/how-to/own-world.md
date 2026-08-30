# Run in your own world

The composed model needs two things from the world: **graded buoyancy**
(water below z = 0, `gz-sim-buoyancy-system` enabled on the boat's
displacement link, `<enable>blueboat::hull_displacement</enable>`; enabling
the whole model `blueboat` also works, with warnings about the parts'
non box collisions) and, for the echosounder, `gz-sim-sensors-system` with
the ogre2 render engine. The simplest start is a copy of the water world,
which holds both plugin blocks:

```bash
cp $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_water.sdf my_world.sdf
```

## Include the default model

Sourcing the workspace puts the package's models directory on
`GZ_SIM_RESOURCE_PATH`, so `model://blueboat` resolves:

```xml
<include>
  <uri>model://blueboat</uri>
  <name>blueboat</name>
  <pose>0 0 0.05 0 0 0</pose>
</include>
```

## Spawn at runtime

```bash
ros2 run ros_gz_sim create -world <your_world> -name blueboat -z 0.05 \
  -file $(ros2 pkg prefix --share blueboat_gazebo)/models/blueboat/model.sdf
```

## Use the stock launch with your world

```bash
ros2 launch blueboat_gazebo sim.launch.xml world:=/path/my_world.sdf
```

spawns the boat (default or `config_file:=` loadout) into it and starts the
bridge and `robot_state_publisher`.

## With a custom loadout

Generate the model first and point at it instead of the installed one:

```bash
ros2 run blueboat_gazebo configure_vehicle.py --config my_loadout.yaml --out-dir ~/my_models/blueboat
```

See [Configure an installed vehicle](installed-vehicle.md).
