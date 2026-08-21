# blueboat_description

URDF description of the Blue Robotics BlueBoat, assembled from
`bluerobotics_parts`: the loadout config (`config/blueboat.yaml`, which
configures nothing for the default boat), the vehicle xacro and an RViz
launch. Pure description, no simulator code.

```bash
ros2 launch blueboat_description display.launch.xml            # config_file:=my_loadout.yaml
```

Documentation: <https://honurobotics.github.io/bluerobotics_models/>, see the
[BlueBoat manual](https://honurobotics.github.io/bluerobotics_models/lyrical/vehicles/blueboat/index.html)
and [Configuring the BlueBoat](https://honurobotics.github.io/bluerobotics_models/lyrical/vehicles/blueboat/configuration.html).
