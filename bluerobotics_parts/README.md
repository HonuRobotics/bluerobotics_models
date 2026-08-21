# bluerobotics_parts

Shared part library for all Blue Robotics vehicle models.

A **part** is a single physical component: one mesh, **no joints**, geometry only — visual, collision and inertia.

Parts are vehicle-agnostic. A part lives here whether one vehicle uses it or both. Assemblies — parts plus the joints between them — live in the per-vehicle `*_description` packages and are composed from a parts list by [`urdf/assembly.xacro`](urdf/assembly.xacro).

See the [repository README](../README.md) for the full design.

## The part is a URDF xacro macro

`urdf/<part>.urdf.xacro` is the part. It is hand-maintained source, committed like any other, and complete on its own. It holds two macros ([`urdf/parts.xacro`](urdf/parts.xacro) documents the contract and includes every part):

* `<part>_info` exports the part's metadata as the property `part_info`: the **attach** offset (where it bolts onto its parent), the spin **axis**, its **slots** and its **frames**.
* `<part>` instantiates it: one link (inertia, visual, optional collision), the mounting joint (`part_joint`, which folds in the attach offset so a mast whose origin is at its centroid still stands on the deck), and its slots and frames as massless links `<name>_<slot>` / `<name>_<frame>`, visible in TF and lumped away in Gazebo where they survive as frames of the same name.

**Slots** are how parts fit together without anyone knowing coordinates: a slot is a named mount point with the part types that fit (`accepts`) and a `default` occupant (or `none`). The chassis declares `motor_port` (accepts the M200 weedless or T200 propellers, default M200), `ping_mount` (accepts the Ping2 bracket, default the bracket), `mast`, `flag`, `payload`; the bracket declares `ping` (default the Ping). An assembly fills every slot with its default and the vehicle config only states differences ([`urdf/assembly.xacro`](urdf/assembly.xacro)). Batteries will use the same mechanism: a battery is a part like any other, and the chassis will declare the bays. **Frames** mark reference points on a part, such as a sensor's beam origin; the Gazebo side places the sensor there.

How the file came to exist does not matter downstream. It can be written by hand from a datasheet, or bootstrapped from a modeler's SDF delivery with `scripts/sdf_to_part.py` (below). Mass, inertia tensor and center of gravity are stated in the part and nowhere else; assemblies compose them, see [AUR_BUOYANCY_DESIGN.md](../AUR_BUOYANCY_DESIGN.md).

## What the modeler delivers

Into `models/<model_name>/`, using exactly the directory names listed in [`models/parts.csv`](models/parts.csv). Filenames are explicit — they repeat the part name, so a file still identifies itself once it has been moved, attached to a message or opened on its own:

```
models/blueboat_chassis/
  blueboat_chassis.visual.glb        # required — visual mesh, PBR materials embedded
  model.sdf                          # collision primitives, as delivered
  blueboat_chassis.collision.stl     # optional — only if a primitive will not do
```

The `.glb` is what the part macro's visual points at, so it stays in the repository. `model.sdf` is the modeler's work product: the collision primitives, and the input to the bootstrap below. Nothing in ROS or Gazebo reads it; once a part's macro exists the SDF is reference material, and the plan is to keep the SDF deliveries on a separate branch so the released package carries only what it uses.

**Collision geometry is specified by the modeler, in `model.sdf`, as primitive shapes in SDF `<geometry>`.** The bootstrap translates it; nothing downstream invents the contact shape.

### Rules

1. **The directory name is the part name.** Not the mesh's internal name, not the Blender object name. If the right directory is not in `parts.csv`, ask before inventing one.
2. **Origin and orientation.** The origin of the part's body-centered frame sits at the **centroid of the mesh** — the center of the geometry, equivalently its center of mass if uniform density is assumed. The frame is aligned per [REP 103](https://www.ros.org/reps/rep-0103.html): **x forward, y left, z up**. Note that the centroid of the mesh is not the part's center of gravity, which depends on where the mass actually sits and is stated separately in the part macro.
3. **Collision shapes: box, cylinder, sphere or mesh — never cone or plane.** URDF cannot express cone or plane at all, and the bootstrap rejects them. Prefer primitives; a coarse approximation of the mesh is what is wanted.
4. **No spaces or `.001`-style suffixes in any name.** Collision and link names become ROS frame and topic names downstream.
5. **Attachment points, when known, as SDF frames.** A `<frame name="attach">` where the part bolts onto its parent and a frame per place other parts bolt onto it save a measurement downstream. Not required; the bootstrap takes slots and frames on the command line.

Materials ride along inside the `.glb`. Gazebo loads glTF PBR directly, so nothing needs declaring anywhere else — but the `.glb` must actually carry them.

### How part names are chosen

Recorded so the catalog stays coherent as it grows. All lowercase, snake_case:

* **Named for the product as Blue Robotics sells it**, not for its function in a vehicle.
* **Vehicle prefix only when the part physically fits that vehicle alone** — `blueboat_payload_bracket`, `bluerov2_payload_skid`.
* **Vendor prefix only when the product name alone is ambiguous** — `waterlinked_a50_dvl` and `marinesitu_c3_stereocamera` need it; `omniscan_450_sidescan`, `sonoptix_echo_multibeam` and `explorehd_camera` do not.
* **Function suffix where the product name does not say what it is** — `_sidescan`, `_multibeam`, `_scanning`, `_stereocamera`.
* **Articulated assemblies split into their moving pieces**, sharing a prefix so they sort together: `newton_gripper_cylinder`, `newton_gripper_shaft`, `newton_gripper_jaw`, `newton_sampler_cup`.

## Bootstrapping a part from an SDF delivery

`scripts/sdf_to_part.py` writes the first version of `urdf/<part>.urdf.xacro` from `models/<part>/model.sdf`:

* the visual, pointing at the delivered `.glb`;
* the collision primitives, translated to URDF (a collision mesh is referenced as delivered);
* an **inertia estimate**: the primitives are run through SDF auto inertia (`gz sdf --expand-auto-inertials`) at a uniform density, which yields mass, center of mass and the full tensor; a collision mesh is integrated directly. With `--mass` the tensor is scaled to the known mass, keeping its shape and center.

Slots, frames, the attach offset and a spin axis can be seeded on the command line:

```bash
ros2 run bluerobotics_parts sdf_to_part.py models/t200_thruster --mass 0.344
ros2 run bluerobotics_parts sdf_to_part.py models/blueboat_antenna_mast --attach "0 0 -0.331"
ros2 run bluerobotics_parts sdf_to_part.py models/ping_singlebeam --frame beam=0,0,-0.044
ros2 run bluerobotics_parts sdf_to_part.py models/blueboat_chassis --mass 12 \
    --slot "motor_port=-0.52,0.301,-0.117;accepts=m200_weedless_prop_ccw,t200_prop_ccw;default=m200_weedless_prop_ccw;joint=continuous" \
    --slot "ping_mount=0,-0.259,0.01;accepts=blueboat_ping_singlebeam_mount;default=blueboat_ping_singlebeam_mount"
```

The tool refuses to overwrite an existing macro unless told to with `--force`: once written, the file is maintained by hand, and a redelivery is compared against it rather than stamped over it. Nothing regenerates it during `colcon build`.

## Accepting a new part

In order — the Gazebo check comes first because everything after it is work done on top of the delivery.

### 1. Files and names

- [ ] Directory name matches a row in [`models/parts.csv`](models/parts.csv). If it does not, stop and ask — do not invent a row.
- [ ] `<part>.visual.glb` and `model.sdf` are both present, named for the part.
- [ ] Collision shapes in `model.sdf` are box, cylinder, sphere or mesh. **Never cone or plane.**
- [ ] `model.sdf` parses: `gz sdf -p models/<part>/model.sdf`

### 2. Look at the delivery in Gazebo

```bash
export SDF_PATH=$GZ_SIM_RESOURCE_PATH
gz sim models/<part>/model.sdf
```

- [ ] **Scale.** Compare against something of known size, not against intuition. This is the most common defect.
- [ ] **Frame location.** Origin at the centroid of the mesh — not at the base, not at the bolt-on point.
- [ ] **Frame orientation.** x forward, y left, z up.
- [ ] **Materials.** PBR renders as intended, not flat grey.
- [ ] **Collision geometry.** A sensible envelope: not inside-out, not oversized, not offset.

Anything wrong here goes back to the modeler. To see every delivery at once, [`worlds/parts_gallery.sdf`](worlds/parts_gallery.sdf) lays out all the `model.sdf` files.

### 3. Bootstrap the macro and review it

```bash
ros2 run bluerobotics_parts sdf_to_part.py models/<part> [--mass KG] [--attach "x y z"] [--slot ...] [--frame ...]
```

- [ ] Read `urdf/<part>.urdf.xacro` through. This is the review it gets; it is source from here on.
- [ ] Mass: stated if known (`--mass`), otherwise the density estimate, flagged in the file header for replacement.
- [ ] Slots (with what fits and the default), frames and the attach offset, if the part has them.
- [ ] Add the include line to [`urdf/parts.xacro`](urdf/parts.xacro), alphabetically.

### 4. Verify the macro

```bash
colcon build --merge-install --packages-select bluerobotics_parts && source install/setup.bash
PARTS=$(ros2 pkg prefix --share bluerobotics_parts)
xacro $PARTS/urdf/part_probe.urdf.xacro part:=<part> > /tmp/probe.urdf && check_urdf /tmp/probe.urdf
```

[`urdf/part_probe.urdf.xacro`](urdf/part_probe.urdf.xacro) mounts the part four ways in one pass: two instances coexist, `collision:=false` works, and a part can parent to another part. `check_urdf` does not resolve `package://`; check mesh URIs resolve separately if in doubt.

### 5. Check inertia, collisions and visuals together

```bash
ros2 run bluerobotics_parts parts_check_world.py --out $PARTS/worlds/parts_check.sdf
gz sim $PARTS/worlds/parts_check.sdf
```

[`worlds/parts_check.sdf`](worlds/parts_check.sdf) lays out every part **from its macro** — each expanded and converted to SDF exactly as the assembled vehicle is — as its own static model on a grid. Right click a part, View → Collisions / Inertia / Center of Mass / Transparent, and compare against the mesh. The committed world is regenerated whenever a macro changes.

### 6. In an assembly

- [ ] Add it to a vehicle's parts config and confirm the aggregate mass properties move the way you would expect.
- [ ] For a USV, check the waterline still looks right; for a UUV, check trim has not been thrown off.

## Parts naming

Parts catalog is [`models/parts.csv`](models/parts.csv) — one row per part. Blue Robotics publish renderings, dimensions and CAD for most parts on the product pages linked there.

```bash
column -s, -t models/parts.csv | less -S     # readable view
```
