# blueboat_gazebo

Gazebo Sim bring up for the BlueBoat: the composed model (thrusters,
hydrodynamics, the Ping2 echosounder), the water and playground worlds, the
sim launch, the generated ros_gz bridge config and `configure_vehicle.py`,
which regenerates every artifact of a configuration from one config file.

```bash
ros2 launch blueboat_gazebo sim.launch.xml                      # config_file:=my_vehicle.yaml
```

Documentation: <https://honurobotics.github.io/bluerobotics_models/>, see
[Running](https://honurobotics.github.io/bluerobotics_models/lyrical/vehicles/blueboat/running.html),
[Driving](https://honurobotics.github.io/bluerobotics_models/lyrical/vehicles/blueboat/driving.html)
and [Gazebo composition](https://honurobotics.github.io/bluerobotics_models/lyrical/design/gazebo-composition.html).
