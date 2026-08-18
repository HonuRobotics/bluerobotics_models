# Blue Robotics models

ROS 2 / Gazebo Sim model packages for Blue Robotics vehicles: the BlueROV2
underwater vehicle (standard and Heavy configurations) and the BlueBoat USV.

| Package | Purpose |
|---------|---------|
| [`bluerobotics_parts`](bluerobotics_parts/) | Every part — mesh, delivered SDF and xacro macro. Shared by all vehicles |
| [`bluerov2_description`](bluerov2_description/) | BlueROV2 assemblies, RViz; pure description, no simulator code |
| [`bluerov2_gazebo`](bluerov2_gazebo/) | Composed Gazebo model (thrusters, hydrodynamics, sensors, grippers), world, launch and ros_gz bridge |
| [`blueboat_description`](blueboat_description/) | BlueBoat assemblies, RViz; no simulator code |
| [`blueboat_gazebo`](blueboat_gazebo/) | Composed BlueBoat model (twin thrusters, hydrodynamics, echosounder), surface-water world, launch and ros_gz bridge |

Targets **ROS 2 Lyrical + Gazebo Jetty** (the default pairing on Ubuntu 26.04),
via `ros_gz`.

## Quick start

From source (binary `apt install ros-<distro>-bluerov2-*` packages are planned;
see each README's binary-install section for how configuration works there):

```bash
cd ~/ws/src && git clone https://github.com/HonuRobotics/bluerobotics_models.git
cd ~/ws
rosdep update
rosdep install --from-paths src --ignore-packages-from-source --default-yes
colcon build --merge-install
source install/setup.bash
ros2 launch bluerov2_gazebo sim.launch.xml     # Gazebo
```

In a second terminal (also sourced):

```bash
ros2 launch bluerov2_description display.launch.xml   # RViz
```

`rosdep update` refreshes the dependency database; skipping it in fresh
containers is the usual cause of "Cannot locate rosdep definition" errors.
The project standard is `colcon build --merge-install` (one deb style prefix,
the layout users get from binary installs). The default isolated layout also
works if you prefer it.

Each package README documents configuration (variant + accessory loadout),
ROS topics and how to include the model in an existing Gazebo world.

---

# Design

URDF is the source of truth. Geometry originates in CAD, is exported by the
modeller as SDF, and is converted into URDF by a script rather than by hand.

```
modeller  ──▶  <part>.glb + model.sdf  ──▶  import script  ──▶  <part>.urdf.xacro
                                                                      │
                                          assemblies (xacro) ◀────────┘
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                    ROS: URDF direct                    Gazebo: merge-includes the URDF
```

Nothing converts formats at runtime. Both consumption paths see the URDF the
build produces.

## Parts

A **part** is a single physical component: one mesh, no joints, geometry only.
Visual, collision and inertia — never sensors, never plugins. A `ping2_sonar`
part is the shape and mass of a Ping2; it becomes a sensor in `*_gazebo`, where
`<sensor>` elements and the plugins that drive them are configured.

Every part lives in `bluerobotics_parts/models/`, in one flat namespace,
regardless of which vehicle uses it. There is no "does a second vehicle use it
yet?" test and no migration when the answer changes. Category subdirectories
were considered and rejected: they buy no namespacing, and recategorising a
part later moves its path.

### The part contract

Three artifacts per part, with distinct authority:

| File | Origin | Authoritative for |
|---|---|---|
| `<part>.glb` | modeller | Visuals and materials — referenced directly, never converted |
| `model.sdf` | modeller | Collision geometry **as delivered** |
| `<part>.urdf.xacro` | generated, then maintained | Collision geometry **as used**, plus link, joint and inertia |

A developer tightening a collision primitive in the xacro puts it out of step
with `model.sdf`. That is expected, not a defect: `model.sdf` records what the
modeller shipped, the xacro records what we build with. Do not "fix" the
divergence by editing `model.sdf`.

`model.sdf` is kept rather than deleted after import. It is the only record of
what the modeller intended, and it is what makes re-import possible.

**Materials come with the mesh.** Gazebo loads PBR directly from `.glb` —
glTF materials, the combined metallic-roughness texture split into separate
maps, normal, emissive and light maps. Nothing is declared in the URDF beyond
the mesh reference. The obligation this puts on the modeller is that the `.glb`
carries proper PBR materials.

### The import script

Parts get revised, so this runs **whenever a part is delivered or updated** —
it is not a one-time migration. It reads `model.sdf`, rewrites each
`<collision>` into URDF form (`<pose>` → `<origin xyz rpy>`, `<box><size>` →
`<box size=…>`), and writes the result into the part's xacro between markers:

```xml
<!-- BEGIN GENERATED COLLISIONS — from model.sdf, do not edit by hand -->
…
<!-- END GENERATED COLLISIONS -->
```

It is idempotent, and it touches only the generated region — a re-import must
not stamp on inertia, joints or visuals a developer has since edited. It fails
loudly rather than emitting something wrong.

### Rules for parts

URDF expresses four collision shapes: **box, cylinder, sphere and mesh**. It has
no cone, capsule, ellipsoid or plane. The export tool offers cone and plane, so
this is reachable in practice and the import script rejects them rather than
approximating.

> **The rule for the modeller: box, cylinder, sphere or mesh — never cone or plane.**

Three collision cases:

| Case | Visual | Collision | For |
|---|---|---|---|
| **1. Visual only** | `.glb` | *none* | Passive accessories that need no contact |
| **2. Visual + primitives** | `.glb` | box, cylinder, sphere | **The default** |
| **3. Visual + collision mesh** | `.glb` | mesh file | Odd shapes where a primitive will not do |

Case 2 is what a part *is*, not a decision made per part: the modeller ships
every part with primitives that coarsely approximate the mesh, so approximate
collision geometry always exists and nobody has to go back and ask for it.
Developers refine those primitives when a part needs better, and drop to Case 1
by removing them when a part needs no contact at all — both are edits to
something that already exists rather than work commissioned from the modeller.

Case 3 carries two costs: graded buoyancy rejects mesh collisions outright, and
mesh contact is materially more expensive than a primitive.

The import script enforces:

| Check | Why |
|---|---|
| Geometry is box / cylinder / sphere / mesh | URDF cannot express cone or plane at all |
| Collision primitives present | Case 2 is the default |
| Names free of spaces and `.00N` suffixes | they become link, frame and topic names |
| Dimensions sane against the part's real size | catches export scale errors |
| `<inertial>` present with plausible mass | parts contribute mass to the assembly |

## Parts tests

When adding new parts to the repo, we run a few manual tests to verify the components (meshes and SDF files) are consistent with the standard workflow and conventions.

### Parts gallery

To quickly review all the parts in the `bluerobotics_parts/models` directory, an AI generated simple world file is included that arranges all the parts in a grid with lighting conducive to reviewing the shapes and textures.

After following the typical build instructions (see above), run Gazebo with the model gallery world:
```
gz sim ~/maritime_ws/src/bluerobotics_models/bluerobotics_parts/models/parts_gallery.sdf
```

### Parts standalone

It is also possible to load the individual parts, by loading the individual `model.sdf` files, e.g.,

```
gz sim ~/maritime_ws/src/bluerobotics_models/bluerobotics_parts/models/blueboat_chassis/model.sdf
```

Because there is no world file, the lighting is default and not representative of the maritime environments, but it is a convenient standalone test.

## Assemblies

Developers write a xacro macro per part; assemblies instantiate them and add the
joints. Joints belong to whatever composes the parts, never to a part itself —
both `fixed` mounts and the `continuous` joints that spin propellers.

```xml
<xacro:macro name="t200_housing" params="name parent *origin">
  <link name="${name}">
    <inertial>…</inertial>
    <visual>
      <geometry>
        <mesh filename="package://bluerobotics_parts/models/t200_housing/t200_housing.glb"/>
      </geometry>
    </visual>
    <!-- BEGIN GENERATED COLLISIONS -->
    <!-- END GENERATED COLLISIONS -->
  </link>
  <joint name="${name}_joint" type="fixed">
    <parent link="${parent}"/><child link="${name}"/>
    <xacro:insert_block name="origin"/>
  </joint>
</xacro:macro>
```

Each vehicle offers a simple, complete standalone configuration and a
programmatic method (xacro and yaml) for more complex ones. Simple things
simple: reuse the checked-in default robot, no config. Complex things possible:
the programmatic path for custom loadouts. The two are deliberately **not kept
in sync** — the standalone configuration is conceptually the programmatic one
with every option turned off, but nothing enforces that, and promising it would
create a maintenance obligation with no payoff.

## Buoyancy

The Gazebo Buoyancy plugin sums every collision in a model, which would make
displacement depend on which accessories are fitted. Instead, **the assembly
owns displacement and parts own contact geometry**.

`<enable>` is evaluated per *link*, not per model: a link that is not enabled is
never given `Volume` or `CenterOfVolume` components and contributes no
displacement. So the assembly carries a dedicated buoyancy link, and the world
enables buoyancy on that link alone:

```xml
<enable>blueboat::buoyancy_link</enable>
```

No part needs to know whether the vehicle floats, and nothing has to be
subtracted to compensate for an accessory.

Displacement geometry is generated from the all-up-round (AUR) vehicle
configuration rather than summed from components — modelling the overall
buoyancy of the assembled vehicle is the normal approach for buoyant bodies:

* **USV pontoons** — several boxes per side rather than one long box, so under
  graded buoyancy each short segment responds to its own local depth and pitch
  restores properly.
* **UUV hull** — a single box whose height is solved so that
  `density × volume = mass × (1 + margin)`, giving near-neutral buoyancy.

Shape matters here. Graded buoyancy accepts **`<box>` and `<sphere>` only**;
anything else displaces nothing and warns once per process, which is easy to
miss. Uniform buoyancy also accepts cylinder and mesh. That restriction applies
to the buoyancy link, not to parts, so it never reaches the modeller.

One consequence to design around: displacement must live entirely on the enabled
link. A genuinely buoyant part — a float, a syntactic block — cannot express
that through its own collision.

## Why it works this way

**The problem is transcription, not format.** The modeller's tooling exports
SDF; the description packages consume URDF. When a person bridges that gap by
retyping geometry, that hand step is the only place defects can enter. A
contributed part once arrived with cylinders of radius 0.41 m on a 1.2 m hull,
collision names containing spaces, geometry yawed 180°, and SDF syntax pasted
into a URDF file where it could not parse — committed commented out, with "TODO:
Verify I'm doing this right". The task as posed had no obvious right answer,
which is why it should not be posed to a person. None of it was detectable until
the whole vehicle assembled, because there was no smaller unit to test.

**SDF-first was prototyped and rejected.** Parts as standalone SDF models,
composed with `<include merge="true">` and converted for ROS by `sdformat_urdf`,
is what [Gazebo's interoperability
docs](https://gazebosim.org/docs/latest/ros2_interop/) recommend, and it works —
verified end to end. It was rejected on ecosystem grounds: benchmarking robots
that ship to both ROS and Gazebo (`clearpath_common` 130 xacro / 0 SDF,
`turtlebot4` 8 / 0, `Universal_Robots_ROS2_Description` 8 / 0), nobody is
SDF-first. Putting a young, thinly-maintained converter on the critical path for
every robot description would make its bugs ours to find. The asset-pipeline
problem it solved is better handled by a script we own.

**The structure is Clearpath's.**
[`clearpath_common`](https://github.com/clearpathrobotics/clearpath_common) is
the closest analogue — a family of configurable robots targeting both ROS and
Gazebo, built from a shared parts library plus a yaml-driven generator. The
addition here is the import script, which they do not need because their
geometry does not arrive from an artist exporting SDF.

## Contributing

Developer workflow (build, tests, pre-commit hooks, conventions):
see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0 (see [LICENSE](LICENSE)). Reused third-party meshes are credited in
[NOTICE](NOTICE) and `bluerov2_description/ASSETS.md`.
