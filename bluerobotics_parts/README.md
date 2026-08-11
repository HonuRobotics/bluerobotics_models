# bluerobotics_parts

Shared part library for all Blue Robotics vehicle models.

A **part** is a single physical component: one mesh, **no joints**, geometry only —
visual, collision and inertia. Never sensors, never plugins. Sensor behaviour is
added later, in the per-vehicle `*_gazebo` package.

Parts are vehicle-agnostic. A part lives here whether one vehicle uses it or
both. Assemblies — parts plus the joints between them — live in the per-vehicle
`*_description` packages.

See the [repository README](../README.md) for the full design.

## What the modeller delivers

Into `models/<model_name>/`, using exactly the directory names listed in
[`models/parts.csv`](models/parts.csv). Filenames are explicit — they repeat the
part name, so a file still identifies itself once it has been moved, attached to
a message or opened on its own:

```
models/blueboat_vessel/
  blueboat_vessel.visual.glb        # required — visual mesh, PBR materials embedded
  model.sdf                         # required — collision primitives
  blueboat_vessel.collision.stl     # optional — only if a primitive will not do
  model.config                      # optional — harmless, unused
```

`model.sdf` keeps its conventional name; Gazebo and the import script both expect
it. Collision meshes carry no materials or UVs, so STL is the leanest choice —
any format Gazebo reads will work, but pick one and stay with it.

### Rules

1. **The directory name is the part name.** Not the mesh's internal name, not the
   Blender object name. If the right directory is not in `parts.csv`, ask before
   inventing one.
2. **Origin and orientation.** The mesh origin sits approximately at the centroid
   of the mesh, oriented **x forward, y left, z up**. This is the one that is
   expensive to get wrong — a part delivered with a different convention looks
   correct in isolation and is wrong in every assembly that uses it.
3. **Collision shapes: box, cylinder, sphere or mesh — never cone or plane.**
   URDF cannot express cone or plane at all, and the import will reject them.
   Prefer primitives; a coarse approximation of the mesh is what is wanted.
4. **No spaces or `.001`-style suffixes in any name.** Collision and link names
   become ROS frame and topic names downstream.

Materials ride along inside the `.glb`. Gazebo loads glTF PBR directly, so
nothing needs declaring anywhere else — but the `.glb` must actually carry them.

### How part names are chosen

Recorded so the catalogue stays coherent as it grows. All lowercase, snake_case:

* **Named for the product as Blue Robotics sells it**, not for its function in a
  vehicle.
* **Vehicle prefix only when the part physically fits that vehicle alone** —
  `blueboat_payload_bracket`, `bluerov2_heavy_kit`. Being sold on a vehicle's
  accessories page is not enough: the T200 thruster and the antenna mast are
  general parts and carry no prefix, even though Blue Robotics list them under a
  vehicle. When in doubt, leave the prefix off — parts are shared by default.
* **Vendor prefix only when the product name alone is ambiguous** — `waterlinked_a50_dvl`
  and `marinesitu_c3_stereocamera` need it; `omniscan_450_sidescan`, `sonoptix_echo_multibeam`
  and `explorehd_camera` do not.
* **Function suffix where the product name does not say what it is** —
  `_sidescan`, `_multibeam`, `_scanning`, `_stereocamera`.
* **Articulated assemblies split into their moving pieces**, sharing a prefix so
  they sort together: `newton_gripper_cylinder`, `newton_gripper_shaft`,
  `newton_gripper_jaw`, `newton_sampler_cup`.

## What happens next

`scripts/import_part.py` reads `model.sdf`, converts the collision geometry into
URDF form, and writes it into `<part_name>.urdf.xacro` between generated-content
markers. It runs on every delivery, not once. `model.sdf` is kept afterwards as
the record of what was delivered and as the input to re-import.

## Parts

The catalogue is [`models/parts.csv`](models/parts.csv) — one row per part, with
the directory name, which vehicle it belongs to, the product page and delivery
notes. That file is the contract; this README describes how to read it.

Blue Robotics publish renderings, dimensions and CAD for most parts on the
product pages linked there.

The general shape: each vehicle is delivered as one complete mesh, with a small
number of deliberate exclusions — propellers, and accessories that are optional
or articulated. Those come as separate parts and are assembled in Gazebo, usually
with a joint. A part carries no joints itself, which is why articulated items
like the Newton gripper arrive as several parts rather than one.

```bash
column -s, -t models/parts.csv | less -S     # readable view
```

## Open questions

**Is `t200_thruster` needed as its own part?** The BlueROV2 vessel mesh already
includes its thruster fairings and ducts, and the BlueBoat vessel may likewise
include the thruster bodies. If so, only the propellers need to be separate and
this part can be dropped.

**Are the two Newton gripper jaws mirror images?** If they are, they need two
meshes rather than one part instantiated twice, and `newton_gripper_jaw` should
split into left and right.

**Colour variants.** The BlueBoat vessel is wanted in blue, red, green and
orange. Undecided whether that is four `.glb` files, or one mesh with swappable
textures — the latter is preferable if the tooling allows it.

## Renaming from earlier deliveries

Parts delivered before this catalogue existed used different names. These are
the canonical ones:

| Delivered as | Canonical name |
|---|---|
| `blueboat.visual` | `blueboat_vessel` |
| `T200/thruster` | `t200_thruster` |
| `T200_prop/thruster_propeller` | `weedless_prop_cw` / `weedless_prop_ccw` |
| `blueboat_prop` | `weedless_prop_cw` / `weedless_prop_ccw` |
| `directional_antenna` | `basestation_antenna` |
| `sonar` | `ping2_sonar` |
| `side_scan_sonar` | `omniscan_450` |
| `surveyor` | `surveyor_multibeam` |
