# Model layout design

Status: draft proposal, for review.

---

# Part 1 — The proposal

## Summary

Keep URDF as the source of truth. Stop transcribing the modeller's geometry by hand — automate it instead.

* **The modeller delivers a part** as a directory containing a `.glb` and a `model.sdf`, which is what their Blender tooling already exports. Nothing about their workflow changes.
* **An import script converts the collision geometry** in `model.sdf` into URDF form, writing it into that part's xacro macro between generated-content markers. The step that produced PR #5's defects becomes a program rather than a person.
* **Developers write the xacro macro** that wraps each part, and the assemblies that compose them — the same pattern Clearpath use across their robot range.
* **Everything downstream is unchanged.** Gazebo merge-includes the URDF as it does today; ROS consumes the URDF directly. No format conversion sits in the runtime path.

Parts live in one flat namespace in a new `bluerobotics_parts` package. A part is geometry only — visual, collision, inertia — with no sensors and no plugins.

This is an incremental change to the current architecture, not a restructure. Two packages keep their shape, the build keeps its shape, and both consumption paths are untouched.

In general, each robot description includes a simple, complete standalone configuration and a programmatic method (xacro and yaml) to generate more complex ones (optional sensors, actuators, etc.). Simple things simple: reuse the checked-in default robot, no config. Complex things possible: the programmatic path for custom configuration. The two are deliberately **not kept in sync** — the standalone configuration is conceptually the programmatic one with every option turned off, but nothing enforces or tests that, and promising it would create a maintenance obligation with no payoff.


## Packages

Three, all ament packages.

| Package | Holds | Consumer |
|---|---|---|
| `bluerobotics_parts` | **Every part** — mesh, delivered SDF, and xacro macro | Every vehicle |
| `<vehicle>_description` | Assemblies, plus the ROS-facing `config/`, `launch/` and `rviz/` | ROS, RViz, anything off-sim |
| `<vehicle>_gazebo` | Plugins, sensors, worlds, bridge config | Gazebo only |

They are ament packages rather than bare directories for a mechanical reason: the environment hook each one installs is what prepends its `share/` to `GZ_SIM_RESOURCE_PATH`, and that is the only thing making meshes resolvable at runtime. A plain directory cannot register itself. `*_gazebo` additionally carries launch files, worlds and generated bridge config, which want colcon install and `$(find-pkg-share …)`; deb releases (see `RELEASING.md`) need packages too.


## Directory layout

```
bluerobotics_parts/
  models/                                  # flat — no category subdirectories
    t200_housing/
      t200_housing.glb                     # delivered by the modeller
      model.sdf                            # delivered by the modeller
      t200_housing.urdf.xacro              # macro; collisions generated, rest maintained
    t200_prop_cw/    …
    blueboat_hull/   …
    ping2_sonar/     …
  scripts/
    import_part.py                         # model.sdf collisions ⇒ urdf.xacro

blueboat_description/
  urdf/
    blueboat.urdf.xacro                    # assembly: composes part macros, adds joints
  config/blueboat.yaml
  launch/display.launch.xml
  rviz/

blueboat_gazebo/
  model.sdf.xacro                          # merge-includes the URDF, adds plugins + sensors
  worlds/
  launch/sim.launch.xml
  config/ros_gz_bridge.yaml
```

`bluerobotics_parts` starts empty. The meshes currently on `lyrical` are being redone by the modeller under this workflow, so parts arrive as they are exported — there is nothing to migrate.

Parts sit in a **flat** `models/` directory. Category subdirectories (bases / sensors / actuators / accessories) were considered and rejected: they buy no namespacing, recategorising a part later moves its path, and grouping comes free from naming — `t200_housing`, `t200_prop_cw`, `t200_prop_ccw` sort together.


## The part contract

Three artifacts per part, with distinct authority. This is the thing most likely to be misread, so it is worth being explicit.

| File | Origin | Authoritative for |
|---|---|---|
| `<part>.glb` | modeller | Visuals and materials — referenced directly by the URDF, never converted |
| `model.sdf` | modeller | Collision geometry **as delivered** |
| `<part>.urdf.xacro` | generated, then maintained | Collision geometry **as used**, plus the link, joint and inertia |

A developer tightening a collision primitive in the xacro will put it out of step with `model.sdf`. That is expected, not a defect: `model.sdf` records what the modeller shipped, the xacro records what we build with. Nobody should "fix" the divergence by editing `model.sdf`.

`model.sdf` is kept rather than deleted after import, for two reasons. It is the only record of what the modeller intended, and it is what makes re-import possible when a part is revised.


## The import script

Parts get revised — a scale error is found, the modeller re-exports. So this is **not a one-time migration**; it runs whenever a part is delivered or updated.

What it does:

1. Reads `model.sdf` and extracts every `<collision>`.
2. Rewrites SDF geometry into URDF form — `<pose>` becomes `<origin xyz rpy>`, `<box><size>` becomes `<box size=…>`, `<cylinder><radius>/<length>` become attributes.
3. Writes the result into the part's xacro between markers:

```xml
<!-- BEGIN GENERATED COLLISIONS — from model.sdf, do not edit by hand -->
…
<!-- END GENERATED COLLISIONS -->
```

4. Validates, and fails loudly rather than emitting something wrong.

Two properties matter. It must be **idempotent** — re-running on an unchanged part changes nothing. And it must **touch only the generated region**, so a re-import does not stamp on the inertia, joint or visual a developer has since edited.

Validation is where the geometry rules are enforced (see [Rules for parts](#rules-for-parts)). URDF has no cone, capsule, ellipsoid or plane, so a part using one cannot be converted at all and the script must say so plainly rather than silently dropping it.


## Composition

Developers write a xacro macro per part, and assemblies instantiate them — the pattern [Clearpath](https://github.com/clearpathrobotics/clearpath_common) use across their robot range, where a shared parts library and a yaml-driven generator build a family of configurable machines.

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

Joints belong to whatever composes the parts, never to a part itself — both `fixed` mounts and the `continuous` joints that spin propellers.


## What changes

| | Today | Proposed |
|---|---|---|
| Part geometry | re-authored by hand from the modeller's SDF | imported by script from the same SDF |
| Part storage | `meshes/` inside each `*_description` | one flat library in `bluerobotics_parts` |
| Part scope | mixed into the vehicle description | geometry only — no sensors, no plugins |
| Buoyancy | summed across all collisions, compensated by a hand-maintained volume table | one enabled buoyancy link on the assembly |
| Assembly | xacro macros | unchanged |
| Gazebo path | merge-includes the URDF | unchanged |
| ROS path | URDF direct | unchanged |

The last three rows are the point: the parts of the system that work are not being touched.


## Decisions

| Decision | One-line reason |
|---|---|
| URDF stays the source of truth | It is the format the ROS ecosystem uses, and everything downstream already consumes it |
| The modeller's `model.sdf` is imported by script, not by hand | The hand step is where PR #5's defects came from |
| `model.sdf` is kept after import | It is the record of intent and the input to re-import |
| Import runs per delivery, not once | Parts get revised; a one-time script recreates the transcription problem |
| A part is geometry only — no sensors, no plugins | Simulation behaviour is a `*_gazebo` concern |
| Parts live in one flat namespace | Categories buy no namespacing and churn paths when a part is recategorised |
| The assembly owns displacement, via one enabled buoyancy link | Decouples flotation from part collisions; removes the hand-maintained volume table |
| PBR is declared nowhere — it lives in the `.glb` | Gazebo loads glTF materials directly |
| Standalone and programmatic configurations are *not* kept in sync | Guaranteeing it buys nothing and costs maintenance |


## Rules for parts

The practical contract. Anything shipped as a part must obey these or it breaks something downstream.

### What a part contains

A part is **geometry only** — visual, collision, inertia. Nothing else.

A `ping2_sonar` part is the shape and mass of a Ping2, not a sensor. It becomes a sensor in `*_gazebo`, when `<sensor>` elements and the plugins that drive them are added and configured. Update rates, topic names and noise models are simulation concerns and live there.

**Materials come with the mesh.** Gazebo loads PBR directly from `.glb` — the loader reads glTF materials, splits the combined metallic-roughness texture into separate maps, and handles normal, emissive and light maps. Nothing is declared in the URDF beyond the mesh reference. What this puts on the modeller is that the `.glb` must carry proper PBR materials, which their workflow already calls for.

### Geometry restrictions

Two constraints, binding different things.

**Everything, always.** URDF expresses four collision shapes: box, cylinder, sphere and mesh. It has no cone, capsule, ellipsoid or plane. The export tool offers cone and plane, so this is reachable in practice — the import script must reject them rather than approximate.

**The assembly's buoyancy link only** — nothing else displaces water, so nothing else is affected:

| Buoyancy mode | Accepts | Used by |
|---|---|---|
| **Graded** | `<box>`, `<sphere>` **only** | USVs |
| **Uniform** | box, sphere, cylinder, mesh | UUVs |

Under graded buoyancy anything outside box/sphere displaces nothing and warns once per process, which is easy to miss entirely.

So there is a single rule for the modeller:

> **box, cylinder, sphere or mesh — never cone or plane.**

The tighter box-or-sphere rule belongs to whoever authors the buoyancy link — a developer, at the assembly level — and never reaches the modeller.

### Collision geometry cases

| Case | Visual | Collision | Used today for |
|---|---|---|---|
| **1. Visual only** | `.glb` | *none* | Every passive accessory on both vehicles |
| **2. Visual + primitives** | `.glb` | box, cylinder, sphere | Manipulator parts (gripper jaws, claw body, sampler cup) |
| **3. Visual + collision mesh** | `.glb` | mesh file | Nothing, currently |

A part's collision is **contact geometry only**. Displacement is not a part concern — see [Buoyancy](#buoyancy-the-assembly-owns-displacement).

**Case 1 — visual only.** These are currently "accessories". They contribute mass but no volume, so no buoyancy and no collisions. Whether neglecting collisions is acceptable depends on the object and the scenario. Collision geometry costs physics time, though primitives are computationally cheap.

**Case 2 — visual mesh, primitive collision. This is the default.** The modeller ships every part with collision primitives that coarsely approximate the mesh. Not a decision made per part — it is simply what a part is, so approximate collision geometry always exists and nobody has to go back and ask for it. Developers refine those primitives in the xacro when a part needs better, and drop to Case 1 by removing them when a part needs no contact at all. Both are edits to something that already exists rather than work commissioned from the modeller.

**Case 3 — visual mesh, collision mesh.** Currently unused, but a path we should have. Two constraints: graded buoyancy rejects mesh collisions outright, so a mesh-collision part cannot displace water on a USV; and mesh collision is materially more expensive per contact than a primitive.

### Validation on import

Enforced by the import script, which fails rather than warns:

| Check | Why |
|---|---|
| Geometry is box / cylinder / sphere / mesh only | URDF cannot express cone or plane at all |
| Collision primitives present, approximating the mesh | Case 2 is the default; developers refine rather than commission |
| Names free of spaces and `.00N` suffixes | they become link, frame and topic names downstream |
| Dimensions sane against the part's real size | catches the r = 0.41 m class of export error |
| `<inertial>` present with plausible mass | parts contribute mass to the assembly |


## Buoyancy: the assembly owns displacement

The Buoyancy plugin sums every collision in a model, which makes displacement a whole-vehicle quantity. This design distributes collisions to parts, so the two pull against each other — and today the repo resolves it by hand, summing accessory volumes and shrinking the hull box to compensate.

**SDF has the override.** `<enable>` is evaluated **per link**, not per model. A link that is not enabled is never given `Volume` or `CenterOfVolume` components, so it contributes no displacement in either graded or uniform mode. Multiple `<enable>` elements accumulate, so several links can be enabled where a vehicle needs distributed displacement.

So the assembly carries a dedicated buoyancy link holding the displacement geometry, and the world enables buoyancy on that link alone:

```xml
<enable>blueboat::buoyancy_link</enable>
```

**Parts own contact geometry; the assembly owns displacement (buoyancy).** No part needs to know whether the vehicle floats, nothing has to be subtracted to compensate for an accessory, and the hand-maintained `accessory_volume` table stops being necessary.

Collisions for buoyant bodies are typically programmatically generated in a manner tied to the overall vehicle (all-up-round, AUR) configuration. This higher level of abstraction — modelling the overall buoyancy of the AUR vehicle instead of summing all the components — is typical of the process for buoyant bodies:

* **BlueBoat pontoons** — six boxes per side rather than one long box, so under graded buoyancy each short segment responds to its own local depth and pitch restores properly. A single box keys off its centre depth and barely restores at all.
* **BlueROV2 hull** — a single box whose height is solved analytically so that `density × volume = mass × (1 + margin)`, giving the documented near-neutral buoyancy.

One consequence to design around: displacement must live **entirely** on the enabled link. A genuinely buoyant part — a float, a syntactic block — cannot express that through its own collision, so its volume has to be represented on the buoyancy link instead.

**Tested.** One model, two links: a small collision on `buoy_link` displacing 1 kg and a large one on `contact_link` displacing 27 kg, 10 kg total mass. With `<enable>testmodel</enable>` it rises (both collisions count); with `<enable>testmodel::buoy_link</enable>` it sinks (only 1 kg displaced). Identical models — only the scope of `<enable>` differed.


---

# Part 2 — Background and justification

## The problem

The modeller's tooling exports SDF. The description packages consume URDF. Today a person bridges that gap by retyping the geometry, and that hand step is the only place defects can enter.

```
modeller SDF  ──✗ discarded
                    hand re-author ──▶ URDF ──▶ (libsdformat) ──▶ SDF
```

Collision data that starts as SDF and ends as SDF makes a round trip through URDF and a human.

The proposal removes the human, not the round trip:

```
modeller SDF ──▶ import script ──▶ URDF (xacro) ──▶ (libsdformat) ──▶ SDF
```

That is a smaller change than it sounds, and deliberately so. The formats, the packages and both consumption paths stay as they are.


## Evidence from PR #5

The commented-out block in PR #5 *is* the modeller's SDF, and what happened to it is what the hand step produces. As contributed it contained:

* cylinders with radius 0.41 m on a hull 1.2 m long
* collision names containing spaces (`blue usv_collider_box`)
* Blender `.00N` suffixes
* SDF syntax (`<pose>`, `<box><size>`) pasted into a URDF file, where it cannot parse
* geometry yawed 180° from the URDF convention, with a z-offset on top

It was committed commented out, with "TODO: Verify I'm doing this right". The contributor was not being careless — the task as posed has no obvious right answer, which is why it should not be posed to a person.

None of these defects is detectable until the whole vehicle assembles and runs, because there is no smaller unit to test. Under this proposal the mesh is checkable on its own in a sandbox world, the collisions are machine-converted, and the shape rules are enforced at import.


## Why not SDF-first

An SDF-first design was considered and prototyped: parts as standalone SDF models, composed with `<include merge="true">`, published to `/robot_description` and converted for ROS by `sdformat_urdf`. Gazebo's [interoperability documentation](https://gazebosim.org/docs/latest/ros2_interop/) recommends exactly this.

It works. Two levels of merge-include flatten to a single `<model>` that `sdformat_urdf` converts, and `robot_state_publisher` publishes TF from it — both verified in the Jetty container.

It was rejected on ecosystem grounds. Benchmarking robots that ship to both ROS and Gazebo:

| Repo | xacro | SDF |
|---|---|---|
| `clearpath_common` | 130 | 0 |
| `turtlebot4` | 8 | 0 |
| `Universal_Robots_ROS2_Description` | 8 | 0 |
| `CentraleNantesROV/bluerov2` | 17 | 1 |

Nobody is SDF-first. `sdformat_urdf` has a few dozen stars and its principal dependents are its own release repositories. Adopting it would put a young, thinly-maintained converter on the critical path for every robot description we produce — we would be the ones finding its bugs, and its documented list of fatal conversion paths would become our support burden.

The asset-pipeline problem that motivated it is better solved by a script we own and can debug.

Recorded here so the option is not re-proposed without this context.


## Prior art

[Clearpath's `clearpath_common`](https://github.com/clearpathrobotics/clearpath_common) is the closest analogue — a family of configurable robots targeting both ROS and Gazebo:

```
clearpath_platform_description/     clearpath_sensors_description/
clearpath_mounts_description/       clearpath_manipulators_description/
clearpath_generator_common/         clearpath_customization/
```

A shared parts library split by kind, plus a yaml-driven generator. 130 xacro files and no SDF, with simulation content isolated in a `gazebo.urdf.xacro` gated behind `<xacro:if value="$(arg is_sim)">`.

The structure proposed here is theirs. The addition is the import script, which they do not need because their geometry does not arrive from an artist exporting SDF.


## What the Buoyancy plugin accepts

From [`Buoyancy.cc`](https://github.com/gazebosim/gz-sim/blob/main/src/systems/buoyancy/Buoyancy.cc):

| Mode | Accepts | Used by |
|---|---|---|
| **Graded** (`<graded_buoyancy>`) | `<box>` and `<sphere>` **only** | USVs |
| **Uniform** (`<uniform_fluid_density>`) | box, sphere, cylinder, mesh (plane ignored) | UUVs |

Graded mode dispatches on shape, and everything that is not a box or sphere falls to a `default:` branch logging *"Only \<box\> and \<sphere\> collisions are supported by the graded buoyancy option"* — behind a `static bool warned`, so it prints once per process and is very easy to miss. The part silently displaces nothing.

This is why the BlueBoat pontoons are boxes. It also means a cylinder is a perfectly reasonable collision choice for a submerged part on a UUV and a silent bug on a USV.


## Where parts come from

The modeller's workflow is [SDF_Gen](https://github.com/sanjanasrinivasan/gz-sim/blob/f1a16c0e26a6d9f0785b5c5013a175dec4615433/tutorials/setting_up_CAD_models.md), a Blender addon driven from CAD (SolidWorks / Fusion / Inventor via the STEPper addon). Its export is:

```
<part>/
  model.sdf        # links, visual, collision primitives
  model.config
  <part>.glb       # visual mesh
```

The tutorial favours primitive colliders over mesh colliders, authored by selecting the visual and fitting a primitive with scale-cage and face-snap tools — which is Case 2, the default.

Note this is a personal fork with a paid per-seat dependency. The proposal deliberately keeps it off the runtime path: it produces an input artifact that a script we control consumes. If the tool changes or becomes unavailable, the import script is what needs adjusting, and parts already imported are unaffected.


## A coupling that already bites

`bluerov2_description/urdf/accessories.xacro:23` carries a hand-maintained `accessory_volume` table listing `0.0` for every passive accessory and a hand-computed volume for the two manipulators, with the comment *"keep these in sync with the collision boxes below."*

That is Case 1 and Case 2 parts sharing one table, kept aligned by hand. The buoyancy link removes the need for it.
