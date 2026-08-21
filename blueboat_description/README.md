# blueboat_description

URDF/xacro **description** of the Blue Robotics BlueBoat (twin-hull USV),
assembled from the shared part library in
[`bluerobotics_parts`](../bluerobotics_parts). Pure description: **no Gazebo
or simulator code** (that lives in [`blueboat_gazebo`](../blueboat_gazebo)).

## What it provides

- A **default BlueBoat that needs no configuration**: the chassis, the two
  outboard propellers (`motor_port`/`motor_stbd`, `continuous` joints), the
  flag and the Ping2 integration kit, as the boat is most often run. Each
  comes from a slot the parts declare, filled with its default. The URDF is
  generated at build time: `urdf/blueboat.urdf`.
- A **configurable loadout** for anyone who wants the exact parts:
  `config/blueboat.yaml` overrides what goes in each slot or adds parts at
  explicit poses; every part type in the `bluerobotics_parts` catalog can be
  fitted.
- **Hull displacement** declared at the assembly: each pontoon is a row of
  box segments so graded buoyancy restores pitch and roll correctly (see
  [Buoyancy](#buoyancy)).

## Layout

```
urdf/     blueboat.urdf.xacro   (assembles the parts listed in the config)
config/   blueboat.yaml         (default loadout, topic namespace, hull displacement)
rviz/     blueboat.rviz
launch/   display.launch.xml
```

## Build

```bash
colcon build --merge-install --packages-select bluerobotics_parts blueboat_description
source install/setup.bash
```

## Configure the loadout

The shipped `config/blueboat.yaml` configures nothing: every slot of every
part fills itself with its default, which is the standard boat. To change
the loadout add entries:

```yaml
parts:
  - {slot: motor_port, type: t200_prop_ccw}        # another accepted option for a slot
  - {slot: ping_mount, type: none}                 # leave a slot empty
  - {slot: mast, type: blueboat_antenna_mast}      # fill a slot that has no default
  - {type: omniscan_450_sidescan, name: sidescan, xyz: "0.2 0.22 -0.03", rpy: "0 0 0"}  # free placement
```

Slots are declared by the parts (the chassis: motors, flag, mast, payload,
Ping kit; the Ping bracket: its Ping) with the types that fit and a default;
see [`ACCESSORIES.md`](ACCESSORIES.md) for the table and the catalog. Slot
entries and free placements can be mixed; ad hoc slots can be declared under
`slots:`. Mistakes (a part a slot does not accept, an unknown slot or type,
a slot configured twice) fail the build naming the problem.

Edit the file and rebuild, or pass `config_file:=<your.yaml>` to the
launches to try a loadout without rebuilding. The composed Gazebo model and
the ros_gz bridge config regenerate from the same resolution (the assembled
URDF carries an `<assembly_part>` manifest of what was fitted), so sensors
and their ROS topics always match. Topics default to
`/<topic_namespace>/<name>/...` and can be overridden per part (`topic`, or
`gz_topic`/`ros_topic` for different names on each side).

## Buoyancy

The BlueBoat floats at the waterline via **graded buoyancy** in
`blueboat_gazebo`, which requires primitive collisions: the config's
`hull_displacement` block declares each pontoon as a row of box segments, so
a pitching hull submerges the down-end segments more and rights itself
([AUR_BUOYANCY_DESIGN.md](../AUR_BUOYANCY_DESIGN.md)). The chassis part's own
collision geometry is switched off for that reason. The boat self-settles to
a draft of roughly `mass / (water_density * 2 * length * width)`, which puts
`base_link` at the waterline.

## API

This package exposes files and frames, no runtime nodes:

| Artifact | Path |
|----------|------|
| Generated URDF | `share/blueboat_description/urdf/blueboat.urdf` |
| Vehicle config | `share/blueboat_description/config/blueboat.yaml` |
| Xacro source | `share/blueboat_description/urdf/blueboat.urdf.xacro` |

Frames and joints (published as TF by `robot_state_publisher`):

| Name | Kind | Notes |
|------|------|-------|
| `base_link` | link (root) | the chassis part, in the frame the modeler delivered (mesh centroid, x forward, y left, z up) |
| `motor_port`, `motor_stbd` + `motor_*_joint` | links, continuous joints | outboard propellers |
| `<part name>` | link, fixed joint | one frame per configured part |
| `<parent>_<slot>`, `<part>_<frame>` | massless links | one frame per slot a part declares (e.g. `base_link_motor_port`) and per reference frame (`ping_beam`) |
| `hull_displacement` | massless link | carries the pontoon buoyancy collisions |

In Gazebo the fixed-joint links are lumped into `base_link` (their frames
survive by name); in RViz/TF they stay separate frames.

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
