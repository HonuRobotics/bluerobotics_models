# blueboat_description

URDF/xacro **description** of the Blue Robotics BlueBoat (twin-hull USV):
geometry and an RViz view. Pure description: **no Gazebo or simulator code**
(that lives in [`blueboat_gazebo`](../blueboat_gazebo)).

## What it provides

- The BlueBoat hull (`base_link`) with primitive catamaran visuals and two
  outboard **T200 propellers** (`motor_port/stbd_link`, `continuous` joints)
  for differential drive.
- **Config-driven accessory mounts** (masts, sonars, brackets, flag) from
  `config/blueboat.yaml`.
- **Distributed pontoon buoyancy collisions**: each pontoon is a row of box
  segments so graded buoyancy restores pitch/roll correctly (see
  [Buoyancy](#buoyancy)).
- The URDF is **generated from xacro at build time** (`urdf/blueboat.urdf`).

## Layout

```
urdf/     blueboat.urdf.xacro (top), thruster.xacro, accessories.xacro
config/   blueboat.yaml   (accessory loadout + topic namespace)
rviz/     blueboat.rviz
launch/   display.launch.xml
```

## Build

```bash
colcon build --merge-install --packages-select blueboat_description
source install/setup.bash
```

## Configure accessories

Edit `config/blueboat.yaml` and rebuild; it is a list of
`{type, name, xyz, rpy}` entries (pose relative to `base_link`, metres and
radians). See [`ACCESSORIES.md`](ACCESSORIES.md) for the catalog. The default
loadout is the Ping2 echosounder only; the rest of the catalog ships as
commented entries. The composed Gazebo model and the ros_gz bridge config
regenerate from this file on rebuild, so sensors and their ROS topics always
match. Topics default to `/<topic_namespace>/<name>/...` and can be
overridden per accessory (`topic`, or `gz_topic`/`ros_topic` for different
names on each side).

## Buoyancy

The BlueBoat floats at the waterline via **graded buoyancy** in
`blueboat_gazebo`, which requires primitive collisions: each pontoon is a row
of `pontoon_segments` box segments, so a pitching hull submerges the down-end
segments more and rights itself. Tunables at the top of
`blueboat.urdf.xacro`: `pontoon_length/width/height`, `pontoon_x/y/z`,
`pontoon_segments`. The boat self-settles to a draft of roughly
`mass / (water_density * 2 * pontoon_length * pontoon_width)`.

## API

This package exposes files and frames, no runtime nodes:

| Artifact | Path |
|----------|------|
| Generated URDF | `share/blueboat_description/urdf/blueboat.urdf` |
| Vehicle config | `share/blueboat_description/config/blueboat.yaml` |
| Xacro sources | `share/blueboat_description/urdf/*.xacro` |

Frames and joints (published as TF by `robot_state_publisher`):

| Name | Kind | Notes |
|------|------|-------|
| `base_link` | link (root) | hull; carries the pontoon buoyancy collisions |
| `motor_port_link`, `motor_stbd_link` + `motor_*_joint` | links, continuous joints | outboard propellers |
| `<accessory name>` | link, fixed joint | one frame per configured accessory |

In Gazebo the fixed-joint accessory links are lumped into `base_link`; in
RViz/TF they stay separate frames.

### Known warning (harmless, do not "fix")

`robot_state_publisher` warns that the root link has an inertia KDL ignores.
This is cosmetic (KDL only publishes TF; Gazebo reads inertia via sdformat).
Do not add the suggested dummy root link: Gazebo's URDF conversion lumps
fixed joints, so a dummy root would absorb `base_link` and break every plugin
that references it.

## View in RViz

```bash
ros2 launch blueboat_description display.launch.xml
```

`display.launch.xml` expands the xacro at launch time, so a custom loadout
needs no rebuild: pass `config_file:=<your.yaml>`.

## Binary (deb) installs

The generated URDF is baked with the default config at packaging time; do not
edit files under `/opt/ros/...`. Customize via the `config_file` launch
argument (no rebuild) or an overlay workspace (regenerates everything
consistently). See the `blueboat_gazebo` README for the full recipe.

## Simulation

Geometry only. For buoyancy, thrusters, hydrodynamics and the echosounder,
use **[`blueboat_gazebo`](../blueboat_gazebo)**.
