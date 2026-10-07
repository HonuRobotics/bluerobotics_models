# Run in your own world

The composed model needs three things from the world: **graded buoyancy**
(water below z = 0, `gz-sim-buoyancy-system` enabled on the vehicle's
displacement link: `<enable>blueboat::hull_displacement</enable>` for the
boat, `<enable>bluerov2::buoyancy_displacement</enable>` for the ROV;
enabling the whole model also works, with warnings about the parts'
non box collisions), **gz-maritime's ocean current system**, and, for the
rendered sensors, `gz-sim-sensors-system` with the ogre2 render engine. The
simplest start is a copy of the vehicle's water world, which holds all three
plugin blocks (`blueboat_water.sdf` / `bluerov2_water.sdf`):

```bash
cp $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_water.sdf my_world.sdf
```

The ocean current system is not optional, even in still water. The
vehicles' surge, sway and heave damping is the water's drag on their
collisions marked `gz:ocean_current="true"`, and that system is what applies
it; without it the vehicle has no damping in those directions and a boat
under thrust speeds up without limit. Slack water is the default, set to
your water's density:

```xml
<plugin filename="gz-maritime-ocean-current-system"
        name="gz::sim::maritime::OceanCurrent">
  <speed>0</speed>
  <direction>0</direction>
  <water_density>1025</water_density>
</plugin>
```

A `<speed>` and the `<direction>` it sets towards, in degrees clockwise from
north, give the world a current the vehicle drifts with.

A world running gz-maritime's buoyancy system needs no `<enable>` entry:
the displacement collisions are marked, so the vehicle floats under any
spawn name ([Marked for any world](../design/buoyancy.md#marked-for-any-world)).

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

spawns the boat (default or a `config_file:=` custom) into it and starts the
bridge and `robot_state_publisher`.

## With a custom config

Generate the model first and point at it instead of the installed one:

```bash
ros2 run blueboat_gazebo configure_vehicle.py --config my_vehicle.yaml --out-dir ~/my_models/blueboat
```

See [Configure an installed vehicle](installed-vehicle.md).
