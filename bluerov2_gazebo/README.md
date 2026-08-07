# bluerov2_gazebo

Gazebo Sim bring-up for the BlueROV2: a self-contained underwater world, the
**composed simulation model** (thrusters + hydrodynamics + sensors), a sim launch
file and the `ros_gz` bridge. Gazebo-specific assets/plugins live here, keeping
[`bluerov2_description`](../bluerov2_description) free of simulator code.

## What it provides
- `model.sdf`: **generated at build time** from `model.sdf.xacro`, config-aware. It
  `<include merge="true">`s the description URDF and adds:
  - one **`Thruster`** plugin per propeller joint (6 or 8 by variant; T200 thrust
    saturation), and a **`Hydrodynamics`** plugin (Fossen drag);
  - one **`<sensor>` per sensor-type accessory**: `explorehd_camera` → camera,
    `marinesitu_c3` → RGBD, `ping360` → `gpu_lidar` (a geometry approximation),
    `dvl_a50` → native `DopplerVelocityLog`.
- `worlds/bluerov2_playground.sdf`: uniform-density water (whole world submerged) +
  the **Buoyancy** world plugin, so the slightly-positive ROV slowly rises, damped
  by hydro.
- `config/ros_gz_bridge.yaml`: **generated at build time** from the same vehicle
  config, so bridge topics always match the configured accessories.
- `launch/sim.launch.xml`, `model.config` (`model://bluerov2_gazebo`).

## Build
```bash
colcon build --merge-install --packages-select bluerov2_description bluerov2_gazebo
source install/setup.bash
```

## See the model in Gazebo
Directly (no ROS), starts **paused**; press ▶ play to watch it rise:
```bash
gz sim $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_playground.sdf
```
Full ROS bring-up (gz server + bridge + robot_state_publisher + GUI):
```bash
ros2 launch bluerov2_gazebo sim.launch.xml   # gui:=false  use_composition:=false  world:=<path>
```
> A `[kdl_parser] root link ... inertia` warning from robot_state_publisher is
> expected and harmless; see the note in the bluerov2_description README.
> Cameras / lidar / DVL are rendered sensors and need a **GPU**.

## API

Topic bases default to `/<topic_namespace>/<accessory name>`; per-accessory
config keys (`topic`, `gz_topic`, `ros_topic`) override them. Optional rows
appear when their accessory is enabled in the config and the bridge regenerates
to match on rebuild.

### ROS interface (via the generated bridge)

| ROS topic | Type | Direction | Available with |
|-----------|------|-----------|----------------|
| `/bluerov2/camera/image` | `sensor_msgs/msg/Image` | publishes | default (camera) |
| `/bluerov2/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | publishes | default (camera) |
| `/clock` | `rosgraph_msgs/msg/Clock` | publishes | always |
| `/bluerov2/ping360/scan` | `sensor_msgs/msg/LaserScan` | publishes | `ping360` |
| `/bluerov2/dvl/velocity` | `marine_acoustic_msgs/msg/Dvl` | publishes | `dvl_a50` |
| `/bluerov2/stereo/{image,depth_image,points,camera_info}` | `Image` / `PointCloud2` / `CameraInfo` | publishes | `marinesitu_c3` |
| `/bluerov2/gripper/cmd_pos` | `std_msgs/msg/Float64` | subscribes | `newton_gripper` |
| `/bluerov2/sampler/cmd_pos` | `std_msgs/msg/Float64` | subscribes | `sediment_sampler` |

`robot_state_publisher` (started by the launch) additionally publishes
`/robot_description` and TF. Claw commands are an angle in radians, from 0
(closed) to 0.6 (open):

```bash
ros2 topic pub /bluerov2/gripper/cmd_pos std_msgs/msg/Float64 "data: 0.6" -1
```

#### Sensor frames

Every sensor tags its messages with `header.frame_id = <accessory name>` — the
accessory's own link, which `robot_state_publisher` puts in TF — so
`lookup_transform('base_link', msg.header.frame_id)` resolves for all of them.

Those frames are **body**-convention (x forward, y left, z up), which is what
Gazebo emits: an RGBD camera facing a wall 2.95 m ahead returns points at
`x=2.95`, not `z=2.95`.

The cameras carry the same body frame, so they do **not** follow REP-145, which
expects image and camera_info to be tagged with an optical frame (z forward, x
right, y down). Consumers that unproject pixels — `image_pipeline`, RViz's
Camera display — need to account for that themselves; the optical frame is
`rpy = (-pi/2, 0, -pi/2)` relative to the accessory link.

### Thrust interface

| gz topic | Type | Direction | Purpose |
|----------|------|-----------|---------|
| `/model/bluerov2/joint/thruster<N>_joint/cmd_thrust` | `gz.msgs.Double` | subscribes | thrust command in newtons, clamped to the T200 limits; N = 1..6 (standard) or 1..8 (heavy) |
| `/model/bluerov2/joint/thruster<N>_joint/ang_vel` | `gz.msgs.Double` | publishes | propeller speed feedback (rad/s) |

Thrust commands are latched: each thruster holds its last command until a new
one arrives. The horizontal thrusters (1-4) are vectored at 45 degrees, so
single-axis motion needs a mix with these signs (thrust in newtons):

| motion | t1 | t2 | t3 | t4 | t5 | t6 |
|--------|----|----|----|----|----|----|
| surge +x (forward) | - | - | + | + | 0 | 0 |
| sway +y (left) | - | + | - | + | 0 | 0 |
| yaw +z (counterclockwise) | - | + | + | - | 0 | 0 |
| heave +z (up) | 0 | 0 | 0 | 0 | - | - |

Command the mix together (`&` + `wait` publishes in parallel). Bringing
thrusters up one command at a time leaves the wrench unbalanced while the
remaining commands arrive, yawing the vehicle off its heading before it
translates:

```bash
# surge forward at ~28 N
gz topic -t /model/bluerov2/joint/thruster1_joint/cmd_thrust -m gz.msgs.Double -p 'data: -10.0' &
gz topic -t /model/bluerov2/joint/thruster2_joint/cmd_thrust -m gz.msgs.Double -p 'data: -10.0' &
gz topic -t /model/bluerov2/joint/thruster3_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /model/bluerov2/joint/thruster4_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```

Stop by publishing `data: 0.0` to all four the same way. Controllers that
publish continuously (teleop, ArduPilot, MAVROS) are unaffected by the onset
ordering.

The same commands are bridged to ROS as
`/bluerov2/thrusters/thruster<N>/thrust` (`std_msgs/msg/Float64`, thrust in
newtons), mirroring the BlueBoat interface.

Never edit the generated `config/ros_gz_bridge.yaml`; edit the vehicle config
and rebuild. Native bridge options (`lazy`, queue sizes, ...) go in each
accessory's `bridge:` dict, and arbitrary extra entries in the top-level
`extra_bridge_topics:` list.

## Binary (deb) installs

From debs, the composed `model.sdf` and the bridge config are baked with the
**default** (camera-only) loadout at packaging time; the out-of-the-box launch
works as documented above. To customize the accessory loadout:

- **Overlay workspace (recommended).** Clone this repo into a colcon workspace,
  edit `bluerov2_description/config/bluerov2.yaml`, `colcon build --merge-install`, source the
  overlay. All three generated artifacts (URDF, `model.sdf`, bridge yaml) stay
  consistent automatically, and the deb remains untouched.

- **Runtime regeneration (advanced, no rebuild).** Everything needed ships in
  the deb (the xacro sources and the bridge generator), but the three artifacts
  must be regenerated **from the same config** or TF, simulation and topics
  will disagree:
  ```bash
  CFG=$HOME/rov/bluerov2.yaml            # your edited copy of the config
  # 1. Gazebo model: shadow model://bluerov2_gazebo with your own generation
  mkdir -p ~/rov/models/bluerov2_gazebo
  xacro $(ros2 pkg prefix --share bluerov2_gazebo)/model.sdf.xacro \
    config_file:=$CFG > ~/rov/models/bluerov2_gazebo/model.sdf
  cp $(ros2 pkg prefix --share bluerov2_gazebo)/model.config ~/rov/models/bluerov2_gazebo/
  export GZ_SIM_RESOURCE_PATH=$HOME/rov/models:$GZ_SIM_RESOURCE_PATH
  # 2. bridge config
  python3 $(ros2 pkg prefix bluerov2_gazebo)/lib/bluerov2_gazebo/generate_bridge_config.py \
    $CFG ~/rov/ros_gz_bridge.yaml
  # 3. launch with all three overridden from the same config
  ros2 launch bluerov2_gazebo sim.launch.xml \
    config_file:=$CFG bridge_config_file:=$HOME/rov/ros_gz_bridge.yaml
  ```
  (The resource-path prepend makes the world's `model://bluerov2_gazebo`
  resolve to *your* model instead of the baked one.)

## Integrate the model into an existing Gazebo project
1. Sourcing the workspace puts `bluerov2_gazebo` on `GZ_SIM_RESOURCE_PATH` (env hook),
   so `model://bluerov2_gazebo` resolves.
2. In your world SDF add the **Buoyancy** world plugin (uniform or graded) and:
   ```xml
   <include>
     <uri>model://bluerov2_gazebo</uri>
     <name>bluerov2</name>
     <pose>0 0 0 0 0 0</pose>
   </include>
   ```
   Buoyancy is a *world* plugin (see the playground world); the model brings its own
   thrusters/hydro/sensors. For rendered sensors also add `gz-sim-sensors-system`.
3. Or spawn at runtime:
   ```bash
   ros2 run ros_gz_sim create -world <your_world> -name bluerov2 \
     -file $(ros2 pkg prefix --share bluerov2_gazebo)/model.sdf
   ```
