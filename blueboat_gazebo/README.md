# blueboat_gazebo

Gazebo Sim bring up for the BlueBoat: the composed model (thrusters,
hydrodynamics, the Ping2 echosounder), the water and playground worlds, the
sim launch, the generated ros_gz bridge config and `configure_vehicle.py`,
which regenerates every artifact of a configuration from one config file.

```bash
ros2 launch blueboat_gazebo sim.launch.xml                      # config_file:=my_vehicle.yaml
ros2 launch blueboat_gazebo sim.launch.xml \
  world:=$(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_waves.sdf   # on the waves
```

Documentation: <https://honurobotics.github.io/bluerobotics_models/>, see
[Running](https://honurobotics.github.io/bluerobotics_models/lyrical/vehicles/blueboat/running.html),
[Actuators](https://honurobotics.github.io/bluerobotics_models/lyrical/vehicles/blueboat/actuators.html)
and [Gazebo composition](https://honurobotics.github.io/bluerobotics_models/lyrical/design/gazebo-composition.html).
