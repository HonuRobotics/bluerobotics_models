# Gazebo composition

`blueboat_gazebo` turns the description into a simulation ready model
without the description knowing Gazebo exists.

## Merge include and lumping

`model.sdf.xacro` merge includes the URDF (`<include merge="true">`): not
the installed ROS one but a **Gazebo flavoured** expansion of the same
xacro (`gltf_up:=z`, installed as `model://blueboat/blueboat.urdf`). The
difference is one thing: glTF is Y-up by specification and the part meshes
conform; RViz and the ROS tools rotate them to Z-up on load, Gazebo does not
(it shows the data as is), so the Gazebo copy pre-rotates every glTF visual
by +90 degrees about x. Same parts, same frames, same manifest; only the
visual orientation differs. `configure_vehicle.py` writes both copies too
(`blueboat.urdf`, `blueboat.gazebo.urdf`). The model then adds the hull
displacement link (the box pontoons from the config's `hull_displacement`,
the only link the worlds enable buoyancy on), the hydrodynamics plugin, the
joint state publisher, one Thruster plugin per propeller and the sensors;
everything that names the root link uses the config's `base.name`. Gazebo's
URDF conversion **lumps every fixed joint**: the chassis, slots, flag,
bracket and Ping all collapse into one `base_link` body; only the
propellers stay separate links on their continuous joints. Physically correct and cheaper. The conversion keeps a
**frame for every lumped link** (`<frame name="ping_beam" attached_to=...>`),
so the names survive even though the bodies do not.

## Sensors and thrusters follow their part

Each sensor is a massless link posed `relative_to` the frame its part
declares for its sensing origin (`ping_beam`), with `frame_id` set to that
frame so the messages name something TF carries. Each propeller (a part
whose `part_info` carries a `drive` table: diameter, thrust limits, sense
of rotation) gets a Thruster plugin on its mounting joint, with the
coefficient sign set by the rotation so a counter rotating pair cancels its
reaction yaw. Both are emitted by running **the same assembly resolution**
the URDF went through, with Gazebo emitters plugged in:
`assemble(..., emit="gz_part", manifest="false")` calls `gz_part` per
resolved instance with the part's info, which emits the Thruster for a
propeller, the sensor for the types it knows (the Ping2 echosounder) and
nothing for geometry only parts. Leave a motor slot empty, rename its
occupant or fit a T200 prop instead and the plugins and topics follow. Move the
part, rename it, fit a second one: the sensor follows, because the Gazebo
side never held a coordinate.

## The bridge agrees by construction

`generate_bridge_config.py` reads the fitted instances from the URDF's
`<assembly_part>` manifest and emits one bridge entry per topic of each
part type that has topics (`PART_TOPICS`: a propeller's `/thrust` command,
the Ping's `/range`), plus `/clock` and `/joint_states`; per instance topic
overrides come from the config entry that fitted it. Nothing about the
drivetrain is hardcoded and no topic bakes the model name. The model's
plugin and sensor topics and the bridge's topics therefore derive from the
same resolution; a test asserts they are equal for several configs. The
generator also runs `bluerobotics_parts.assembly.check`, so a config that
names a slot or instance the assembly does not have fails here, at build or
at launch, with the reason.

## Build time and launch time

At build, the installed defaults are generated from the shipped config: the
URDF, `model.sdf` (`model://blueboat`, with a specs comment
stamped in) and `config/ros_gz_bridge.yaml`. At launch, `sim.launch.xml`
runs `configure_vehicle.py --config <file> --cache`, which regenerates the
three into a per config directory under `$ROS_HOME/blueboat_gazebo/`
(named after the config's content, so nothing piles up), spawns that model
into the vehicle free water world and starts the bridge on that config. The same tool with
`--out-dir` gives a user, including one on a binary install, a model
directory usable as `model://` and a bridge config to hand to their own
launch.

## What is in the composed model

| Element | From |
|---|---|
| geometry, inertia, joints | the URDF (merge included) |
| `hull_displacement` link | box pontoons from the config; `<enable>blueboat::hull_displacement</enable>` in the world |
| `gz-sim-hydrodynamics-system` | placeholder USV damping coefficients, to be identified |
| `gz-sim-thruster-system`, one per propeller | on `<name>_joint`, limits and diameter from the part's `drive` table (T200 16 V placeholders today), counter rotating |
| `gz-sim-joint-state-publisher-system` | `/<ns>/joint_states`, bridged for RViz |
| `gpu_lidar` "ping" | the Ping2 as a one ray downward range sensor at `ping_beam` |
