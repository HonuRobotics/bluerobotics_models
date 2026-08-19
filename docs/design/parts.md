# Parts library

A **part** is a single physical component: one mesh, no joints, geometry only.
Visual, collision and inertia — never sensors, never plugins. A `ping2_sonar`
part is the shape and mass of a Ping2; it becomes a sensor in `*_gazebo`, where
`<sensor>` elements and the plugins that drive them are configured.

Every part lives in `bluerobotics_parts/models/`, in one flat namespace,
regardless of which vehicle uses it. There is no "does a second vehicle use it
yet?" test and no migration when the answer changes. Category subdirectories
were considered and rejected: they buy no namespacing, and recategorising a
part later moves its path.

## The part contract

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

## The import script

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

## Rules for parts

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

## Reviewing new parts

When adding new parts to the repo, a few manual tests verify the components
(meshes and SDF files) are consistent with the standard workflow and
conventions.

### Parts gallery

To quickly review all the parts in the `bluerobotics_parts/models` directory,
a simple world file is included that arranges all the parts in a grid with
lighting conducive to reviewing the shapes and textures.

After following the [installation instructions](../getting-started/installation.md),
run Gazebo with the model gallery world:

```bash
gz sim ~/ws/src/bluerobotics_models/bluerobotics_parts/models/parts_gallery.sdf
```

### Parts standalone

It is also possible to load the individual parts, by loading the individual
`model.sdf` files, e.g.:

```bash
gz sim ~/ws/src/bluerobotics_models/bluerobotics_parts/models/blueboat_chassis/model.sdf
```

Because there is no world file, the lighting is default and not representative
of the maritime environments, but it is a convenient standalone test.
