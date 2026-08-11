# bluerobotics_parts

Shared part library for all Blue Robotics vehicle models.

A **part** is a single physical component: one mesh, **no joints**, geometry only — visual, collision and inertia. 

Parts are vehicle-agnostic. A part lives here whether one vehicle uses it or both. Assemblies — parts plus the joints between them — live in the per-vehicle `*_description` packages.

See the [repository README](../README.md) for the full design.

## What the modeller delivers

Into `models/<model_name>/`, using exactly the directory names listed in [`models/parts.csv`](models/parts.csv). Filenames are explicit — they repeat the part name, so a file still identifies itself once it has been moved, attached to a message or opened on its own:

```
models/blueboat_vessel/
  blueboat_vessel.visual.glb        # required — visual mesh, PBR materials embedded
  model.sdf                         # required — collision primitives
  blueboat_vessel.collision.stl     # optional — only if a primitive will not do
  model.config                      # optional — harmless, unused
```

`model.sdf` keeps its conventional name; Gazebo and the import script both expect it. Collision meshes carry no materials or UVs, so STL is the leanest choice — any format Gazebo reads will work, but pick one and stay with it.

### Rules

1. **The directory name is the part name.** Not the mesh's internal name, not the Blender object name. If the right directory is not in `parts.csv`, ask before inventing one.
2. **Origin and orientation.** The mesh origin sits approximately at the centroid of the mesh, oriented **x forward, y left, z up**. This is the one that is expensive to get wrong — a part delivered with a different convention looks correct in isolation and is wrong in every assembly that uses it.
3. **Collision shapes: box, cylinder, sphere or mesh — never cone or plane.** URDF cannot express cone or plane at all, and the import will reject them. Prefer primitives; a coarse approximation of the mesh is what is wanted.
4. **No spaces or `.001`-style suffixes in any name.** Collision and link names become ROS frame and topic names downstream.

Materials ride along inside the `.glb`. Gazebo loads glTF PBR directly, so nothing needs declaring anywhere else — but the `.glb` must actually carry them.

### How part names are chosen

Recorded so the catalogue stays coherent as it grows. All lowercase, snake_case:

* **Named for the product as Blue Robotics sells it**, not for its function in a vehicle.
* **Vehicle prefix only when the part physically fits that vehicle alone** — `blueboat_payload_bracket`, `bluerov2_payload_skid`. 
* **Vendor prefix only when the product name alone is ambiguous** — `waterlinked_a50_dvl` and `marinesitu_c3_stereocamera` need it; `omniscan_450_sidescan`, `sonoptix_echo_multibeam` and `explorehd_camera` do not.
* **Function suffix where the product name does not say what it is** — `_sidescan`, `_multibeam`, `_scanning`, `_stereocamera`.
* **Articulated assemblies split into their moving pieces**, sharing a prefix so they sort together: `newton_gripper_cylinder`, `newton_gripper_shaft`, `newton_gripper_jaw`, `newton_sampler_cup`.

## What happens next

`scripts/import_part.py` reads `model.sdf`, converts the collision geometry into URDF form, and writes it into `<part_name>.urdf.xacro` between generated-content markers. It runs on every delivery, not once. `model.sdf` is kept afterwards as the record of what was delivered and as the input to re-import.

## Parts naming 

Parts catalog is [`models/parts.csv`](models/parts.csv) — one row per part.  Blue Robotics publish renderings, dimensions and CAD for most parts on the product pages linked there.


```bash
column -s, -t models/parts.csv | less -S     # readable view
```

