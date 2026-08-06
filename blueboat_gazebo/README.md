# blueboat_gazebo

Gazebo Sim bring-up for the BlueBoat: the composed simulation model (twin
thrusters, hydrodynamics, echosounder), a surface-water world, a sim launch
file and the generated ros_gz bridge. Gazebo-specific assets and plugins live
here, keeping [`blueboat_description`](../blueboat_description) free of
simulator code.

## What it provides

- `model.sdf`: **generated at build time** from `model.sdf.xacro`. It
  `<include merge="true">`s the description URDF and adds two **`Thruster`**
  plugins (counter-rotating, T200 thrust limits), a **`Hydrodynamics`**
  plugin, and the **Ping2 echosounder** as a single-beam down `gpu_lidar`.
- `worlds/blueboat_playground.sdf`: **graded buoyancy** (water below z=0), a
  seabed and a visual water surface; the boat floats at the waterline.
- `config/ros_gz_bridge.yaml`: **generated at build time** from the same
  vehicle config, so bridge topics always match the configured accessories.
- `launch/sim.launch.xml`, `model.config` (`model://blueboat_gazebo`).

## Build

```bash
colcon build --packages-select blueboat_description blueboat_gazebo
source install/setup.bash
```

## See the model in Gazebo

Directly (no ROS), starts **paused**; press play to watch it settle level:

```bash
gz sim $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_playground.sdf
```

Full ROS bring-up (gz server + bridge + robot_state_publisher + GUI):

```bash
ros2 launch blueboat_gazebo sim.launch.xml   # gui:=false  use_composition:=false  world:=<path>
```

> A `[kdl_parser] root link ... inertia` warning from robot_state_publisher is
> expected and harmless; see the note in the blueboat_description README.

## API

Topic bases default to `/<topic_namespace>/<accessory name>`; per-accessory
config keys (`topic`, `gz_topic`, `ros_topic`) override them.

### ROS interface (via the generated bridge)

| ROS topic | Type | Direction | Available with |
|-----------|------|-----------|----------------|
| `/blueboat/thrusters/port/thrust` | `std_msgs/msg/Float64` | subscribes | always (drivetrain) |
| `/blueboat/thrusters/stbd/thrust` | `std_msgs/msg/Float64` | subscribes | always (drivetrain) |
| `/blueboat/ping/range` | `sensor_msgs/msg/LaserScan` | publishes | default (`ping_sonar`) |
| `/clock` | `rosgraph_msgs/msg/Clock` | publishes | always |

`robot_state_publisher` (started by the launch) additionally publishes
`/robot_description` and TF. Thrust commands are in newtons, clamped to the
T200 limits; the differential of the two gives surge and yaw:

```bash
ros2 topic pub /blueboat/thrusters/port/thrust std_msgs/msg/Float64 "data: 20.0" -1
ros2 topic pub /blueboat/thrusters/stbd/thrust std_msgs/msg/Float64 "data: 20.0" -1
```

### Gazebo transport interface (gz topics)

| gz topic | Type | Direction | Purpose |
|----------|------|-----------|---------|
| `/model/blueboat/joint/motor_<side>_joint/cmd_thrust` | `gz.msgs.Double` | subscribes | thrust command (bridged from the ROS topics above) |
| `/model/blueboat/joint/motor_<side>_joint/ang_vel` | `gz.msgs.Double` | publishes | propeller speed feedback (rad/s) |

Thrust commands are latched: each motor holds its last command until a new one
arrives. Command both motors together (`&` + `wait` publishes in parallel);
bringing them up one command at a time applies a differential wrench while the
second command is in flight and yaws the boat off its heading:

```bash
# ahead at ~20 N
gz topic -t /model/blueboat/joint/motor_port_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /model/blueboat/joint/motor_stbd_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```

Equal thrust drives ahead; differential thrust yaws (more starboard thrust
turns to port and vice versa). Stop with `data: 0.0` to both. Controllers that
publish continuously are unaffected by the onset ordering.

Never edit the generated `config/ros_gz_bridge.yaml`; edit the vehicle config
and rebuild. Native bridge options (`lazy`, queue sizes, ...) go in each
accessory's `bridge:` dict, and arbitrary extra entries in the top-level
`extra_bridge_topics:` list.

## Binary (deb) installs

From debs, the composed model and bridge config are baked with the default
loadout. To customize without a rebuild: pass `config_file:=` and
`bridge_config_file:=` to the launch, regenerate the model with the shipped
`model.sdf.xacro` into a directory that shadows `model://blueboat_gazebo` via
`GZ_SIM_RESOURCE_PATH`, and regenerate the bridge with the shipped
`generate_bridge_config.py`. All three must come from the same config. An
overlay workspace is the recommended path for anything long-lived.

## Integrate the model into an existing Gazebo project

1. Sourcing the workspace puts `blueboat_gazebo` on `GZ_SIM_RESOURCE_PATH`
   (env hook), so `model://blueboat_gazebo` resolves.
2. Your world needs the **graded Buoyancy** world plugin (water below z=0)
   and, for the echosounder, `gz-sim-sensors-system`:

   ```xml
   <include>
     <uri>model://blueboat_gazebo</uri>
     <name>blueboat</name>
     <pose>0 0 0.25 0 0 0</pose>
   </include>
   ```

   Copy the plugin blocks from `worlds/blueboat_playground.sdf`.
3. Or spawn at runtime:

   ```bash
   ros2 run ros_gz_sim create -world <your_world> -name blueboat -z 0.25 \
     -file $(ros2 pkg prefix --share blueboat_gazebo)/model.sdf
   ```
