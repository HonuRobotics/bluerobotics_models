# Visual model specification

Version 0.2, draft, 2026-09-16. Supersedes the earlier "Visual asset spec" draft, which is kept alongside this document as [asset-spec.md](asset-spec.md) and audited in section 3 of the review.

This specification states what a delivered visual model must be. The reasoning behind each rule, the evidence for it, and the record of what was measured and verified is kept separately in [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md). Rules live here. Rationale lives there, and in the Implementation Notes below.

Every rule in this document is in one of three states, marked inline and collected in section 13: decided, under discussion with a proposal on the table, or open with no proposal yet. Section 2.4 defines the marks.

## 1. Introduction

### 1.1 Scope

This specification constrains the visual models delivered for the parts library. It does not replace the standards it builds on. It stands in three different relationships to them, and every rule below is one of the three:

- **Narrowing.** Using less than the standard allows, because this project does not need the rest. Most of this document is narrowing.
- **Adding.** Requiring something the standard does not, because a consumer of ours needs it. These exist because Gazebo and RViz each implement only part of glTF, so a conforming file is not always a usable one. Such rules are marked as target constraints and name the consumer that motivates them.
- **Departing.** Differing from what the standard says, which is done rarely and never silently. The forward axis in section 5.3 is the only current candidate.

Anything not falling into one of those three is the standard's, and this document does not restate it.

It specifies:

- the file format, and the subset of it that may be used
- the coordinate system, units and frame of a delivered model
- geometry, material, texture and transparency requirements
- what accompanies a delivery, and how a delivery is checked

It does not specify collision geometry, mass properties, inertia, joints, slots or anything else expressed in a part's macro, beyond requiring in section 4.1 that a delivery carries the collision file. Those are defined by the part contract in [Parts](../design/parts.md).

### 1.2 Relationship to external standards

The workflow this specification serves is built on published standards owned by other people, and defines project convention only where no standard reaches. This is deliberate. A project-local convention must be taught to every modeler, defended in every review and remembered by everyone who touches the pipeline. A standard is documented by someone else, understood by people not yet hired, and supported by software nobody here has to maintain.

| Standard | Role here |
|---|---|
| glTF 2.0, Khronos, registry revision 2.0.1 | The mesh format and its material model. Normative except where this specification narrows, adds to, or departs from it, each of which is marked. The Khronos registry text is cited rather than ISO/IEC 12113:2022, which froze the same content in 2022 and does not carry the extension registry |
| REP 103, ROS | Coordinate conventions and units for the part frame |
| BCP 14 | The meaning of the requirement keywords in this document |
| [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md), ROS and Gazebo (Draft) | Asset conventions for simulation interoperability, written with glTF 2.0 as the export target. Cited below wherever a rule here matches one of its requirements |

Three obligations follow from that design goal, and this document is bound by all of them. Where this specification departs from a standard, the departure is stated explicitly and the reason given, never left as a silent local habit. Where it adds a requirement the standard does not make, the rule says which consumer needs it, so that a reader can tell a limitation of our tools from a property of the format. And where a standard is silent, this specification says so plainly rather than implying an authority that does not exist.

**Implementation Note.** Gazebo's glTF support carries no roadmap commitment, and this document does not treat it as one. The published Gazebo roadmap has no glTF, GLB, PBR or mesh-format item. The direction is on record only in project management committee minutes: [2026-08-17](https://discourse.openrobotics.org/t/gazebo-pmc-meeting-minutes-2026-08-17/57494) discusses deprecating COLLADA in favor of glTF and GLB and leaves it unresolved, and [2026-06-15](https://discourse.openrobotics.org/t/gazebo-pmc-meeting-minutes-2026-06-15/55498) decided to move mesh loading to Assimp by default. Behavior is what `MeshManager.cc` does today, which routes `gltf`, `glb` and `fbx` to the Assimp loader while `dae`, `obj` and `stl` keep their custom ones. Rules below cite that behavior as intent or as fact accordingly, never a roadmap.

**Implementation Note.** There is no community practice for glTF robots to copy, and this specification is doing original work where it goes beyond the standards above. A survey of the Gazebo Fuel library on 2026-09-12 found three robot platforms in glTF among 427, and a survey of public repositories found a cohort small enough to name, whose files break several rules stated here (JPEG normal maps, `KHR_texture_transform`, no size discipline). Both surveys are in [community-exemplars.md](community-exemplars.md). Where the field's practice and a rule here disagree, the rule says so and states the remedy, rather than assuming deliveries will arrive conforming.

### 1.3 Project-specific content (Informative)

This specification is written for the Blue Robotics parts library, but most of it is not specific to that library or to this repository. The general content is the format subset, the coordinate and frame rules, and the material, texture and transparency requirements, all of which follow from glTF and from how robotics renderers consume it. The project-specific content is confined to section 4.1, naming and delivery location, and the toolchain versions in section 11.

A future generalization would keep the former and replace the latter. Contributors should resist mixing the two.

> **Decided.** This specification, with the modeling workflow it serves, subsumes the mesh conventions in [Parts](../design/parts.md). Parts keeps the part contract, the macro, slots and frames, and points here for everything about the delivered model. Until that edit lands the two still overlap, and where they disagree this document governs; Parts rule 2 on the origin is the known case. Tracked as review decision 11.

> **Open.** Whether a modeler may deliver a compound object, a whole vehicle rather than a single part, as one glTF file with its components as separate nodes, so that the xacro, URDF and SDF assembly can be built from what the file already states. The alternative, and what the library does today, is one part per model with the assembly expressed only in the macro. Settling it needs two things: whether any of the assembly can be driven from node structure that the macro does not already state better, and the node question in section 5.5, of which a compound delivery is the larger case. It would also bring `assembly`, defined in section 3 as out of scope, partly into scope. Not yet on the review's decision list.

## 2. Document conventions

### 2.1 Audience

This specification addresses two parties:

- **the modeler**, who authors and delivers a model
- **the integrator**, who accepts a delivery and maintains the part that uses it

Requirements are imposed only on the audience of the text stating them. Where the audience is not obvious from context, it is named.

### 2.2 Normative terminology

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY and OPTIONAL are to be interpreted as described in BCP 14.

References to external documents are normative if this specification uses those keywords to refer to them or to their requirements.

### 2.3 Informative language

Some text is purely informative, giving background or explaining why a rule exists. A section whose title is suffixed "(Informative)" contains only informative language. All Notes, Implementation Notes and Examples are informative. Everything not so marked is normative.

### 2.4 Decision status

Where this specification states a requirement in normative language, the team has decided it. Three kinds of block mark everything else, so that the state of every question is visible in the text rather than discoverable only by asking:

> **Decided.** A decision taken after the first draft, with the reason in one or two sentences and where the evidence is. The rule it produced appears as normative text next to it. The block exists so a reader can see what changed and why. 

> **Discuss.** A proposal is on the table and states the rule as it would read, but the team has not agreed to it. Until it does, the proposed rule imposes no requirement. Tracked as review decision N.

> **Open.** No proposal yet. The block names what has to be settled and, where known, what would settle it. Tracked as review decision N.

The plan is to settle every Discuss item and as many Open items as possible before the first pilot of the modeling workflow, so that a modeler in the pilot works to a document whose rules are agreed. Some Open items will stay open through the pilot, because settling them all is beyond the time and budget available, and the pilot itself is expected to inform them. An item left open is a known gap, not an oversight.

A delivery cannot fail to conform on a point marked Discuss or Open. Where an interim instruction is needed while a question is open, it is stated in normative language outside the block and marked as interim.

Decision numbers refer to section 10 of [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md). Section 13 lists every block in this document with its status.

## 3. Terminology

The definitions below govern within this specification and supersede any other meaning these terms may carry elsewhere. Terms drawn from glTF keep their glTF meaning and are marked.

part::
A single physical component, geometry only, no joints. The unit this specification delivers.

model::
The visual geometry delivered for a part: the file `<part>.visual.glb` and its contents. Used in preference to "mesh" throughout, because whether a part is one glTF mesh, one node or several is undecided (section 5.5), and "mesh" would prejudge it.

mesh::
As in glTF 2.0: an array of primitives, carrying no transform of its own. Used only in that sense.

primitive::
As in glTF 2.0: the unit of a draw call, holding `attributes`, `indices`, an optional `material` and a `mode`. Carries no transform.

node::
As in glTF 2.0: an object in the node hierarchy that may carry a local transform and may instantiate a mesh.

submesh::
Not a glTF term. The unit Gazebo's loader produces from a file: one submesh per primitive, named after the node that instantiates the primitive's mesh. It is neither a node arrangement nor a second mesh, and a single mesh of four primitives becomes four submeshes. Section 6.3 states what follows from that.

scene::
As in glTF 2.0: a list of root nodes. A file may hold several scenes and names one as default; a file with none is a library of entities that a viewer cannot show.

part frame::
The coordinate frame in which a part's macro expresses its attach point, slots and frames. Defined by REP 103: x forward, y left, z up.

delivery::
The set of files handed over for one part, together with whatever accompanies them under section 4.

assembly::
Parts plus the joints between them. Out of scope here.

The word "asset" is not used in this specification. In 3D work it spans meshes, textures, rigs, scenes and library entries at every scale, and glTF itself uses it both for a whole file and for the `asset` object inside one that holds the file's metadata, so it cannot be used precisely here. See [Parts](../design/parts.md).

## 4. Delivery

### 4.1 Files

A delivery MUST include a visual model named `<part>.visual.glb`, where `<part>` is the part name.

The part name MUST be lowercase snake_case, and MUST match the directory it is delivered into. Naming rules for parts are given in [Parts](../design/parts.md) and are not repeated here.

A delivery MUST also include a `model.sdf` for the part in which collision geometry is expressed as SDF primitive shapes: box, cylinder or sphere. The content of that file, and the collision conventions it must follow, are defined by [Parts](../design/parts.md) and [Add a part](../how-to/add-part.md); `sdf_to_part.py` bootstraps the part macro from it.

At this time, this document assumes the modeler provides `model.sdf` with collisions as SDF primitives.  Extending the rule to other collision representations, mesh collision in particular, is tracked as a repository issue, "Collision delivery: extend beyond SDF primitives to mesh collision". 

> **Discuss.** Whether a delivery carries a manifest recording the source of the geometry, the source of its dimensions and the texture provenance. Proposed: yes, because it is cheap and answers questions the audit could not. Archiving the Blender source file is a separate and heavier commitment, storage, licensing of purchased textures and an implied ability to re-export, and is not proposed. Tracked as review decision 12. 

> **Discuss.** Whether every part must cite a published dimensional figure, and what to do for parts where none exists. Proposed: yes where one exists, because it is the one check that would have caught a defect the earlier audits missed. Tracked as review decision 13.

### 4.2 Format

The model MUST be glTF 2.0 in the binary container, `.glb`. The `.gltf` form, with geometry in a side `.bin` and images as separate files, MUST NOT be delivered.

**Implementation Note.** Why the binary container, in order of weight:

- gz-common 7.3.0 drops the glTF root rotation for a `.gltf` file and keeps it for a `.glb`, because it compares an already-lowercased extension against the literal `"glTF"`. A `.gltf` delivery would load into Gazebo mis-oriented and report nothing.
- Gazebo decodes external textures eagerly when the mesh loads.
- One artifact cannot arrive incomplete. A directory of six files can, and the acceptance tooling reads a `.glb` with no search path at all.
- The legibility `.gltf` would give is already available from the container: `glb_inventory.py` reports per-image size, format and texel density, and `glb_probe` reports what the loader built.

What the rule gives up: with `.gltf` the images version independently in git, which matters because textures are 59 percent of every byte stored, so re-exporting geometry to change one map is waste. Both defects above have upstream fixes that the pinned container does not yet carry, so this is worth revisiting when the container moves. Evidence in section 1.8 of [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).

The file MUST validate against the Khronos glTF Validator with zero errors. Validator warnings and infos MUST be reviewed but do not by themselves fail a delivery.

> **Open.** Whether textures are embedded in the container, delivered as external files, or either. The container decision above does not settle this: a `.glb` packs only its first buffer into the binary chunk, and an image may still carry a `uri` pointing at an external file. All deliveries to date embed, and the acceptance tooling reads a delivery with no search path. Against that, Drake refuses `.glb` outright and argues external files load faster, and JPL packages the same way for RViz, so if a model is ever consumed outside Gazebo and RViz, packaging is the first thing that breaks. Tracked as review decision 16.

**Implementation Note.** Embedding gives one artifact that cannot arrive incomplete. External files version independently, so a texture can be re-authored without re-exporting geometry. The geometry remains an opaque binary either way.

### 4.3 Asset header

`asset.version` MUST be `"2.0"`.

`asset.minVersion` MUST NOT be present.

**Implementation Note.** The second rule is the one that earns its place: a stray `minVersion` written by some future exporter is a hard load failure in a consumer that would otherwise have been fine. There is no glTF 2.1 and none is planned. The Khronos registry carries 2.0 only, currently revision 2.0.1, and states that every update to it is a backwards-compatible patch; new capability arrives as extensions rather than as minor versions.

## 5. Coordinate system, units and frame

### 5.1 Units

All linear distances MUST be in meters, at real-world scale, as glTF requires.

The Blender scene unit scale MUST be 1.0, and object scale MUST be applied before export. A file whose scale is wrong is silently wrong: nothing downstream can detect it.

### 5.2 Up axis

The model MUST be Y-up, as glTF specifies.

**Implementation Note.** This is not a stylistic preference. Every consumer converts on the assumption that glTF is Y-up. RViz rotates a glTF mesh as it loads, and the part macro applies the matching rotation for Gazebo. A Z-up file renders correctly in one and wrong in the other.

**Implementation Note.** The RViz rotation is younger and narrower than it looks. It was added by `ros2/rviz` #1482, merged to `rolling` on 2025-06-16 and deliberately not backported, so Jazzy and Kilted do not have it. These models render correctly in RViz only on distributions downstream of that merge; on Jazzy every part appears rotated ninety degrees. This is a distribution floor for consumers of the library, not a defect in the file.

> **Discuss.** Whether this specification states that distribution floor as a requirement on the integrator, and where. Proposed: state it here and in the repository README, as the oldest ROS distribution on which the models render correctly in RViz. Not yet on the review's decision list.

### 5.3 Forward axis

> **Discuss.** Whether the delivered file faces +X, which is what authoring in the part frame produces and what every current delivery does, or +Z, which is the convention stated in glTF. Proposed: +X, stated as a deliberate departure from the glTF wording, because the frame is the interface with the part macro and moving would cost a re-export of every file and an extra rotation in two code paths. Tracked as review decision 2.

[REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md) requires "the strict ROS Right-Handed convention: X-forward, Y-left, Z-up", which is external support for +X. Its Z-up is stated about the USD stage and does not bear on the Y-up rule in section 5.2. See the reference for the rest.

**Implementation Note.** glTF says "the front side of a glTF asset faces +Z", but states it about the asset as a whole rather than any individual mesh, and states it without a normative keyword. No validator checks it.

Interim rule. Until this is decided, modelers SHOULD continue to author in the part frame, which yields a file facing +X, and MUST NOT re-orient a delivery to face +Z without agreement.

### 5.4 Origin

> **Discuss.** Where a part's origin sits within its geometry. Our documents state three rules, centroid, author's choice, and centroid near a sensible mounting point, and the library follows none of them. Measured, it is centered in plan and referenced to the mounting plane vertically on all but two parts. Proposed: adopt the measured convention, stated as "centered in plan, zero on the mounting plane, with the mounting face named in the part's macro comment", because it is what makes a part sit correctly at a slot, it matches fourteen of fifteen files already, and it is checkable by measurement once the face is named. Tracked as review decision 2.

**Implementation Note.** glTF has no concept of a mesh origin, pivot or reference point. The origin is simply the zero of the coordinate space, and geometry is placed relative to it by vertex positions and node transforms. Nothing in a file can declare where the origin is meant to be, and no validator can check it, which is why the rule must be stated here and in the part macro, and verified by measurement. The measurement reads the `POSITION` accessor bounds and composes the node's local transform; accessor bounds alone are wrong for the three files carrying a node translation.

### 5.5 Scenes and nodes

The delivered file MUST contain exactly one scene, and that scene MUST list only the root node.

**Implementation Note.** A file with no scene is a library of entities that a viewer cannot show, and a file with several leaves which one renders to the client. Neither is wanted here. Several current deliveries carry leftover empty scenes and `bluerov2_chassis` carries two, which this rule catches.

The delivered file MUST contain exactly one root node, and that node MUST NOT carry a `rotation` or a `matrix` transform. Transforms MUST be applied in Blender before export.

A `translation` on the root node is permitted and is applied by both consumers.

The root node MUST be named `<part>`, with no Blender numeric suffix such as `.001` and no spaces. This is the only name in the file either consumer reads: Gazebo names each submesh after its node, never after the mesh or the material.

**Implementation Note.** The prohibition on rotation and matrix nodes is a tooling constraint, not a format one. glTF permits them and both consumers honor them. The project's `gltf_to_yup.py` refuses to convert a file containing them, because it does not conjugate rotations.

> **Open.** Whether a part may be delivered as more than one node, and what "one mesh" in [Parts](../design/parts.md) means when a part carries several primitives. Facts already established: a part with more than one material must have more than one primitive, so a one-primitive rule is a ban on multi-material parts; every primitive under one node becomes a Gazebo submesh carrying that node's name, so an SDF `<submesh>` cannot tell them apart; and an SDF `<material>` collapses every primitive to one material. What remains is whether any part needs submesh selection from SDF, whether the rule should be stated on nodes rather than meshes, and what Parts should say once settled. The mechanism behind those facts, and the proposal to rule submesh selection out, are in section 6.3. Tracked as review decision 15.

## 6. Geometry

Every primitive MUST use triangle topology.

Every primitive MUST provide `POSITION`, `NORMAL` and `TEXCOORD_0`.

Normals MUST be authored, with hard edges where the part has them. A file delivered without normals will have them generated on import, discarding the author's intent.

The model SHOULD NOT contain degenerate, zero-area triangles.

`TANGENT` is OPTIONAL and is NOT REQUIRED.

**Implementation Note.** Exporting tangents is harmless and improves portability to other viewers, and the Khronos validator emits a portability warning when a normal-mapped primitive omits them. Neither of this project's consumers reads them: the loader has no tangent channel, and the renderer generates its own from the first UV set. What matters instead is a clean UV set on normal-mapped surfaces, since that is the input to that generation. Across the 54 glTF models in Fuel, exactly one primitive carries tangents.

### 6.1 UV sets

The model MUST have exactly one UV set, `TEXCOORD_0`, with coordinates inside the range 0 to 1.

[REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md) requires the same range and adds uniqueness: "Unique UVs must be packed into the [0, 1] space". It reserves coordinates outside that range for seamless tiling with repeat wrap modes, which this document does not permit. See the reference for the rest.

A second UV set MAY be used, and then only to carry a baked ambient occlusion lightmap.

**Implementation Note.** Every texture except a lightmap is read from the first UV set. Coordinates are stored as half floats after loading, so precision degrades outside the 0 to 1 range.

### 6.2 Budgets

> **Discuss.** The triangle budget per part. The earlier draft proposed about 25,000; the current library ranges from 164 to 21,776. A single number is not defensible until each part states how much detail its role warrants, so the proposal is to record a visual requirement per part as one of a few named tiers, for example functional for the vehicles and the parts fitted to them, accessory for sensors and brackets, and scenery for items seen at distance, and then to set a triangle and texture budget per tier. Tracked as review decisions 5 and 18.

**Implementation Note.** Neither consumer imposes a triangle limit. Texture memory dominates the cost, not geometry.

### 6.3 Primitives and submeshes

**Implementation Note.** "Submesh" is a Gazebo word rather than a glTF one, and the mismatch is what makes it hard to picture. It is not a node arrangement and not a second mesh. Gazebo's loader walks the node hierarchy and emits one submesh for every primitive it meets, naming each after the node that instantiated that primitive's mesh, never after the mesh or the material. One node holding one mesh of four primitives therefore arrives as four submeshes all bearing that node's name, and two nodes arrive as the sum of their primitives, each batch carrying its own node's name. The submesh count is the primitive count; the names come from the nodes. The loader probe in section 2.1 of the review prints that list, and is the only way to see it without a renderer.

**Implementation Note.** A part has more than one primitive when it has more than one material, and in practice only then, because a primitive holds at most one `material` and glTF offers no other way to put two materials on one mesh. The specification gives one further reason, to limit the number of indices per draw call, which does not arise at these part sizes. So the primitive count of a well-formed part is its material count, and section 7 already requires every primitive to have a material.

**Implementation Note.** What follows from that. SDF can select one submesh from a file with `<mesh><submesh><name>`, and Gazebo resolves the name by returning the first submesh that matches it and then stopping. Primitives sharing a node are therefore indistinguishable: such a selection takes the first and drops the rest, with no error and no warning. Naming submeshes after their node rather than after themselves is a known upstream defect, `gz-common` pull request 659, open and unfinished since December 2024, so the collision cannot be designed around by naming things more carefully at this end. The neighboring override is in section 7: an SDF `<material>` replaces the material on every primitive with one, so per-primitive materials survive only while nothing declares one.

> **Discuss.** Whether this specification constrains primitives and rules out submesh selection. Proposed, as two rules: a primitive MUST exist only to carry a material distinct from its siblings, so that the primitive count equals the material count and nothing is split for any other reason; and a delivery MUST be usable as one whole mesh, with neither the part macro nor any world depending on `<mesh><submesh>` to select part of one. Both are free today, since nothing in the library splits a primitive gratuitously and nothing uses submesh selection, and together they keep the upstream naming defect permanently outside this project. The alternative, making selection work, needs one primitive per node and a naming rule for each, which is the multiple-node question in section 5.5. Not yet on the review's decision list.

## 7. Materials

The metallic-roughness workflow MUST be used. The specular-glossiness extension MUST NOT be used.

**Every primitive MUST have a material assigned.** A primitive without one renders as white metal, because that is the glTF default material, and there is no fallback to a neighboring material.

`metallicFactor` and the metalness channel together MUST reflect what the part is made of. Plastics, composites and painted surfaces MUST be non-metallic. Only genuinely metallic surfaces may be metallic.

**Implementation Note.** This is the most common and most damaging defect found in the current library. The glTF default for `metallicFactor` is 1.0, so a material whose metalness nobody set is fully metallic, and a metallic-roughness texture whose blue channel is white makes it metallic regardless of the factor. A plastic hull declared metallic renders dark under every light. Four of fifteen delivered files currently have this defect, and the same trap is live across Fuel.

Any material carrying a texture MUST also carry a `baseColorTexture`.

**Implementation Note.** This is a target constraint rather than a glTF rule. RViz iterates a material's texture properties and asks for the diffuse texture; on a material whose only texture is a normal map, that lookup fails and RViz terminates. The project works around existing files with a baked neutral base color, and a regression test guards against new ones.

A material property that is uniform across the surface SHOULD be delivered as a factor, not as a texture. A texture whose every texel is identical is a factor written the long way and costs a decode, a sampler and a file for nothing.

**Implementation Note.** All seven metallic-roughness textures in the current library are a single uniform color, six of them white, which is the metalness defect above seen from the other side: a constant-white blue channel tells the renderer the part is metal everywhere.

`normalTexture.scale` and `occlusionTexture.strength` MUST be 1.0. Both are ignored by this project's consumers, so a value baked into the file will not be applied.

Material names SHOULD name the component they cover, not a color. Material names are not read by either consumer and are hygiene only.

**Implementation Note.** The materials in the file are what renders. The generated part SDF declares no `<material>`, and if one were declared it would replace every embedded material with that one, so per-primitive materials survive only while nothing overrides them. This matches every glTF exemplar found outside the project, none of which declares a material in SDF.

> **Discuss.** Whether the workspace rule that PBR materials must be declared in the SDF applies to GLB parts at all. It was written for COLLADA, where the SDF is the only place a PBR material can live. For GLB it contradicts the rule above, the generated part SDF, and every glTF exemplar found. Proposed: restate the workspace rule as applying to COLLADA visuals only. Not yet on the review's decision list.

## 8. Textures

Embedded images MUST be PNG or JPEG. No other image format loads.

**Implementation Note.** KTX2, Basis and WebP are all reachable from the Blender export dialog and all fail. The part loads untextured, with an error naming an unsupported compressed image format.

Textures MUST be 2048 pixels or smaller on each side.

Any texture carrying alpha MUST be PNG.

Normal, metallic, roughness and packed ORM textures MUST be PNG, which [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md) also requires. It permits JPEG for base color and emissive only where they carry no alpha, and excludes EXR, TIFF and other high dynamic range formats from material maps. See the reference for the rest.

**Implementation Note.** The rule follows from the transfer function glTF assigns to each slot. Base color and emissive are sRGB color, which is what JPEG was designed for. Normal, metallic-roughness and occlusion are linear data whose channels are unrelated scalars or the components of one vector, and JPEG's chroma subsampling blends channels that have nothing to do with each other. Measured on the BlueBoat normal map, JPEG at quality 95 with 4:4:4 subsampling leaves a mean error of 0.4 degrees and a 99.9th percentile above 6 degrees, concentrated at UV shell boundaries.

**Implementation Note.** Deliveries from anyone working in the normal way will arrive with JPEG normal maps: every normal map in the current library is JPEG, as are most in Fuel and in the Gazebo team's own demo assets. The Blender exporter inherits the format of the source image, so this is a texture-authoring decision, not an export setting. A JPEG normal map cannot be repaired by converting it to PNG, because the damage is already in the pixels; the remedy is to re-export from the source texture.

> **Discuss.** Whether base color and emissive textures may be JPEG, and the size cap per map type. Proposed: PNG by default for every map. JPEG is permitted for `baseColorTexture` and `emissiveTexture` only when all four hold: the material is `OPAQUE`, so no alpha is needed; the encoder is set to libjpeg quality 95 or better with 4:4:4 chroma subsampling, not a default; the JPEG is actually smaller than the PNG, which for flat maps it often is not; and the image is plugged into no other slot. Every JPEG in the current library is quality 75 at 4:2:0 and fails the second condition. For size, roughness and metalness maps SHOULD be smaller than the base color map, because they receive no mipmaps and shimmer at distance. Tracked as review decision 4.

**Implementation Note.** Base color and emissive are treated as sRGB; every other map is linear. 16-bit images are converted to 8 bits on upload and buy nothing. PNG and JPEG both decode to the same size in video memory, so the choice costs disk and transfer, never GPU memory.

A base color texture on an `OPAQUE` material SHOULD NOT carry an alpha channel. glTF ignores the channel on an opaque material, and a reader of the file cannot tell whether it was meant.

Occlusion, roughness and metalness MAY be packed into a single texture, with occlusion in red, roughness in green and metalness in blue, as glTF specifies.

Image names SHOULD identify what the map is, for example `Albedo-<component>` and `Normal-<component>`. This is the only signal a reviewer has for telling maps apart in a delivery.

## 9. Transparency

Transparency MUST be planned per material and MUST NOT be painted per pixel as a gradient.

For cutouts such as vents, perforations and mesh guards, the material MUST use `alphaMode: MASK` with `alphaCutoff` 0.5 and binary alpha in a PNG base color texture.

An opaque part MUST NOT be tagged `alphaMode: BLEND`.

**Implementation Note.** A base color texture needs an alpha channel in exactly one case: the opacity varies across the surface of one material, which is the cutout case above. Uniform translucency is a factor, not a channel. The BlueBoat chassis is a cutout region wearing the wrong clothes: 0.56 percent of its map is non-opaque and the whole hull is tagged `BLEND` for it, where `MASK` at cutoff 0.5 loses nothing.

> **Discuss.** How uniform translucency, such as an acrylic tube, is expressed, and whether `BLEND` is used at all given that this project's primary consumer ignores it. Proposed: give each translucent region its own material with the opacity in `baseColorFactor` alpha and the texture RGB only. Whether that material is tagged `BLEND` for the benefit of other viewers, or left `OPAQUE` so the file reads the same everywhere, is the part still to agree. Tracked as review decision 6.

**Implementation Note.** Gazebo honors `MASK` and ignores `BLEND` entirely, rendering the material opaque. Uniform opacity reaches it instead through the alpha of `baseColorFactor`, on any alpha mode, and is applied twice, so an alpha of 0.5 renders at about 0.25. `doubleSided` is honored only on a `MASK` material; every other surface is back-face culled, so thin geometry needs thickness.

## 10. Prohibited content

A delivered file MUST NOT contain:

- a non-empty `extensionsRequired` array
- animations, skins, cameras or lights
- Draco mesh compression
- KTX2 or Basis textures
- the `KHR_texture_transform` extension

**Implementation Note.** These are prohibited for different reasons, and the reasons matter if one is ever reconsidered. Draco decodes correctly in both consumers but defeats the project's own inspection tools. Texture transform is parsed and then ignored, so textures render in the wrong place. Animations are imported and force the bounding box to a unit cube, breaking culling. Cameras and lights are ignored harmlessly. An empty `extensionsRequired` is the single check that covers the general case. The Gazebo team's own demo assets declare `KHR_texture_transform` and `KHR_materials_specular`, so files from that workflow will fail this section and need re-export.

## 11. Authoring toolchain

> **Discuss.** Whether the Blender and exporter versions are pinned as part of the project's version stack, and at which version. Proposed, from section 7 of the review: Blender 5.1 with `io_scene_gltf2` 5.1.20, an export preset shipped with this specification, and assimp 6.0.4 pinned in drydock alongside the Gazebo libraries, with versions tracked at patch level because the behavior that changed during the audit changed in a patch release. The modeler is outside our infrastructure, so the authoring half is a convention plus an acceptance check, not a technical constraint. Tracked as review decisions 8, 10 and 17.

Interim rule. Until that is decided, a delivery MUST record the exporter that produced it, which glTF does automatically in `asset.generator`, and the integrator SHOULD check it against previous deliveries.

**Implementation Note.** Every current delivery reports `Khronos glTF Blender I/O v5.1.20`, which corresponds to Blender 5.1. The generator string records the tool but not the settings, so two files from the same exporter can still differ in image format, tangents and compression. A version pin is therefore necessary but not sufficient, and the checks in section 12 constrain the outcome rather than the settings.

## 12. Conformance

A delivery conforms when all of the following hold. The first two are the modeler's responsibility, the third and fourth the integrator's.

1. **Valid.** Zero errors from the Khronos glTF Validator.
2. **Intended.** The model renders as the modeler intended in a conformant viewer. The Khronos glTF Sample Viewer is the reference. Blender's viewport is not, because it shows Blender's materials rather than the exported file.
3. **Compliant.** Every MUST in this specification is satisfied, checked mechanically where possible.
4. **Usable.** The part renders correctly in Gazebo and loads in RViz.

**Implementation Note.** These are four different questions and they fail independently. A file can be valid and not what the modeler meant. It can be both and still render wrong in Gazebo, which implements a subset of glTF and is actively changing. Passing in Gazebo is necessary and never sufficient, because a defect can be masked by something Gazebo ignores. External viewers such as Babylon and F3D are not a Gazebo proxy either; `glb_probe`, which prints what the loader built, is.

### 12.1 Checks (Informative)

The mechanical checks implied by this specification, and where they are described, are collected in the review document: file-level lint in section 2.2, the loader probe in section 2.1, the validator in section 2.6, the render checks in section 2.3, and the pass or fail table in section 2.5.

> **Discuss.** Whether the probe and the lint become a CI test alongside the existing base color guard, and where they live. Proposed: yes, because a floating assimp and Gazebo version can only be tolerated if the acceptance check is automated. Tracked as review decision 7.

> **Discuss.** Whether to commit a probe dump per part, so that a redelivered binary mesh produces a readable diff. Tracked as review decision 14.

## 13. Decision status (Informative)

Every Decided, Discuss and Open block in this document, in order:

| Section | Question | Status | Decision |
|---|---|---|---|
| 1.3 | This document subsumes the mesh conventions in Parts | Decided | 11 |
| 1.3 | Compound object delivered as one glTF assembly | Open | none yet |
| 4.1 | Collision geometry and `model.sdf` in a delivery | Decided | 1, 3 |
| 4.1 | Delivery manifest; Blender source archival | Discuss | 12 |
| 4.1 | Cited dimensional source per part | Discuss | 13 |
| 4.2 | Textures embedded or external | Open | 16 |
| 5.2 | Stating the RViz distribution floor | Discuss | none yet |
| 5.3 | Forward axis +X | Discuss | 2 |
| 5.4 | Origin placement | Discuss | 2 |
| 5.5 | Multiple nodes, and what "one mesh" means | Open | 15 |
| 6.2 | Triangle budget, by visual requirement tier | Discuss | 5, 18 |
| 6.3 | Primitive count, and ruling out submesh selection | Discuss | none yet |
| 7 | PBR-in-SDF workspace rule for GLB parts | Discuss | none yet |
| 8 | Base color format and per-map size caps | Discuss | 4 |
| 9 | Uniform translucency and use of BLEND | Discuss | 6 |
| 11 | Toolchain version pin | Discuss | 8, 10, 17 |
| 12.1 | Probe and lint in CI | Discuss | 7 |
| 12.1 | Committed probe dump per part | Discuss | 14 |

Decision numbers refer to section 10 of [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md). Review decision 9, contributing the loader table upstream, is not a rule of this specification and is not listed. Items marked "none yet" were raised in the glTF reading notes after the review's list was written and should be added to it.
