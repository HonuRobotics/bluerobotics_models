# Describing a surface: the empirical way and the physically based way

For an engineer who does not work in graphics. It compares the older way a 3D part carried its appearance, an empirical reflection model with a single image, against the physically based way that glTF uses. It covers what each stores, what each asks the author to decide, how the numbers are encoded, and how to read a file of either kind.

It is deliberately general. Nothing here is specific to this project's parts, tools or conventions; those live in [model-spec.md](model-spec.md) and [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).

**Terminology.** This document keeps three terms apart that are commonly run together:
1. reflection model
2. parameterization 
3. format
and never uses "shading model", which is used both for the first of those and for an unrelated renderer technique (2.1.1).

**Status: outline with subsections.** Section headings carry one line on what they do; notes in italic say what a subsection will establish and will be replaced. Plain text under a heading is content already agreed and is kept.

## 1. The terms this document keeps apart

Three independent choices, and a classification of the first of them. Most confusion in this area comes from running them together.

### 1.1 Reflection model: what is computed at a single point on a surface
*The equation taking an incoming light direction and an outgoing view direction and returning how much light leaves. The formal name for a reflection model is BRDF, bidirectional reflectance distribution function: a function rather than stored data, bidirectional for the two directions it takes, reflectance for the fraction it returns, distribution because the answer varies with direction. A mirror concentrates it into a narrow lobe; matte paint spreads it almost evenly. This document never calls these shading models, since that phrase also names an unrelated renderer technique (2.1.1).*

Every reflection model belongs to one of the two categories below. A model is physically based if it conserves energy, is reciprocal, and takes parameters standing for measurable quantities. 

#### 1.1.1 Empirical reflection models
*Everything failing that test. Many exist, Minnaert, Strauss and Lafortune among them, but none appear in any format compared here, so the only two treated are Phong and Blinn-Phong: cheap, tuned until the result looked acceptable, and capable of reflecting more light than arrives. Detailed in 2.1.*

#### 1.1.2 Physically based reflection models
*Cook-Torrance and the microfacet family, Oren-Nayar, and Lambert. Detailed in 2.2.*

(Aside:
Lambert's membership is the surprise. It predates the physically based movement by decades, and it has no specular term at all, where every other model in this category describes both a diffuse and a specular response. So it reads as old-fashioned and incomplete, but the test is about the maths, not the era: it conserves energy and is reciprocal, so it passes. Whether the rendering community calls it PBR depends on which sense is meant. By the test, it belongs. In everyday usage, "PBR" means a complete material with a specular term, and Lambert on its own is not that. Its actual role is as a component: it supplies the diffuse term inside the microfacet models, including glTF's own material.

### 1.2 Parameterization: how an author supplies values to the model
*For physically based reflection models only. Metallic-roughness and specular-glossiness are parameterizations. They take different inputs from the author and compute the same variables the reflection model needs.*

*Every reflection model is driven by values the author supplies, so in the widest sense every model has a parameterization. The distinction is whether anything sits between those values and the equation. For an empirical model, the coefficients in the governing equations of the relection model are set directly.  A physically based model's equation runs on variables that are awkward to author directly, the reflectance at normal incidence and the spread of microfacet normals among them, so in practice they are derived from friendlier inputs. Metallic-roughness derives them from base color, metallic and roughness; specular-glossiness derives the same variables from a different set of inputs. The derivation is what this document calls the parameterization, and it is a choice only on the physically based side, because only there is there more than one.*

*How many there are, and how they relate. Metallic-roughness and specular-glossiness are the two complete parameterizations in wide use. Several richer ones exist, Disney principled, Autodesk Standard Surface and OpenPBR among them, and each is metallic-roughness at its core plus optional layers on top: clearcoat, sheen, transmission, subsurface. They are supersets, not alternatives. When a material moves between tools, the core travels everywhere; each added layer travels only where both sides support it, which is how glTF handles them, as optional extensions over a fixed core. Section 3 treats the two complete ones, their common ancestor, and how the supersets reduce to them.*

### 1.3 Format: which file carries the result
*The third of the three independent choices, after reflection model (1.1) and parameterization (1.2), and cross-cutting on both. A format can carry one reflection model, several, or none, and can support one parameterization or more than one. Compared in section 4.*

### 1.4 Where glTF's own wording differs from this document's
*Disclosure of one usage issue. The [glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) says "metallic-roughness material model" for what this document calls a parameterization. "Material model" is a common phrase and a loose one. In this document's terms it means a (reflection model, parameterization) pair, taken together as one package, so glTF's phrase names the microfacet reflection model of 2.2 fed by the metallic-roughness parameterization of 3.2. Wherever the specification says material model, read it as that pair.*

*Not every pair is allowed. A parameterization is written to produce the variables of one particular reflection model, so it only pairs with that model. Metallic-roughness and specular-glossiness both produce the microfacet model's variables, so both pair with Cook-Torrance and neither pairs with Phong or with Lambert on its own. An empirical model pairs only with its own terms. The pairs in actual use are therefore few: the microfacet model with either of the two parameterizations, and each empirical model with itself.*

% CLAUDE: Name the allowable pairs.   If we can't mix and match, then the reflection model and parameterization are not separate degrees of freedom.

## 2. The reflection models in common use

Each model, in the two categories named in 1.1, treated individually. Each gets its character, its cost, where it is the right choice, and what it cannot represent, with links to references and to illustrations of the reflection lobe.

### 2.1 Empirical reflection models

#### 2.1.1 Phong
*One name collision to dispose of. "Phong shading" also names a renderer technique, evaluating the lighting at every pixel of a triangle rather than only at its corners. It has nothing to do with the Phong reflection model, is not a choice an author makes, and is not discussed further in this document. The equation treated in this subsection is the reflection model.*

#### 2.1.2 Blinn-Phong

### 2.2 Physically based reflection models

#### 2.2.1 Lambert
#### 2.2.2 Cook-Torrance, and the microfacet idea
*Where roughness stops being a dial. It sets how widely the microfacet normals scatter, which sets the width of the reflection lobe.*

##### The three interchangeable terms inside it
*Specific to microfacet models and to nothing else in this document. Distribution, geometry and Fresnel, each with competing choices: GGX also written Trowbridge-Reitz, Smith, Schlick. glTF fixes one of each.*

#### 2.2.3 Oren-Nayar, and other physically based diffuse models

### 2.3 Where the boundary is soft
*Normalized Blinn-Phong conserves energy and so sits on the line. The test is real but the boundary has cases on it.*

### 2.4 Side by side: cost, and what each cannot represent

## 3. Parameterizations

Only relevant to physically based models, and the layer where two renderers, or a renderer and the authoring tool that wrote the file, most often disagree while both claiming to support PBR.

### 3.1 Why a separate parameterization exists at all
### 3.2 Metallic-roughness
### 3.3 Specular-glossiness, and why it was retired
### 3.4 Disney principled, the common ancestor of both
### 3.5 The richer supersets, and how they reduce to the two

## 4. Which formats carry which

The cross-cutting table, and the distinction between formats that hold geometry and formats that reference it.

### 4.1 Formats that carry geometry
*Table placeholder. glTF: metallic-roughness only in core, unlit by extension, no Phong. COLLADA: constant, Lambert, Phong, Blinn as named elements in `profile_COMMON`. OBJ and MTL: the Phong family, plus metallic-roughness through an unofficial extension. FBX: Lambert and Phong, PBR only through non-standard blocks, and proprietary so what readers implement is the practical answer. STL: no material at all. USD: metallic-roughness and a specular workflow in one model. MaterialX: any of them, since it describes shading networks and ships glTF's and USD's as nodes.*

### 4.2 Formats that reference geometry rather than carrying it
*SDF and URDF, a different role: they name a mesh file and may override its material. SDF carries the Phong family, metallic-roughness and specular-glossiness, so it is more expressive on paper than glTF. URDF carries one RGBA color and one texture filename, and is the least expressive format in this document.*

### 4.3 Expressible, and actually implemented, are different questions
*SDF names both PBR workflows and Gazebo implements only the metal one. A format's capability is an upper bound on what a reader will do with it.*

## 5. The shared substrate: geometry and texture coordinates

What both ways agree on. A surface is triangles, and a triangle's corners carry more than position.

### 5.1 Vertices, triangles and indices
### 5.2 Vertex attributes: position, normal, texture coordinate
*Includes hard and soft edges, which look like a rendering choice and are geometry. A hard edge exists because two faces do not share vertices, each carrying its own normal. The author controls it, it is stored in the file, and it is why vertex counts exceed corner counts.*
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
