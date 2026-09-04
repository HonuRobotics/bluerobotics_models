# Visual asset pipeline: technical review and proposed guidelines

Working document as a part of the new modeling workflow. The intent is to review the background (what is our sources of truth for model file formats and review?) and work throught the suggestions (see `docs/reference/asset-spec.md`) on what to assess for each glTF/GLB file.  

The document has two halves. Sections 0 to 6 are the audit proper: the ground rules, what GLB is and what our consumers do with it, the tools that decide each question, then the draft spec item by item, the delivered files measured, and the two artifact reports that came with the draft. Those sections stay about the draft spec and can be read on their own. Sections 7 to 9 go the other way, proposing guidelines the audit says are missing rather than judging ones that exist: pinning the authoring tools as part of the project's version stack, reconciling the draft against the guidelines this repo already has, and the topics neither document covers. Section 10 collects everything that needs a decision from the team.

## Context / Starting Point

- `docs/reference/asset-spec.md`, the draft from Carlos (untracked in the branch at the time of writing).  Added to gi. 
- Two Claude artifacts Carlos linked, the "Parts Library Audit" (the 12 non-chassis parts) and the "BlueBoat Chassis Audit", both dated 2026-09-03 and both measured by a direct GLB parse against the draft spec. They could not be fetched from this session (public, non-member pages), so their text was pasted in and is reproduced verbatim alongside this document as [ASSET_AUDIT_PARTS_LIBRARY.md](ASSET_AUDIT_PARTS_LIBRARY.md) and [ASSET_AUDIT_BLUEBOAT_CHASSIS.md](ASSET_AUDIT_BLUEBOAT_CHASSIS.md); section 6 audits them. A third, the "BlueROV2 Chassis Audit", is referenced by both as a companion and has not been seen.
- What this repo already decided: `docs/design/parts.md` (mesh conventions), `docs/how-to/add-part.md` (the acceptance steps), the earlier README section "Accepting a new part" (commit `b5daead`, August 2026), and the sandbox findings carried over from the vrx4 branch.
- The delivered files themselves: 15 `.visual.glb` under `bluerobotics_parts/models/`, all exported by `Khronos glTF Blender I/O v5.1.20` which specifies the Blender add-on (`io_scene_gltf2`), co-maintained by Blender Foundation and Khronos Group.
- The Gazebo project's own written record on glTF: docs, changelogs, trackers and PMC minutes, surveyed 2026-09-04 and reported in section 1.8.

## Main Issues

We (Honu) are new to the details of glTF and how they are rendered in verious tools.   The points below are meant as the highest-level topics that are affecting this workflow.

* The [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) covers a larger scope of 3D asset use cases that required by this project.    The spec for glTF assets includes a large variety arrays (e.g., scene, node, camera, animation, skin, etc. ) that are not pertinent to this use case.   (The glTF spec is almost complex enough to be used as an SDF or URDF replacement.  For this project we must be intentional about what subset of functionality is being used so thta we (and our agents) don't naively apply the entire specification.     We started by using glTF as a drop-in replacement for Collada mesh + 1 PNG texture.  Doing so naively was a mistake as the glTF, in its full scope, is not really compartable to Collada .dae mesh plus a single texture.   
* Multiple sources of "truth".  Ryan is mainly looking at Blender, I'm mainly looking at Gazebo (and accidently tried an older version of Gazebo) and Carlos is using Gazebo and other viewers such as F3D, as well as Claude introspection of the file contents against `asset-spec.md`.   We all are "seeing" different rendering behavior and we currently lack an agreed up common source of "truth"

## 0. Background

### 0.1 Sources of truth



Three different things get called "correct" in this work, and they disagree with each other. Every finding in this document is measured against one of them and says which.

| | Truth | Defined by | Tool that decides |
|---|---|---|---|
| T1 | The format | The [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) (registry revision 2.0.1) and the Khronos extension registry. | The Khronos glTF Validator, the conformance tool Khronos maintains (version 2.0.0-dev.3.10, linux64 release binary). Zero errors means the file is glTF. Evidence tag V. |
| T2 | The intended appearance | What a conformant renderer shows for the file. Khronos maintains the glTF Sample Viewer as the reference renderer for exactly this question. | The glTF Sample Viewer, in a browser. Not Blender, see below. Evidence tag R. |
| T3 | The targets | What our two consumers render: Gazebo (gz-sim 10, gz-rendering 10, Ogre-Next 2.3) and RViz (rviz_rendering 15.2). Each implements a subset of T1: Gazebo's subset is tabulated in section 1.4, RViz's in section 1.5. | `glb_probe` for what the loader built (no GPU); the Gazebo parts world and RViz for what it looks like. Evidence tags S and P. |

The rules that follow from this:

- T1 is authoritative over the file. A rule in our spec that contradicts T1 is wrong. Where T3 deviates from T1, this document says so, and the resulting rule is written as a target constraint ("Gazebo ignores BLEND, so do not use it"), never as a glTF rule ("BLEND is unsupported").
- T2 is authoritative over intent. The modeler works in Blender's shader graph and viewport, which render Blender's material, not the file. The exporter is a translation, and things are lost or defaulted in it (metallic factor, image format, alpha mode, tangents). Blender is therefore not a viewer of the delivery at all. The modeler-side check of the file is to open the exported GLB in the Sample Viewer, or to re-import it into an empty Blender scene. Third-party viewers (the Babylon sandbox, three.js viewers, f3d) each implement a different subset of T1 with their own defaults; they are triage aids, useful when they agree with the Sample Viewer and not evidence when they disagree with it.
- T3 is authoritative over acceptance. A part is accepted when it renders as intended in Gazebo and loads in RViz, because that is what ships. A T3 gap is our constraint to document, not a defect in the file.
- Gazebo is not a reference for anything. It has not implemented the whole of T1 (section 1.4 lists the fields and extensions it drops or alters), and nothing in the Gazebo project claims it has. "It looks right in Gazebo" is necessary and not sufficient: a file can look right in Gazebo because a defect happens to be dropped (the BlueBoat's BLEND flag), and a conformant file can look wrong in Gazebo (any BLEND glass).

Every defect falls into one of four classes, named by the truth it fails:

| Class | Fails | Who fixes it | In the current deliveries |
|---|---|---|---|
| Invalid | T1: the validator reports an error | The modeler, at export | None. All 15 files validate with zero errors (section 2.6). |
| Unintended | T2: valid, but not what the modeler meant | The modeler, at source | Metalness 1.0 on plastic hulls; 22 percent of the BlueROV2 chassis without a material; BLEND on an opaque hull |
| Unsupported | T3: valid and right in the reference viewer, but Gazebo or RViz drops or alters it | Us, as a documented target constraint in the spec | BLEND ignored; `doubleSided` ignored outside MASK; texture transform ignored; tangents regenerated with Ogre's algorithm rather than MikkTSpace; RViz needs a base color texture on any textured material |
| Pipeline | T1, T2 and T3 all pass, but our own tooling or conventions cannot take it | Us, as a documented convention | Forward is +X where the spec says the front faces +Z; rotation nodes refused by `gltf_to_yup.py`; node names becoming Gazebo submesh names |

The spec sentences this document leans on, quoted from the Khronos source (`specification/2.0/Specification.adoc` on the `main` branch of KhronosGroup/glTF):

- Coordinates and units: "glTF uses a right-handed coordinate system. glTF defines +Y as up; the front side of a glTF asset faces +Z, the left side of a glTF asset faces +X." and "The units for all linear distances are meters."
- Tangents: "When tangents are not specified, client implementations SHOULD calculate tangents using default MikkTSpace algorithms with the specified vertex positions, normals, and texture coordinates associated with the normal texture."
- Missing material: "If `material` is undefined, then a default material MUST be used." and "The default material, used when a mesh does not specify a material, is defined to be a material with no properties specified. All the default values of `material` apply." (those defaults are white base color, metallic 1.0, roughness 1.0).
- BLEND: "Support for this mode varies. There is no perfect and fast solution that works for all cases."
- `doubleSided` true: "back-face culling is disabled and double sided lighting is enabled."
- Extensions: "All glTF extensions required to load and/or render an asset MUST be listed in the top-level `extensionsRequired` array".

### 0.2 How the audit works

Every requirement gets three separate answers, because they fail independently:

| Question | Meaning |
|---|---|
| Technically correct? | Does the toolchain we ship actually behave the way the requirement's rationale says? Judged against the versions installed in the drydock container and listed in section 1.2 below, never against glTF folklore or another engine. |
| Applicable? | Does it matter for this project's pipeline (Blender to GLB to xacro part macro to URDF and SDF, rendered by Gazebo and by RViz)? |
| In scope? | Does it belong in a spec handed to a modeler, or is it our tooling's job, or someone else's decision? |

Verdict vocabulary: Verified (rationale and rule both hold), Corrected (rule survives, rationale or wording does not), Refuted (rule should go), Open (needs a project decision, not a technical one).

Evidence tags, used everywhere below:

| Tag | Evidence |
|---|---|
| S | Read in the source of the installed version (the files listed in section 1.2). |
| P | Observed by running `glb_probe` (section 2.1) against our files inside the drydock container. |
| F | Measured in the delivered files (JSON chunk and decoded textures, section 2.2). |
| D | Stated by the glTF 2.0 specification or a vendor document. |
| V | Reported by the Khronos glTF Validator on the delivered file (section 2.6). |
| W | Stated in the Gazebo project's written record: docs, changelogs, release notes, tracked issues and pull requests, PMC minutes (section 1.8). |
| R | Seen in the Khronos glTF Sample Viewer. Not used yet in this document; it is the tag for T2 checks once someone runs them. |
| U | Not verified yet. Says what test would settle it. |

## 1. Background: glTF and what our consumers do with it

### 1.1 The format

glTF 2.0 is a full JSON scene description plus binary buffers plus images. GLB is its single-file (binary) packaging: a 12-byte header (`glTF`, version 2, total length), a JSON chunk, and one BIN chunk. 

* Images either sit in the BIN chunk, referenced by a `bufferView`, or are external files referenced by a `uri`. The format allows both and both consumers load either, so which one we require is a project constraint rather than a format question. Every current delivery embeds (vice reference external file). Section 10, decision 16 sets out the trade-off: embedding gives one artifact that cannot arrive incomplete, while external files let a texture be re-authored and reviewed without re-exporting the geometry.
* Neither of our consumers parses glTF. Both hand the file to the **Open Asset Import Library**, known as assimp, a third-party library that decodes many 3D formats into one format-neutral scene structure of its own. Gazebo and RViz each then translate that structure into their own renderer, and they do it differently. So nothing in either program reads glTF directly, and the format is two translations away from anything drawn on screen.
* Both link the same shared copy of that library, `libassimp.so.6`. One parser therefore feeds both consumers, which means a change in it moves Gazebo and RViz together, and neither one's release notes would mention it.
* Once assimp has parsed the file, `.gltf` and `.glb` are treated identically. The extension matters only for dispatch: Gazebo routes `gltf`, `glb` and `fbx` to its assimp-backed loader while keeping its own hand-written loaders for `stl`, `dae` and `obj`, and RViz applies its up-axis rotation for `gltf`, `glb` and `vrm`.


The parts of the JSON that matter here:

- `nodes`: a tree with optional `translation`, `rotation`, `scale` or `matrix`, each optionally pointing at a `mesh`. A `scene` lists root nodes; a file can hold several scenes and names one as default.
- `meshes[].primitives[]`: the drawable units. Each has `attributes` (`POSITION`, `NORMAL`, `TANGENT`, `TEXCOORD_0..n`, `COLOR_0`), `indices`, a `mode` (4 = triangles) and an optional `material`. A mesh with several primitives is one Blender object with several material slots.
- `materials[]`: `pbrMetallicRoughness` (`baseColorFactor` RGBA, `baseColorTexture`, `metallicFactor`, `roughnessFactor`, `metallicRoughnessTexture` with roughness in G and metalness in B), `normalTexture` (with `scale`), `occlusionTexture` (R channel, with `strength`), `emissiveTexture` and `emissiveFactor`, `alphaMode` (`OPAQUE`, `MASK` with `alphaCutoff`, `BLEND`) and `doubleSided`. Every texture reference carries a `texCoord` set index.
- `images`, `samplers`, `textures`: images plus wrap and filter settings.
- `extensionsUsed` and `extensionsRequired`: the second is a promise that a loader without that extension must refuse the file.

Conventions fixed by the glTF spec [D]: 
* units are meters; 
* the coordinate system is right-handed, and has two parts
    * with +Y up. The up axis convention is structural: every importer, including PUT ANME OF ONE WE USE, relies on this convention, e.g, RViz rotates a glTF mesh as it loads.  Consequently, a file exported Z-up is a defect (section 1.6).
    * the front side of an asset faces +Z, and the left side faces +X. The facing axes are a convention rather than a requirement, and it is the one place this project departs from the specification's own words. See the note below.
* UV (texture coordinates) place their origin at the top-left of the image. Important to state because other formats put it at the bottom-left, which is why the loader flips them on import (section 1.3).
* base color and emissive textures are sRGB, every other map is linear. The distinction is whether an image holds a color a person chose or a number a shader uses for compute. Color images are stored with a gamma curve, sRGB, which spends more of the available range on darker tones where the eye is more sensitive; a renderer undoes that curve before any lighting math and reapplies it on output. Roughness, metalness, occlusion and normal maps hold measurements rather than colors, so applying a color curve to them corrupts the values. This is not a subtlety: Gazebo once treated every PBR texture as sRGB and its meshes rendered visibly too dark (section 1.8).
* normal maps are tangent space with the OpenGL convention (green points up); 
* a primitive without a material renders with the default material, which is white, metallic 1.0, roughness 1.0. 

**On the "+Z forward" convention, and what the spec does and does not fix.** This deserves to be exact, because it is where we knowingly differ from the specification's text. The full sentence reads: "glTF defines +Y as up; the front side of a glTF asset faces +Z, the left side of a glTF asset faces +X." Three things follow from how it is written.

* It is stated about the asset, meaning the file as a whole, not about each mesh or node inside it. It describes which way a finished model faces. It does not constrain any individual mesh in the tree.
* It carries no normative keyword. The specification uses MUST and SHOULD deliberately and often, and this sentence has neither. (See section 2.2.1 of the spec which declares the usage convention.   Because the spec is so verbose on this point, we can infer that omitting the normative keywords in this case is not accidental.)
* No programmatic tool can check compliance, because no tool can know which way a model is supposed to face.  This is a human-facing semantic. 
* the Khronos validator does not flag our files (section 2.6).

It says nothing about where a mesh's geometry sits relative to its own origin, or how that origin is oriented. glTF positions meshes with node transforms and leaves the geometry reference entirely to the author. 

Importantly, the specification, as written, does not answer the question of where a part's origin should be located and how it is oriented. See open decision, Section 10, decision 2.

So our parts are not invalid, and nothing here is a violation a tool could detect. What the format leaves us is two open questions it declines to answer: which way a part faces in the file, and where its origin sits. Both are ours to decide, both are currently answered by habit rather than by a written rule, and section 10, decision 2 carries them. What follows is what we do now and what the alternatives cost.

**Orientation: what we do now.** Every delivered file has forward on +X and up on +Y. That is a consequence rather than a decision anyone recorded. The modeler builds the part in Blender facing +X with Z up, which is the ROS convention of REP 103 and the same frame the part macro uses, and Blender's exporter applies its fixed Y-up conversion on the way out, mapping x, y, z to x, z, minus y. The file's layout follows from authoring in the robot's convention. Nobody chose the file's axes directly.

The alternative is to author so the file comes out +Z forward, matching the sentence above. In Blender that means facing the part along minus Y, which is that program's own front-view convention, so the two ecosystems genuinely disagree and we sit on the robotics side of it.

| | Forward on +X, what we do | Forward on +Z, the glTF convention |
|---|---|---|
| Modeler's mental model | One frame throughout: the part is built in the same axes the robot uses | Two frames: build in the robot's, face it in the format's |
| Instruction needed | An explicit override of the spec sentence, which a modeler reading Khronos documentation will not expect | None, the format's own wording is the rule |
| Generic viewers | The part faces sideways in any viewer that assumes the convention | The part faces the viewer as intended |
| Cost to change | None, this is the current state | Re-export or re-bake all fifteen files, and add a yaw to the visual rotation in the part macro and the RViz path |

The risk of leaving it as it is: a modeler who follows the Khronos sentence literally delivers a part that looks correct in every viewer and points sideways in every assembly, and nothing in the file or the validator flags it.

**Origin: what we do now.** The written rule and the library disagree. `docs/design/parts.md` says the origin sits at the mesh centroid, the older README said the centroid and where the part would sensibly be mounted from, and the draft spec says it is the part author's choice. Measuring the delivered files against their own bounding boxes shows the library follows none of those three consistently, and instead follows a fourth rule nobody wrote down:

- The two lateral axes are centered, within a few millimeters, on all but two parts. The exceptions are the flag, whose origin is on its pole rather than in the middle of the cloth, and the payload bracket.
- The vertical axis carries a deliberate offset on almost every part, placing the origin at a mounting face rather than in the middle. The base station antenna is the clearest case, with its bounding-box center nearly three hundred millimeters above the origin, which puts the origin at the foot of the mast.
- Exactly one part, the T200 thruster, is centered on all three axes.

So the working convention is centered in plan, referenced to the mounting plane vertically. That is a defensible rule and arguably the right one, since it is what makes a part sit correctly when fitted to a slot. It is simply not the rule any of our documents state.

| | Centroid | Mounting reference, what the library does | Author's choice, declared per part |
|---|---|---|---|
| Fitting a part to a slot | Needs an offset in the macro for anything that does not straddle its mount | The mount sits where the slot is, and the attach vector is often zero | Varies per part |
| Replacing a delivered mesh | Reproducible without asking anyone | Reproducible only if the reference face is named | Requires reading the part's comment |
| Matching the current files | Would require moving fourteen of fifteen origins | Already true | Already true, but unstated |
| Checkable | Yes, mechanically | Only if the part declares which face | No |

The macro tolerates all three, because the attach vector folds any origin into the mounting joint, which is exactly why this has drifted without anything breaking.

### 1.2 The consumers

Read out of the drydock container on 2026-09-04. Nothing in this project pins them: the Gazebo libraries are whatever the `ros-lyrical-gz-*-vendor` packages (the Jetty line) resolve to on Ubuntu 26.04, and assimp is the Ubuntu package. An `apt upgrade` or an image rebuild can move any row, and every S-tagged claim below is tied to these numbers.

**Is any of this stable?** No, and the written record is unambiguous about it (section 1.8). glTF loading arrived in Gazebo Garden in 2022 and has been under continuous correction since. The metallic-roughness maps were being written out rotated ninety degrees. Every PBR texture was treated as color data, so meshes rendered visibly too dark. Embedded JPEG textures failed to load at all, with an error message about texture settings that named nothing relevant. The root node transform was dropped, then restored for glTF only. Occlusion was disabled because the renderer could not use it, then re-enabled from a different channel. Nine changes to the loader alone merged between July and September 2026, and the rotation and default-material behavior changed again between the version installed here and the next patch release, which is the table below. A recollection that an older Gazebo handled GLB very differently is not a false memory. It is what this history predicts.

**How much resolution does the tracking need?** Patch level. The change that moved under us during this audit was 7.3.0 to 7.3.1, so tracking at the minor version would not have caught it, and a pin that names anything coarser than the patch would not be worth writing. The same applies to assimp, which is the component actually doing the parsing and is versioned independently of everything else here (section 7.5). Section 10, decision 17 carries this.


| Component | Version | Role |
|---|---|---|
| gz-sim | 10.5.0 | Chooses whether the SDF material or the mesh's own materials are used |
| gz-rendering | 10.0.2 | Builds the Ogre-Next mesh and material from what gz-common loaded |
| gz-common | 7.3.0 | The loader: `AssimpLoader.cc` (external library, version not pinned, so could introduce instability), `Image.cc` (stb_image), `Material.cc`, `Pbr.cc`, `SubMesh.cc` |
| Ogre-Next | 2.3.3 | The renderer: HLMS PBS datablocks, tangent generation at mesh import |
| assimp | 6.0.4 (Ubuntu, linked against Draco) | Parses glTF for both Gazebo and RViz |
| rviz_rendering | 15.2.5 (Ogre 1.9) | RViz mesh loader: `mesh_loader_helpers/assimp_loader.cpp` |
| Blender glTF I/O | 5.1.20 | The exporter that wrote every delivered file |

Sources read for this document (branches `gz-common7`, `gz-rendering10`, `gz-sim10`, assimp tag `v6.0.4`, ogre-next `v2-3`, rviz `rolling`) are cached in the session scratchpad; nothing below is from memory of older versions. gz-common 7 decodes images with stb_image, not FreeImage, which changes what "supported image format" means compared with older Gazebo.

One caveat on that, found while auditing the written record (section 1.8). The gz-common source read here is the `gz-common7` branch tip, which is ahead of the installed 7.3.0: releases 7.3.1 (2026-08-18) and 7.4.0 (2026-08-24) exist upstream, plus merges not yet released. Two of those changes land in `AssimpLoader.cc` and are compared against the 7.3.0 tag here:

| Behavior | 7.3.0, the installed version | 7.3.1 and later, the branch read | Effect on us |
|---|---|---|---|
| glTF root node rotation | `useIdentityRotation = (extension != "glb" && extension != "glTF")`. The extension is lowercased before the comparison, so `"glTF"` never matches and a `.gltf` file loses its root rotation. `.glb` matches and keeps it. | The literal is corrected to `"gltf"`, so both keep it (gz-common PR 858) | None. We deliver `.glb` only, which took the same path before and after. It is a small argument for requiring GLB over `.gltf` on this version. |
| assimp's own default material | No filter exists. Every assimp material becomes a gz `Material`. | `IsDefaultMaterial` skips a material named `DefaultMaterial` carrying exactly two properties (gz-common PR 858) | None. A glTF primitive without a material gets a fully populated synthesized material, which fails that two-property test, so it survives on both. Probe-confirmed on 7.3.0 (section 1.3, step 6). |
Yes, and that is the conclusion section 0.1 is built on rather than an aside. Gazebo has not implemented the whole of glTF, it is openly still working on the parts it does implement, and the project publishes almost nothing saying which parts those are (section 1.8). Expecting it to agree with the specification was never a safe assumption, and the table above is the compact demonstration: one file, one specification, two adjacent patch releases, different behavior. This is exactly why this review separates the format from the targets and gives each its own tool. A file is correct because it validates and matches its intent. Gazebo tells us what will ship today, on this version, which is a different and more perishable question.


Where the branch and the installed version could differ, a P-tagged observation wins over an S-tagged one, because the probe links against the installed library and the source is the branch. Every S claim in this document was checked for such a gap; these two are the only ones found, and neither changes a conclusion.

### 1.3 The Gazebo path, step by step

1. The gz-sim server never loads a visual mesh. Visuals are loaded by whichever process renders: the GUI, or a rendering sensor. Collision meshes are loaded by the physics side through the same gz-common loader. [S]
2. `MeshManager` dispatches on the lowercased extension: `stl` to the STL loader, `dae` to the Collada loader, `obj` to the OBJ loader, and `gltf`, `glb`, `fbx` to `AssimpLoader`. The two `.dae` files still in the tree (`ping360`, `bluerov2_heavy_chassis`) therefore go through a different loader with different material semantics; they are outside this spec until converted. [S]
3. `AssimpLoader::Load` imports with `JoinIdenticalVertices`, `RemoveRedundantMaterials`, `SortByPType`, `FlipUVs`, `PopulateArmatureData`, `Triangulate` and `GenNormals`. Not requested: `CalcTangentSpace` (tangents are never computed here), `FindDegenerates` (degenerate triangles survive), `GenUVCoords`. Assimp assertion failures and exceptions are caught and reported as a load failure, not a crash. [S]
4. Root transform: for `glb` the root node transform is kept as exported; for other formats its rotation is dropped, and on the installed 7.3.0 that wrongly includes `.gltf` (section 1.2). Every node's translation, rotation, scale or matrix is multiplied down the tree and baked into the vertices. Node transforms are therefore honored, not ignored. [S, P: the T200 files carry a 2.8 mm translation node and the probe's bounding box shifts by exactly that.]
5. Each assimp mesh, which is one glTF primitive, becomes one gz `SubMesh` named after the glTF node that carries it, not after the glTF mesh. Seven primitives on one node become seven submeshes with the same name. [S, P: `bluerov2_chassis` yields seven submeshes all named `Frame.001`.] Vertices, normals (authored ones kept; generated only when absent), every UV set, and 32-bit indices are copied. Tangents and vertex colors are not stored: `SubMesh` has no tangent channel and the factory has a `TODO: diffuse colors`. [S]
6. Materials: `CreateMaterial` builds a gz `Material` plus `Pbr` for every assimp material (on 7.3.1 and later, every one that is not assimp's own two-property default). Section 1.4 tabulates what it reads. A glTF primitive with no material gets assimp's synthesized glTF default (white, metallic 1, roughness 1, opaque), which is fully populated and so survives that filter on either version; Gazebo renders it as dull white metal. [S, P: `material[6]` on the chassis.]
7. gz-rendering's `Ogre2MeshFactory` builds an Ogre v1 mesh (positions, normals, all UV sets as float2, a dummy UV set if there is none, 32-bit indices) and then calls `importV1(v1Mesh, halfPos=false, halfTexCoords=true, qTangents=true)`. Ogre-Next's `importV1` with `qTangents=true` generates tangents from UV set 0 whenever the mesh lacks them, which for us is always. UVs are stored as 16-bit half floats. [S]
8. `BaseMaterial::CopyFrom` copies, in order: ambient, diffuse (RGBA), specular, emissive, shininess, transparency, alpha-from-texture (enabled, threshold, two-sided), render order, base color texture, then the PBR set: normal, roughness and metalness maps, roughness and metalness factors, environment map, emissive map, light map with its UV set. Ogre-Next combines factor and map for metalness and roughness; the factor is a multiplier on the map as in glTF. [S for the copy order; U for the exact shader combination, which is documented behavior of Ogre-Next's PBS but not re-read in shader source for this audit.]
9. Textures are uploaded from memory as RGBA8; base color and emissive as sRGB, normal, roughness and metalness as linear (Ogre-Next's `suggestUsingSRGB`). Normal maps are reduced to a two-channel signed format, so only R and G are used and the blue channel is reconstructed. Mipmaps are generated for the base color and normal maps only; roughness and metalness maps get none. Sampler wrap is always repeat; the glTF sampler is not read. 16-bit PNGs decode but are converted to 8-bit on upload. [S]
10. Transparency: Ogre2's `UpdateTransparency` computes `opacity = (1 - transparency) * diffuse.alpha`; anything below 1.0 moves the material to the transparent render queue. `SetAlphaFromTexture` (MASK) switches on alpha test with the cutoff, a transparent-alpha blend block, and two-sided lighting, which in Ogre-Next also disables back-face culling. Nothing else touches the cull mode, whose default is `CULL_CLOCKWISE`: back faces of OPAQUE and BLEND materials are culled regardless of `doubleSided`. [S, P: `twoSided 0` on every delivered material although all are exported `doubleSided: true`.]
11. gz-sim `SceneManager`: if the SDF `<visual>` carries a `<material>`, that one material is loaded and set on the whole geometry, replacing every embedded material. If it does not, the submesh materials from the file are used, with the visual's `<transparency>` multiplied in. The generated part SDF never emits `<material>`, so embedded materials are what renders. This also means an SDF-side material can only ever be a single material per visual: per-primitive materials are lost the moment one is declared. [S]

### 1.4 What the loader reads from a glTF material

| glTF field | assimp property | gz-common result | Renders as |
|---|---|---|---|
| `baseColorFactor` RGB | `COLOR_DIFFUSE` | `Diffuse` | Multiplies the base color texture (alpha, see next row) |
| `baseColorFactor` alpha | `COLOR_DIFFUSE` alpha and `OPACITY` | `Diffuse.A = a` and `Transparency = 1 - a` | Opacity `a * a` in Ogre2, on every alpha mode, because both terms carry it [S; visual confirmation pending, U] |
| `baseColorTexture` | `aiTextureType_DIFFUSE` | base color image (UV set 0 assumed) | sRGB albedo with mipmaps |
| `alphaMode: MASK`, `alphaCutoff`, `doubleSided` | `GLTF_ALPHAMODE`, `GLTF_ALPHACUTOFF`, `TWOSIDED` | `SetAlphaFromTexture(true, cutoff, twoSided)` | Alpha test at cutoff, no back-face culling. Only read when a base color texture exists |
| `alphaMode: BLEND` | `GLTF_ALPHAMODE` | nothing (`BLEND not supported yet` in source) | Opaque, texture alpha ignored |
| `doubleSided` on OPAQUE or BLEND | `TWOSIDED` | not read | Back faces culled |
| `metallicFactor`, `roughnessFactor` | `METALLIC_FACTOR`, `ROUGHNESS_FACTOR` | `Pbr::Metalness`, `Pbr::Roughness`; metalness also becomes the Phong specular color | Multipliers on the maps |
| `metallicRoughnessTexture` | `GLTF_PBRMETALLICROUGHNESS_METALLICROUGHNESS_TEXTURE` | split into a metalness map (B) and a roughness map (G), 8-bit single channel | Linear, no mipmaps |
| `occlusionTexture` on UV set 0 | `aiTextureType_LIGHTMAP`, uv index 0 | R channel extracted into a light map on set 0 | Ambient occlusion |
| `occlusionTexture` on UV set 1 or higher | `aiTextureType_LIGHTMAP`, uv index n | whole image as light map on set n | Baked lightmap on its own UVs |
| `normalTexture` | `aiTextureType_NORMALS` | normal map, tangent space | R and G only; `scale` ignored |
| `emissiveFactor`, `emissiveTexture` | `COLOR_EMISSIVE`, `aiTextureType_EMISSIVE` | `Emissive`, emissive map | sRGB emissive, 0 to 1 |
| `KHR_materials_emissive_strength` | `EMISSIVE_INTENSITY` | not read | No HDR emissive |
| `KHR_materials_transmission` | `TRANSMISSION_FACTOR` | `Transparency = factor` | Transparent, so not ignored |
| `KHR_texture_transform` | `UVTRANSFORM` | not read | Textures render untransformed, i.e. misplaced |
| `KHR_materials_pbrSpecularGlossiness` | diffuse and specular colors, `aiTextureType_SPECULAR` | diffuse color, specular map name only | No roughness or metalness maps; not a working import |
| `KHR_materials_specular` | `COLOR_SPECULAR`, `SPECULAR_FACTOR`, specular textures | specular color and a specular map name | Effectively ignored under the metal workflow |
| `KHR_materials_clearcoat`, `sheen`, `ior`, `volume`, `anisotropy`, `unlit` | read by assimp | not read | Ignored |
| `KHR_draco_mesh_compression` | decoded by assimp (Ubuntu build links Draco) | plain geometry | Works in both consumers |
| `KHR_texture_basisu`, `EXT_texture_webp` | parsed by assimp | `Unable to load embedded texture. Unsupported compressed image format` | Untextured, with an error on the console |
| Embedded PNG or JPEG | `aiTexture` with format hint | decoded with stb_image | Works. Only these two hints are accepted |
| `samplers` | read by assimp | not read | Always repeat, linear |
| `COLOR_0` vertex colors | read by assimp | not copied | Ignored |
| `TANGENT` | read by assimp | not copied | Ogre-Next regenerates from UV0 |
| `animations`, `skins` | read | skeleton and animation built | Bounding box forced to a unit cube when an animation exists, so a stray animation breaks culling |
| `cameras`, `KHR_lights_punctual` | read by assimp | not read | Ignored |

### 1.5 The RViz path

`rviz_rendering::AssimpLoader` imports with `SortByPType`, `GenNormals`, `Triangulate`, `GenUVCoords`, `FlipUVs`, then for `.gltf`, `.glb` and `.vrm` multiplies the root node by a +90 degree rotation about X, taking glTF Y-up to ROS Z-up. Materials are Ogre 1.9 fixed-function: diffuse, ambient, specular, emissive colors, shininess, opacity from `baseColorFactor` alpha, and exactly one texture, looked up as `aiTextureType_DIFFUSE`. Metalness, roughness, normal, occlusion and emissive maps do not exist in RViz. [S]

The lookup loop is the known trap: it iterates every material property and, on any `$tex.file` entry, asks for the diffuse texture. A material whose only texture is a normal map has such an entry, the diffuse lookup fails, the resulting path resolves to the mesh directory, and the resource retriever's exception terminates RViz. That is why `gltf_bake_basecolor.py` and the guard in `test/test_parts.py` exist (commit `01b05f9`). Any spec for these files must carry the rule: a material with any texture must also have a base color texture. [S, and the repo's own regression test]

### 1.6 The pipeline in this repo, and where forward is

Blender is Z-up with the same right-handed convention as ROS, so a part is modeled x forward, y left, z up, exactly the part frame the macro uses. Blender's exporter writes Y-up glTF by mapping (x, y, z) to (x, z, -y). In the file, forward is +X, up is +Y, and +Z is the part's right-hand side. `parts.xacro` rotates every glTF visual by +90 degrees about x when expanded with `gltf_up:=z` for Gazebo, which maps file (X, Y, Z) to (X, -Z, Y) = ROS (x, y, z). RViz applies the identical rotation itself, which is why the installed URDF stays unrotated. `gltf_to_yup.py` applies the same (x, z, -y) bake for a delivery exported Z-up, and refuses files with rotation or matrix nodes because it does not conjugate them. [S, and `parts.xacro` lines 71 to 86]

The consequence for the spec: the glTF convention "front faces +Z" does not apply. Every delivered file has its long axis on X (the BlueBoat hull is 1.19 m along X and 0.93 m along Z [F]). A modeler who reads "+Z forward" literally and rotates the model to face +Z in the exported file would deliver a part that looks fine in every viewer and faces left in every assembly.

### 1.7 What must be considered when moving this project to GLB

The distilled list. Each item is backed by sections 1.3 through 1.6.

1. Embedded images must be PNG or JPEG. Anything else (KTX2, Basis, WebP) fails with a console error and an untextured part, not silently. [S]
2. Only `alphaMode: MASK` is honored, and only when a base color texture exists. `BLEND` is ignored and renders opaque. Uniform transparency comes from `baseColorFactor` alpha alone, on any alpha mode, and comes out squared. An OPAQUE material exported with alpha 0.8 in its factor turns translucent in Gazebo. [S, P]
3. `doubleSided` is honored only through MASK. Every OPAQUE surface is back-face culled, so thin geometry (flags, fins, mesh guards) must have thickness or use MASK. [S, P]
4. The name Gazebo sees is the glTF node name. Mesh names and material names are never read. `<submesh><name>` in SDF selects by node name, and every primitive under one node shares it. [S, P]
5. Tangents are never read from the file and always generated by Ogre-Next from UV set 0. Exporting them changes nothing. What matters for normal-mapped surfaces is a clean UV0: no zero-area UV triangles, no overlapping islands with mixed handedness. Tangent generation also needs a UV set to exist at all. [S]
6. Base color and emissive upload as sRGB, the rest linear, matching glTF. Normal maps lose their blue channel (reconstructed). Roughness and metalness maps get no mipmaps, so large ones shimmer at distance; they should be smaller than the base color map. 16-bit maps buy nothing. [S]
7. Occlusion works two ways: packed into R of the metallic-roughness texture on UV0 (Gazebo splits it out), or as a separate light map on UV1. Base color, normal and metallic-roughness always read UV0. [S]
8. UVs are stored as half floats. Precision near 1.0 is one texel of a 2048 map; at UV 4 it is four texels. Keep UVs inside [0, 1] for a reason, not a habit. [S]
9. Node transforms are applied by both consumers, so a translation or scale node is not a defect for rendering. Our own tool `gltf_to_yup.py` refuses rotation and matrix nodes, which is the actual reason to require applied transforms. [S]
10. A primitive without a material renders as white metal in Gazebo. There is no fallback to a neighboring material. [S, P]
11. A metallic-roughness texture whose B channel is white makes the part fully metallic regardless of intent; with `metallicFactor` 1.0 (the glTF and Blender default) the factor cannot rescue it. Four of the fifteen delivered files have this. [F, P]
12. Transmission is not ignored: it becomes transparency. Texture transform is ignored in the worst way: the texture renders in the wrong place. Draco decodes fine in both consumers. Animations are imported and break the bounding box. The "do not use" list is right; its stated reasons are mostly wrong. [S]
13. RViz reads only the base color texture and colors, requires a base color texture on any textured material, and shares the `baseColorFactor` alpha behavior. Both consumers must be checked at acceptance. [S]
14. A `<material>` in SDF replaces every embedded material with one. The part pipeline must keep not emitting one, and the earlier sandbox conclusion "declare PBR in SDF" was a workaround, not a loader limit: its symptom (bright mis-lit facets on the BlueBoat) is what a fully metallic hull looks like under an environment light. [S, F]
15. Legacy `.dae` files use a different loader; the spec covers them only once they are re-exported as GLB. [S]
16. Units are meters with no loader-side scaling. Blender unit scale must be 1.0 and object scale applied, otherwise the file is silently the wrong size. [D]
17. No loader limit on triangles (32-bit indices). The budget is a policy. Texture memory dominates: three 2048 square maps per part are about 64 MB uncompressed with mipmaps. [S]

### 1.8 The written record: what the Gazebo project says about glTF

Sections 1.3 to 1.7 are what the code does. This section is what the project has written down, surveyed on 2026-09-04 across the Gazebo docs, the gz-common, gz-rendering and gz-sim changelogs and trackers, the release notes, and the Open Robotics Discourse (the PMC meeting minutes). Evidence tag W. It matters for two reasons: it tells us which of our findings are project-acknowledged behavior rather than accidents we have to live with, and it tells us what is about to change.

**The documentation barely exists.** The only official statement of format scope is one sentence in the gz-common `MeshManager` API reference: supported formats are STL, COLLADA, OBJ, glTF (GLB) and FBX, with glTF and FBX going through assimp unless `GZ_MESH_FORCE_ASSIMP` is set. No tutorial mentions glTF. The Blender tutorial still recommends COLLADA for visual geometry, and the Fuel pages list `.dae`, `.stl`, `.obj` without a preference. The docs issue asking for this (gazebosim/docs 308) has been open since 2022, and in May 2026 a maintainer wrote on it that the format list "is hardly discoverable" and that the documentation "is lacking". Practical consequence: Carlos's draft spec could not have been written from Gazebo documentation, because there is none to write it from. Neither could this audit, which is why section 1 is a source read.

**Most of what we depend on has no written record at all.** A search of the Gazebo organization's issues and pull requests returns nothing for glTF `alphaMode`, MASK, BLEND, `alphaCutoff`, `doubleSided`, `KHR_texture_transform`, Draco, KTX2 or Basis, vertex colors, glTF sampler wrap and filter modes, or reading `TANGENT` from a file. Every one of those is a rule in our spec. They are neither promised nor disclaimed by the project, so they can change in any release without anyone considering it a regression, and our only protection is the acceptance check.

**Where the record confirms our findings independently.** These stop being our private conclusions:

| Our finding | The record |
|---|---|
| Submesh names are node names, not mesh names (1.3, step 5) | gz-common PR 659, open since December 2024: "Submeshes were named by the name of the node that contained them, not the actual submesh." Known, unfixed. |
| The metallic-roughness texture is split into separate maps (1.4) | gz-common issue 363 chose that design; PR 532 later fixed the split maps being written out rotated 90 degrees. |
| Occlusion is read from the R channel of the ORM texture (1.7, item 7) | gz-common PR 538 first disabled assimp's lightmap because "occlusion maps are not yet supported in gz-rendering"; PR 630 then re-enabled it reading occlusion from the roughness-metalness texture. |
| Base color and emissive are sRGB, other maps linear (1.3, step 9) | gz-rendering PR 931: the previous behavior assumed every PBR texture was sRGB, "as the result the meshes are rendered darker than it should be". |
| Normal maps become two-channel signed 8-bit with mipmaps (1.3, step 9) | gz-rendering PR 1068. |
| Tangents are generated by the renderer, and generation needs a UV set (1.7, item 5) | gz-rendering PR 976 fixed an Ogre exception when a submesh lacked texture coordinates during tangent generation. Nothing anywhere describes reading tangents from the file. |
| Transmission becomes plain transparency (1.4) | gz-common PR 577: "currently just parsing the transmission factor property and modeling it as simple transparency setting". |
| Embedded PNG and JPEG only (1.7, item 1) | gz-common PR 545 added embedded JPEG support; before it such files failed with "a confusing error message about invalid texture settings". |
| RViz reads only the base color texture (1.5) | ros2/rviz PR 1001, which added GLB loading, notes "There are lots more things potentially in a GLB file, like all sorts of PBR stuff". |

**Where the record adds something we did not have.** The material-override gap in `SceneManager` (1.3, step 11) is a bare `TODO(anyone)` in the source with no issue tracking it, so nobody is working on it. Several PRs record that Gazebo's rendering of the Khronos sample models does not match their reference images, with the discrepancies left unresolved in the PR: the damaged helmet, a bottle that "appears a lot darker than expected", a light bulb that "should be transparent". That is the project itself observing T1-versus-T3 drift of the kind section 0.1 describes, which is a useful thing to be able to cite when a modeler asks why their file looks different here.

**What is about to change.** Three things, in descending order of consequence for us:

1. **COLLADA is on the way out and glTF is the intended replacement.** The PMC minutes of 2026-08-17 record a discussion of "long-term deprecation of COLLADA (DAE) format support in favor of modern standards like glTF/GLB", noting that major tools including Blender have dropped COLLADA, with a transition strategy and Fuel compatibility checks to be outlined before removal. This is the strongest available answer to "is GLB the right bet for this project", and it retires the question. It also raises the priority of the two `.dae` stragglers (1.7, item 15).
2. **All mesh loading is moving to assimp.** The PMC minutes of 2026-06-15 record a decision to transition from the custom Collada, OBJ and STL loaders to assimp by default, keeping the custom ones behind an environment variable for one release before removing them. Work through 2026 is labeled for the release line after Jetty. Our `.dae` files would then load through the same path as our GLBs, with the behavior differences that PR 845 is currently cataloguing.
3. **The loader is under active change right now.** Nine AssimpLoader pull requests merged between July and September 2026, several backported into the `gz-common7` line we are on: texture naming and memory handling, node traversal order and the naming of unnamed submeshes, GLB animation transforms, lazy loading of external textures, and the two changes compared in section 1.2. Section 1.2's warning that nothing pins these versions is not theoretical.

Two smaller notes. Animations in glTF were not previously loaded as animations by gz-sim at all; a pull request merged into the gz-sim 10 branch on 2026-08-27, after our 10.5.0, changes that, which slightly raises the cost of a stray animation in a delivery (1.7, item 12). And a maintainer stated in 2022 that rigged glTF bones becoming joints is not planned, which is not something we want anyway.

**What we could contribute back.** Our section 1.4 table is, as far as this survey found, the only systematic statement anywhere of which glTF material fields Gazebo honors. Two candidates: a comment on gazebosim/docs 308 offering the table, since a maintainer has already asked for exactly this and the issue is open; and an issue for the `SceneManager` material-override TODO, since a per-visual `<material>` silently discarding every embedded material is a trap other people will hit. Section 7 carries this as a decision rather than an action.

Open items worth watching, all of which would change something in section 1:

| Repo | Item | State | Why it matters here |
|---|---|---|---|
| gz-common | 659, assimp submesh naming | open pull request | Would change the names SDF `<submesh>` selects by, which our node-naming rule depends on |
| gz-common | 920, lazy loading of external textures | open pull request | Changes when and whether external textures are decoded |
| gz-common | 845, unified loader test suite | open pull request | Cataloguing where the assimp and custom loaders differ, ahead of the switchover |
| gz-common | 404, custom mesh loaders | open | Would let a project supply its own assimp flags |
| gz-rendering | 60, Ogre2 transparency | open since 2020 | Transparent-object sorting, the pass our BLEND advice avoids |
| gz-rendering | 267, negative scale inverts normals | open since 2021 | A mirrored part delivered with negative scale would shade wrong |
| gazebosim/docs | 308, best practices for 3D designs | open since 2022 | Where a maintainer asked for the supported-format list |

## 2. Verification tooling and criteria

### 2.1 glb_probe: what Gazebo actually built

A 90-line program linked against the installed gz-common 7 that loads a mesh through `MeshManager` exactly as Gazebo does and prints the submeshes (name, counts, UV sets, material index) and every material (diffuse RGBA, transparency, alpha-from-texture, threshold, two-sided, emissive, and each PBR map with its decoded size). Loader errors and debug lines print inline. It lives in `~/maritime_ws/spike/glb_probe/` for now; it should move into `bluerobotics_parts/scripts` (or a `gz`-style tool in `maritime-workspace`) once the acceptance list references it.

```bash
# build once, inside drydock
cd ~/maritime_ws/spike/glb_probe && mkdir -p build && cd build
cmake .. -DCMAKE_PREFIX_PATH="/opt/ros/lyrical/opt/gz_common_vendor;/opt/ros/lyrical/opt/gz_math_vendor;/opt/ros/lyrical/opt/gz_utils_vendor;/opt/ros/lyrical/opt/gz_cmake_vendor"
make
# run on a delivery
cd ~/maritime_ws/src/bluerobotics_models/bluerobotics_parts/models
~/maritime_ws/spike/glb_probe/build/glb_probe <part>/<part>.visual.glb
```

The vendor packages install as `gz-common` (unversioned) with the target `gz-common::gz-common-graphics`; the versioned `gz-common7` config does not exist in the vendor layout.

This is the only proxy for Gazebo that does not need a GPU. It does not render, so it cannot judge how a material looks; it settles what the material is.

### 2.2 File-level lint

The checks below are what the audit ran by hand with a Python script over the JSON chunk and the decoded images (PIL and numpy on the host). They should become `scripts/glb_lint.py` and a test in `test/test_parts.py`, next to the existing base color guard:

- Header: magic `glTF`, version 2, two chunks, JSON then BIN.
- `extensionsRequired` empty; `extensionsUsed` empty or on an allow list.
- Exactly one scene, or a default `scene` set, one root node, node named for the part.
- Every primitive: `mode` 4, `POSITION`, `NORMAL`, `TEXCOORD_0` present, `material` set.
- Every material: `pbrMetallicRoughness` present, `alphaMode` in {OPAQUE, MASK}, `baseColorFactor` alpha 1.0 unless the part declares a translucent region, `metallicFactor` and B-channel mean of the metallic-roughness texture consistent with a stated metal or non-metal, a `baseColorTexture` wherever any other texture exists (RViz).
- Images: `mimeType` PNG or JPEG, size at most 2048, PNG wherever alpha is used, sizes of roughness/metalness maps at most half the base color map.
- Nodes: no `rotation` or `matrix`; `translation` reported, not failed.
- Extents: accessor min and max on the part node versus the datasheet, in the file's Y-up frame (length on X, height on Y, width on Z).
- Triangle count against the budget.

### 2.3 Eyes on a render

Unchanged from the existing acceptance steps, with the material checks made specific:

1. `parts_check.sdf` in Gazebo: scale against a known object, frame orientation, origin, collisions toggled on, and now: no white-metal patches (missing material), no dark hull (metalness), cutouts actually cut (MASK), thin parts visible from both sides.
2. RViz with the installed URDF: the part renders, is upright, and RViz does not exit.
3. Optional and not built yet: a headless render (Ogre2 with EGL and a camera sensor) that captures the parts world to PNG so a reviewer on a laptop can compare before and after a redelivery. [U]

### 2.4 External viewers are not a Gazebo proxy

The Babylon sandbox, three.js viewers and f3d honor BLEND, `doubleSided`, exported tangents, texture transforms and most extensions. They approximate T2 (section 0.1), each with its own gaps, and are useful to inspect names and material assignment. They are the wrong tool to predict Gazebo: the BlueBoat renders ghostly in Babylon and fully opaque in Gazebo, from the same file. When the question is "what should this file look like", the answer is the Khronos Sample Viewer, not any of them. f3d is not installed in the container.

### 2.5 Acceptance criteria, as pass or fail

| Criterion | Tool | Pass |
|---|---|---|
| Loads without error in gz-common | glb_probe | No `[error]` lines |
| Every primitive has a material | glb_probe, lint | No submesh with `material NONE`, no white/1/1 material |
| Names | lint | Node name equals the part name; no `.001`, no spaces |
| Frame and extent | lint against datasheet, Gazebo | Within stated tolerance, X forward, Y up in file |
| Alpha modes | lint, Gazebo | Only OPAQUE and MASK; MASK only with a PNG base color |
| Metalness | lint (B channel mean, factor) | Non-metal parts read below 0.1 |
| RViz | RViz | Renders and stays up |
| Textures | lint | PNG or JPEG, at most 2048, PNG where alpha or normal |
| Transforms | lint | No rotation or matrix nodes |
| Extensions | lint | `extensionsRequired` empty |
| Spec-valid (T1) | Khronos validator | Zero errors; warnings and infos listed and explained |
| Intended (T2) | Sample Viewer, or a Blender re-import | Looks like what the modeler meant, signed off by the modeler |

### 2.6 The Khronos glTF Validator

The T1 tool. It is a single static binary from the KhronosGroup/glTF-Validator releases on GitHub (no apt package; the current release is a prerelease tag), run on the host or in the container:

```bash
gh release download 2.0.0-dev.3.10 -R KhronosGroup/glTF-Validator -p 'gltf_validator-2.0.0-dev.3.10-linux64.tar.xz'
tar xf gltf_validator-2.0.0-dev.3.10-linux64.tar.xz
./gltf_validator -o -a <part>.visual.glb      # JSON report on stdout, every message on stderr
```

Run on all 15 delivered files on 2026-09-04 [V]:

- Errors: none in any file. Every delivery is conformant glTF 2.0, so no current defect is in the Invalid class.
- Warning `MESH_PRIMITIVE_GENERATED_TANGENT_SPACE` on the 11 files that carry a normal map: "Material requires a tangent space but the mesh primitive does not provide it. Runtime-generated tangent space may be non-portable across implementations." This is the validator restating the spec's SHOULD on tangents (section 0.1), and it is the only place the draft spec's tangent rule has a basis. Section 3, item 10 weighs it.
- Info `UNUSED_OBJECT` six times in `bluerov2_chassis`: the `TEXCOORD_0` attribute on primitives 1 to 6, whose materials have no textures. Harmless.

The validator checks structure, accessors, image headers and the material schema. It cannot know that a white metalness channel on a plastic hull is wrong, so a clean validator run says nothing about the Unintended class; that is what T2 is for. It belongs in the lint (section 2.2) as the first step, since everything after it assumes a valid file.

## 3. Audit of `docs/reference/asset-spec.md`, item by item

Numbered in document order. Quoted text is Carlos's.

### Files

1. "glTF 2.0 binary (.glb), textures embedded." Technically correct [S]: embedded PNG and JPEG load in both consumers. Applicable, in scope. Verified. Add the image-format constraint explicitly (PNG or JPEG; nothing else loads), since "embedded" alone admits KTX2.

2. "`<part>.visual.glb`, next to `<part>.collision.stl`" and "Collision meshes are separate, simplified STL files." The visual name matches the repo convention. The collision statement does not: `parts.md` says collision is primitives stated in the macro, from the modeler's `model.sdf`, with a mesh only when a primitive will not do; one `.collision.stl` exists in the tree today against nine `model.sdf` files. Open. This is a pipeline decision (does the modeler still deliver `model.sdf`? do we accept STL envelopes?), and the spec must say which. See section 10, decision 1.

3. "Budget about 25k triangles per part; textures 2048 px or smaller, PNG." No loader limit on either [S]; policy. Two technical corrections: JPEG is fine for base color and is what every delivery uses, while PNG is needed for anything with alpha and preferable for normal maps; and roughness/metalness maps get no mipmaps, so they should be capped lower (1024) than the base color. Corrected: keep the numbers as policy, split the format rule per map, and note that texture memory, not triangles, is the cost.

4. "Name meshes, nodes and materials after the component … Mesh names are addressable from SDF as submeshes." Corrected. Gazebo never reads mesh or material names; the submesh name is the node name [S, P]. The rule survives as hygiene plus one hard requirement: the node is named for the part. The defect noted (`Cube.001`, `Cube.018`) is real but the addressable names are actually `blueboat_chassis.visual.001` and `Frame.001`, which carry Blender's numeric suffix and, for the chassis, the wrong name. Material names for colors (`TEMP-GRAY`) are a hygiene issue only. Add: one root node, one scene, no leftover scenes (six files carry empty extra scenes from the Blender file). [F]

### Units, frame, origin

5. "Meters, at real world scale … the BlueROV2 chassis measures its 457 x 338 x 254 mm exactly." Verified [F]: accessor extents are 0.457 on X, 0.338 on Z, 0.254 on Y. Applicable, in scope. Add the tolerance and where to read the numbers (accessor min/max on the part node, or the probe's bounding box), and that height is the file's Y.

6. "Author to the glTF spec: +Y up, +Z forward, no baked rotation nodes." Y up: Verified against T1 [D], and it is the whole reason `parts.xacro` and RViz agree. +Z forward: the draft quotes T1 correctly ("the front side of a glTF asset faces +Z"), and this project deliberately does not follow that sentence: forward is +X in every delivered file, because the modeler authors in the ROS frame and the exporter's fixed conversion does the rest (section 1.6). Whether it stays that way is open, with the trade-offs set out in section 1.1 and the call in section 10, decision 2. Class: Pipeline. Refuted as a rule for our modelers [F, S]; the spec text must state our convention and say explicitly that it overrides the glTF front-facing convention. Rotation nodes: the loader applies them [S], the constraint comes from `gltf_to_yup.py` [S], so the rule stands with a corrected reason and should say "transforms applied in Blender before export". "Do not fix the orientation for Gazebo yourself": Verified.

7. "Author the mesh in the part frame … Where the origin sits within the part is the part author's choice." Technically neutral: `attach` folds any origin into the mounting joint [S, `parts.xacro`]. It conflicts with `parts.md` rule 2, "origin at the mesh centroid", and the older README's "approximately at the centroid, in the place the part would sensibly be mounted from". Open. See section 10, decision 2.

### Geometry

8. "Authored normals with deliberate hard edges; no degenerate triangles." Verified [S]: authored normals are kept, `GenNormals` only fills gaps, and `FindDegenerates` is not run so degenerates survive into tangent generation. Keep.

9. "One UV set, inside [0, 1]. A second UV set only for a baked ambient occlusion lightmap." Verified [S]: all textures except the light map read set 0; set n is honored for occlusion. The [0, 1] rule gets a real rationale (half-float storage, repeat sampling). Keep, with the rationale.

10. "Export tangents whenever a normal map is present. Gazebo does not generate them." Split by truth. Against T1 [D, V]: tangents are optional, the spec says a client SHOULD generate missing ones with MikkTSpace, and the validator flags their absence on a normal-mapped primitive as a portability warning, not an error. Exporting them is a legitimate best practice for portability across viewers. Against T3 [S]: the stated rationale is false. gz-common has no tangent channel, so exported tangents are discarded, and Ogre-Next generates its own from UV0 at import, with Ogre's algorithm rather than MikkTSpace. Verdict: Refuted as a Gazebo requirement and as a defect; the 11 files "missing" tangents are conformant and Gazebo would not use the tangents if they were there. The rule may stay as an optional, zero-cost export setting for other viewers, but it must not appear on a defect list. What does matter for T3 is a clean UV0 on normal-mapped surfaces, since that is the input to Gazebo's generation. Class: Unsupported (Gazebo does not honor the spec's MikkTSpace recommendation). How visible the algorithm difference is on our hard-edged low-poly parts is unverified [U].

### Materials

11. "Metallic roughness workflow only. Every primitive must have a material assigned … falls back to the glTF default, which is full metal." Verified [S, P]: the unassigned chassis primitive (4776 of 21776 triangles, 22 percent) becomes a white, metallic 1.0, roughness 1.0 material. Keep, and state that the specular-glossiness extension is not a working import.

12. The map table. Base color: Verified; alpha rules refined in items 14 to 17 below. ORM packing: Verified [S], occlusion in R is split out when on UV0. Normal: Verified that it is read; PNG over JPEG is policy; add that `normalTexture.scale` is ignored and must be 1.0 in the file, and that only R and G reach the GPU. Emissive: Verified [S], factor and map read, strength extension ignored. Corrected on details only.

13. "Metalness is black on plastics … the BlueBoat shipped with metalness at 1.0 across the entire hull." Verified [F]: the metallic-roughness image's B channel is 255 everywhere and the factor is 1.0. Extend: `basestation_antenna`, `surveyor_multibeam` and `omniscan_450_sidescan` ship the same all-white map with factor 1.0, so the same defect. Turn into a measurable criterion (section 2.5).

### Transparency

14. "Gazebo supports two of glTF's three alpha modes." Corrected [S, P]: one mode (MASK) is honored via `alphaMode`; BLEND is ignored and renders opaque. Uniform transparency exists, but it comes from `baseColorFactor` alpha regardless of the mode.

15. "Cutouts: MASK, cutoff 0.5, binary alpha in the base color texture." Verified [S]: cutoff, alpha test and two-sided are all honored, and only here. Add: the base color must be PNG (JPEG has no alpha), and the material needs a base color texture for the mode to be read at all.

16. "Glass and acrylic: own material with a uniform baseColorFactor alpha and BLEND. Gazebo applies the uniform opacity to the whole material." Corrected [S]: the opacity comes from the factor alpha and is applied squared (alpha 0.5 renders at 0.25); the BLEND tag is irrelevant to Gazebo and only matters to other viewers and RViz. Keep the rule, state the squaring so the modeler picks the alpha for Gazebo, and mark the visual check as pending [U].

17. "Not available: gradient transparency … never tag an opaque part BLEND: viewers move it to the translucent pass, where it renders ghostly (defect found: the whole BlueBoat is one BLEND material)." Gradient alpha: Verified, not available. The BlueBoat finding: Corrected [P]. In Gazebo the BLEND tag is dropped and the hull renders opaque with its 0.45 percent of cutout texels uncut; "ghostly" is what Babylon shows. The rule (never BLEND) stands for cross-viewer consistency and because it hides the fact that the cutouts do not work.

### Do not use

18. The extension list "Gazebo's loader ignores all of them, silently." Corrected per extension [S, the table in section 1.4]: transmission becomes transparency; texture transform misplaces textures; specular-glossiness half-imports; Draco decodes fine in both consumers; KTX2, Basis and WebP fail loudly; animations import and break the bounding box; cameras and lights are ignored. The ban stands on all of them, with tooling as the reason for Draco (`gltf_to_yup.py` and the lint cannot read compressed accessors) and `extensionsRequired` empty as the hard check.

### Checklist before delivery

19. Babylon sandbox walk. Corrected: valid for names and material assignment, not a Gazebo proxy (section 2.4). Add the probe.

20. `f3d`: "renders dark means a metalness defect; renders ghostly means a BLEND defect." Corrected: dark is a fair metalness signal in any PBR viewer; ghostly is a viewer artifact that Gazebo will not show, so the BLEND check belongs in the lint, not in a viewer. f3d is not in the container.

21. Dimensions and part frame. Verified; add the how (item 5 above).

22. Tangents exported. Refuted (item 10 above). Drop.

## 4. The delivered files, measured

Fifteen GLBs, all Blender glTF I/O 5.1.20, all conformant glTF 2.0 with zero validator errors [V], no extensions used or required, all materials `doubleSided: true` (ignored by Gazebo), no `TANGENT` attributes (a validator warning, irrelevant to Gazebo), one UV set each, every image embedded. Numbers from the JSON chunk, the decoded images, and the probe. [F, P]

| Part | Node name | Prims | Tris | Alpha mode | Metal factor | MR map B mean | Base color | Normal | Issues |
|---|---|---|---|---|---|---|---|---|---|
| basestation_antenna | basestation_antenna.visual.001 | 1 | 942 | OPAQUE | 1.0 | 255 | JPEG 128x256, pure white | JPEG 128x256 | Fully metallic; albedo is a constant |
| blueboat_antenna_mast | blueboat_antenna_mast.visual.001 | 1 | 2756 | OPAQUE | 0.0 | 255 | JPEG 512 | JPEG 512 | OK (factor 0 masks the white map) |
| blueboat_chassis | blueboat_chassis.visual.001 | 1 | 10668 | BLEND | 1.0 | 255 | PNG 2048 RGBA, 0.45 % alpha below 128 | JPEG 2048 | Fully metallic; BLEND dropped, cutouts not cut |
| blueboat_flag | blueboat_flag.visual.001 | 1 | 164 | OPAQUE | 0.0 | none | JPEG 256 | none | OK |
| blueboat_payload_bracket | blueboat_payload_bracket.visual.001 | 1 | 1703 | OPAQUE | 0.0 | none | JPEG 64, constant | none | OK; constant albedo could be a factor |
| blueboat_ping_singlebeam_mount | blueboat_ping_singlebeam_mount.visual.001 | 1 | 806 | OPAQUE | 0.0 | none | JPEG 128, pure black | none | Pure black albedo, check intent |
| bluerov2_chassis | Frame.001 | 7 | 21776 | OPAQUE | 0.0 (0 to 5), default (6) | none | 1x1 white PNG bake, dark factor | JPEG 2048 | 22 % of triangles unassigned; color-named TEMP materials; node misnamed; leftover scene |
| m200_weedless_prop_ccw / cw | m200_weedless_prop_ccw.visual.001 / cw | 1 | 388 | OPAQUE | 0.0 | 255 | JPEG 512, constant | JPEG 512 | OK; leftover scenes |
| omniscan_450_sidescan | omniscan_450_sidescan.visual.001 | 1 | 748 | OPAQUE | 1.0 | 255 | JPEG 256 | none | Fully metallic; scene named `Scene` |
| ping_singlebeam | ping_singlebeam.visual.001 | 1 | 422 | OPAQUE | 0.0 | none | JPEG 256, near black | JPEG 256 | Check albedo intent |
| surveyor_multibeam | surveyor_multibeam.visual.001 | 1 | 725 | OPAQUE | 1.0 | 255 | JPEG 256, pure black | JPEG 256 | Fully metallic, black albedo |
| t200_prop_ccw / cw | t200_prop_ccw_visual.001 / t200_prop_cw.visual.001 | 1 | 260 | OPAQUE | 0.0 | none | JPEG 512, constant | JPEG 512 | 2.8 mm translation node; leftover scenes; inconsistent node naming |
| t200_thruster | t200_thruster.001 | 1 | 1860 | OPAQUE | 0.0 | none | JPEG 512, constant | JPEG 512 | Translation node; leftover scenes |

Pattern worth naming to the modeler: every metallic-roughness map in the set is a solid color, and every one has B = 255. With `metallicFactor` 0 the map is masked and the part is fine; with the Blender default of 1.0 the part is metal. The fix at source is a black metallic channel, or no metallic-roughness texture with roughness carried by the factor.

## 5. What the draft spec does not cover and should

1. RViz: a material with any texture needs a base color texture (section 1.5), and RViz shows only base color and colors, so a part that relies on its normal or emissive map to read correctly will look flat there.
2. Back-face culling on everything but MASK (section 1.7, item 3): thin surfaces need thickness.
3. `baseColorFactor` alpha as a transparency trap on OPAQUE materials (section 1.7, item 2).
4. Scene and node hygiene: one scene, one root node, named for the part; no leftover scenes.
5. Node transforms: applied, except translations which are tolerated and reported.
6. Texture size per map type, and the no-mipmap cost of large roughness and metalness maps.
7. `normalTexture.scale` and `occlusionTexture.strength` are ignored: bake them to 1.0.
8. Vertex colors and glTF samplers are ignored: do not rely on them.
9. Animations must be absent, with the reason (bounding box).
10. The collision delivery and the origin rule (section 3, items 2 and 7) as explicit decisions.
11. Which images inside the file are named how. The current deliveries already use `Albedo-…`, `Normal-…`, which the earlier modeler notes asked for; make it a rule since it is the only thing that tells a reviewer which map is which in the probe output.
12. Legacy `.dae` parts: out of spec until re-exported.

## 6. The two Claude artifacts

Both artifacts measure the files against the draft spec, so they inherit its errors: wherever the spec's rationale is wrong (section 3), the artifact's verdict built on it is wrong the same way. Their measurements, on the other hand, are almost all correct and were re-measured here. The split below is measurement (does the number hold?) versus verdict (does the conclusion follow, given what the loader really does?).

Both are reproduced verbatim next to this file, each carrying a header that points back here: [ASSET_AUDIT_PARTS_LIBRARY.md](ASSET_AUDIT_PARTS_LIBRARY.md) and [ASSET_AUDIT_BLUEBOAT_CHASSIS.md](ASSET_AUDIT_BLUEBOAT_CHASSIS.md). They are snapshots of a source document, not project truth, and nothing in them was corrected in the reproduction.

### 6.1 Parts Library Audit (the 12 non-chassis parts)

Measurements re-checked [F]:

| Claim | Result |
|---|---|
| Triangle counts, mesh names, texture counts and sizes per part | All match the table in section 4. |
| "26 images, not one PNG" | 28 images, and across 13 files rather than 12: the report says "the 12 GLB parts" but its own table lists 13 rows. Both counts are off. All 28 are JPEG, so the conclusion holds. |
| Metalness PASS on the props and the mast despite an all-white map | Correct, and for the right reason: their `metallicFactor` is 0 and the factor multiplies the map. This is also the evidence that the "set `metallicFactor: 0` as a stopgap" fix works in Gazebo (the loader reads the factor and gz-rendering sets it on the datablock [S, P]). |
| Saturated metalness on `basestation_antenna`, `surveyor_multibeam`, `omniscan_450_sidescan` | Confirmed, B channel 255 with factor 1.0. |
| No degenerate triangles, unit-length normals, UVs in [0, 1], every material OPAQUE, no orphan primitives, no extensions | All confirmed by a zero-area triangle count, normal lengths and UV ranges over every primitive. |
| Dimensions | All extents re-measured and identical. Two of the "plausible" rows can be promoted to datasheet checks: the T200 body at 112.8 x 97 mm against the 113 mm by 100 mm datasheet, and the M200 propeller at 110.3 mm against the 112 mm propeller diameter on the BlueBoat product page. The rest remain plausibility checks until someone pulls the datasheets. |
| T200 files carry a 2.8 mm by −2.9 mm node translation | Confirmed. Both loaders apply it and `gltf_to_yup.py` rotates it correctly, so it is harmless; the suggestion to comment it in the macro is good. |
| Material names "consistently component names" | Mostly. `Propeller.001` and `Thruster-Prop.002` carry Blender suffixes, which matters only as hygiene since Gazebo never reads material names. |

Verdicts:

- "Normal maps without tangents, 9 of 12. Gazebo does not generate tangents." Measurement right, verdict Refuted (section 3, item 10). The exporter's Tangents checkbox is irrelevant to Gazebo and RViz.
- "Every texture is JPEG, visibly wrong for normal maps." Measurement right; policy verdict. Two nuances: Gazebo keeps only R and G of a normal map, so only artifacts in those channels matter, and Blender's exporter writes JPEG when the source image is JPEG under its default Automatic setting, so the fix may be at the texture source rather than the preset. Visibility of the blocking on our parts is unverified [U].
- "Blender default mesh names, 12 of 12." Right, and incomplete: the node names carry the same `.001` suffixes, and node names are the ones Gazebo uses (section 3, item 4). Renaming the mesh datablock alone changes nothing visible; renaming the object does.
- "Fix the export preset once (tangents on, PNG for normal maps) and re-export." Half survives: PNG for normal maps, and add the metalness fix and the object rename to the same pass.
- "Migrate the two DAE stragglers." Agreed (section 1.7, item 15).
- Headline "defects are pipeline settings, not modeling": partly. The all-white metallic-roughness maps are a texturing choice at source, present in every file, and only masked where the factor happens to be 0.

### 6.2 BlueBoat Chassis Audit

Measurements re-checked [F, P]:

| Claim | Result |
|---|---|
| 2.99 MB, 10,668 triangles, 10,455 vertices, uint16 indices, three 2048 textures, base color PNG, normal and metallic-roughness JPEG | All confirmed. |
| 1.192 x 0.925 x 0.692 m; "real hull is 1.146 m long" | Extents confirmed. The datasheet figure is not: the Blue Robotics product page gives 120 cm length, 93 cm beam and 46 cm height deployed. Length and beam match the mesh; the mesh's 0.69 m height exceeds the deployed height by 0.23 m, which needs an explanation (what the top of the chassis mesh is) before this row can pass [U]. |
| Origin at hull center, Y up, no rotation nodes | Confirmed. |
| 2 degenerate triangles, unit normals, u in [0, 0.98], v in [0, 1] | Confirmed (2 zero-area triangles; UVs within [0.001, 0.999]). |
| Metalness 1.0 on 100 percent of pixels, factor 1.0, roughness mean 0.93 | Confirmed (B 255, G 236, factor 1.0). |
| No occlusion (R = 255), no UV1 | Confirmed. |
| Normal map mean 0.50/0.50/0.96 | Confirmed (127/127/245). |
| BLEND, double-sided, cutout region 0.3 percent, 0.2 percent partial | Confirmed within rounding: 0.45 percent of texels below alpha 128, 0.21 percent strictly partial. |
| `extensionsUsed` empty | Confirmed. |

Verdicts:

- Metalness FAIL: Verified, and it is the finding that matters most. "Renders dark in Gazebo" is consistent with the probe (metalness map and factor 1.0 both reach the datablock) and awaits a visual confirmation [U].
- Transparency FAIL with the note "alpha silently ignored by Gazebo": Verified, and note this artifact states the Gazebo behavior correctly where the draft spec ("supports two of three modes") and the headline of this same artifact ("makes it render ghostly") do not. In Gazebo the hull is opaque with uncut cutouts [P]. Switching to MASK at 0.5 is the right fix and will work: the base color is a PNG with binary alpha and the material has a base color texture, which is the precondition for MASK to be read [S].
- Tangents FAIL: Refuted (section 3, item 10).
- ORM FAIL for "no occlusion, R unused": over-strict. Occlusion is optional in the draft spec's own table, and R = 255 is the valid "no occlusion" state. Downgrade to N/A unless the team wants baked occlusion.
- Normal and metallic-roughness maps as JPEG PARTIAL: policy (section 6.1).
- Names FAIL: Verified, with the node name `blueboat_chassis.visual.001` being the one to fix.
- Degenerate triangles PARTIAL: Verified; two is trivial and harmless for rendering, worth removing in the same pass.
- The headline count "10 PASS, 3 PARTIAL, 5 FAIL" does not match its own rows, which hold 9 PASS, 3 PARTIAL, 5 FAIL and one N/A across 18 requirements. Trivial in itself, but it is the kind of summary number that gets quoted. After the corrections above the tally is 9 PASS, 3 PARTIAL, 3 FAIL, 2 N/A and 1 open: tangents stop being a failure, the ORM row becomes N/A, and the real-scale row reopens pending the height question.
- Fix order proposed (metalness, MASK, tangents, PNG re-export with baked occlusion, rename, degenerates): keep 1, 2, 5, 6; drop 3; make 4 optional.

### 6.3 BlueROV2 Chassis Audit

Not seen. The measurements this document already holds for that file (section 4, and section 3 items 4 and 11) will be compared against it when it arrives.

## 7. Proposed guideline: pin the authoring stack

Sections 3 to 6 audit the draft spec and the files. This section and the two after it go the other way: guidelines the audit says we are missing, written as proposals rather than findings. This first one came out of the version work in sections 1.2 and 1.8, and it is the one with the widest reach.

### 7.1 The proposal

We already think of the runtime side as a stack whose versions move together: Ubuntu 26.04, ROS Lyrical, Gazebo Jetty. Nobody proposes running Jetty against a different ROS on a whim, because the combination is what has been tested. The authoring side has exactly the same property and none of the discipline. A `.glb` is not a neutral document; it is the output of one exporter version driven by one set of settings, and both of those are free variables today.

The proposal is to name the authoring tools as part of the same stack, declare them alongside the runtime versions, and treat a change to either as the same kind of event: something the team decides, tests and records, rather than something that arrives with a modeler's routine software update.

The current, undeclared state of that stack, read out of the delivered files and the container:

| Layer | Version in use | How it is fixed today |
|---|---|---|
| Authoring: Blender | 5.1 | Nothing. Inferred from the exporter version. |
| Authoring: `io_scene_gltf2` exporter | 5.1.20 | Nothing. Recorded in each file, checked by nobody. |
| Authoring: export settings | unknown | Nothing. Not recorded anywhere, including in the file. |
| Runtime: Ubuntu | 26.04 | The drydock image |
| Runtime: ROS | Lyrical | The drydock image |
| Runtime: Gazebo | Jetty, gz-common 7.3.0 | The drydock image, unpinned within it (section 1.2) |

The authoring row is the weaker half. Every one of the 15 delivered files was written by exporter 5.1.20, which is fortunate rather than arranged: one modeler on one machine who has not upgraded mid-project. Nothing would tell us if that changed. The first sign would be a part that renders differently, and the investigation would run through the mesh, the material and the loader before anyone thought to compare generator strings.

### 7.2 What actually varies

The case for pinning rests on whether exporter behavior really moves. It does, and the export dialog alone is enough to make the point. These are the defaults and options in the exporter our modeler is running, read from its source on the Blender 5.1 release branch:

| Setting | Default | What it does to us |
|---|---|---|
| Images | `AUTO`, described as "Save PNGs as PNGs, JPEGs as JPEGs, WebPs as WebPs. For other formats, use PNG" | Explains the all-JPEG library: the format follows the source texture, so the format is decided in the texturing tool, not at export |
| Images set to `WEBP`, or "Create WebP" enabled | off | Gazebo cannot decode WebP. The part loads untextured with a console error (section 1.7, item 1). One dropdown between a good delivery and a broken one |
| Tangents | off | The 11 normal-mapped files without tangents are simply the default, not a missed checkbox |
| Draco mesh compression | off | On, it would still load in Gazebo but defeat our own tools (section 3, item 18) |
| Vertex colors | exported when a material uses them | Silently dropped by Gazebo (section 1.4) |

Two things follow. The advice in both artifact reports to "fix the export preset" to get PNG is half right: under the default the image format is inherited from the source texture, so forcing PNG at export is one fix and re-authoring the source textures is the other, and only the second one also fixes the base color that is currently a JPEG. And "one exporter checkbox, missed on every export" is not what happened with tangents; that checkbox is off by default and always has been.

Beyond the dialog, the exporter is ordinary software under active development: the version numbering tracks Blender's own releases, and the audit already found the corresponding runtime library changing under us twice inside two point releases (section 1.2). There is no reason to expect the authoring side to be more stable than the runtime side.

### 7.3 What a version pin can and cannot do

This is the part worth being precise about, because a pin promises more than it delivers if stated loosely.

**What the file records.** Every glTF file carries an `asset.generator` string, and all 15 of ours read exactly `Khronos glTF Blender I/O v5.1.20`. That is unusually good news: unlike most toolchain pins, which are a promise in a document that nothing verifies, this one is checkable from the artifact itself, at acceptance, without asking anyone what they ran. The exporter version's first two components track the Blender release, so the string also fixes Blender to 5.1.

**What the file does not record.** The generator string names the tool and says nothing about how it was driven. Two files from exporter 5.1.20 can differ in image format, tangents, Draco, vertex colors and every other option in the dialog. Pinning the version therefore removes one source of variability and leaves the larger one untouched.

The conclusion is that a version pin has to come in a pair with outcome checks. Settings are unobservable, so the spec constrains what the settings produce, and the lint verifies that: image MIME types, `extensionsRequired` empty, no unexpected attributes. Most of those checks are already in section 2.2 for other reasons, which makes this cheap. The rule to state plainly is that the declared version is necessary and not sufficient, and that a file from the right exporter can still be wrong.

### 7.4 How it would be enforced

Three mechanisms, in order of how much they cost and how much they buy:

1. **Check the generator string at acceptance.** One line in the lint: `asset.generator` must equal the declared string. It costs nothing, it runs on every delivery, and it turns a silent tool upgrade into a message at the moment it first matters. This is the whole enforcement story for the version half of the pin, and it should go in whether or not the rest is adopted.
2. **Ship an export preset.** The exporter operator declares Blender's `PRESET` option, so the export settings can be saved as a preset file and handed to the modeler to drop into their Blender configuration, the same way we hand over any other project configuration. That converts "please set Images to PNG and leave Draco off" from a paragraph in a specification that a person has to re-read every time into a dropdown they select once. The preset belongs in the repo next to the spec.
3. **Ask the modeler to enable "Remember Export Settings".** The exporter can store its settings inside the `.blend` file, which is off by default. Turning it on makes a project's export settings travel with the project and survive the modeler's own machine being rebuilt. It only helps if we ever receive or archive `.blend` files, which is section 9.1's question.

### 7.5 The stack, as it would be declared

What we would write down, and where. The runtime rows already exist in drydock; the point is to state all of it in one place so the combination is a thing the team owns:

| Layer | Pinned to | Recorded in | Verified by |
|---|---|---|---|
| Blender | 5.1 | The asset spec, and this table | The generator string, indirectly |
| `io_scene_gltf2` | 5.1.20 | The asset spec, and this table | `asset.generator` in the lint |
| Export settings | A named preset shipped with the spec | The preset file in this repo | The outcome checks in section 2.2, not the preset itself |
| Ubuntu, ROS, Gazebo | 26.04, Lyrical, Jetty | drydock's project definition | The container build |
| assimp | 6.0.4 | Nothing today. Would be drydock's apt list | The container build |

The assimp row is the one this table was missing, and it is not covered by anything else. It is worth stating why, because the natural assumption is that it rides along with Gazebo. It does not:

- Both consumers link the same shared system library, `/usr/lib/x86_64-linux-gnu/libassimp.so.6`, rather than a private copy.
- Both express the dependency as a floor rather than a pin, `libassimp6 (>= 6.0.4+ds)`, so any newer version satisfies it.
- It is an independent Ubuntu package on Ubuntu's release schedule, not Gazebo's or ROS's.

So an assimp upgrade changes how our GLB files are parsed for Gazebo and RViz at the same moment, without a release of either, and without an entry in either project's changelog. It is the layer that actually reads the file, the layer whose type system reshapes glTF concepts on the way through, and the only layer in the chain that nobody in this project has been tracking. It also becomes more load-bearing over time, since Gazebo has decided to route its remaining formats through it.

Two caveats to set expectations. The modeler is outside our infrastructure, so this pin is a convention plus an acceptance check, not a technical constraint the way the container is; we cannot install Blender for them. And a pin is a commitment to move deliberately, not to never move: Blender 5.1 will age, the glTF exporter improves, and the point of naming the version is that upgrading becomes a decision with a re-export and a re-check behind it rather than an accident. Section 10 carries the adoption decision.

## 8. Reconciliation with the existing repo guidelines

The draft spec is not arriving into a vacuum. This repo already documents mesh conventions in `docs/design/parts.md`, an acceptance procedure in `docs/how-to/add-part.md`, two glTF entries in the FAQ, and an older and more detailed acceptance checklist in the parts README as of commit `b5daead`. A new spec that contradicts those leaves two sources of truth, so this section reads the existing guidelines against what the audit established. It is deliberately about the existing documents, not the draft.

### 8.1 `docs/design/parts.md`, the mesh conventions

| Existing text | Status | What to do |
|---|---|---|
| "Each part's visual mesh lives in `models/<part>/` as `<part>.visual.glb`, PBR materials embedded" | Holds | Keep |
| "Gazebo loads glTF directly and the ROS tools show the same file" | Holds, and is now the settled answer to the old sandbox workaround (section 1.7, item 14) | Keep |
| Collision as primitives in the macro, "never cone or plane, which URDF cannot express" | Holds, and conflicts with the draft spec's `.collision.stl` | Keep, and settle the conflict (section 10, decision 1) |
| Rule 1, the directory name is the part name | Holds | Keep, and add that the glTF node name must match it, because that is the name Gazebo exposes (section 1.7, item 4) |
| Rule 2, "Origin at the mesh centroid, x forward, y left, z up" | Ambiguous, and now demonstrably read two ways | Rewrite. The axes named are the part frame in ROS terms, but the file stores them Y-up, so a modeler reading this sentence while looking at an exported file sees a contradiction. Say both: the part frame is x forward, y left, z up, and the file therefore has forward on +X and up on +Y |
| Rule 3, "The `.glb` must be Y-up … fixed once with `gltf_to_yup.py`" | Holds | Keep. Add the reason the tool refuses rotation and matrix nodes, which is the real basis for the draft spec's "no baked rotation" rule (section 3, item 6) |
| Rule 4, "No spaces or `.001` style suffixes in any name" | Holds, and is the most-violated rule in the library: every one of the 15 files carries a `.001` suffix on its node name | Keep, and enforce it in the lint rather than in prose |
| Part naming scheme | Holds, untouched by this audit | Keep |
| "Inertia values are placeholders until measured" | Holds, outside this audit's scope | Keep |

The gap: `parts.md` says nothing about materials beyond "PBR materials embedded". Every material finding in this audit, the metalness defect included, has no home in the existing guidelines.

### 8.2 `docs/how-to/add-part.md`, the acceptance steps

The procedure holds and is the right shape. Its verification step covers the build, the probe and the review world, and the mesh instruction is one line: put a Y-up `.glb` with embedded PBR materials in the right place. What it lacks is any check that the mesh is correct, which is precisely what sections 2.5 and 2.6 provide. The change is additive: a delivery-check step before the existing steps, running the validator, the lint and the probe, on the principle the older README already stated, that there is no sense doing work on top of a delivery that is the wrong size or facing the wrong way.

### 8.3 The FAQ

Both glTF entries are accurate and worth keeping. They also read as the only place a material or orientation problem is explained to a user, which is more weight than a FAQ should carry once a spec exists.

### 8.4 The older README checklist, commit `b5daead`

This is the most detailed acceptance procedure the project has written, and most of it did not survive into the current docs. Reading it back:

- "The Gazebo check comes first because everything after it is work done on top of the delivery" is the right ordering principle and should be restated wherever the checklist ends up.
- "Anything wrong here goes back to the modeller. Do not work around it downstream" is a policy this audit repeatedly vindicates: the baked base color texture, added on our side to keep RViz alive, is a workaround we now maintain forever.
- Its "three files per part" model, with `model.sdf` from the modeler as the source of physical truth, is the direct ancestor of the collision question in section 10, decision 1.
- Its material check, "PBR renders as intended, not flat grey", is the check that would not have caught any of the defects this audit found. A metallic hull renders dark, not grey. That is the difference between a check written from intuition and one written from the loader.

### 8.5 The one contradiction to resolve first

Across `parts.md`, the older README and the draft spec, the mesh origin is stated three ways: at the centroid, at the centroid and where the part would sensibly be mounted from, and wherever the part author chooses. The macro tolerates all three, so nothing has broken yet, and that is exactly why it has drifted. It needs one sentence in one place (section 10, decision 2).

## 9. Further proposed guidelines

Topics the audit turned up that no existing document covers and the draft spec does not address. Each is a proposal, not a finding.

### 9.1 Provenance: what accompanies a delivery

Today a delivery is a `.glb`, and everything about where it came from is lost. There is no record of the source `.blend`, the texture sources, the reference the modeler worked from, or which version of a part supersedes which. The audit felt this immediately: the question "is this black albedo intentional?" has no answer available to anyone except by asking the modeler, and the question "what is the top of the BlueBoat chassis mesh?" is still open in section 6.2 for the same reason.

The proposal is a short manifest per part, in the repo next to the mesh, recording the source of the geometry, the source of the dimensions, the texture provenance, the delivery date and the exporter string. Whether we also archive the `.blend` is a separate and heavier question, bearing on whether we could ever re-export a part without the modeler.

### 9.2 The dimensional source of truth

Section 6.1 found the practical version of this problem: of eleven parts checked for dimensions, two could be compared against a published figure and nine were marked "plausible", which is not a check. Worse, the one chassis figure that was quoted precisely, a 1.146 m hull, does not match the manufacturer's published length.

The proposal is that every part declares where its dimensions come from, as a citable figure rather than a judgment: the vendor datasheet or product page, the specific dimensions taken from it, and the tolerance we hold the mesh to. That converts scale from the most expensive defect class, which the older README already identified it as, into a lint check. Where no published figure exists, saying so explicitly is also an answer, and a better one than "plausible".

### 9.3 Names are an interface, not decoration

The existing rule forbids `.001` suffixes because names become frame and topic names. The audit adds a second and stronger reason: the glTF node name is what Gazebo exposes as the submesh name, so it is the identifier an SDF `<submesh>` selects by, and it is a known-unfixed upstream behavior rather than an accident (section 1.8). Names in the file are part of the interface between the modeler and the simulation, and the guideline should say which names matter and which do not: node names are load-bearing, mesh and material names are hygiene, image names are how a reviewer tells the maps apart in a probe dump.

### 9.4 Redelivery

The parts pipeline was designed around a first delivery. What happens on the second is undocumented: which files are regenerated, which hand-authored values survive, and how a reviewer sees what changed. The older README settled part of this by committing generated files and making re-import a person's decision, which is the right instinct. The unaddressed half is the mesh: a redelivered `.glb` is an opaque binary in the diff, so the only way to see what changed is to compare probe output before and after. That argues for keeping a probe dump per part in the repo, which is a small text file that diffs meaningfully and would have made most of section 4 unnecessary.

### 9.5 Retiring the two COLLADA parts

Two parts are still `.dae`. The audit treats them as out of scope, and section 1.8 supplies the deadline the project itself has set: COLLADA deprecation is under discussion upstream in favor of glTF, and all mesh loading is moving to assimp, which changes how those files load even before they are removed. This is no longer a tidiness item.

### 9.6 What the modeler checks, and what we check

The draft spec ends with a delivery checklist aimed at the modeler, and this audit produced acceptance criteria aimed at us. They should be one flow with a clear division: the modeler validates the file (section 2.6) and confirms it looks right in the reference viewer, because those are questions about the file and its intent; we check it against the targets and the datasheet, because those are questions about our stack. Stating the split prevents the failure mode where both sides assume the other checked the thing.

## 10. Decisions the team has to make

These are not technical and the audit does not settle them.

1. Collision delivery. Existing pipeline: the modeler writes `model.sdf` with SDF primitives, `sdf_to_part.py` bootstraps the macro, primitives are the norm. Draft spec: a simplified `.collision.stl` next to the visual. Pick one, or state when each applies.
2. **Mesh origin and orientation**, the two things glTF declines to specify and we have never written down (section 1.1). Orientation: keep forward on +X, which is what authoring in the ROS frame produces and what all fifteen files do, or move to the +Z the format's own wording describes and pay for it in re-exports and an extra rotation in two code paths. Origin: the documents say centroid, the draft spec says the author's choice, and the library actually does neither. It is centered in plan and referenced to the mounting plane vertically, on all but two parts. Decide which of the three rules we mean, and note that the measured convention is probably the right one and simply undocumented. Whatever is chosen, the question a replacement mesh has to answer is what it is authored to, so the rule has to be stated in a form a second modeler could follow without asking.
3. Whether the modeler still delivers `model.sdf` at all, or only the GLB plus a filled-in datasheet row.
4. Texture format policy per map (PNG only, or JPEG for base color) and the size caps per map. Note what section 7.2 established: under the exporter's default the format is inherited from the source texture, so this decision is partly about how the textures are authored, not only about the export dialog.
5. Budgets: 25k triangles is a guess; the chassis meshes are at 11k and 22k and every accessory is below 3k.
6. Whether to keep the `BLEND` tag on translucent materials for the benefit of other viewers, given Gazebo ignores it.
7. Whether `glb_probe` and the lint become a CI test alongside the existing base color guard, and where they live.
8. Whether to pin the Gazebo library versions, and assimp with them. Nothing pins either today, the loader is under active change, and two behavioral changes already exist upstream of the installed version (sections 1.2 and 1.8). assimp is the sharper half of this: it is what actually parses our files, both consumers link the same shared copy, and both depend on it only by a lower bound, so it moves on Ubuntu's schedule with no Gazebo or RViz release involved (section 7.5). Pinning either would go in drydock's `projects/maritime/apt-packages.txt`, which is outside this repo. The alternative is to leave them floating and rely on the acceptance check to catch drift, which only works if the check is automated.
9. Whether to contribute the section 1.4 table upstream, on the open docs issue that asked for it, and whether to file an issue for the `SceneManager` material-override TODO (section 1.8). Both are small, both make the next person's version of this audit unnecessary, and neither is free.

From the proposal sections:

10. Whether to adopt the authoring stack pin (section 7), and if so at which version. Decisions 8 and 10 are the same question asked about the two ends of the pipeline, and answering them together is cheaper than answering either alone. The generator-string check is worth doing regardless of the wider answer, because it costs one line and is the only thing standing between us and a silent tool upgrade. Adopting the rest means naming the Blender version, shipping an export preset, and accepting that upgrading later is a scheduled re-export rather than a surprise.
11. Where the reconciliation in section 8 comes to rest. Either the draft spec absorbs the mesh conventions from `parts.md` and that file points at it, or `parts.md` stays authoritative for conventions and the spec covers only what a modeler needs. Both of those work. Having both documents state the rules independently is what does not, and that is the situation today.
12. Whether a delivery carries a manifest, and whether we archive the `.blend` (section 9.1). The manifest is cheap and answers questions this audit could not. The `.blend` is a real commitment: storage, licensing of any purchased textures, and an implied ability to re-export that we would then be expected to have.
13. Whether every part must cite a published dimensional figure (section 9.2), and what to do for parts where none exists. This is the one proposal that would have caught a defect the artifact reports missed.
14. Whether to commit a probe dump per part (section 9.4), so that a redelivered binary mesh produces a readable diff.
15. **Open and unresolved: what "one mesh" means, and whether a part may carry submeshes.** Flagged as pending; this review should not be closed out without it. `docs/design/parts.md` defines a part as "one mesh", and four different things could satisfy that sentence: one file, one glTF node, one glTF mesh, or one primitive. They are not interchangeable, and the delivered library already spans them. Fourteen of the fifteen files are a single node holding a single mesh with a single primitive. The BlueROV2 chassis is a single node holding a single mesh with seven primitives across six materials. What the audit already establishes, so that the discussion starts from facts rather than from the wording: a part with more than one material must have more than one primitive, because glTF has no other way to express it, so a literal one-primitive rule is a ban on multi-material parts; every primitive under one node becomes a Gazebo submesh carrying that node's name, so those seven arrive as seven identically named submeshes that an SDF `<submesh>` cannot tell apart, and that naming is a known unfixed upstream bug (sections 1.7 item 4 and 1.8); and declaring a material in SDF collapses every primitive to one material (section 1.3, step 11), so per-primitive materials survive only while nothing overrides them. The questions left are whether any part needs submesh selection from SDF at all, whether the rule should be stated on nodes rather than meshes, and what `parts.md` should say once it is settled.
16. Whether textures are embedded in the GLB, kept external, or allowed either way (section 1.1). Embedding is what every delivery does today and what the draft spec requires. It yields one artifact that cannot arrive incomplete, and it is why the acceptance tooling can read a delivery with no search path. External files version independently in git, so a texture can be re-authored and reviewed without re-exporting the geometry, and a diff names which map changed. Three things weigh against, and none is decisive: the geometry stays an opaque binary either way, so splitting the textures out only improves the texture half of the problem; external files have to be found at load time, which both consumers do by resolving relative to the mesh; and a delivery becomes able to arrive incomplete for the first time. Note also that Gazebo currently decodes external textures eagerly when the mesh loads, a performance problem with an open upstream fix (section 1.8).
17. How much version resolution to maintain (section 1.2). The answer the audit points to is patch level, because the behavior that changed during this work changed in a patch release. Anything coarser would not have caught it. This applies to assimp as much as to Gazebo, and it sets what decision 8 would have to write down if the answer there is to pin.
