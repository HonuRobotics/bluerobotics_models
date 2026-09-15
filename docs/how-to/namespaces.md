# Several vehicles and several simulations

## One name per instance

Every instance of a vehicle goes by one name, which is at once its Gazebo
model name and its topic namespace (`/<name>/...` for every sensor and
thruster topic, on both the Gazebo and the ROS side). By default the name is
the config's `topic_namespace` (`blueboat` or `bluerov2`). Give an instance
another name with `name:=`:

```bash
ros2 launch blueboat_gazebo sim.launch.xml name:=boat_b x:=4 yaw:=1.57
```

`name:=` is passed to `configure_vehicle.py --name`, which applies it to
the config before generating the artifacts (the config actually used is
written next to them as `vehicle.yaml`), so the model name, the plugin
topics and the bridge cannot disagree. `x`, `y`, `z`, `roll`, `pitch` and
`yaw` place the instance.

The launch always starts its own Gazebo server, so running it twice gives
two simulations, not two boats. Until the launch is split into a world part
and a spawn part, a second copy in a running world is spawned by hand from
the artifacts generated for its name, with its own bridge:

```bash
dir=$($(ros2 pkg prefix blueboat_gazebo)/lib/blueboat_gazebo/configure_vehicle.py \
        --config $(ros2 pkg prefix --share blueboat_description)/config/blueboat.yaml \
        --name boat_b --cache)
ros2 run ros_gz_sim create -name boat_b -file $dir/model.sdf -x 4 -Y 1.57
ros2 run ros_gz_bridge parameter_bridge --ros-args -r __node:=boat_b_bridge \
        -p config_file:=$dir/ros_gz_bridge.yaml
```

Per part, `topic`, `gz_topic` and `ros_topic` in the config still override
the base name, and the override goes under the instance name too, so two
instances of one config never share a topic. An override that starts with
a slash is used as given and is then shared by every instance.

Two things about a renamed instance to keep in mind:

- Buoyancy in this repository's worlds is enabled by model name
  (`<enable>blueboat::hull_displacement</enable>`), so a second name needs a
  second `<enable>` line in the world, or a world that floats the vehicle by
  the displacement boxes it marks (see the gz-maritime worlds).
- Joint states are bridged as `/<name>/joint_states`, and every TF frame
  and sensor `frame_id` carries `<name>/` in front, so two instances have
  separate TF trees. Only `/clock` and the node names of this repository's
  own launch stay shared; gz-maritime's spawn launch runs the nodes in the
  instance namespace and bridges the clock once.

## Several simulations

To run several **simulations** side by side instead, give each Gazebo
instance its own `GZ_PARTITION` and each ROS graph its own `ROS_DOMAIN_ID`.
