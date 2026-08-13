# bluerobotics_parts

Shared part library for all Blue Robotics vehicle models.

A **part** is a single physical component: one mesh, **no joints**, geometry only — visual, collision and inertia. 

Parts are vehicle-agnostic. A part lives here whether one vehicle uses it or both. Assemblies — parts plus the joints between them — live in the per-vehicle `*_description` packages.

See the [repository README](../README.md) for the full design.

## What the modeler delivers

Into `models/<model_name>/`, using exactly the directory names listed in [`models/parts.csv`](models/parts.csv). Filenames are explicit — they repeat the part name, so a file still identifies itself once it has been moved, attached to a message or opened on its own:

```
models/blueboat_vessel/
  blueboat_vessel.visual.glb        # required — visual mesh, PBR materials embedded
  model.sdf                         # required — collision primitives
  blueboat_vessel.collision.stl     # optional — only if a primitive will not do
  model.config                      # optional — harmless, unused
```

`model.sdf` keeps its conventional name; Gazebo and the import script both expect it. Collision meshes carry no materials or UVs, so STL is the leanest choice — any format Gazebo reads will work, but pick one and stay with it.

**Collision geometry is specified by the modeler, in `model.sdf`, as primitive shapes in SDF `<geometry>`.** Nothing downstream invents the contact shape: the URDF form is a translation of that file rather than a second description of the same thing.

Two more files live in the same directory. The modeler does not write them — see [The three files per part](#the-three-files-per-part).

### Rules

1. **The directory name is the part name.** Not the mesh's internal name, not the Blender object name. If the right directory is not in `parts.csv`, ask before inventing one.
2. **Origin and orientation.** The origin of the part's body-centered frame sits at the **centroid of the mesh** — the center of the geometry, equivalently its center of mass if uniform density is assumed. The frame is aligned per [REP 103](https://www.ros.org/reps/rep-0103.html): **x forward, y left, z up**. Note that the centroid of the mesh is not the part's center of gravity, which depends on where the mass actually sits and is stated separately in `<part>.urdf.xacro`.
3. **Collision shapes: box, cylinder, sphere or mesh — never cone or plane.** URDF cannot express cone or plane at all, and the import will reject them. Prefer primitives; a coarse approximation of the mesh is what is wanted.
4. **No spaces or `.001`-style suffixes in any name.** Collision and link names become ROS frame and topic names downstream.

Materials ride along inside the `.glb`. Gazebo loads glTF PBR directly, so nothing needs declaring anywhere else — but the `.glb` must actually carry them.

### How part names are chosen

Recorded so the catalog stays coherent as it grows. All lowercase, snake_case:

* **Named for the product as Blue Robotics sells it**, not for its function in a vehicle.
* **Vehicle prefix only when the part physically fits that vehicle alone** — `blueboat_payload_bracket`, `bluerov2_payload_skid`. 
* **Vendor prefix only when the product name alone is ambiguous** — `waterlinked_a50_dvl` and `marinesitu_c3_stereocamera` need it; `omniscan_450_sidescan`, `sonoptix_echo_multibeam` and `explorehd_camera` do not.
* **Function suffix where the product name does not say what it is** — `_sidescan`, `_multibeam`, `_scanning`, `_stereocamera`.
* **Articulated assemblies split into their moving pieces**, sharing a prefix so they sort together: `newton_gripper_cylinder`, `newton_gripper_shaft`, `newton_gripper_jaw`, `newton_sampler_cup`.

## The three files per part

A finished part is three files, and which of them is written by a person matters:

| File | Written by | Contains |
|---|---|---|
| `model.sdf` | the modeler | Collision geometry, as SDF primitive shapes |
| `<part>.collision.xacro` | `scripts/import_part.py` | The same collision geometry translated into a URDF macro |
| `<part>.urdf.xacro` | hand-authored | The part macro assemblies call. Mass, inertia tensor and center-of-gravity pose |

**Who authors what, and what reads what.** The modeler works in SDF — that is what their tooling produces, and `model.sdf` is their work product. ROS and Gazebo read the xacro. `scripts/import_part.py` is the seam between the two.

SDF is not an interim format on the way to something else, and `model.sdf` is not deleted once a part is finished. It stays in version control as the record of what was delivered, which is what you go back to when a part's geometry is later disputed. The import script stays for the same reason, plus one more: it has to keep working every time a part is redelivered.

`<part>.urdf.xacro` includes `<part>.collision.xacro` and calls its macro, so sourcing the generated geometry is a one-line include rather than a block pasted into the middle of a hand-written file.

They are separate files on purpose. Generated content and hand-authored content in one file means a re-import either clobbers measured values or has to be careful not to; split apart, the generated file is overwritten wholesale and the hand-authored one is never touched by tooling at all.

**The generated file is committed.** It is generated once, at design time, and checked into the repo like any other source. It is not a build artifact: nothing regenerates it during `colcon build`, and a fresh clone has a complete part without running the import. Re-running the import is something a person does when the modeler redelivers, not something the build does.

Inertia is the half no mesh can supply. Mass, the inertia tensor and the center-of-gravity pose come from measurement or from the vendor, not from the primitive geometry, and they are stated once — in the part, and nowhere else. Assemblies compose them; nothing re-derives them from a box. See [AUR_BUOYANCY_DESIGN.md](../AUR_BUOYANCY_DESIGN.md) for how assemblies use them.

Collision is optional per part at the point of use — an assembly can mount a part with `collision: false` and get the visual and the mass without the contact geometry.

## Accepting a new part

What to do when the modeler delivers. In order — the Gazebo check comes first because everything after it is work done on top of the delivery, and there is no point doing that work on a part that is the wrong scale or facing the wrong way.

Run everything inside the drydock container, from `~/maritime_ws`.

### 1. Files and names

- [ ] Directory name matches a row in [`models/parts.csv`](models/parts.csv). If it does not, stop and ask — do not invent a row.
- [ ] `<part>.visual.glb` and `model.sdf` are both present, named for the part.
- [ ] Collision shapes in `model.sdf` are box, cylinder, sphere or mesh. **Never cone or plane** — URDF cannot express them and the import will reject them.
- [ ] `model.sdf` parses:

      gz sdf -p models/<part>/model.sdf

### 2. Bring it into Gazebo

Eyes on a render. None of this can be done from a terminal, and all of it is cheaper to catch now than after the part is wired into an assembly.

```bash
export SDF_PATH=$GZ_SIM_RESOURCE_PATH
gz sim models/<part>/model.sdf
```

- [ ] **Scale.** Compare against something of known size in the world, not against intuition. This is the most common defect.
- [ ] **Coordinate frame location.** Origin sits at the centroid of the mesh — not at the base, and not at the point the part happens to bolt on.
- [ ] **Coordinate frame orientation.** Per [REP 103](https://www.ros.org/reps/rep-0103.html): x forward, y left, z up. A part delivered in another convention looks correct in isolation and is wrong in every assembly that uses it — worth being deliberate rather than glancing.
- [ ] **Materials.** PBR renders as intended, not flat grey. Materials must be inside the `.glb`.
- [ ] **Collision geometry.** Turn on collision display and confirm the primitives are a sensible envelope — not inside-out, not wildly oversized, not offset from the mesh.

Anything wrong here goes back to the modeler. Do not work around it downstream.

### 3. Generate the collision macro

```bash
ros2 run bluerobotics_parts import_part.py models/<part>
```

- [ ] `<part>.collision.xacro` is written, and the geometry in it matches what you just looked at.
- [ ] Read it through. This is the only review it gets — nothing regenerates it afterwards.
- [ ] Commit it. It is source, not a build artifact.

> `scripts/import_part.py` is not written yet. Until it is, the collision macro is hand-written to the same shape, which makes the read-through matter more rather than less.

### 4. Fill in the mass properties

In `<part>.urdf.xacro`, from measurement or the vendor — not from the mesh, and not from the primitive:

- [ ] `<mass>` in kg.
- [ ] `<origin>` of the `<inertial>` block — the center-of-gravity pose in the part frame. 
- [ ] `<inertia>` tensor about that CoG.
- [ ] No `TODO` markers left behind.

### 5. Verify the part macro runs

Add the include line to [`urdf/parts.xacro`](urdf/parts.xacro), alphabetically, then:

```bash
colcon build --merge-install --packages-select bluerobotics_parts
source install/setup.bash
PARTS=$(ros2 pkg prefix bluerobotics_parts)/share/bluerobotics_parts
xacro $PARTS/urdf/part_probe.urdf.xacro part:=<part> > /tmp/probe.urdf
check_urdf /tmp/probe.urdf
```

[`urdf/part_probe.urdf.xacro`](urdf/part_probe.urdf.xacro) mounts the part four ways in one pass, so this covers the things that actually break:

- [ ] It instantiates at all.
- [ ] Two instances coexist — `probe` and `probe_second` — with no name collision.
- [ ] `probe_nocol` has the visual but no collision, so `collision:=false` works.
- [ ] `probe_stacked` hangs off `probe` rather than `base_link`, so a part can parent to another part.
- [ ] `check_urdf` parses and prints the tree.

`check_urdf` validates the XML but does not resolve `package://`, so it passes even when the mesh file is missing entirely. Check the URIs separately:

```bash
for u in $(grep -o 'package://[^"]*' /tmp/probe.urdf | sort -u); do
  pkg=${u#package://}; rel=${pkg#*/}; pkg=${pkg%%/*}
  d=$(ros2 pkg prefix --share "$pkg" 2>/dev/null)
  [ -n "$d" ] && [ -f "$d/$rel" ] && echo "ok       $u" || echo "MISSING  $u"
done
```

- [ ] Every mesh URI resolves to a file that exists.

Two failure modes worth recognizing. A part name that is not included yet fails with `unknown macro name: xacro:<part>`, which names the thing you forgot. Omitting `part:=` altogether fails with `Undefined substitution argument part`.

### 6. In an assembly

- [ ] Mount it on a real vehicle and confirm the aggregate mass properties move the way you would expect for something of that mass in that position.
- [ ] For a USV, check the waterline still looks right; for a UUV, check trim has not been thrown off.

## Parts naming 

Parts catalog is [`models/parts.csv`](models/parts.csv) — one row per part.  Blue Robotics publish renderings, dimensions and CAD for most parts on the product pages linked there.


```bash
column -s, -t models/parts.csv | less -S     # readable view
```

