# glTF Background

These are notes from my working through the glTF specification.   

Here is what I want Claude Code to do:
* I've noted questions I have with "Q: ".   Take a cut at answering the question and add the answer below the quesiton with "A (CC): " prepended.  

## References
This section is a running history of the references I've reviewed as part of these notes.


### Khronos.org

- Develops and maintains open standards for "connectinog silicon to software" - low-level APIs and file formats. 
- 150 members
- They maintain many of the specifications, including [OpenGL](https://www.khronos.org/opengl/) and [Collada](https://www.khronos.org/collada/)


### [glTF 2.0 Specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)

**The JPEG of 3D**

Q: glTF as an ISO/IEC 12113:2022 specification.  Is there any functional difference betwee the glTF 2.0 spec and the ISO version?  
A: No.   The difference is that the ISO froze in 2022.  The Khronos version is live, updates and includes the extension registry.   So cite the Khronos registry version, and cite a specific revision with it, because it moves. `model-spec.md` already says "registry revision 2.0.1"


Q: I still don't understand what an "accessor" is.  "An object describing the number and the format of data elements stored in a binary buffer."   Could you give a couple concrete examples?

A (CC): Three levels, and the accessor is the top one. A **buffer** is an undifferentiated blob of bytes. A **buffer view** is a byte range within it, offset and length, still untyped. An **accessor** says how to read that range: what the elements are, how many, and what they are made of. It is a C-style cast plus a count.

From `minimal.gltf` in this directory, small enough to check by hand:

```
accessors[0]    {bufferView: 0, componentType: 5126, type: "VEC3",   count: 4}
bufferViews[0]  {byteOffset: 0, byteLength: 48}
```
Read bytes 0-48 as 4 groups of 3 float32s. That is 4 x 3 x 4 = 48 bytes, and it is the quad's four corner positions. In C: `(float3 *)(buffer + 0)` with `n = 4`.

```
accessors[3]    {bufferView: 3, componentType: 5123, type: "SCALAR", count: 6}
bufferViews[3]  {byteOffset: 128, byteLength: 12}
```
Read bytes 128-140 as 6 uint16s. That is 6 x 2 = 12 bytes, and they are vertex indices: 6 indices, three per triangle, so two triangles.

A real part is the same shape at scale. `t200_prop_cw` has a POSITION accessor of 302 VEC3 float32s (3,624 bytes) and an index accessor of 780 uint16s, which is 260 triangles.

Why the indirection exists, since two levels would seem enough: several accessors can read one buffer view at different offsets and strides, which is how interleaved vertex data is expressed. And the accessor is where `min`/`max` live, required on POSITION, which is why a reader can get a bounding box without decoding a byte of geometry.

One asymmetry worth knowing: an embedded image names a buffer view directly and has no accessor, because a JPEG is not an array of typed elements. That is the only structural thing separating texture bytes from geometry bytes inside a GLB.

- This is the reason why our collada workflow won't work - "Complete 3D scene representation. Not restricted to single objects, glTF can represent entire scenes, including nodes, transformations, transform hierarchy, meshes, materials, cameras, and animations."

A (CC): Careful here, this reason does not hold up, though the conclusion does. COLLADA is *also* a full scene format with a node hierarchy, cameras, animations and a transform tree; scene representation is not what separates them. Two things actually broke the workflow. First, the material model: COLLADA carried a Phong/Blinn material with a diffuse texture, and glTF carries metallic-roughness PBR, where metalness defaults to 1.0 and a plastic hull nobody set renders as dark metal. Four of fifteen delivered parts have exactly that defect. Second, scope: glTF's specification covers far more than we need, so a naive reading applies rules that do not apply to us, which is the argument for a narrowing spec rather than for abandoning COLLADA.

Q: 2.4. glTF Basics.  For image files, what are the tradeoffs in jpg vs png and what are the scenarios where you would use each?

A (CC): PNG is lossless and carries alpha; JPEG is lossy and cannot. Both decode to RGBA8 on the GPU, so **the choice costs disk and transfer, never video memory** - a 2048 map occupies 16 MB decoded whichever format it arrived in. That rules out one argument only: you cannot justify JPEG as a way to fit more or larger textures into GPU memory, because it does not. It is not a claim that the choice is invisible. JPEG changes the decoded pixels, permanently, and whether that matters depends entirely on what the pixels mean - which is the subject of the table.

Where it does bite is by map type, because JPEG's 8x8 DCT blocking and chroma subsampling corrupt different data differently:

| Map | Format | Why |
|---|---|---|
| Base color | JPEG fine at high quality | Perceptual sRGB data, which is what JPEG was designed for. PNG **required** if the map carries alpha - a cutout mask through JPEG is ragged. |
| Normal | PNG | RGB encodes a direction, not a color. Subsampling mixes channels and perturbs the vectors, giving blotchy shading. Every normal map in our library is currently JPEG. |
| Metallic-roughness / ORM | PNG | Independent scalars packed per channel. Chroma subsampling blends channels that have nothing to do with each other. |
| Emissive | JPEG fine | Same argument as base color. |

Scale, from our own measurements: the one 2048 PNG base color in the library is 2,182 KB against the 2048 JPEG normal at 280 KB. PNG everywhere at 2048 is expensive on disk, which is why the rule wants to be per map type rather than blanket.

The Blender exporter inherits the format from the source image, which is why the library is 31 JPEG to 2 PNG: this is a texture-authoring decision, not an export-dialog one.

**This is review decision 4, and REP-0158 gives it an external authority we thought it lacked** - see the note at the bottom of this file. It mandates lossless PNG for normal, metallic, roughness and packed ORM, and permits JPEG only for color maps without alpha. That is the table above, arrived at independently.

Q: What would be your proposed guidelines for asset authors?   Draft a guideline, when it is obvious to use one or the other and when there might be good reasons to use either.

A (CC): Drafted below reasoning only from the glTF 2.0 specification, so that the rule stands on the format rather than on any one consumer. Quotations are from `Specification.adoc` at the registry head. Anywhere a consumer might disagree with the spec-derived rule, or where REP-0158 says something adjacent, it is called out inline as a flag rather than resolved.

Measurements are from the fifteen delivered `*.visual.glb` files, taken 2026-09-12.

**Step 0. The choice really is binary.**

Core glTF recognizes two image media types and no others. The spec gives the magic-byte table for `image/png` and `image/jpeg` only, and requires that "the image data **MUST** match the `image.mimeType` property when the latter is defined." Anything else - WebP, KTX2, Basis - exists only behind an extension (`EXT_texture_webp`, `KHR_texture_basisu`), which is a separate decision about extensions, not about texture format. So within core glTF there is nothing to choose but PNG or JPEG, and every map must be one of them.

**Step 1. The spec assigns a transfer function per texture slot, and that decides most of it.**

The governing sentence is in section 5.19: "Any colorspace information (such as ICC profiles, intents, gamma values, etc.) from PNG or JPEG images **MUST** be ignored. Effective transfer function (encoding) is defined by a glTF object that refers to the image." An image in glTF has no color space of its own. The material slot it is plugged into defines how its bytes are read, and the spec fixes that per slot:

| Slot | What the spec says it is | Transfer function |
|---|---|---|
| `baseColorTexture` | "**MUST** contain 8-bit values encoded with the sRGB opto-electronic transfer function" | sRGB |
| `emissiveTexture` | same sentence, verbatim | sRGB |
| `metallicRoughnessTexture` | "green channel contains roughness values and its blue channel contains metalness values ... **MUST** be encoded with linear transfer function and **MAY** use more than 8 bits per channel" | linear |
| `normalTexture` | "encodes XYZ components of a normal vector in tangent space as RGB values stored with linear transfer function" | linear |
| `occlusionTexture` | "The red channel of the texture encodes the occlusion value ... Other texture channels (if present) do not affect occlusion" | linear |

That split is the guideline. JPEG is a perceptual codec: it transforms RGB into YCbCr and then discards chroma resolution and high-frequency detail on the premise that the three channels are a correlated color being looked at by an eye. In the two sRGB slots that premise holds exactly - they are sRGB color, which is what JPEG was designed for. In the three linear slots it fails on its own terms. A `metallicRoughnessTexture` has no color in it at all: green and blue are two unrelated scalars and red is ignored, so a codec that averages chroma is averaging quantities the spec defines as independent. A `normalTexture` is worse, because its three channels are not even independent - they are components of one vector, and the spec adds a constraint no color has: "Normal textures **SHOULD NOT** contain blue values less than or equal to `0.5`."

A second, quieter point in the same sentences: `metallicRoughnessTexture` **MAY** use more than 8 bits per channel. Only PNG can carry that. Choosing JPEG for a linear slot forecloses a precision option the spec explicitly grants, and does so silently.

**Step 2. Alpha is a capability question, not a quality one.**

Section 5.19.6: "The alpha value is taken from the fourth component of the _base color_ for metallic-roughness material model," and under `MASK`, "If the alpha value is greater than or equal to the `alphaCutoff` value then it is rendered as fully opaque, otherwise, it is rendered as fully transparent." JPEG has no fourth component. So a base color texture that participates in `MASK` or `BLEND` must be PNG; there is no judgment in it.

The converse is also in the spec and worth stating, because it prevents a defensive habit: "Normal textures **SHOULD NOT** contain _alpha_ channel as it not used anyway." An RGBA PNG normal map is a third more bytes for a channel the spec says will be ignored.

**Step 3. A uniform map is a factor written the long way.**

The spec defines the relationship: where a map is present the factor multiplies it, and where no map is present the factor is the whole value. A map whose every texel is identical therefore has an exact, lossless expression as a factor, and carrying it as an image adds a decode, a sampler, a texture binding and a file with nothing in them.

This is not hypothetical. All seven `metallicRoughnessTexture` images in the library are a single uniform color - one unique value per channel across every texel. Six are `(255, 255, 255)` and `blueboat_chassis` is `(255, 236, 255)`, giving occlusion 1.0, roughness 0.93 to 1.0, and metalness 1.0. That is 82.9 KB spent encoding seven numbers, and it is the metalness defect recorded earlier in this file seen from the other side: the parts are not accidentally metallic, a constant-white blue channel is telling the renderer they are metal everywhere.

So the first question about a map's format is whether the map should exist. If it is uniform, delete it and set `metallicFactor`, `roughnessFactor` or `baseColorFactor`; the format question then does not arise.

**Step 4. What lossy encoding costs in the linear slots, measured.**

On `blueboat_chassis` normal at 2048, using the decoded shipped file as ground truth and restricting to the textured area because 15.4% of that map is flat background fill:

| Encoding | Size | Mean angular error | p99 | p99.9 |
|---|---|---|---|---|
| PNG | 2,322 KB | 0 | 0 | 0 |
| JPEG q95 4:4:4 | 780 KB | 0.41 deg | 2.60 deg | 6.18 deg |
| JPEG q95 4:2:0 | 501 KB | 0.66 deg | 5.60 deg | 13.90 deg |
| JPEG q90 4:2:0 | 382 KB | 0.71 deg | 5.42 deg | 13.99 deg |
| JPEG q80 4:2:0 | 294 KB | 0.82 deg | 5.29 deg | 13.23 deg |

Two readings. Chroma subsampling costs more than the quality slider - q90 at 4:4:4 beats q95 at 4:2:0 on the same content - which follows directly from step 1, since subsampling is the step that assumes the channels are chroma. And the maximum error is far above p99.9, over 100 degrees, concentrated at UV shell boundaries where ringing pulls background texels into the shell. Those are the seams a reviewer looks at first.

One thing this does *not* show, and the distinction matters. The spec says "Normal vectors **MUST** be normalized before being used in lighting equations," so a conforming client repairs the length of a damaged normal. It cannot repair the direction. Length deviation is therefore not the rendering error - but it is a free detector of lossy encoding, and by that detector our shipped maps are damaged: between 17% and 52% of textured texels are more than 1% off unit length, part by part, `t200_thruster` worst at 52%. The 8-bit quantization floor for perfectly unit normals is 0.0% by the same measure, so bit depth does not explain any of it.

Unresolved, and worth an hour with the source bakes: eight of the eleven normal maps contain texels with blue at or below 0.5, which the spec says they **SHOULD NOT**; `blueboat_antenna_mast` and `blueboat_chassis` reach blue exactly 0.0, which is not a possible tangent-space normal. A one-generation JPEG re-encode of `bluerov2_chassis` normal, whose minimum blue is 0.545, created no new violations at any quality, so the encoder is not obviously the cause and the bake is the other suspect.

**Step 5. Only now, budget.**

Re-encoding every map in the library as PNG at its current resolution takes the texture payload from 2,896 KB to 6,749 KB, a factor of 2.3. Normal maps are the entire cost: `blueboat_chassis` normal goes from 280 KB to 2,322 KB, and every other normal map runs 6x to 10x. Base color and metallic-roughness maps mostly get *smaller* as PNG, being flat content that PNG's filters handle and JPEG does not - `surveyor_multibeam` base color goes from 1.8 KB to 0.3 KB.

**Where either format is genuinely defensible.**

1. **Base color and emissive, at any size.** These are the sRGB slots; JPEG at quality 95 with 4:4:4 is the sensible default and PNG is equally defensible, often smaller, when the map is flat. Encode both and keep the smaller. The only hard constraint is alpha.
2. **A normal map on a part whose budget genuinely binds.** Reduce resolution rather than fidelity. PNG at half resolution totals 2,178 KB across the library, less than the JPEG payload shipped today. A 1024 lossless normal map and a 2048 JPEG one cost about the same bytes; the first has correct values at lower spatial frequency, the second has wrong values at high frequency, and the spec's normalization requirement does not rescue the second.
3. **Work in progress.** JPEG during iteration is fine. The rule binds at delivery, where the file becomes the interface.

Never defensible at delivery: a JPEG normal, occlusion, metallic-roughness or ORM map justified on the grounds that the artifacts are invisible. They are measurable, they concentrate at seams, and a reviewer cannot distinguish an encoding artifact from a baking error - which turns a cheap check into an expensive one.

**Proposed spec text, glTF-only.**

> Images **MUST** be `image/png` or `image/jpeg`; no texture extension is permitted.
> `baseColorTexture` and `emissiveTexture` **MAY** be JPEG, quality 95 or higher with 4:4:4 chroma subsampling, or PNG.
> `baseColorTexture` **MUST** be PNG where `alphaMode` is `MASK` or `BLEND`.
> `normalTexture`, `occlusionTexture` and `metallicRoughnessTexture` **MUST** be PNG.
> `normalTexture` images **MUST NOT** carry an alpha channel, and **SHOULD NOT** contain blue values at or below 0.5.
> A texture whose texels are all one value **MUST** be removed and expressed as the corresponding factor.
> Where a texture budget binds, reduce resolution rather than changing a linear-slot map to a lossy format.

Every clause there is checkable straight out of the GLB, which the current asset-spec row is not.

**Flags to look into later.**

> **Gazebo.** (a) [GLB_INVENTORY.md](GLB_INVENTORY.md) records that Gazebo reads none of the glTF sampler and always repeats, so `wrapS`/`wrapT`/filter settings are not a lever here; whether that also means mipmaps are generated or ignored is unchecked, and it changes how much a high-resolution map is actually worth. (b) Gazebo decodes with `stb_image`, which reads 16-bit PNG but may deliver 8 bits to the renderer - so the spec's "**MAY** use more than 8 bits per channel" permission may not survive the loader, which would remove one of the arguments above. (c) Whether Gazebo honors `occlusionTexture` at all, given that ambient occlusion in a rasterizer is optional, is unverified. (d) The project rule in `CLAUDE.md` that PBR must be declared in the SDF rather than read from the GLB cuts across this whole section: if the SDF is the material source of record, then these rules govern what the modeler delivers and a second, parallel set governs what Gazebo renders. That needs settling before the spec text above is adopted.
>
> **RViz.** Not examined. RViz loads meshes through its own resource pipeline rather than through gz-rendering, so glTF support, embedded-texture support and PBR support are all separate questions there, and a rule tuned to Gazebo may simply not apply. Worth one experiment with a delivered part before the spec claims to cover both.
>
> **REP-0158.** Its texture-format rule and the one derived here agree on the outcome - lossless PNG for normal, metallic, roughness and packed ORM; JPEG only for color maps without alpha - which is reassuring, since they were reached from different directions. Two things to check rather than assume. It mandates packed ORM, while glTF's `occlusionTexture` and `metallicRoughnessTexture` are separate slots that merely *may* share an image, so "one packed texture" is a stricter rule than the format requires and the spec text above does not impose it. And REP-0158 reasons in USD `UsdPreviewSurface` terms, where occlusion is not part of the surface at all in the same way - so its silence or emphasis on a channel should not be read as a glTF statement.

Note: 3.2. Asset - I think we should have our narrowing specicifation be specific to both version and minVersion.  We should probably be just 2.0 (no 1.0 and no 2.1 until we understand it.)

Suggested rule: `asset.version` MUST be `"2.0"`; `asset.minVersion` MUST be absent. The second half is the more useful requirement, because a stray `minVersion` from some future exporter is a load failure in a consumer that would otherwise have been fine.

3.4. Coordinate System and Units - This is a big one for later.   

Q: 3.5.1. Overview - What could this mean for our narrowing spec?   Is it clear if we want the glTF assets to contain a scene?  Or not - treated as a library of individual entities such as materials or meshes?   We aren't ready to answer that question definitively yet, but what are the things we need to know to make that decision?

A (CC): You are right that it is not answerable yet. Here is what the decision turns on, and what we already know.

What the spec permits: a glTF asset MAY contain zero scenes, in which case it is a library of entities to be used by some other means, and a viewer has nothing to show. Our library today: 14 of 15 files are one scene, one node, one mesh. `bluerov2_chassis` has two, and several files carry leftover empty scenes.

What we would need to establish, roughly in order of how cheaply it can be settled:

1. **Does anything downstream ever need to select a sub-entity out of the file?** Today, never - one file per part, and `part_visual` points at the whole file with no `<submesh>`. This only becomes live if we deliver an assembled robot in one file.
2. **What does the loader actually do** with (a) no scene, (b) two scenes, (c) a non-default scene? One afternoon with `glb_probe` settles it, and nothing else will - the Gazebo project has almost nothing written down about glTF.
3. **Does a scene-less file survive the modeler's own check?** Most viewers render nothing without a scene, which would break the Sample Viewer self-check step and the appearance gate with it. This is close to decisive.
4. **Can Blender even export one?** It exports the scene. A library file would need post-processing, so the delivery would no longer be what the modeler exported and could not be reproduced by them.
5. **What does the validator say** about zero scenes, and about unreferenced entities.

My read: require exactly one scene for v1.0 - which is checkable and rules out the leftover-empty-scene defect we already have - and revisit "library" only if the assembled-delivery question below goes that way. Note the two questions are the same question: a library file is only useful when something else composes it, and composition is the thing we have parked.


#### https://github.com/KhronosGroup/glTF-Tutorials


#### [glTF Quickstart](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/figures/gltfOverview-2.0.0d.png)


### [Video: Discussing Vulkan, Neural Rendering, SLANG, AI & More - Neil Trevett & Khronos Group Interview](https://www.youtube.com/watch?v=HLIHnG_cYkk)

- Neil Trevett: VP Developer Ecosystems, NVIDIA; President, Kronos Group

- Programming and using GPUs: 
    - Vulkan: New generation GPU API, used for AI/ML acceleration
    Q: How does Vulcan compare/contrast with CUDA?

    A (CC): They overlap only in GPU compute, and are not competitors elsewhere. Vulkan is Khronos's cross-vendor graphics *and* compute API - AMD, Intel, NVIDIA, Qualcomm, Apple via MoltenVK - and is deliberately explicit: you manage memory, synchronization and command buffers yourself, which is the price of portability. Shaders compile to SPIR-V, which is why SPIR-V and Slang appear alongside it in the interview. CUDA is NVIDIA-only and is a C++ single-source model, host and device code in one file, pitched much higher; its real moat is the library stack above it (cuBLAS, cuDNN, TensorRT), not the language. So: training and HPC go to CUDA on ecosystem grounds; compute that must run on any GPU goes to Vulkan. CUDA does no rasterization or presentation at all, so for putting pixels on screen they are not alternatives. Relevance to this project is close to zero - our stack is Ogre-Next under gz-rendering, and CI runs headless on Mesa with EGL.
    - SPIR-V: Intermediate representation for compilers.
    - Slang: Language (and compiler) - new generation shading language. Replaced glsl.

glTF
- Evolving, started as a display format (how to display ) and evolving to scene understanding
- Just added Gaussian Splats
- 

### [glTF 2.0 Quickstart and tools](https://github.com/kcoley/glTF)

- Mine this for useful stuff, but the parent repo is likely stale
- Lots of resources here.  Just links in the README. Some of the reference may be old.  For example, the "Sample Model" link points to a 

Reading 


### [OpenUSD Conventions for Simulation Asset Interoperability in Open Source Robotics](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md)

- Maybe we don't need glTF at all?

A (CC): Having read it: REP-0158 is not an argument against glTF, it is an argument for authoring so that glTF export works. It mandates `UsdPreviewSurface` as the normative surface definition *"to ensure a direct mapping to glTF 2.0's pbrMetallicRoughness workflow"*, forbids UDIMs because glTF cannot express them, and requires CCW winding to match glTF's front-face rule. glTF 2.0 is its export target, named throughout.

The two are different layers. glTF is a delivery format for one textured mesh - the JPEG of 3D, as your note above says. OpenUSD is a composition format: references, payloads, layering, variants. USD does what our xacro assembly does, not what our `.glb` does.

Status and weight: Draft, 2026-03-03, authors from Robotec.ai, NVIDIA and Ekumen, sponsored by Michael Carroll of Intrinsic, with both the ROS and **Gazebo** PMCs listed. So it is a real signal about direction, and not yet settled.

Three things in it we should act on regardless of whether we ever touch USD:

1. **It is an external authority for decision 4.** *"Lossless PNG"* is mandated for normal, metallic, roughness and packed ORM maps; JPEG is permitted only for color maps without alpha. We had concluded the budget row had no authority outside this project. On texture format, it now has one, and it agrees with the analysis above.
2. **It supports our +X forward decision.** It requires ROS convention throughout - X forward, Y left, Z up - for exactly the reason we did: the frame is the interface. Note its Z-up applies to the USD *stage*, not to a glTF file, so there is no conflict with our Y-up rule; they are different layers.
3. **Several of its rules are already ours**: unique UVs packed into [0,1], triangulated geometry, no HDR texture formats.

Where it genuinely bears on us is the question we parked - delivering a robot as one assembled asset. It is explicit that this is a composition problem: `kind="component"` for a distributable part, `kind="assembly"` for an aggregate, composed by References and Payloads, with `physics.usda` and `ros.usda` as separate layers. That is a serious answer to a problem we have not yet framed, and it is worth reading against that open question rather than against the choice of `.glb`.

One caution for later: it also says *"OpenUSD and robotics XML formats (URDF, SDF, MJCF) are fundamentally mismatched paradigms. Conversions are inherently lossy."* Our whole pipeline is xacro to URDF to SDF, so adopting USD would not be a format swap.


## Closely Related Work and Examples

Are there others with the same challenges (glTF interpretation/narrowing and workflow specification) and can we learn from them.

### Community standards, documents, discussion, etc.

#### Gazebo community and developers

Q: Gazebo is usually good about roadmaps.  To they have a roadmap that includes some details of glTF support - or any discussions online, or evidence in the code?

#### Examples

Can we identify


##### Fuel

A (CC): Surveyed the whole library on 2026-09-12 through the Fuel REST API rather than the web UI, because neither mesh format nor articulation is a searchable field there. `GET /1.0/models?per_page=100` walks all 3,371 records; `/1.0/{owner}/models/{name}/tip/files` gives each model's file tree; `/tip/files/model.sdf` gives the SDF. For the glTF assets themselves, an HTTP Range request for the first twenty bytes of a `.glb` yields the JSON chunk length, and a second range request yields the chunk - so every glTF file in Fuel can be inspected without downloading a byte of geometry. That matters here: the 54 glTF files total 534 MB, of which one model is 429 MB.

Your read is right. The sharper version is that glTF is nearly absent from Fuel, and entirely absent from the part of Fuel we would want to learn from.

Excluding the 1,033 GoogleResearch scanned objects - shoes, bottles, toys, uniformly OBJ plus MTL plus JPEG, one mesh each - leaves 2,333 models with retrievable file trees:

| Contains | models |
|---|---|
| `.dae` | 1,404 |
| `.obj` | 350 |
| `.stl` | 300 |
| `.gltf` or `.glb` | 54 |

Narrowing to things that are robots in our sense - at least one `<sensor>` or an actuation/control plugin, which catches quadrotors whose only joints spin propellers and free-flyers with thrusters and no joints at all - gives 427 models. Three of them use glTF. By upload year there were none before 2024 and exactly one per year since, against 21 to 75 COLLADA platforms per year throughout. All 33 `<actor>` skins in the library are COLLADA.

So there is no community practice for glTF robots to copy. There is no second opinion to check ours against. That is a finding rather than a dead end, since it removes "but everyone else does it this way" as an argument in either direction, but it does mean the spec is doing original work and should say so.

The three that qualify:

| Model | Container | Links | Joints | Triangles | Note |
|---|---|---|---|---|---|
| `Open-RMF/Caddy` | `.gltf` + `.bin` | 11 | 8 | 7,714 | The only single-file-plus-`<submesh>` precedent in Fuel |
| `proque/atmos` | GLB | 9 | 0 | 195,403 | Thrusters, IMU, barometer, navsat; factor-only materials |
| `proque/atmos_dual` | GLB | 13 | 4 | 1,463,312 | Mixes one GLB with four DAE meshes; absolute versioned URL as the mesh URI |

`Open-RMF/Caddy` is worth reading in full, because it is the one model in Fuel that answers question 1 in section 3.5.1 above - does anything downstream ever need to select a sub-entity out of the file. It carries the whole vehicle in `polaris.gltf` and each link picks its own part out by node name:

```xml
<mesh>
  <uri>model://Caddy/meshes/polaris.gltf</uri>
  <submesh><name>Front_Wheel_Left</name><center>true</center></submesh>
</mesh>
```

Eleven visuals, one URI, eleven `<submesh>` selections, `<center>true</center>` on every moving part so its geometry is recentered on its joint origin and `<center>false</center>` on the chassis. Three defects in it are as instructive as the pattern. The file declares an external `"uri": "Ranger_Diffuse.png"` that is not in the upload - fetching it returns 404 - so the only articulated glTF robot in Fuel renders untextured, which is a direct argument for self-contained GLB over `.gltf` plus loose files. Node names are duplicated between each parent transform node and its mesh child, so `Steering_Wheel` matches two nodes and `<submesh>` resolution is ambiguous. And a 0.0255 scale factor is baked into every node transform rather than into the mesh data.

What the other 51 glTF files tell us, all of them props, scenes or test uploads. Seven of the 54 are byte-identical re-uploads of someone else's asset, so there are 47 distinct files.

- **Container**: 53 GLB to 1 `.gltf` plus `.bin`, and the one non-GLB is the broken one.
- **Tooling**: 50 of 54 from the Blender glTF exporter, versions 3.3 through 5.1. Two from Sketchfab, one from Unity. No pipeline diversity to learn from.
- **Scope actually used**: zero animations, zero skins, zero cameras, across every file. Every primitive is mode 4. Exactly one primitive in the entire corpus carries `TANGENT`, which agrees with what `glb_probe` found about our own loader.
- **Texture format**: 5,429 JPEG images against 95 PNG. Forty-four of the 54 carry normal maps and 37 carry packed metallic-roughness maps, overwhelmingly as JPEG. This contradicts decision 4 and REP-0158 head-on. It does not overturn either - a corpus of warehouse props is not evidence about correctness - but it does say that assets delivered to us by anyone working in the normal way will arrive with JPEG normal maps, so the spec needs to state the rule and the remedy rather than assume the toolchain produces PNG.
- **The metalness default trap is live**: 128 materials across 9 models leave `metallicFactor` unset, so 1.0, with no metallic-roughness texture to override it. `dhyutin/trial` is 8 of 8; `proque/atmos` is 80 of 404. The same defect we found in four of fifteen delivered parts.
- **Extensions**: `KHR_materials_specular` in 29 models, `KHR_materials_ior` in 13, `KHR_materials_transmission` in 9, `KHR_texture_transform` in 6, `KHR_materials_unlit` in 2. Five models put `KHR_texture_transform` in `extensionsRequired` rather than `extensionsUsed`, which a spec-compliant reader must refuse to load outright. Those five are a ready-made conformance probe for what Gazebo actually does - `OpenRobotics/Distribution_Warehouse` is the convenient one.

The two assets worth keeping as reference material:

- `OpenRobotics/Forklift` - the best-authored glTF asset in Fuel. Self-contained GLB, 15,492 triangles, embedded albedo, normal and packed metalness-roughness maps, and roughly 30 hand-placed primitive colliders in the SDF against the single visual mesh. That collision discipline is worth as much as the material work. Its normal map is JPEG.
- `OpenRobotics/Ionic Mascot` - the factor-only case: 12 materials, no textures at all, explicit `metallicFactor: 0` on the non-metals. Also a counter-example on naming, with 148 nodes called `Cylinder002`, `Line001`, `Torus008`. Nothing in that file could be addressed by `<submesh>`.

One caution about reading Fuel for SDF convention rather than for assets. Across the 427 robot platforms, 67% use primitive-only collision, 64% declare `<material>` in the SDF, 30% still reference the Gazebo Classic `gazebo.material` script, and only 8% use `<submesh>` at all - the dominant pattern is one mesh file per link, as in `bosdyn_spot` with 27 separate meshes. Of the 65 platforms declaring `<pbr>` in the SDF, every one pairs it with COLLADA and none with glTF. The two material approaches in the library are cleanly separated, and nobody does both, which is the one thing worth reconciling against the "PBR must be declared in the SDF" rule in our own `CLAUDE.md`.

##### Repos

Q: What are  popular (can be measured via github analytics) projects using glTF assets in Gazebo?