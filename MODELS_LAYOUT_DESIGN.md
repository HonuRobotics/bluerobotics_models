# Model layout design

Status: draft proposal, for review.

---

# Part 1 — The proposal

## Summary

Move the source of truth from URDF to SDF - enable more interoperability with fewer steps.

* **Parts** are standalone SDF models — `model.sdf` + `model.config` + mesh — which is what the modeller's Blender tool exports. A part is **geometry only**: visual, collision and inertia. No sensors, no plugins, no simulation behaviour. Parts live in one flat namespace in a new `bluerobotics_parts` package.
* **Assemblies** are also SDF, composing parts with `<include merge="true">`.  A *standalone* assembly is the off-the-shelf vehicle — a plain `model.sdf`, hand-written and directly loadable. A *programmatic* assembly is a `model.sdf.xacro` generated from a yaml config. Composition is only expressible in SDF: URDF has no include mechanism, only xacro's text preprocessing.
* **Gazebo** consumes the assembly SDF directly, with a plugin and sensor layer added in `*_gazebo`.
* **ROS** gets that same assembly SDF published to `/robot_description`, with `<collision>` stripped. `robot_state_publisher` parses it through `sdformat_urdf`. **No URDF file is maintained anywhere.**


Two terms used throughout:

* **standalone** — a plain `model.sdf`, checked in and loadable as-is with `gz sim -f`. No generator in the path. True of every part, and of the off-the-shelf assemblies.
* **programmatic** — a `model.sdf.xacro` expanded at build time from a yaml config. Its output is an ordinary `model.sdf` with the same properties as a standalone one.

In general, each robot description includes a simple, complete standalone SDF assembly and a programmatic method (xacro and yaml) to generate more complex configurations (optional sensors, actuators, etc.).   Simple things simple: reuse the checked-in standalone robot, no build, no config. Complex things possible: the programmatic path for custom configuration. The two are deliberately **not kept in sync** — the standalone assembly is conceptually the programmatic one with every option turned off, but nothing enforces or tests that, and promising it would create a maintenance obligation with no payoff.

## Packages

Three, all ament packages.

| Package | Holds | Consumer |
|---|---|---|
| `bluerobotics_parts` | **Every part**, and its mesh — regardless of which vehicle uses it | ROS and Gazebo |
| `<vehicle>_description` | **Only assemblies** — standalone and programmatic SDF — plus the ROS-facing `config/`, `launch/` and `rviz/` | ROS, RViz, anything off-sim |
| `<vehicle>_gazebo` | Plugins, sensors, worlds, bridge config | Gazebo only |


That makes every *model* in `<vehicle>_description` an assembly. Any robot is at least two parts joined together, so a description package holds no standalone parts by definition — only assemblies, alongside the non-model files ROS needs (`config/`, `launch/`, `rviz/`).

They are ament packages rather than bare directories because the environment hook each one installs is what prepends its `share/` to `GZ_SIM_RESOURCE_PATH`, and that is the only thing making meshes and models resolvable at runtime. A plain directory cannot register itself. `*_gazebo` additionally carries launch files, worlds and generated bridge config, which want colcon install and `$(find-pkg-share …)`; deb releases (see `RELEASING.md`) need packages too.

This is also the layout the [`sdformat_urdf` documentation](https://github.com/ros/sdformat_urdf/tree/rolling/sdformat_urdf#considerations-for-mesh-uris) recommends — ship models inside a ROS package, reference them with `package://`, put `<prefix>/share` on `GZ_SIM_RESOURCE_PATH`. The existing `resource_paths.dsv.in` hooks already do this correctly.

## Directory layout

```
bluerobotics_parts/                 # EVERY part, whoever uses it
  models/                            # plain SDF, no build step
    blueboat_hull/   { model.sdf, model.config, blueboat_hull.glb }
    bluerov2_hull/   …
    t200_housing/    …
    t200_prop_cw/    …
    t200_prop_ccw/   …
    ping2_sonar/     …
    ping2_mount/     …
    antenna_mast/    …

blueboat_description/                # assemblies only, simulator-free
  models/
    blueboat/      { model.sdf, model.config }   # standalone assembly: parts + joints
  model.sdf.xacro                    # programmatic assembly (config-driven)
  config/blueboat.yaml
  launch/display.launch.xml          # RViz
  rviz/

blueboat_gazebo/                     # simulation-only
  model.sdf.xacro                    # merge-includes the description assembly, adds plugins + sensors
  worlds/
  launch/sim.launch.xml
  config/ros_gz_bridge.yaml
```

There is no URDF. `robot_state_publisher` accepts SDF on `/robot_description` and converts it internally through `sdformat_urdf`, so URDF becomes something a parser produces in memory.

`bluerobotics_parts` starts empty. The meshes currently on `lyrical` are being redone by the modeller under this workflow, so parts arrive as they are exported — there is nothing to migrate or reconcile.

Parts sit in a **flat** `models/` directory. Category subdirectories (bases / sensors / actuators / accessories) were considered and rejected: they cost an extra `GZ_SIM_RESOURCE_PATH` entry each for `model://` to resolve, they buy no namespacing because Gazebo's model namespace is flat regardless, and recategorising a part later renames its URI. Grouping comes free from naming — `t200_housing`, `t200_prop_cw`, `t200_prop_ccw` sort together.


## SDF foundation for both ROS and Gazebo robot models

```
parts (SDF) ──merge──▶ description assembly (SDF) ──merge──▶ gazebo model (+plugins) ──▶ Gazebo
                                │
                                └──▶ strip <collision> ──▶ /robot_description ──▶ robot_state_publisher ──▶ TF
```

Gazebo gets the full model with plugins. ROS gets the description-layer assembly, plugin-free and collision-stripped, published as SDF. Neither path re-authors anything the other declared.

Keeping the ROS path on the *description* layer rather than the gazebo layer matters: it preserves the simulator-free boundary, so nothing in ROS ends up depending on `*_gazebo`.

The collision-stripped SDF is a **checked-in artifact** — generated, committed and reviewed like any other file, so a change to it shows up in a PR. No existing tool does the stripping (`gz sdf -p` resolves includes and nothing more), but it is roughly fifteen lines of `xml.etree`. The cost of checking it in is staleness, guarded the usual way: regenerate in CI and fail if the result differs from what is committed.

### It also splits the work cleanly

The same boundary that separates parts from assemblies separates the people doing the work.

The modeller produces **parts** — one physical component each, exported straight from Blender as `model.sdf` + `model.config` + mesh, and checkable in isolation by loading the file. Developers compose those parts into **assemblies**, adding joints, and layer simulation behaviour on top in `*_gazebo`.


## What changes

| Tier | Today | Proposed |
|---|---|---|
| Part | meshes only; collisions re-authored by hand in xacro | `model.sdf` + `model.config` + mesh, straight from the modeller |
| Standalone assembly | does not exist | plain SDF, checked in, directly loadable |
| Programmatic assembly | `*.urdf.xacro` → URDF | `model.sdf.xacro` → SDF — same xacro, pointed at SDF |
| Gazebo model | merge-includes the URDF | merge-includes the description SDF — unchanged in shape |
| ROS description | generated URDF file | the description SDF, filtered, published to a topic |

The three-package structure, the `merge=true` layering and the config-driven generation all survive. Only the format flips, and the hand re-authoring step disappears.


## Decisions

| Decision | One-line reason | Detail |
|---|---|---|
| SDF is the source of truth | It is what the modeller's tool exports, what Gazebo consumes, and a superset of URDF | [Why SDF-first](#why-sdf-first) |
| No URDF is maintained | `sdformat_urdf` converts in memory inside `robot_state_publisher` | [Why SDF-first](#why-sdf-first) |
| `<collision>` is stripped from the ROS projection | Nothing in ROS consumes it, and unsupported shapes abort the whole conversion | [What sdformat_urdf costs](#what-sdformat_urdf-costs) |
| Every part carries a `model.sdf` | "No collision" and "collision nobody declared" must not look identical | [Collision cases](#collision-geometry-cases) |
| Parts live in one flat namespace | Categories cost resource-path entries and URI stability, and buy no namespacing | above |
| All three are ament packages | Only an ament package can install the resource-path hook | above |
| A part is geometry only — no sensors, no plugins | Simulation behaviour is a `*_gazebo` concern; `sdformat_urdf` drops link sensors anyway | [What a part contains](#what-a-part-contains) |
| The assembly owns displacement, via one enabled buoyancy link | Decouples flotation from part collisions; removes the hand-maintained volume table | [Buoyancy](#buoyancy-the-assembly-owns-displacement) |
| Standalone and programmatic assemblies are *not* kept in sync | Guaranteeing it buys nothing and costs maintenance | [Summary](#summary) |
| Parts ship with coarse primitive collisions by default | Approximate geometry always exists; developers refine instead of commissioning | [Collision cases](#collision-geometry-cases) |
| PBR is declared nowhere — it lives in the `.glb` | Gazebo loads glTF materials directly; nothing to restate in SDF | [What a part contains](#what-a-part-contains) |
| The collision-stripped SDF is checked in, guarded by CI | Reviewable and diffable; regeneration in CI catches staleness | above |


## Rules for parts

The practical contract. Anything shipped as a part must obey these or it breaks something downstream.

### What a part contains

A part is **geometry only** — visual, collision, inertia. Nothing else.

A `ping2_sonar` part is the shape and mass of a Ping2, not a sensor. It becomes a sensor in `*_gazebo`, when `<sensor>` elements and the plugins that drive them are added and configured. Update rates, topic names and noise models are simulation concerns and live there.

That boundary holds on every axis: `sdformat_urdf` drops link sensors anyway, so a part carrying one would lose it on the ROS path; and it keeps the modeller's contract narrow enough that they never have to reason about simulation behaviour. Geometry in, geometry out.

It works mechanically because merge-include does not rename links — `*_gazebo` can attach a `<sensor>` to a link that arrived from a part, by name.

**Materials come with the mesh.** Gazebo loads PBR directly from `.glb` — the loader reads glTF materials, splits the combined metallic-roughness texture into separate maps, and handles normal, emissive and light maps. Nothing is declared in SDF: a part references its mesh and the materials arrive with it. What this puts on the modeller is that the `.glb` must carry proper PBR materials, which their workflow already calls for. SDF `<material><pbr>` stays available as an override if a vehicle ever needs a variant finish on a shared part, but that is an exception rather than the pattern.

### Geometry restrictions

Two separate constraints, binding different things. Keeping them apart matters, because only one of them is the modeller's problem.

**Everything on the ROS path** — every part and every assembly, visuals as well as collisions. `sdformat_urdf` converts four shapes: box, cylinder, sphere and mesh. Anything else aborts the conversion outright, taking the whole robot description with it.

**The assembly's buoyancy link only** — nothing else displaces water, so nothing else is affected:

| Buoyancy mode | Accepts | Used by |
|---|---|---|
| **Graded** | `<box>`, `<sphere>` **only** | USVs |
| **Uniform** | box, sphere, cylinder, mesh | UUVs |

Under graded buoyancy anything outside box/sphere displaces nothing and warns once per process, which is easy to miss entirely.

So there is a single rule for the modeller:

> **box, cylinder, sphere or mesh — never cone or plane.**

That is worth stating explicitly because the export tool offers all five, and the two that are unsafe look no different from the three that are. A cone chosen for a nose fairing produces a part that behaves perfectly in Gazebo and silently destroys the ROS description of every vehicle that includes it.

The tighter box-or-sphere rule belongs to whoever authors the buoyancy link — a developer, working at the assembly level — and never reaches the modeller.

### Collision geometry cases

Not every part needs collision geometry, and the ones that do need it for different reasons.

| Case | Visual | Collision | Used today for |
|---|---|---|---|
| **1. Visual only** | `.glb` | *none* | Every passive accessory on both vehicles |
| **2. Visual + primitives** | `.glb` | SDF box, cylinder, sphere | Manipulator parts only (gripper jaws, claw body, sampler cup) |
| **3. Visual + collision mesh** | `.glb` | mesh file | Nothing, currently |

A part's collision is **contact geometry only**. Displacement is not a part concern — see [Buoyancy](#buoyancy-the-assembly-owns-displacement).

**Case 1 — visual only.** These are currently "accessories". They contribute mass but no volume, so no buoyancy and no collisions. Whether neglecting collisions is acceptable depends on the object and the scenario. Collision geometry costs physics time, though primitives are computationally cheap.

Every part carries a `model.sdf` regardless. Collisions are declared there explicitly, even when the answer is none — an empty or commented collision section states the intent, where a silent absence does not. The modeller should always include a non-empty `model.sdf`; it ships as the default and users modify as needed.

**Case 2 — visual mesh, primitive collision. This is the default.**

The modeller ships every part as a visual `.glb` plus a `model.sdf` whose collision primitives are a coarse approximation of that mesh. Not a decision to be made per part — it is simply what a part is, so approximate collision geometry always exists and nobody has to go back and ask for it.

Developers refine those primitives in `model.sdf` when a part needs something better, and drop to Case 1 by removing them when a part needs no contact at all. Both are edits to something that already exists rather than work commissioned from the modeller.

**Case 3 — visual mesh, collision mesh.** Currently unused, but a path we should have. Two constraints: graded buoyancy rejects mesh collisions outright, so a mesh-collision part cannot displace water on the BlueBoat; and mesh collision is materially more expensive per contact than a primitive.

### Validation on import

Every incoming part is checked before it lands:

| Check | Why |
|---|---|
| Geometry is box / cylinder / sphere / mesh only | cone and plane are fatal to `sdformat_urdf`, including in **visuals** |
| Collision primitives present, approximating the mesh | Case 2 is the default; developers refine rather than commission |
| No nested `<model>`, no `<pose>` on the model | fatal to `sdformat_urdf` |
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

The displacement geometry itself is unchanged in character — it is still shaped by what the plugin needs rather than by what the vehicle looks like, and still generated from the all-up-round configuration rather than summed from components:

* **BlueBoat pontoons** — six boxes per side rather than one long box, so under graded buoyancy each short segment responds to its own local depth and pitch restores properly. A single box keys off its centre depth and barely restores at all.
* **BlueROV2 hull** — a single box whose height is solved analytically so that `density × volume = mass × (1 + margin)`, giving the documented near-neutral buoyancy.

One consequence to design around: displacement must live **entirely** on the enabled link. A genuinely buoyant part — a float, a syntactic block — cannot express that through its own collision, so its volume has to be represented on the buoyancy link instead.

Verified in the container; see [What the Buoyancy plugin accepts](#what-the-buoyancy-plugin-accepts).

## Feasibility: already checked

The proposal composes parts into assemblies with `<include>`. A plain `<include>` produces a **nested** `<model>`, which `sdformat_urdf` refuses outright — no URDF, no TF, no RViz. `merge="true"` is supposed to lift the included links and joints into the parent instead, leaving one flat model. Everything depends on that holding through two levels: parts into the description assembly, then that into the gazebo model.

Gazebo itself is happy with nested models, and the ROS path has never been exercised, so "merge-include works today" told us nothing. It has now been tested directly.

**Method.** Two throwaway parts (a box and a sphere, each `model.sdf` + `model.config`), one assembly merge-including both and joining them with a `fixed` joint, and a second assembly merge-including that. Resolved with `gz sdf -p`, then fed to `robot_state_publisher`.

**Results — all pass:**

| Check | Result |
|---|---|
| Level 1 flattens | ✅ one `<model>`, links `box_link` + `sphere_link` |
| Level 2 flattens | ✅ still one `<model>`, same links and joint |
| `sdformat_urdf` converts | ✅ `robot_state_publisher: Robot initialized` |
| TF published | ✅ `/tf_static`: `box_link` → `sphere_link` |

Three things worth recording:

* **Link names are not prefixed.** `box_link` stays `box_link` after merging. Joint references, `/joint_states` names and the bridge config are therefore unaffected by composition — this was an open worry and it is resolved.
* **Merge emits helper frames** named `_merged__<part>__model__` to carry each include's pose. These are `<frame>` elements, not models, so they do not trip the no-nested-model rule.
* **The only message is the familiar harmless one** — `kdl_parser` complaining that the root link has an inertia, already documented in the package READMEs.

Gotcha for anyone repeating this: `gz sdf -p` reads **`SDF_PATH`**, not `GZ_SIM_RESOURCE_PATH`. With only the latter set, `model://` URIs fail to resolve and the errors look like malformed SDF rather than a missing path.


---

# Part 2 — Background and justification

## The problem

ROS wants URDF. Gazebo wants SDF. Nobody wants to maintain both, and the repo currently maintains a hand-authored bridge between them.

### The circularity in today's workflow

The part's `model.sdf` is discarded. Collisions are re-authored by hand as xacro primitives in the URDF, the URDF is assembled, and then `<include merge="true">` converts it back to SDF for Gazebo:

```
modeller SDF  ──✗ discarded
                    hand re-author ──▶ URDF ──▶ (libsdformat) ──▶ SDF
```

Collision data that starts as SDF and ends as SDF makes a round trip through URDF and a human. The hand step is the only place errors can enter — and PR #5 is what it produces.

The proposal is linear instead:

```
modeller SDF ──▶ SDF assembly (merge-include) ──▶ Gazebo
                        └──▶ (collisions filtered) ──▶ /robot_description ──▶ ROS
```

SDF is authored once and consumed by Gazebo unchanged. URDF becomes a derived, lossy projection for ROS — which is all ROS needs.


## Why SDF-first

The argument is about our asset pipeline, not about format aesthetics.

**Our geometry arrives as SDF.** The modeller exports `model.sdf` + `model.config` + `.glb` from Blender. Every URDF-first arrangement throws that `model.sdf` away and has a person retype the geometry in a second format. That hand step is the only place errors can enter, and PR #5 is a catalogue of what it produces: cylinders of radius 0.41 m on a 1.2 m hull, collision names with spaces in them, geometry yawed 180°, and SDF syntax pasted into a URDF file where it cannot parse.

Nothing else in the design produces defects of that kind, because nothing else requires a human to transcribe machine-generated data.

That is the whole case. It is worth being precise about what it is *not*:

* It is not that SDF is a better format. For our geometry — primitives, meshes, fixed and continuous joints — URDF expresses everything we need.
* It is not that the redundancy is expensive today. The current `merge=true` arrangement already declares geometry once; the duplication is in the *authoring*, not in the files.

Gazebo's [ROS 2 interoperability documentation](https://gazebosim.org/docs/latest/ros2_interop/) does recommend maintaining one format and making it SDF, published to `/robot_description` and parsed through `sdformat_urdf`. That is useful confirmation the path is supported, but it is not the reason to take it — see the honest accounting below.

### The options considered

| | Source of truth | Redundancy | Main cost |
|---|---|---|---|
| 1. **URDF-first, SDF wraps it** (today) | URDF | Low — geometry declared once; the SDF `merge=true` includes it | The modeller's SDF is thrown away and retyped by hand |
| 2. **URDF-only with `<gazebo>` tags** | URDF | None | Couples `*_description` to the simulator; still retypes the modeller's SDF |
| 3. **SDF-first, URDF derived** ← proposed | SDF | None | `sdformat_urdf` constraints, and an ecosystem almost nobody else is in |
| 4. **A third source generating both** | A spec (yaml) | None in source | You own a generator and two outputs |
| 5. **Maintain both, CI-compare** | Both | High | Fallback only |

### Option 2 deserves better than a one-line dismissal

Option 2 is not the ROS 1 relic this document previously implied. It is what [Clearpath](https://github.com/clearpathrobotics/clearpath_common) ship today across a range of configurable robots — 130 xacro files, zero SDF, with simulation content isolated in a `gazebo.urdf.xacro` gated behind `<xacro:if value="$(arg is_sim)">`.

That gating answers our stated objection. The coupling to the simulator is real but conditional and contained in one file, rather than smeared through the description. `<gazebo reference="…">` [failing silently against a non-existent link](https://github.com/gazebosim/sdformat/issues/1372) is a genuine footgun, but a known one.

Option 2 loses on one point only, and it is the point above: it still requires the modeller's SDF to be discarded and retyped. Everything else about it is cheaper and better-supported than what we propose.

### The honest accounting

Benchmarked against robots that ship to both ROS and Gazebo:

| Repo | xacro | SDF |
|---|---|---|
| `clearpath_common` | 130 | 0 |
| `turtlebot4` | 8 | 0 |
| `Universal_Robots_ROS2_Description` | 8 | 0 |
| `CentraleNantesROV/bluerov2` | 17 | 1 |

Nobody is SDF-first. `sdformat_urdf` itself has a few dozen stars and its principal dependents are its own release repositories.

So the risk here is not technical — merge-include and the collision filter are both tested and work. **The risk is ecosystem.** We would be among the first to run a real vehicle through `sdformat_urdf`, which means we find its bugs, with a thin maintainer base and no accumulated community answers. The 32 fatal conversion paths listed below stop being trivia and become a support burden we own.

Two things are worth borrowing regardless of which option wins. Clearpath's package decomposition — a shared parts library split by kind, plus a yaml-driven generator — is prior art for the structure proposed here, and validates that half of the design without argument. And their `is_sim` gating is a cleaner containment pattern than we credited.

### What SDF-first buys that the others cannot

Two design questions stop existing under option 3 rather than getting solved:

* **What is a part?** Under URDF-first a per-part `model.sdf` is a parallel declaration nothing consumes. Under SDF-first the assembly merge-includes the parts, so the part model *is* the consumed artifact — the thing the modeller exports is the thing the simulator loads.
* **Where does PBR live?** In the mesh, which SDF carries through intact and URDF cannot represent at all.

The recommendation is option 3, on the strength of the asset-pipeline argument alone. If the team weighs ecosystem risk higher than the cost of hand-transcription, option 2 with an import validator is the defensible alternative, and this document should not pretend otherwise.


## What `sdformat_urdf` costs

The constraint list, from the [package documentation](https://github.com/ros/sdformat_urdf/tree/rolling/sdformat_urdf). Violating any of these **fails the conversion outright**:

* A single `<model>`, not in a `<world>`, with **no nested `<model>`**
* No `<pose>` on the model
* Geometry limited to box, cylinder, sphere, mesh
* Joints limited to continuous, fixed, prismatic, revolute
* Links and joints must form a tree from the canonical link

And these degrade with a warning: `<pbr>` materials are ignored (only solid colours survive, as `0.4 × ambient + 0.8 × diffuse`), and `<link>` sensors are dropped.

### Why collisions are stripped rather than converted

`convert_geometry` in [`sdformat_urdf.cpp`](https://github.com/ros/sdformat_urdf/blob/rolling/sdformat_urdf/src/sdformat_urdf.cpp) handles four shapes. Plane errors explicitly; anything else falls through to `"Unknown geometry shape"`. Both return `nullptr`, and the caller does not tolerate it:

```cpp
urdf_collision->geometry = convert_geometry(*sdf_collision->Geom(), errors);
if (!urdf_collision->geometry) {
  errors.emplace_back(..., "Failed to convert geometry on collision [...]");
  return nullptr;          // whole link conversion abandoned
}
```

So an unsupported collision shape does not degrade — it aborts. No URDF, no `/robot_description`, no TF, no RViz. Since the export tool offers cone and plane, that is reachable in practice.

**Verified, not inferred.** A part carrying a `<cone>` was built, resolved with `gz sdf -p` (Jetty's SDF keeps the cone happily), and fed to `robot_state_publisher`:

| Part | Result |
|---|---|
| cone **collision**, box visual | `Unknown geometry shape` → `Failed to convert geometry on collision [c]` — no robot |
| cone **visual**, box collision | `Unknown geometry shape` → `Failed to convert geometry on visual [v]` — no robot |
| cone collision **stripped** | `Robot initialized` |

That confirms all three claims: the failure is fatal rather than degrading, visuals are equally fatal, and stripping collisions rescues the collision case. It also confirms the limit of the fix — a cone in a *visual* is still fatal, which is why export-side validation remains mandatory.

Nothing on the ROS side consumes collisions: `robot_state_publisher` needs links and joints, RViz shows visuals, NAV2 uses a footprint, and `<collision>` is optional in URDF. Meanwhile Gazebo reads the unfiltered SDF directly. Stripping loses nothing real and makes that failure class impossible.

It does not make the projection bulletproof — the same converter runs on **visuals**, and nested models, model poses and unsupported joint types are also fatal. Export-side validation is still required.


## What the Buoyancy plugin accepts

From [`Buoyancy.cc`](https://github.com/gazebosim/gz-sim/blob/main/src/systems/buoyancy/Buoyancy.cc):

| Mode | Accepts | Used by |
|---|---|---|
| **Graded** (`<graded_buoyancy>`) | `<box>` and `<sphere>` **only** | BlueBoat |
| **Uniform** (`<uniform_fluid_density>`) | box, sphere, cylinder, mesh (plane ignored) | BlueROV2 |

Graded mode dispatches on shape, and everything that is not a box or sphere falls to a `default:` branch logging *"Only \<box\> and \<sphere\> collisions are supported by the graded buoyancy option"* — behind a `static bool warned`, so it prints once per process and is very easy to miss. The part silently displaces nothing.

This is why the BlueBoat pontoons are boxes. It also means a cylinder is a perfectly reasonable collision choice for a submerged part on the ROV and a silent bug on the boat.

The plugin reads collision components out of the ECM, so it does not care whether they were authored in SDF or arrived via URDF conversion — Gazebo always loads SDF in the end.


## Where parts come from

The modeller's workflow is [SDF_Gen](https://github.com/sanjanasrinivasan/gz-sim/blob/f1a16c0e26a6d9f0785b5c5013a175dec4615433/tutorials/setting_up_CAD_models.md), a Blender addon driven from CAD (SolidWorks / Fusion / Inventor via the STEPper addon). Its export is:

```
<part>/
  model.sdf        # links, visual, collision primitives
  model.config
  <part>.glb       # visual mesh
```

That is already a standalone Gazebo model — the exact "part" artifact this proposal is built on. The tool emits it natively; we do not have to invent it, and the modeller does not have to learn a second format.

The tutorial also favours primitive colliders over mesh colliders, authored by selecting the visual and fitting a primitive with scale-cage and face-snap tools. That matches Case 2 — subject to the graded-buoyancy restriction to box and sphere.


## Evidence from PR #5

The commented-out block in PR #5 *is* SDF_Gen output, and it is what the current hand-translation step produces. As exported it contained:

* cylinders with radius 0.41 m on a hull 1.2 m long
* collision names containing spaces (`blue usv_collider_box`)
* Blender `.00N` suffixes
* SDF syntax (`<pose>`, `<box><size>`) pasted into a URDF file, where it cannot parse
* geometry yawed 180° from the URDF convention, with a z-offset on top

None of these are detectable until the whole vehicle assembles and runs, because there is no smaller unit to test. Under this proposal each is a part-level check: load `model.sdf` on its own and look at it.


## A coupling that already bites

`bluerov2_description/urdf/accessories.xacro:23` carries a hand-maintained `accessory_volume` table listing `0.0` for every passive accessory and a hand-computed volume for the two manipulators, with the comment *"keep these in sync with the collision boxes below."*

That is Case 1 and Case 2 parts sharing one table, kept aligned by hand. Any redesign should either derive those volumes from the collision geometry or remove the need for the table.
