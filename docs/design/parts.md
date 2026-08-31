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

## Meshes

Each part's visual mesh lives in `bluerobotics_parts/models/<part>/` as
`<part>.visual.glb`, PBR materials embedded; Gazebo loads glTF directly
and the ROS tools show the same file. Collision geometry is stated in the
macro as primitives (box, cylinder, sphere, or a mesh when a primitive
will not do; never cone or plane, which URDF cannot express); a coarse
envelope is preferred, and collision is optional at the point of use.

Conventions:

1. **The directory name is the part name.**
2. **Origin at the mesh centroid, x forward, y left, z up**
   ([REP 103](https://www.ros.org/reps/rep-0103.html)). The centroid is not
   the center of gravity; that is stated separately in the part.
3. **The `.glb` must be Y-up**, as the glTF specification requires (the
   default of any glTF exporter). A Z-up file shows correctly in Gazebo
   but rolled 90 degrees in RViz and every other ROS tool, and is fixed
   once with `gltf_to_yup.py`, which bakes the rotation into the file.
4. **No spaces or `.001` style suffixes in any name**; they become frame
   and topic names.

Part names: lowercase snake_case, named for the product as Blue Robotics
sells it; a vehicle prefix only when the part fits that vehicle alone
(`blueboat_payload_bracket`); a vendor prefix only when the product name is
ambiguous (`waterlinked_a50_dvl`); a function suffix where the name does not
say what it is (`_sidescan`, `_multibeam`); articulated assemblies split into
their moving pieces (`newton_gripper_cylinder`, `_shaft`, `_jaw`).

Inertia values are placeholders until measured or vendor values replace
them; each part's file header says which it is.

## Reviewing parts

`worlds/parts_check.sdf` lays out every part from its **macro** (expanded and
converted to SDF exactly as the vehicle is) as its own static model; the
Gazebo entity menu toggles collisions, inertia and center of mass against
the mesh. The step by step acceptance list is in
[Add a part](../how-to/add-part.md).
