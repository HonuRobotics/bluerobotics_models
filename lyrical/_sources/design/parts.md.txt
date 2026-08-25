# Parts

A **part** is a single physical component: one mesh, no joints, geometry
only (visual, collision, inertia). Parts are vehicle agnostic and live in
`bluerobotics_parts` whether one vehicle uses them or several; assemblies
(parts plus the joints between them) live in the per vehicle description
packages.

## The part contract

A part is one file, `bluerobotics_parts/urdf/<part>.urdf.xacro`, holding two
macros (`bluerobotics_parts/urdf/parts.xacro` documents them and includes
every part):

| Macro | Role |
|---|---|
| `<part>_info` | exports the metadata as the property `part_info`: `attach` (where the part bolts onto its parent, "x y z" in its own frame), `slots` (name → `xyz`, `rpy`, `accepts`, `default`, `joint`), `frames` (name → `xyz`, `rpy`) and, for propellers, `drive` (`diameter`, `max_thrust`, `min_thrust`, `rotation`), what a simulator needs to drive the part on its joint |
| `<part>` | instantiates it: one link (inertia, visual, optional collision), the mounting joint, and the slots and frames as massless links `<name>_<slot>` / `<name>_<frame>` |

Every part macro takes the same parameters: `name`, `parent` (`""` for the
assembly root), `xyz`/`rpy`, `collision` (`false` to fit without contact
geometry), `joint` (`fixed`, or `continuous` for parts that spin) and
`axis`, whose default is the part's own spin axis. The helper `part_joint`
folds the attach offset in, so a mast whose origin is at its centroid still
stands on the deck when fitted at a deck slot.

Mass, inertia and center of gravity are stated in the part and nowhere else;
assemblies compose them ([Buoyancy](buoyancy.md)).

## What the modeler delivers

Into `bluerobotics_parts/models/<part>/`, using exactly the names in
`models/parts.csv`:

```
models/blueboat_chassis/
  blueboat_chassis.visual.glb        # required: visual mesh, PBR materials embedded
  model.sdf                          # collision primitives, as delivered
  blueboat_chassis.collision.stl     # optional: only if a primitive will not do
```

Rules:

1. **The directory name is the part name.** If the right directory is not in
   `parts.csv`, ask before inventing one.
2. **Origin at the mesh centroid, x forward, y left, z up**
   ([REP 103](https://www.ros.org/reps/rep-0103.html)). The centroid is not
   the center of gravity; that is stated separately in the part.
3. **Collision shapes: box, cylinder, sphere or mesh. Never cone or plane.**
   URDF cannot express them and the bootstrap rejects them. Prefer
   primitives; a coarse envelope is what is wanted. Every part ships with
   primitives; developers refine or drop them (collision is optional at the
   point of use).
4. **No spaces or `.001` style suffixes in any name**; they become frame and
   topic names.
5. **Attachment points as SDF frames when known** (`attach`, and one per
   mount point): they save a measurement downstream. Not required.

Materials ride inside the `.glb`; Gazebo loads glTF PBR directly. The
`.glb` must be **Y-up**, as the glTF specification requires (the default
of any glTF exporter); a delivery exported Z-up shows correctly in Gazebo
but rolled 90 degrees in RViz and every other ROS tool, and is fixed once
with `gltf_to_yup.py`, which bakes the rotation into the file. The `.glb`
stays in the repository (the part's visual points at it). `model.sdf`
is the modeler's work product and the bootstrap input; nothing in ROS or
Gazebo reads it, and the plan is to keep the SDF deliveries on a side branch
so the released packages carry only what they use.

Part names: lowercase snake_case, named for the product as Blue Robotics
sells it; a vehicle prefix only when the part fits that vehicle alone
(`blueboat_payload_bracket`); a vendor prefix only when the product name is
ambiguous (`waterlinked_a50_dvl`); a function suffix where the name does not
say what it is (`_sidescan`, `_multibeam`); articulated assemblies split into
their moving pieces (`newton_gripper_cylinder`, `_shaft`, `_jaw`).

## Bootstrapping from a delivery

`sdf_to_part.py` writes the first version of the part from `model.sdf`:
the visual (pointing at the `.glb`), the collision primitives translated to
URDF, and an **inertia estimate**: the primitives run through SDF auto
inertia (`gz sdf --expand-auto-inertials`) at a uniform density, giving
mass, center of mass and the full tensor; a collision mesh is integrated
directly; `--mass` scales the tensor to a known mass, keeping its shape.
Slots, frames, attach and the spin axis come from flags; a propeller's
`drive` table is added by hand. The tool refuses to overwrite an existing
part: from the first write on, the file is source.

Inertia estimates are placeholders until measured or vendor values replace
them; the file header says which it is.

## Reviewing parts

`worlds/parts_check.sdf` lays out every part from its **macro** (expanded and
converted to SDF exactly as the vehicle is) as its own static model; the
Gazebo entity menu toggles collisions, inertia and center of mass against
the mesh. `worlds/parts_gallery.sdf` does the same for the raw deliveries.
The step by step acceptance list is in [Add a part](../how-to/add-part.md).
