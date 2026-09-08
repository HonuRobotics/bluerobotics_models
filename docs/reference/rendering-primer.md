# Describing a surface: the empirical way and the physically based way

For an engineer who does not work in graphics. It compares the older way a 3D part carried its appearance, an empirical shading model with a single image, against the physically based way that glTF uses. It covers what each stores, what each asks the author to decide, how the numbers are encoded, and how to read a file of either kind.

It is deliberately general. Nothing here is specific to this project's parts, tools or conventions; those live in [model-spec.md](model-spec.md) and [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).

**Status: outline with subsections.** Section headings carry one line on what they do; notes in italic say what a subsection will establish and will be replaced.

## 1. The two terms

Two independent choices: which shading model, and which format. A shading model is a reflection model plus a parameterization.

The field is not consistent about what to call that package. These names all refer to the same thing:

| Name | Used by |
|---|---|
| shading model | Marschner and Shirley ch. 4 and 10, Hoffman 2013, Burley 2012, Unreal, OpenPBR |
| material model | glTF specification, Filament, Burley 2012 |
| reflection model, BRDF model | Marschner and Shirley ch. 24, pbrt |
| lighting model, illumination model | Eck, OpenGL-era texts |

This document uses `shading model`, the textbook term.  Two of the others are avoided: "material model", because glTF's `material` is a data object holding parameters (9.3); and "Phong shading" on its own, because it also names a per-pixel renderer technique (Marschner and Shirley 8.2.5).

### 1.1 Shading model: the package a renderer evaluates at a point on a surface
*The unit every renderer and authoring tool works in: a reflection model, 1.1.1, plus a parameterization, 1.1.2.*

*Category: empirical or physically based. The precise test is physically plausible, Lewis 1994: energy conserving and reciprocal. Physically based is looser, built from a physical picture of the surface and constrained to be plausible; parameters are not part of the test, Burley 2012. Microfacet is narrower than either, one family of physically based models, so not a synonym for them.* % CLAUDE: Can we say empirical or physically-based.  Physically-plausable (Lewis 1994) is a subset of physcially-based.   Microfacet is a subset of physically-plausible (ref)?

#### 1.1.1 Reflection model: what is computed at a single point
*Reflection model and BRDF name the same thing here. Spell out the acronym, bidirectional reflectance distribution function: incoming direction and outgoing direction in, fraction of light out. BRDF is the mathematical name for the class of function, a reflection model a named one. Marschner and Shirley 18.1.6.*

#### 1.1.2 Parameterization: how an author supplies values to the reflection model
*The author-facing parameters and the rule mapping them to the reflection model's variables. Empirical reflection models take their coefficients directly; physically based ones derive them from friendlier inputs. Cook-Torrance is the only reflection model with more than one parameterization in use, so it is the only one whose name does not settle the shading model.* % CLAUDE: Are there multiple parameterizations for the same reflection model?  Are there multiple reflection models that use the same parameterization?   Or are they always 1:1?  If it is always 1:1, maybe we don't need separate subsubsections?

#### 1.1.3 The shading models in use

| Shading model | Reflection model | Parameterization | Category |
|---|---|---|---|
| Lambert | cosine law | diffuse reflectance | physically based, see 2.2.1 |
| Phong, Blinn-Phong | cosine-power lobe over Lambert | ambient, diffuse, specular, emission, shininess | empirical |
| Oren-Nayar | microfacet diffuse | diffuse reflectance, roughness | physically based |
| Metallic-roughness | Cook-Torrance microfacet | base color, metallic, roughness | physically based |
| Specular-glossiness | the same | diffuse color, specular color, glossiness | physically based |
| Supersets of 3.5 | the same plus layers | the three above plus one per layer | physically based |

### 1.2 Format: which file carries the result

The other independent choice. A format can carry one shading model, several, or none.

| Format | Shading models it can carry |
|---|---|
| glTF 2.0 | metallic-roughness; unlit  % CLAUDE: what does unlit mean? and the supersets by extension % CLAUDE: ? |
| COLLADA | Lambert, Phong, Blinn-Phong, constant % CLAUDE: Describe a constant shading model above as a simple, minimal example. |
| OBJ with MTL | Phong family % CLAUDE: Why introduce "family"?  Again adding seeminly unnecessary words to confuse the reader.  Explain.
; metallic-roughness only by unofficial extension |
| FBX | Lambert, Phong; physically based only in vendor blocks |
| STL | none, geometry only |
| USD | metallic-roughness and a specular workflow in one model |
| MaterialX | any, since it describes shading networks |
| SDF | Phong family, metallic-roughness, specular-glossiness |
| URDF | none: one color and one texture filename |

*Section 4 expands this and separates what a format can express from what its readers implement.*

## 2. The shading models in common use

Each model in 1.1.3: character, cost, where it fits, what it cannot represent, with lobe illustrations. The models are described independently of any file format; where a specification is named it is as a published source for the math.

### 2.1 Empirical shading models
#### 2.1.1 Phong % CLAUDE: Should you have "Phone Family"?  See above. 
*Marschner and Shirley 10.2; Eck 4.1.4 for the OpenGL form.*
#### 2.1.2 Blinn-Phong
*The half-vector variant and the typical exponent values, Marschner and Shirley 4.5.2.*

### 2.2 Physically based shading models
#### 2.2.1 Lambert
*Passes the test and predates the movement; no specular term, so not "PBR" in everyday usage. Its role is the diffuse term inside the microfacet models. Marschner and Shirley 18.1.6.*
#### 2.2.2 Cook-Torrance, and the microfacet idea
*Roughness as the width of the microfacet distribution, hence of the lobe.*
##### The three interchangeable terms inside a microfacet reflection model
*Distribution, geometry and Fresnel, each with competing choices: GGX % CLAUDE: ?, Smith and Schlick among them. Whoever implements the model fixes one of each . Hoffman 2013.*
#### 2.2.3 Oren-Nayar, and other physically based diffuse models

### 2.3 Where the boundary is soft
*Normalized Blinn-Phong conserves energy and crosses the line. Real-time implementations routinely trade plausibility for speed and say so. The category is about how a model was built, not a pass or fail.* % CLAUDE: Very confusing.  Rephrase

### 2.4 Side by side: cost, and what each cannot represent

## 3. Parameterizations

The layer where two tools most often disagree while both claiming PBR.

### 3.1 Why the author's parameters are not the reflection model's variables
*Roughness is squared before use; specular color at normal incidence is derived from base color and metallic. Burley's five principles.*
### 3.2 Metallic-roughness
*Three inputs; the metallic blend of a dielectric and a metal BRDF, glTF Appendix B.*
### 3.3 Specular-glossiness, its older lineage, and why glTF retired it
*The specular-color workflow that predates the metallic idea; same reflection model, one more image, impossible combinations expressible. Archived by Khronos.*
### 3.4 Disney principled, where metallic-roughness comes from
*Burley 2012, cited by glTF Appendix B.*
### 3.5 The richer supersets, and how they reduce to metallic-roughness
*Standard Surface, OpenPBR, Blender Principled: the core three plus layers, each layer a glTF extension or nothing.*

## 4. Which formats carry which

### 4.1 Formats that carry geometry
*The table of 1.2, with what each format's readers actually implement.*
### 4.2 Formats that reference geometry rather than carrying it
*SDF and URDF name a mesh file and may override its material.*
### 4.3 Expressible, and actually implemented, are different questions
*SDF names both parameterizations; Gazebo implements one.*

## 5. The shared substrate: geometry and texture coordinates

### 5.1 Vertices, triangles and indices
### 5.2 Vertex attributes: position, normal, texture coordinate
*Hard and soft edges are geometry, not rendering. Flat and smooth shading, the technique words, Eck 4.1.3.*
### 5.3 UV coordinates: an address on an image for every vertex
### 5.4 Unwrapping, and why a curved surface must be cut before it will lie flat
### 5.5 Texel density: image resolution measured on the surface rather than in the image

## 6. What each way asks the author to supply

### 6.1 Under an empirical model: ambient, diffuse, specular, emission, shininess
*Five; Eck 4.1.1, COLLADA `profile_COMMON`.*
### 6.2 What those numbers are, and what they are not
*Tuned per viewpoint, Marschner and Shirley 24.5, against a Fresnel reflectance near 0.04.*
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

### 7.1 Level by level
*Table: shading model, category, parameterization, author values, file element, formats.*
### 7.2 What each can express, and what it cannot
### 7.3 What each requires the author to decide
### 7.4 How well each survives being opened in a different tool
### 7.5 How each behaves under lighting the author did not choose
### 7.6 What each costs in data

## 8. How the data is stored and encoded

### 8.1 Numbers in a buffer: offset, type, count
### 8.2 Vertices and indices, and what a triangle costs in bytes
### 8.3 Images: PNG and JPEG, and what the container does not record about them
### 8.4 Color images and data images: sRGB against linear
### 8.5 Packing several quantities into one image
### 8.6 Defaults, and what a file leaves unsaid

## 9. Reading a glTF file end to end

### 9.1 The file set: the JSON, the binary buffer, the images beside them
### 9.2 From scene to triangle: the chain of references, read top to bottom
### 9.3 The material, and how it names its images
*glTF's `material` object: the data holding one shading model's parameters, not the shading model.*
### 9.4 The two containers: a `.gltf` with its files beside it, against a single `.glb`

## 10. Glossary

### 10.1 The terminology of section 1
### 10.2 The texture words
### 10.3 The geometry words
### 10.4 The storage words

## 11. References

*Marschner and Shirley 4th ed. ch. 4, 8, 10, 18, 24; Eck ch. 4 and app. B; pbrt 4th ed. ch. 9; Hoffman 2013; Burley 2012; Lewis 1994; Physically Based Rendering in Filament, the documentation for Google's open-source real-time renderer; glTF 2.0 §3.9 and Appendix B; OpenPBR.*
