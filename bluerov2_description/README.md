# bluerov2_description

URDF/xacro **description** of the Blue Robotics BlueROV2 (underwater ROV): geometry,
meshes and an RViz view. Pure description: **no Gazebo or simulator code** (that
lives in [`bluerov2_gazebo`](../bluerov2_gazebo)).

## What it provides
- The BlueROV2 hull (`base_link`) + the vectored **T200 thrusters** (`thruster1..N`,
  `continuous` joints).
- Two **variants** selected from config: `standard` (6 thrusters) and `heavy`
  (8-thruster Heavy kit + heavy frame mesh).
- **Config-driven accessory mounts** (sonars, cameras, DVL, skid, …) from
  `config/bluerov2.yaml`.
- A `base_link` **buoyancy collision box sized analytically at build time** so the
  whole vehicle (hull + thrusters + accessories) is ~0.02 % positively buoyant (near-neutral), for
  *any* loadout; see [Buoyancy](#buoyancy).
- The URDF is **generated from xacro at build time** (`urdf/bluerov2.urdf`).

Meshes are open-source placeholders (Apache-2.0; see [`ASSETS.md`](ASSETS.md)); real
sensor behaviour lives in `bluerov2_gazebo`.

## Layout
```
urdf/     bluerov2.urdf.xacro (top), thruster.xacro, accessories.xacro
config/   bluerov2.yaml   (variant + accessory loadout)
meshes/   hull / thruster / accessory meshes
rviz/     bluerov2.rviz
launch/   display.launch.xml
```

## Build
```bash
colcon build --merge-install --packages-select bluerov2_description
source install/setup.bash
```

## Configure variant & accessories
Edit `config/bluerov2.yaml` and rebuild.
- `variant: standard | heavy` selects 6 vs 8 thrusters + the matching frame mesh.
- `accessories:` is a list of `{type, name, xyz, rpy}` (pose relative to `base_link`,
  m / rad).

| `type` | Accessory |
|--------|-----------|
| `ping360` | scanning imaging sonar |
| `dvl_a50` | Water Linked DVL |
| `explorehd_camera` | HD camera |
| `marinesitu_c3` | stereo camera |
| `sonoptix_echo` / `omniscan_450_fs` | imaging sonars |
| `newton_gripper` | Newton subsea gripper |
| `sediment_sampler` | sediment sampler claw |
| `payload_skid` / `roof_rack` | payload frames |

The default loadout is the forward camera only; the rest of the catalog ships
as commented entries; uncomment to enable. The composed Gazebo model **and the
ros_gz bridge config regenerate from this file** on rebuild, so sensors and
their ROS topics always match. Topics default to `/<topic_namespace>/<name>/...`
and can be overridden per accessory (`topic`, or `gz_topic`/`ros_topic` for
different names on each side).

## Binary (deb) installs

When installed from debs (`apt install ros-<distro>-bluerov2-description`), the
generated URDF is baked with the **default** config at packaging time, and the
files under `/opt/ros/...` are root-owned and overwritten on upgrade, so do not
edit them. Two supported ways to customize the loadout:

1. **Launch-time config (no rebuild).** `display.launch.xml` expands the xacro
   at launch, so point it at your own config file:
   ```bash
   cp $(ros2 pkg prefix --share bluerov2_description)/config/bluerov2.yaml ~/my_rov.yaml
   # edit ~/my_rov.yaml, then:
   ros2 launch bluerov2_description display.launch.xml config_file:=$HOME/my_rov.yaml
   ```
   The same works for any tool that accepts a URDF; generate one directly:
   ```bash
   xacro $(ros2 pkg prefix --share bluerov2_description)/urdf/bluerov2.urdf.xacro \
     config_file:=$HOME/my_rov.yaml > ~/my_rov.urdf
   ```
2. **Overlay workspace (for simulation, or anything long-lived).** Clone this
   repo into a colcon workspace, edit `config/bluerov2.yaml`, build and source;
   the overlay shadows the deb and regenerates *all* artifacts (URDF, Gazebo
   model and bridge) consistently. See the `bluerov2_gazebo` README.

## Buoyancy
The `base_link` collision box is **not hand-tuned**: the xacro sums the total mass
(hull + thrusters + configured accessories) and solves the box height so that
`water_density · volume = mass · (1 + margin)`. So adding/removing accessories keeps
the vehicle slightly positive automatically. Tunables (top of `bluerov2.urdf.xacro`):
`water_density`, `buoyancy_margin` (default 0.0002), `buoyancy_cob_z`. The buoyancy
*force* is applied by the world plugin in `bluerov2_gazebo`; this box just sets the
displaced volume.

## View in RViz
```bash
ros2 launch bluerov2_description display.launch.xml
```
Thrusters + accessories appear as separate frames; the joint sliders spin the props.

### Known warning (harmless, do not "fix")

`robot_state_publisher` prints:

> `[kdl_parser]: The root link base_link has an inertia specified in the URDF,
> but KDL does not support a root link with an inertia. As a workaround, you
> can add an extra dummy link to your URDF.`

This is cosmetic here: KDL is only used to publish TF, which never touches
inertia, and Gazebo reads the inertia through sdformat, not KDL. **Do not apply
the suggested dummy-root workaround**: Gazebo's URDF conversion lumps fixed
joints, so a dummy root would absorb `base_link` and break every plugin and
sensor that references it.

## API

This package exposes files and frames, no runtime nodes:

| Artifact | Path |
|----------|------|
| Generated URDF | `share/bluerov2_description/urdf/bluerov2.urdf` |
| Vehicle config | `share/bluerov2_description/config/bluerov2.yaml` |
| Xacro sources | `share/bluerov2_description/urdf/*.xacro` |

Frames and joints (published as TF by `robot_state_publisher`):

| Name | Kind | Notes |
|------|------|-------|
| `base_link` | link (root) | hull; carries the buoyancy collision box |
| `thruster<N>`, `thruster<N>_joint` | link, continuous joint | N = 1..6 (standard) or 1..8 (heavy) |
| `<accessory name>` | link, fixed joint `<name>_joint` | one frame per configured accessory (except the claws, below) |
| `<claw>_body` | link, fixed joint `<claw>_mount` | claw housing; the claw's mount frame |
| `<claw>_jaw_left/right`, `<claw>_cup_left/right` | links, revolute joints `<...>_joint` | claw fingers; 0 (closed) to 0.6 rad (open) |

In Gazebo the fixed-joint accessory links are lumped into `base_link` (see the
known-warning note); in RViz/TF they stay separate frames.

## Use the URDF in ROS
Installed at `share/bluerov2_description/urdf/bluerov2.urdf`:
```bash
ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -p robot_description:="$(cat $(ros2 pkg prefix --share bluerov2_description)/urdf/bluerov2.urdf)"
```
Meshes use `package://bluerov2_description/meshes/...` (resolved via the ament index
in RViz, and via the installed `GZ_SIM_RESOURCE_PATH` hook in Gazebo).

## Simulation
Geometry only. For buoyancy, thrusters, hydrodynamics and sensors, use
**[`bluerov2_gazebo`](../bluerov2_gazebo)**.
