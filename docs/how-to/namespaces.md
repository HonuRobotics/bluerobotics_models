# Several vehicles and several simulations

## One name per instance

Every instance of a vehicle goes by one name, which is at once its Gazebo
model name and its topic namespace (`/<name>/...` for every sensor and
thruster topic, on both the Gazebo and the ROS side). By default the name is
the config's `topic_namespace` (`blueboat` or `bluerov2`). A name is letters,
digits and underscores, starting with a letter, because it also has to be a
valid ROS name; the generator refuses anything else.

`name:=` on the sim launch is passed to `configure_vehicle.py --name`, which
applies it to the config before generating the artifacts (the config actually
used is written next to them as `vehicle.yaml`), so the model name, the
plugin topics and the bridge cannot disagree. `x`, `y`, `z`, `roll`, `pitch`
and `yaw` place the instance:

```bash
ros2 launch blueboat_gazebo sim.launch.xml name:=boat_b x:=4 yaw:=1.57
```

Joint states are bridged as `/<name>/joint_states`, and every TF frame and
sensor `frame_id` carries `<name>/` in front, so two instances have separate
TF trees. The node names of this repository's own launch
(`robot_state_publisher`, `ros_gz_bridge`) carry no instance name, since
that launch runs one vehicle; gz-maritime's spawn launch, below, runs each
instance's nodes in its namespace.

### Topic overrides under the name

Per part, `topic`, `gz_topic` and `ros_topic` in the config still override
the base name, and the override goes under the instance name too, so two
instances of one config never share a topic: `topic: sonar` on the Ping of
`boat_b` gives `/boat_b/sonar/range`. An override that starts with a slash
is used as given, and is then shared by every instance.

```{note}
Before this rule, a relative override replaced the namespace: `topic: sonar`
gave `/sonar/range`. A config written that way, or one that spelled the
namespace out (`gz_topic: blueboat/ping_raw`), now gets the namespace in
front of it. To keep an absolute topic, start it with a slash.
```

`extra_bridge_topics` are appended to the bridge config verbatim, so they
are shared by every instance too.

## A second instance in the same world

`sim.launch.xml` starts a Gazebo server of its own, so running it twice gives
two simulations, not two boats. Several instances share one world through
gz-maritime, whose simulation launch names no vehicle and whose spawn launch
adds any vehicle by name and pose, running this generator for it. In one
terminal, the ocean:

```bash
ros2 launch kai_bringup simulation.launch.xml
```

In another terminal, one command per boat:

```bash
boat="$(ros2 pkg prefix blueboat_gazebo)/lib/blueboat_gazebo/configure_vehicle.py --config $(ros2 pkg prefix --share blueboat_description)/config/blueboat.yaml"
ros2 launch kai_bringup spawn_vehicle.launch.xml name:=boat_a y:=4 generator:="$boat"
ros2 launch kai_bringup spawn_vehicle.launch.xml name:=boat_b y:=-4 yaw:=1.57 generator:="$boat"
```

Each boat gets its topics under its name, its own bridge and
`robot_state_publisher` in its namespace, and its own TF prefix; the clock
is bridged once by the simulation launch, which drops the `/clock` entry
this bridge config carries. The boats float there under any name because
their displacement collisions are marked ([Buoyancy](../design/buoyancy.md)).
In this repository's own worlds, buoyancy is enabled by model name
(`<enable>blueboat::hull_displacement</enable>`), so a renamed instance
needs its own `<enable>` line in a copy of the world.

## Several simulations

To run several **simulations** side by side instead, give each Gazebo
instance its own `GZ_PARTITION` and each ROS graph its own `ROS_DOMAIN_ID`.
