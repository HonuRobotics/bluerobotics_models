# Community exemplars: who else ships glTF to Gazebo and RViz

Survey run 2026-09-12. The question was whether anyone outside this project is authoring and provisioning robot models as glTF for Gazebo and RViz, and if so whose practice is worth copying. It is the outward-looking companion to [GLB_INVENTORY.md](GLB_INVENTORY.md), which measures our own files, and to the Fuel survey, which established that glTF is almost absent from Fuel. Fuel turned out to be the wrong place to look: the people doing this work keep their assets in their own repositories.

## Method

GitHub code search over the text formats that reference a mesh — `extension:urdf`, `extension:xacro`, `extension:sdf` containing `.glb` or `.gltf` — which finds the reference even though the binary itself is not indexed. That is 2,672 URDF, 497 SDF, 288 xacro and 259 SDF-with-`.gltf` hits, sampled to 207 distinct repositories and ranked by stars and last push. Then org-scoped searches (`org:gazebosim`, `org:open-rmf`, `org:RobotecAI`, `org:Ekumen-OS`, `org:foxglove`), the REP and Discourse threads where the format question is being argued, and direct inspection of the candidate files. Five exemplar GLBs were downloaded and their JSON chunk parsed for generator, extensions, image MIME types and triangle counts; those numbers are quoted below and are reproducible with `~/maritime_ws/spike/glb_community_probe.py`, which downloads each file and parses its JSON chunk.

One caveat on the population. Most of those 2,672 URDF files are manipulation and VLA research — dexterous hands, teleoperation rigs, scene-generation papers — targeting MuJoCo, Isaac or SAPIEN, where glTF has been ordinary for years. They are not evidence about Gazebo or RViz. The Gazebo-and-RViz cohort is small enough to name person by person, which is what follows.

## The cohort

### gazebosim/jetty_demo — the closest thing to an upstream reference

The demo world for the Gazebo Jetty release, by `iche033` (Ian Chen), `aaronchongth` (Aaron Chong), `arjo129` (Arjo Chakravarty) and `scpeters` (Steve Peters). Seventeen warehouse models, every one of them a single self-contained `base_visual.glb` beside a `model.sdf`, and sixteen older COLLADA models — `ur10`, `vehicle_with_wheel_slip`, `cordless_drill` — left as they were. The new assets are glTF; nothing was migrated.

The `model.sdf` pattern is worth quoting in full because it is so spare:

```xml
<visual name="base_visual">
  <geometry><mesh><uri>base_visual.glb</uri></mesh></geometry>
</visual>
<collision name="forklift_b132_collider_cylinder">
  <pose>-0.455378 0.684627 0.285136 0.0 1.570796 0.0</pose>
  <geometry><cylinder><radius>0.284716</radius><length>0.224494</length></cylinder></geometry>
</collision>
```

One visual, no `<material>` and no `<pbr>`, and roughly thirty hand-placed primitive colliders per model named `<part>_collider_<shape>`. That naming convention also appears in `iche033/simple_warehouse`, in `ros-physical-ai/demos`, and in this repository, which suggests a shared Blender-side workflow that nobody has published; the Blender exporter Gazebo does ship, `gz-sim/examples/scripts/blender/sdf_exporter.py`, still writes `model.dae` and knows nothing about GLB.

What the files themselves contain is more surprising than the SDF:

| File | Size | Nodes | Tris | Images | Extensions |
|---|---|---|---|---|---|
| `Forklift/base_visual.glb` | 4.0 MB | 1 | 15,492 | 3 JPEG (base, MR, normal) | `KHR_materials_specular`, `KHR_materials_ior` |
| `Distribution_Warehouse/base_visual.glb` | 85.5 MB | 3,010 | 331,438 | 27 JPEG | `KHR_texture_transform` |
| `iche033/simple_warehouse` `thor_table.glb` | 49.7 MB | 91 | 187,508 | PNG base and MR, mixed normals | none |

All from `Khronos glTF Blender I/O` v4.4 to v4.5. Three things follow. The texture-format rule we derived, and REP-158 with it, is not what the Gazebo team practices: normal and metallic-roughness maps here are JPEG. Extensions are used casually, including `KHR_texture_transform`, which our own audit found Gazebo's loader ignores, so textures should misplace — either the transform is identity in that file or the audit's finding needs revisiting against Jetty. And there is no size discipline at all: 85 MB in one visual, 3,010 nodes, against the budget question in section 10 of the pipeline review.

### open-rmf/rmf_site — glTF generated rather than authored

The RMF site editor writes its own glTF. `crates/rmf_site_editor/src/site/sdf_exporter.rs` calls a purpose-built `bevy_gltf_export` crate and emits `level_N_visual.glb` and `level_N_collision.glb` per building level, `model_N_visual.glb` / `model_N_collision.glb` per model and `lift_N.glb` per lift, then writes an SDF that points at them. Visual and collision are separate GLB files by construction, and there is a `scripts/blender/obj_to_glb.py` for the legacy floor meshes. This is the only example found of a tool that treats GLB as a compile target for Gazebo rather than as a delivery format from a modeler.

### husarion/rosbot_ros — a commercial product doing it per-link

ROSbot XL and ROSbot 3 descriptions, one GLB per link under `meshes/rosbot/`, referenced from URDF so the same file serves RViz and Gazebo:

```xml
<origin xyz="0.0 0.0 -0.0173" rpy="${pi/2} 0.0 ${pi/2}" />
<mesh filename="package://rosbot_description/meshes/rosbot/body.glb" scale="0.001 0.001 0.001" />
```

They keep millimeter units in the file and correct with `scale`, and they carry the axis correction in the visual origin rather than baking it, which is the same trade-off `parts.xacro` makes with `gltf_up`. Their `body.glb` was written by `trimesh`, not Blender, and carries no textures at all — two materials, flat colors, 16,221 triangles. A CAD-to-GLB conversion, not an art pipeline. `ros-physical-ai/demos` does the same for the SO-ARM101: untextured GLB visuals, primitive colliders.

### RobotLocomotion — the informed dissent on packaging

Toyota Research Institute is the largest user of glTF in URDF and SDFormat found anywhere, and it does the opposite of what we do on two counts. `RobotLocomotion/models` holds 148 `.gltf` files with 148 matching `.bin` sidecars, plus 48 KTX2 textures — external assets everywhere, no GLB. That is not an accident of tooling: Drake's [file formats page](https://drake.mit.edu/doxygen_cxx/group__geometry__file__formats.html) says `.glb` "container" files are not supported at all, and that "`.gltf` files with external assets (i.e., separate `.bin` and `.png` files) will load faster than `.gltf` files with assets embedded." Their stated reason for glTF over OBJ is ours: "glTF is designed, from the start, to support Physically Based Rendering." NASA JPL's `nasa-jpl/m2020-urdf-models`, the Perseverance and Ingenuity models used for operations visualization in RViz, is packaged the same way — 36 `.gltf` with 36 `.bin`.

So the self-contained-GLB decision has a real dissenting camp with a loading-cost argument behind it, and the dissent is not compatible with us either way: KTX2 fails loudly in Gazebo and GLB fails in Drake.

### usnistgov/ARIAC — a migration caught in the middle

The NIST competition environment currently holds 37 `.glb`, 13 `.dae`, 9 `.gltf` with sidecars and 29 `.stl`, mixed across `ariac_description` and `ariac_gz`. Useful as evidence that a large, maintained, Gazebo-first project is converting rather than having converted, and that nobody enforces one packaging choice across a repository.

### vanttec/vanttec_usv — the nearest maritime peer, inverted

The only maritime project in the sample. Visuals are COLLADA with `<pbr>` maps declared in the SDF the classic way, and the single GLB in the repository is `hull_collision.glb` — glTF used for collision and COLLADA for visual, exactly backwards from everyone above. No conclusions drawn from one repository, but it is the state of the art in our own domain.

## The people, and the two organizations that turned out not to be doing this

The user hypothesis was Intrinsic, Ekumen and Robotec.ai. Verified handles and affiliations from GitHub profiles and merged work:

| Who | Handle | Where | The glTF-relevant work |
|---|---|---|---|
| Ian Chen | `iche033` | Gazebo rendering | `jetty_demo` and `simple_warehouse` assets; gz-rendering |
| Steve Peters | `scpeters` | Gazebo | `jetty_demo` |
| Arjo Chakravarty | `arjo129` | Intrinsic | `jetty_demo`, Open-RMF |
| Aaron Chong | `aaronchongth` | Intrinsic | `jetty_demo` RMF integration |
| Morgan Quigley | `codebot` | Intrinsic | ros2/rviz #1001, the PR that made RViz load GLB at all (2023) |
| Alejandro Hernández Cordero | `ahcorde` | OSRF / Gazebo | backported GLB loading to Humble and Iron; reviews the loader work |
| Luca Della Vedova | `luca-della-vedova` | Intrinsic | rmf_site glTF export |
| Michel Hidalgo | `hidmic` | Ekumen Labs | ros2/rviz #1482, the glTF Y-up fix |
| Calder Phillips-Grafflin | `calderpg-tri` | TRI | ros2/rviz #1229, the report behind it |
| Adam Dąbrowski | `adamdbrw` | Robotec.ai | author of REP-158 |
| Mateusz Żak | `zakmat` | Robotec.ai | REP-158 peer review and compliance checker |
| Jimmy McElwain | `jimmy-mcelwain` | Yaskawa Motoman | pushing the format question from the OEM side, in both the REP thread and Discourse |

Ekumen's own robot, `Ekumen-OS/andino`, is STL and JPEG with no glTF anywhere; their glTF contribution is Michel Hidalgo's work inside the RViz loader. Robotec.ai's robot assets — `ROSCon2023Demo`, the UR and OTTO gems — are FBX, STL and COLLADA, because O3DE's asset processor consumes them; `.glb` appears in their repositories only as a line in `sceneassetimporter.setreg`. Their glTF contribution is REP-158, which is an OpenUSD authoring convention whose declared export target is glTF 2.0. Neither organization is a source of Gazebo-facing glTF assets to copy, and saying so is worth as much as the positive findings.

## What this changes for us

1. The RViz Y-up rotation is younger and narrower than we treated it. `ros2/rviz` #1482 merged to `rolling` on 2025-06-16 and `ahcorde` declined to backport it — "this change might break many users" — so Jazzy and Kilted do not have it. Our files render correctly in RViz here because our distro is downstream of that merge. Anyone consuming these models on Jazzy sees every part rotated ninety degrees. That belongs in the model spec as a stated distro floor, not as an assumption.

2. The `<pbr>`-in-SDF rule in the workspace `CLAUDE.md` disagrees with every glTF exemplar found. Jetty's own models declare no material in the SDF and rely on what is inside the GLB, as do 53 of the 54 glTF models in Fuel. The rule may be correct for COLLADA and wrong for GLB, or correct for our gz-common version and stale; either way it now has enough counter-evidence to be worth re-deriving rather than repeating.

3. Our texture-format rule is on the standards side of a split. REP-158 backs it and the shipped assets do not — jetty's Forklift carries a JPEG normal map and a JPEG metallic-roughness map, as does most of Fuel. The spec should keep the rule and say plainly that assets arriving from anyone working normally will violate it.

4. Self-contained GLB is defensible but no longer uncontested. Drake refuses GLB outright and argues external `.bin` loads faster; JPL packages the same way for RViz. If a model of ours is ever meant to be consumed outside Gazebo and RViz, packaging is the first thing that breaks, and the spec should say what the fallback is.

5. There is an upstream gap we are sitting in the middle of. The Gazebo team's assets are GLB, its published Blender exporter writes COLLADA, and the `<part>_collider_<shape>` convention that three separate projects use is undocumented. Whatever we build to emit colliders and visuals from Blender is a plausible upstream contribution rather than a private tool.

## Where the argument is being had

- REP-158, "OpenUSD Conventions for Simulation Asset Interoperability in Open Source Robotics", in `openrobotics/reps` — drafted PR #29 (merged 2026-06-17), peer review addressed in PR #30 (2026-07-13). The [Discourse thread](https://discourse.openrobotics.org/t/draft-rep-158-openusd-conventions-for-simulation-asset-interoperability-in-open-source-robotics/55526) carries the substantive debate, including a mesh-granularity exchange directly on our per-link question: combining meshes to the smallest possible set is preferable for performance, acknowledged as context-dependent rather than prescribed.
- ["ROS2 URDF Mesh File Types"](https://discourse.openrobotics.org/t/ros2-urdf-mesh-file-types/54954), May 2026, opened because Blender 5.0 dropped COLLADA export. Converging on glTF 2.0 for visual and STL for collision, blocked on Isaac Sim's URDF importer still accepting only dae, obj and stl. No governance action, no migration plan.
- The gz-common assimp loader PRs, which the pipeline review already tracks.
