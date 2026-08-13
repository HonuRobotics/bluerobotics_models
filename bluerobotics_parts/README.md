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
  blueboat_vessel.urdf.xacro        # required — the part's macro; see below
  blueboat_vessel.collision.stl     # optional — only if a primitive will not do
  model.config                      # optional — harmless, unused
```

`model.sdf` keeps its conventional name; Gazebo and the import script both expect it. Collision meshes carry no materials or UVs, so STL is the leanest choice — any format Gazebo reads will work, but pick one and stay with it.

The `.urdf.xacro` is required for every part, but it is not something the modeller authors from scratch — see [The part macro](#the-part-macro).

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

## The part macro

Every part has a `<part_name>.urdf.xacro` defining one macro that instantiates the part as a link: visual mesh, inertia, and optionally collision. It is what assemblies consume — they include the macro rather than reaching into the mesh or the SDF.

The file has two halves, and the distinction matters:

| Content | Origin |
|---|---|
| Visual and collision geometry | **Generated** by `import_part.py`, between the markers, from `model.sdf` |
| Mass, inertia tensor, center-of-gravity pose | **Hand-authored** outside the markers, from physical reality |

Collision is optional per part — some parts need contact geometry, many do not — but where it exists, the starting point is a translation of what `model.sdf` already describes, so the modeller's collision primitives remain the single description of the part's shape.

Inertia is the half no mesh can supply. Mass, the inertia tensor and the center-of-gravity pose come from measurement or from the vendor, not from the primitive geometry, and they are the source of truth for that part. Assemblies compose them; nothing re-derives them from a box. Because they live outside the generated markers, re-importing a redelivered mesh does not disturb them.

This is what makes the part the unit of truth for mass properties. See [AUR_BUOYANCY_DESIGN.md](../AUR_BUOYANCY_DESIGN.md) for how assemblies use it.

## Composing an assembly

Assemblies are described by a parts-level YAML that lists which parts a configuration contains and where they sit, generalizing the `accessories:` list in `bluerov2_description/config/bluerov2.yaml`. The YAML generates the model.

Membership is explicit rather than assumed — the chassis is not always included, so a configuration that is a subassembly, a bare frame or a test rig is expressible without a special case.

Whether that file lives per assembly or once at the parts level is still open; see the design document.

## Parts naming 

Parts catalog is [`models/parts.csv`](models/parts.csv) — one row per part.  Blue Robotics publish renderings, dimensions and CAD for most parts on the product pages linked there.


```bash
column -s, -t models/parts.csv | less -S     # readable view
```

