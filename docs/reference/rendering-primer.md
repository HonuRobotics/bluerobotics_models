# Describing a surface: the empirical way and the physically based way

For an engineer who does not work in graphics. It compares the older way a 3D part carried its appearance, an empirical reflection model with a single image, against the physically based way that glTF uses. It covers what each stores, what each asks the author to decide, how the numbers are encoded, and how to read a file of either kind.

It is deliberately general. Nothing here is specific to this project's parts, tools or conventions; those live in [model-spec.md](model-spec.md) and [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).

**Terminology.** This document keeps four words apart that are commonly run together, and never uses "shading model", which is ambiguous between two of them.

**Status: outline with subsections.** Section headings carry one line on what they do; notes in italic say what a subsection will establish and will be replaced. Plain text under a heading is content already agreed and is kept.

## 1. The terms this document keeps apart

Three independent choices, one classification of the first of them, and two things commonly mistaken for one of the three. Most confusion in this area comes from running them together.

### 1.1 Reflection model: what is computed at a single point on a surface
*The equation taking an incoming light direction and an outgoing view direction and returning how much light leaves. The frmal name for a reflection model is BRDF, bidirectional reflectance distribution function: a function rather than stored data, bidirectional for the two directions it takes, reflectance for the fraction it returns, distribution because the answer varies with direction. A mirror concentrates it into a narrow lobe; matte paint spreads it almost evenly. This document never calls these shading models, since that phrase also names something else (1.3).*


#### 1.1.1 Empirical reflection models
*Everything else. Not a designed family with shared traits, which is why the group has no positive definition. Phong and Blinn-Phong are the members that matter here: cheap, tuned until the result looked acceptable, and capable of reflecting more light than arrives. Detailed in section 2.*
% CLAUDE: Again, if there are not others, say that.  If there are many others, but we can ignore them say that.  Mentioning just two and leaving the rest ambiguous is - well - ambiguous.  

#### 1.1.2 Physically based reflection models
*Cook-Torrance and the microfacet family, Oren-Nayar, and Lambert. Detailed in section 2.*

Lambert's membership is the surprise. It predates the physically based movement by decades and is diffuse-only, % CLAUDE: Diffuse-only is confusing, because you don't say the other half.   Other PBR is not diffuse-only?  What else is contained.  
% CLAUDE: Double check this.  Does the rendering community consider Lambert as a PBR approach?
so it reads as old-fashioned, but the test is about the maths, not the era: it conserves energy and is reciprocal, so it passes. It is not an alternative to the microfacet models but a component of them, supplying the diffuse term inside glTF's own material.

### 1.2 Parameterization: how an author supplies values to the model
*For physically based reflection models only.  Metallic-roughness and specular-glossiness are parameterizations They feed the same underlying maths in different currencies.* % CLAUDE: Different currencies?  BS and revice.  

*Why only physically based models have this layer. An empirical model has none because the values the author supplies, diffuse color, specular color, shininess, are the variables that appear in its equation, with nothing in between. A physically based model's equation runs on different variables: the reflectance at normal incidence and the spread of microfacet normals, among others. The author does not supply those directly. Metallic-roughness is the rule for deriving them from base color, metallic and roughness; specular-glossiness derives the same variables from a different set of inputs. That derivation is the parameterization, and it is the layer an empirical model does not have.*% CLAUDE: Are there other parameterizations?

### 1.3 Shading interpolation, and why it is not one of these questions
*Flat, Gouraud and per-pixel interpolation decide where the reflection model gets evaluated across a triangle. Named once because "Phong" labels both an interpolation scheme and a reflection model, and the two are unrelated. It belongs to the renderer, appears in no file format here, and is settled: per-pixel won. Set aside after this subsection.* % CLAUDE: Not sure what is going on here.  How is this related.  Can we mix and match shading interpolation method wtih reflextion models and parameterization?  

### 1.4 Hard and soft edges are geometry, not interpolation
*The one thing that looks like an interpolation choice and is not. A hard edge exists because two faces do not share vertices, each carrying its own normal. The author controls it, it is stored in the file, and it is why vertex counts exceed corner counts.* % CLAUDE: Don't understand how this relates or why it is here?

### 1.5 Format: which file carries the result
*The third independent choice, and cross-cutting on the other two. % CLAUDE: I count 4 choices 1.1--1.4.
A format can carry one reflection model, several, or none, and can support one parameterization or more than one. Compared in section 4.* 

### 1.6 Where glTF's own wording differs from this document's
*Disclosure of one usage issue. The glTF specification % CLAUDE: Link to the URL for the spec
says "metallic-roughness material model" for what this document calls a parameterization. Reading the specification alongside this text, that phrase is the thing defined in 1.2.*
% CLAUDE: So is "material model" a common phrase?  Should we map it to the terms above?

## 2. The reflection models in common use

% CLAUDE: Separate into Empirical and Physically based categories.  
Each model in the two categories named in 1.1, treated individually.

*Each model gets its character, its cost, where it is the right choice, and what it cannot represent, with links to references and to illustrations of the reflection lobe.*

### 2.1 Lambert
### 2.2 Phong
### 2.3 Blinn-Phong
### 2.4 Cook-Torrance, and the microfacet idea
*Where roughness stops being a dial. It sets how widely the microfacet normals scatter, which sets the width of the reflection lobe.*

### 2.5 The interchangeable terms inside a microfacet model % CLAUDE: Is microfacet specific to 2.4 only?  If so, should these be subsubsections under 2.4?
*Distribution, geometry and Fresnel, each with competing choices: GGX also written Trowbridge-Reitz, Smith, Schlick. glTF fixes one of each.*

### 2.6 Oren-Nayar, and other physically based diffuse models
### 2.7 Where the boundary is soft
*Normalized Blinn-Phong conserves energy and so sits on the line. The predicate is real but the boundary has cases on it.*

### 2.8 Side by side: cost, and what each cannot represent

## 3. Parameterizations

Only relevant to physically based models, and the layer where two tools % CLAUDE: what do you mean tools - renderers? 
most often disagree while both claiming to support PBR.

### 3.1 Why a separate parameterization exists at all
### 3.2 Metallic-roughness
### 3.3 Specular-glossiness, and why it was retired
### 3.4 Disney principled, the common ancestor of both

## 4. Which formats carry which

The cross-cutting table, and the distinction between formats that hold geometry and formats that reference it.

### 4.1 Formats that carry geometry
*Table placeholder. glTF: metallic-roughness only in core, unlit by extension, no Phong. COLLADA: constant, Lambert, Phong, Blinn as named elements in `profile_COMMON`. OBJ and MTL: the Phong family, plus metallic-roughness through an unofficial extension. FBX: Lambert and Phong, PBR only through non-standard blocks, and proprietary so what readers implement is the practical answer. STL: no material at all. USD: metallic-roughness and a specular workflow in one model. MaterialX: any of them, since it describes shading networks and ships glTF's and USD's as nodes.*

### 4.2 Formats that reference geometry rather than carrying it
*SDF and URDF, a different role: they name a mesh file and may override its material. SDF carries the Phong family, metallic-roughness and specular-glossiness, so it is more expressive on paper than glTF. URDF carries one RGBA colour and one texture filename, and is the least expressive format in this document.*

### 4.3 Expressible, and actually implemented, are different questions
*SDF names both PBR workflows and Gazebo implements only the metal one. A format's capability is an upper bound on what a reader will do with it.*

## 5. The shared substrate: geometry and texture coordinates

What both ways agree on. A surface is triangles, and a triangle's corners carry more than position.

### 5.1 Vertices, triangles and indices
### 5.2 Vertex attributes: position, normal, texture coordinate
### 5.3 UV coordinates: an address on an image for every vertex
### 5.4 Unwrapping, and why a curved surface must be cut before it will lie flat
### 5.5 Texel density: image resolution measured on the surface rather than in the image

## 6. What each way asks the author to supply

The two practices end to end, once the vocabulary and the models are in place.

### 6.1 Under an empirical model: diffuse, specular, ambient, shininess
### 6.2 What those numbers are, and what they are not
### 6.3 What has to be painted into the single image
### 6.4 Under metallic-roughness: six properties instead of one image
### 6.5 Supplying a value two ways: a constant, an image, or both
### 6.6 Base color
### 6.7 Metallic
### 6.8 Roughness
### 6.9 Normal
### 6.10 Occlusion
### 6.11 Emissive

## 7. The two ways side by side

The comparison itself, once both have been described.

### 7.1 Level by level
*Summary table placeholder. Rows: reflection model, Blinn-Phong or Lambert against Cook-Torrance with GGX; physically based, no against yes; parameterization, none separate against metallic-roughness; author-supplied values; the element carrying it in a file, `<phong>` inside `profile_COMMON` against `pbrMetallicRoughness`; formats that can carry it.*

### 7.2 What each can express, and what it cannot
### 7.3 What each requires the author to decide
### 7.4 How well each survives being opened in a different tool
### 7.5 How each behaves under lighting the author did not choose
### 7.6 What each costs in data

## 8. How the data is stored and encoded

The layer underneath both: how numbers and images become bytes, and the encoding decisions that are invisible until they are wrong.

### 8.1 Numbers in a buffer: offset, type, count
### 8.2 Vertices and indices, and what a triangle costs in bytes
### 8.3 Images: PNG and JPEG, and what the container does not record about them
### 8.4 Color images and data images: sRGB against linear
### 8.5 Packing several quantities into one image
### 8.6 Defaults, and what a file leaves unsaid

## 9. Reading a glTF file end to end

One complete part in the text form, where the description, the geometry and the images sit in separate files that reference each other.

### 9.1 The file set: the JSON, the binary buffer, the images beside them
### 9.2 From scene to triangle: the chain of references, read top to bottom
*Also where to show what a glTF file holds that has nothing to do with materials.*

### 9.3 The material, and how it names its images
### 9.4 The two containers: a `.gltf` with its files beside it, against a single `.glb`

## 10. Glossary

Every term used above, defined in one place for lookup rather than for reading in order.

### 10.1 The terminology of section 1
### 10.2 The texture words
### 10.3 The geometry words
### 10.4 The storage words

## 11. References
