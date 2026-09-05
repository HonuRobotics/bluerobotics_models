# Visual model specification

Version 0.1, draft. Supersedes the earlier "Visual asset spec" draft, which is kept alongside this document as [asset-spec.md](asset-spec.md) and audited in section 3 of the review.

This specification states what a delivered visual model must be. The reasoning behind each rule, the evidence for it, and the record of what was measured and verified is kept separately in [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md). Rules live here. Rationale lives there, and in the Implementation Notes below.

## 1. Introduction

### 1.1 Scope

This specification constrains the visual models delivered for the parts library. It does not replace the standards it builds on. It selects a subset of them, and adds project requirements only where those standards are silent.

It specifies:

- the file format, and the subset of it that may be used
- the coordinate system, units and frame of a delivered model
- geometry, material, texture and transparency requirements
- what accompanies a delivery, and how a delivery is checked

It does not specify collision geometry, mass properties, inertia, joints, slots or anything else expressed in a part's macro. Those are defined by the part contract in [Parts](../design/parts.md).

### 1.2 Relationship to external standards

The workflow this specification serves is built on published standards owned by other people, and defines project convention only where no standard reaches. This is deliberate. A project-local convention must be taught to every modeler, defended in every review and remembered by everyone who touches the pipeline. A standard is documented by someone else, understood by people not yet hired, and supported by software nobody here has to maintain.

| Standard | Role here |
|---|---|
| glTF 2.0, Khronos | The mesh format and its material model. Normative except where this specification narrows it |
| REP 103, ROS | Coordinate conventions and units for the part frame |
| BCP 14 | The meaning of the requirement keywords in this document |

Two obligations follow from that design goal, and this document is bound by both. Where this specification departs from a standard, the departure is stated explicitly and the reason given, never left as a silent local habit. Where a standard is silent, this specification says so plainly rather than implying an authority that does not exist.

### 1.3 Project-specific content (Informative)

This specification is written for the Blue Robotics parts library, but most of it is not specific to that library or to this repository. The general content is the format subset, the coordinate and frame rules, and the material, texture and transparency requirements, all of which follow from glTF and from how robotics renderers consume it. The project-specific content is confined to section 3, naming, section 4.1, delivery location, and the toolchain versions in section 9.

A future generalization would keep the former and replace the latter. Contributors should resist mixing the two.

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

### 2.4 Undecided items

Where this specification states a requirement, the team has decided it. Where a question is open, the document says so in an Undecided block naming the decision that would settle it:

> **Undecided.** What the question is, and what has to be settled. Tracked as review decision N.

An Undecided block imposes no requirement. It is included rather than omitted so that the holes in this specification are visible to the people affected by them, instead of being discoverable only by asking. A delivery cannot fail to conform on an undecided point.

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

part frame::
The coordinate frame in which a part's macro expresses its attach point, slots and frames. Defined by REP 103: x forward, y left, z up.

delivery::
The set of files handed over for one part, together with whatever accompanies them under section 4.

assembly::
Parts plus the joints between them. Out of scope here.

The word "asset" is not used in this specification. In 3D work it spans meshes, textures, rigs, scenes and library entries at every scale, and glTF itself uses it for the block describing an entire file, so it cannot be used precisely here. See [Parts](../design/parts.md).

## 4. Delivery

### 4.1 Files

A delivery MUST include a visual model named `<part>.visual.glb`, where `<part>` is the part name.

The part name MUST be lowercase snake_case, and MUST match the directory it is delivered into. Naming rules for parts are given in [Parts](../design/parts.md) and are not repeated here.

> **Undecided.** Whether a delivery also includes collision geometry from the modeler, as an SDF of primitive shapes as the current pipeline expects, or as a simplified STL as the earlier draft proposed. Tracked as review decision 1.

> **Undecided.** Whether a delivery carries a manifest recording the source of the geometry, the source of its dimensions and the texture provenance, and whether the Blender source file is archived. Tracked as review decision 12.

### 4.2 Format

The model MUST be glTF 2.0 in the binary container, `.glb`.

The file MUST validate against the Khronos glTF Validator with zero errors. Validator warnings and infos MUST be reviewed but do not by themselves fail a delivery.

> **Undecided.** Whether textures are embedded in the container, delivered as external files, or either. All deliveries to date embed. Tracked as review decision 16.

**Implementation Note.** Embedding gives one artifact that cannot arrive incomplete. External files version independently, so a texture can be re-authored without re-exporting geometry. The geometry remains an opaque binary either way.

## 5. Coordinate system, units and frame

### 5.1 Units

All linear distances MUST be in meters, at real-world scale, as glTF requires.

The Blender scene unit scale MUST be 1.0, and object scale MUST be applied before export. A file whose scale is wrong is silently wrong: nothing downstream can detect it.

### 5.2 Up axis

The model MUST be Y-up, as glTF specifies.

**Implementation Note.** This is not a stylistic preference. Every consumer converts on the assumption that glTF is Y-up. RViz rotates a glTF mesh as it loads, and the part macro applies the matching rotation for Gazebo. A Z-up file renders correctly in one and wrong in the other.

### 5.3 Forward axis

> **Undecided.** Whether the delivered file faces +X, which is what authoring in the part frame produces and what every current delivery does, or +Z, which is the convention stated in glTF. Tracked as review decision 2.

**Implementation Note.** glTF says "the front side of a glTF asset faces +Z", but states it about the asset as a whole rather than any individual mesh, and states it without a normative keyword. No validator checks it. Until this is decided, modelers SHOULD continue to author in the part frame, which yields a file facing +X, and MUST NOT re-orient a delivery to face +Z without agreement.

### 5.4 Origin

> **Undecided.** Where a part's origin sits within its geometry. The current library is centered in plan and referenced to the mounting plane vertically on all but two parts, which matches none of the three rules our documents state. Tracked as review decision 2.

**Implementation Note.** glTF has no concept of a mesh origin, pivot or reference point. The origin is simply the zero of the coordinate space, and geometry is placed relative to it by vertex positions and node transforms. Nothing in a file can declare where the origin is meant to be, and no validator can check it, which is why the rule must be stated here and in the part macro, and verified by measurement.

### 5.5 Node transforms

The delivered file MUST contain exactly one root node, and that node MUST NOT carry a `rotation` or a `matrix` transform. Transforms MUST be applied in Blender before export.

A `translation` on the root node is permitted and is applied by both consumers.

**Implementation Note.** The prohibition on rotation and matrix nodes is a tooling constraint, not a format one. glTF permits them and both consumers honor them. The project's `gltf_to_yup.py` refuses to convert a file containing them, because it does not conjugate rotations.

> **Undecided.** Whether a part may be delivered as more than one node, and what "one mesh" means when a part carries several primitives. Tracked as review decision 15.

## 6. Geometry

Every primitive MUST use triangle topology.

Every primitive MUST provide `POSITION`, `NORMAL` and `TEXCOORD_0`.

Normals MUST be authored, with hard edges where the part has them. A file delivered without normals will have them generated on import, discarding the author's intent.

The model SHOULD NOT contain degenerate, zero-area triangles.

`TANGENT` is OPTIONAL and is NOT REQUIRED.

**Implementation Note.** Exporting tangents is harmless and improves portability to other viewers, and the Khronos validator emits a portability warning when a normal-mapped primitive omits them. Neither of this project's consumers reads them: the loader has no tangent channel, and the renderer generates its own from the first UV set. What matters instead is a clean UV set on normal-mapped surfaces, since that is the input to that generation.

### 6.1 UV sets

The model MUST have exactly one UV set, `TEXCOORD_0`, with coordinates inside the range 0 to 1.

A second UV set MAY be used, and then only to carry a baked ambient occlusion lightmap.

**Implementation Note.** Every texture except a lightmap is read from the first UV set. Coordinates are stored as half floats after loading, so precision degrades outside the 0 to 1 range.

### 6.2 Budgets

> **Undecided.** The triangle budget per part. The earlier draft proposed about 25,000. The current library ranges from 164 to 21,776. Tracked as review decision 5.

**Implementation Note.** Neither consumer imposes a triangle limit. Texture memory dominates the cost, not geometry.

## 7. Materials

The metallic-roughness workflow MUST be used. The specular-glossiness extension MUST NOT be used.

**Every primitive MUST have a material assigned.** A primitive without one renders as white metal, because that is the glTF default material, and there is no fallback to a neighboring material.

`metallicFactor` and the metalness channel together MUST reflect what the part is made of. Plastics, composites and painted surfaces MUST be non-metallic. Only genuinely metallic surfaces may be metallic.

**Implementation Note.** This is the most common and most damaging defect found in the current library. The glTF default for `metallicFactor` is 1.0, so a material whose metalness nobody set is fully metallic, and a metallic-roughness texture whose blue channel is white makes it metallic regardless of the factor. A plastic hull declared metallic renders dark under every light. Four of fifteen delivered files currently have this defect.

Any material carrying a texture MUST also carry a `baseColorTexture`.

**Implementation Note.** This is a target constraint rather than a glTF rule. RViz iterates a material's texture properties and asks for the diffuse texture; on a material whose only texture is a normal map, that lookup fails and RViz terminates. The project works around existing files with a baked neutral base color, and a regression test guards against new ones.

`normalTexture.scale` and `occlusionTexture.strength` MUST be 1.0. Both are ignored by this project's consumers, so a value baked into the file will not be applied.

Material names SHOULD name the component they cover, not a color. Material names are not read by either consumer and are hygiene only.

## 8. Textures

Embedded images MUST be PNG or JPEG. No other image format loads.

**Implementation Note.** KTX2, Basis and WebP are all reachable from the Blender export dialog and all fail. The part loads untextured, with an error naming an unsupported compressed image format.

Textures MUST be 2048 pixels or smaller on each side.

Any texture carrying alpha MUST be PNG.

> **Undecided.** Whether base color textures may be JPEG, and the size cap per map type. Every current delivery is JPEG, because the Blender exporter's default inherits the format of the source image. Tracked as review decision 4.

**Implementation Note.** Roughness and metalness maps receive no mipmaps, so large ones shimmer at distance and SHOULD be smaller than the base color map. Base color and emissive are treated as sRGB; every other map is linear. 16-bit images are converted to 8 bits on upload and buy nothing.

Occlusion, roughness and metalness MAY be packed into a single texture, with occlusion in red, roughness in green and metalness in blue, as glTF specifies.

Image names SHOULD identify what the map is, for example `Albedo-<component>` and `Normal-<component>`. This is the only signal a reviewer has for telling maps apart in a delivery.

## 9. Transparency

Transparency MUST be planned per material and MUST NOT be painted per pixel as a gradient.

For cutouts such as vents, perforations and mesh guards, the material MUST use `alphaMode: MASK` with `alphaCutoff` 0.5 and binary alpha in a PNG base color texture.

An opaque part MUST NOT be tagged `alphaMode: BLEND`.

> **Undecided.** How uniform translucency, such as an acrylic tube, is expressed, and whether `BLEND` is used at all given that this project's primary consumer ignores it. Tracked as review decision 6.

**Implementation Note.** Gazebo honors `MASK` and ignores `BLEND` entirely, rendering the material opaque. Uniform opacity reaches it instead through the alpha of `baseColorFactor`, on any alpha mode, and is applied twice, so an alpha of 0.5 renders at about 0.25. `doubleSided` is honored only on a `MASK` material; every other surface is back-face culled, so thin geometry needs thickness.

## 10. Prohibited content

A delivered file MUST NOT contain:

- a non-empty `extensionsRequired` array
- animations, skins, cameras or lights
- Draco mesh compression
- KTX2 or Basis textures
- the `KHR_texture_transform` extension

**Implementation Note.** These are prohibited for different reasons, and the reasons matter if one is ever reconsidered. Draco decodes correctly in both consumers but defeats the project's own inspection tools. Texture transform is parsed and then ignored, so textures render in the wrong place. Animations are imported and force the bounding box to a unit cube, breaking culling. Cameras and lights are ignored harmlessly. An empty `extensionsRequired` is the single check that covers the general case.

## 11. Authoring toolchain

> **Undecided.** Whether the Blender and exporter versions are pinned as part of the project's version stack, and at which version. Tracked as review decision 10.

Until that is decided, a delivery MUST record the exporter that produced it, which glTF does automatically in `asset.generator`, and the integrator SHOULD check it against previous deliveries.

**Implementation Note.** Every current delivery reports `Khronos glTF Blender I/O v5.1.20`, which corresponds to Blender 5.1. The generator string records the tool but not the settings, so two files from the same exporter can still differ in image format, tangents and compression. A version pin is therefore necessary but not sufficient, and the checks in section 12 constrain the outcome rather than the settings.

## 12. Conformance

A delivery conforms when all of the following hold. The first two are the modeler's responsibility, the third and fourth the integrator's.

1. **Valid.** Zero errors from the Khronos glTF Validator.
2. **Intended.** The model renders as the modeler intended in a conformant viewer. The Khronos glTF Sample Viewer is the reference. Blender's viewport is not, because it shows Blender's materials rather than the exported file.
3. **Compliant.** Every MUST in this specification is satisfied, checked mechanically where possible.
4. **Usable.** The part renders correctly in Gazebo and loads in RViz.

**Implementation Note.** These are four different questions and they fail independently. A file can be valid and not what the modeler meant. It can be both and still render wrong in Gazebo, which implements a subset of glTF and is actively changing. Passing in Gazebo is necessary and never sufficient, because a defect can be masked by something Gazebo ignores.

### 12.1 Checks (Informative)

The mechanical checks implied by this specification, and where they are described, are collected in the review document: file-level lint in section 2.2, the loader probe in section 2.1, the validator in section 2.6, and the render checks in section 2.3.

## 13. Open items (Informative)

Every Undecided block in this document, in order:

| Section | Question | Decision |
|---|---|---|
| 4.1 | Collision geometry in a delivery | 1 |
| 4.1 | Delivery manifest and Blender source archival | 12 |
| 4.2 | Textures embedded or external | 16 |
| 5.3 | Forward axis | 2 |
| 5.4 | Origin placement | 2 |
| 5.5 | Multiple nodes, and what "one mesh" means | 15 |
| 6.2 | Triangle budget | 5 |
| 8 | Base color format and per-map size caps | 4 |
| 9 | Uniform translucency and use of BLEND | 6 |
| 11 | Toolchain version pin | 10 |

Decision numbers refer to section 10 of [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).
