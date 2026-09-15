# Several vehicles and several simulations

## One name per instance

Every instance of a vehicle goes by one name, which is at once its Gazebo
model name and its topic namespace (`/<name>/...` for every sensor and
thruster topic, on both the Gazebo and the ROS side). By default the name is
the config's `topic_namespace` (`blueboat` or `bluerov2`). A name is letters,
digits and underscores, starting with a letter, because it also has to be a
valid ROS name.

`name:=` on the sim launch is passed to `configure_vehicle.py --name`, which
applies it to the config before generating the artifacts (the config actually
used is written next to them as `vehicle.yaml`), so the model name, the
plugin topics and the bridge cannot disagree. `x`, `y`, `z`, `roll`, `pitch`
and `yaw` place the instance:

```bash
ros2 launch blueboat_gazebo sim.launch.xml name:=boat_b x:=4 yaw:=1.57
```

Per sensor part, `topic`, `gz_topic` and `ros_topic` in the config still
override the base name under the namespace.

## A second instance in the same world

`sim.launch.xml` starts a Gazebo server of its own, so running it twice gives
two simulations, not two boats: the second server refuses the world name
and the ROS graph fills with duplicate node names. Until the launch is split
into a simulation part and a spawn part (item 1 of the
[multi-vehicle plan](https://github.com/HonuRobotics/gz-maritime/blob/lyrical/MULTI_VEHICLE_PLAN.md)),
a second instance is generated and spawned by hand. In one terminal, the
simulation with the first boat:

```bash
ros2 launch blueboat_gazebo sim.launch.xml
```

In a second terminal, the artifacts of the second instance, then the spawn:

```bash
ros2 run blueboat_gazebo configure_vehicle.py --config $(ros2 pkg prefix --share blueboat_description)/config/blueboat.yaml --name boat_b --out-dir ~/boat_b
ros2 run ros_gz_sim create -name boat_b -x 4 -Y 1.57 -file ~/boat_b/model.sdf
```

In a third terminal, its bridge, which keeps running:

```bash
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$HOME/boat_b/ros_gz_bridge.yaml
```

`/boat_b/motor_port/thrust` and the rest are then on the ROS graph next to
`/blueboat/...`. Two things about the second instance to keep in mind:

- **In this repository's worlds it sinks.** Their buoyancy plugin floats the
  links named in the world file, `<enable>blueboat::hull_displacement</enable>`,
  and nothing names `boat_b`. Add `<enable>boat_b::hull_displacement</enable>`
  to a copy of the world, or use a world whose buoyancy reads the marks the
  displacement collisions carry, such as gz-maritime's open water world,
  where any name floats
  ([Buoyancy](../design/buoyancy.md)).
- **Its bridge also carries `/clock` and `/joint_states`**, and
  `robot_state_publisher` is not started for it, so the two instances share
  the clock topic and the joint states, and only the first has TF. Bridging
  joint states under the instance name and running each instance's nodes in
  its namespace is item 4 of the plan.

## Several simulations

To run several **simulations** side by side instead, give each Gazebo
instance its own `GZ_PARTITION` and each ROS graph its own `ROS_DOMAIN_ID`.
