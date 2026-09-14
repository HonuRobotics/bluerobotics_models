# Several vehicles and several simulations

## One name per instance

Every instance of a vehicle goes by one name, which is at once its Gazebo
model name and its topic namespace (`/<name>/...` for every sensor and
thruster topic, on both the Gazebo and the ROS side). By default the name is
the config's `topic_namespace` (`blueboat` or `bluerov2`). To put a second
copy of the vehicle in the same world, give it another name:

```bash
ros2 launch blueboat_gazebo sim.launch.xml
ros2 launch blueboat_gazebo sim.launch.xml name:=boat_b x:=4 yaw:=1.57   # in a second terminal, into the same world
```

`name:=` is passed to `configure_vehicle.py --name`, which applies it to
the config before generating the artifacts (the config actually used is
written next to them as `vehicle.yaml`), so the model name, the plugin
topics and the bridge cannot disagree. `x`, `y`, `z`, `roll`, `pitch` and
`yaw` place the instance.

Per sensor part, `topic`, `gz_topic` and `ros_topic` in the config still
override the base name under the namespace.

Two things about a renamed instance to keep in mind:

- Buoyancy in this repository's worlds is enabled by model name
  (`<enable>blueboat::hull_displacement</enable>`), so a second name needs a
  second `<enable>` line in the world, or a world that floats the vehicle by
  the displacement boxes it marks (see the gz-maritime worlds).
- The bridge's `/joint_states` and `/clock`, and the node names, are not
  yet under the instance name; two instances share them for now.

## Several simulations

To run several **simulations** side by side instead, give each Gazebo
instance its own `GZ_PARTITION` and each ROS graph its own `ROS_DOMAIN_ID`.
