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

This document uses shading model, the textbook term, and keeps reflection model for the half of it defined in 1.1.1. Two of the others are avoided: "material model", because glTF's `material` is a data object holding parameters (9.3); and "Phong shading" on its own, because it also names a per-pixel renderer technique (Marschner and Shirley 8.2.5).

### 1.1 Shading model: the package a renderer evaluates at a point on a surface
*The unit every renderer and authoring tool works in: a reflection model, 1.1.1, plus a parameterization, 1.1.2.*

*Category: empirical or physically based, according to how the reflection model was derived. Empirical means adjusted until it looked right; physically based means derived from a physical picture of the surface, with energy conservation and reciprocity as design goals.*

*Microfacet, Cook and Torrance 1982, is the family of physically based models built from the picture of a surface as many tiny mirrors.*

#### 1.1.1 Reflection model: what is computed at a single point
*Reflection model and BRDF name the same thing here. Spell out the acronym, bidirectional reflectance distribution function: incoming direction and outgoing direction in, fraction of light out. BRDF is the mathematical name for the class of function, a reflection model a named one. Marschner and Shirley 18.1.6 defines it by describing the instrument that would measure it, a light in one direction and a detector in the other.*

*Three acronyms one letter apart, and the letter is the direction the light leaves. A BRDF, R for reflectance, covers light that leaves on the side it arrived from. A BTDF, T for transmittance, covers light that goes through and leaves on the far side. A BSDF, S for scattering, is the two together; Filament states it as a BSDF "composed of two other functions: the BRDF and the BTDF". Anything opaque needs only the BRDF, which is why this document says reflection model throughout. The exception is 2.2.4, where adding transmission makes the model a BSDF.*

#### 1.1.2 Parameterization: how an author supplies values to the reflection model
*The author-facing parameters and the rule mapping them to the reflection model's variables. Empirical reflection models take their coefficients directly; physically based ones derive them from friendlier inputs.*

*The two are not one to one, which is why they are named separately. One reflection model can have several parameterizations: Cook-Torrance takes both metallic-roughness and specular-glossiness, section 3. The reverse does not happen, since a parameterization is written to produce one reflection model's variables. Every other row of 1.1.3 has a single parameterization, so there the two names pick out the same thing.*

#### 1.1.3 The shading models in use

| Shading model | Reflection model | Parameterization | Category |
|---|---|---|---|
| Constant, also called unlit | none; the color is returned unchanged | one color | neither: no light enters the computation |
| Lambert | cosine law | diffuse reflectance | physically based, see 2.2.1 |
| Phong, Blinn-Phong | cosine-power lobe over Lambert | ambient, diffuse, specular, emission, shininess | empirical |
| Oren-Nayar | microfacet diffuse | diffuse reflectance, roughness | physically based |
| Cook-Torrance with metallic-roughness | Cook-Torrance microfacet | base color, metallic, roughness | physically based |
| Cook-Torrance with specular-glossiness | the same | diffuse color, specular color, glossiness | physically based |
| The layered supersets, 2.2.4 | the same, plus one lobe per layer | the three above plus a group per layer | physically based |

*Constant is the minimal case and the one to read first: no lights, no directions, no surface normal, just the color as authored. Everything below it in the table is a way of deciding how much of the light arriving at a point leaves it toward the eye.*

![One sphere per shading model, rendered under identical lighting](images/shading_models.png)

*Figure. One sphere per row of the table, same geometry, same three lights, same sky, so the only variable is the shading model. Regenerated by `docs/_tools/shading_models_figure.py`. The last two panels are the same reflection model reached through different parameterizations, and they agree to floating-point noise.*

*The two Cook-Torrance rows are named here by their pairing. The field usually says just "metallic-roughness", letting the parameterization stand for the whole shading model, which is why 3.2 says which of the two is meant.*


### 1.2 Format: which file carries the result

The other independent choice. A format can carry one shading model, several, or none.

| Format | Shading models it can carry |
|---|---|
| glTF 2.0 | metallic-roughness in core; constant and the layered supersets of 2.2.4, both by extension |
| COLLADA | constant, Lambert, Phong, Blinn-Phong |
| OBJ with MTL | constant, Lambert, Phong; metallic-roughness only by unofficial extension |
| FBX | Lambert, Phong; physically based only in vendor blocks |
| STL | none, geometry only |
| USD | metallic-roughness and a specular workflow in one model |
| MaterialX | any, since it describes shading networks |
| SDF | Phong, Blinn-Phong, metallic-roughness, specular-glossiness |
| URDF | none: one color and one texture filename |

*Most formats name a shading model and leave its math to the reader; COLLADA names Phong and Blinn-Phong without defining either. glTF 2.0 is the exception and specifies both: it is a container, and in its Appendix B a normative definition of exactly one shading model, Cook-Torrance with metallic-roughness, the fifth row of 1.1.3. That is why it appears in section 3 as a source for equations and in section 4 as a format.*

*Section 4 expands this table and separates what a format can express from what its readers implement.*

## 2. The shading models in common use

Each model in 1.1.3: character, cost, where it fits, what it cannot represent, with lobe illustrations. The models are described independently of any file format; where a specification is named it is as a published source for the math.

### 2.1 Empirical shading models
#### 2.1.1 Phong
*Marschner and Shirley 10.2; Eck 4.1.4 for the OpenGL form.*
#### 2.1.2 Blinn-Phong
*The half-vector variant and the typical exponent values, Marschner and Shirley 4.5.2.*

### 2.2 Physically based shading models
#### 2.2.1 Lambert
*Passes the test and predates the movement; no specular term, so not "PBR" in everyday usage. Its role is the diffuse term inside the microfacet models. Marschner and Shirley 18.1.6.*
#### 2.2.2 Cook-Torrance, and the microfacet idea
*Roughness as the width of the microfacet distribution, hence of the lobe.*
##### The three factors inside a microfacet reflection model
*A microfacet reflection model is not one equation but a template with three slots, each a function in its own right.*

*Distribution decides how the tiny mirrors are oriented, and so how wide the highlight is. Geometry decides how much they block one another, which matters most at grazing angles. Fresnel decides how reflectance rises as the view flattens toward the surface.*

*Several published functions compete for each slot, and an implementation picks one per slot. The usual three are Trowbridge-Reitz, written GGX everywhere, then Smith, then Schlick. Hoffman 2013 makes the point that most new microfacet papers are a new function for one slot rather than a new model.*

#### 2.2.3 Oren-Nayar, and other physically based diffuse models

#### 2.2.4 The layered supersets: Disney principled, Standard Surface, OpenPBR
*They are not extra parameters on one reflection model, which is why they sit here rather than in section 3. Each adds lobes: a clearcoat is a second specular BRDF evaluated on top, sheen swaps in a different distribution, transmission adds a transmitted term and turns the BRDF into a BSDF. So both halves grow, the reflection model and the parameterization together.*

*Each reduces to Cook-Torrance with metallic-roughness when its layers are switched off, which is what makes them supersets and what lets a material move between tools with its core intact.*

### 2.3 Where empirical and physically based overlap
*The two cases where the category of 1.1 and its plausibility test disagree. Blinn-Phong can be normalized so that it conserves energy: an empirical model that passes. And physically based models as shipped often fail it, because real-time renderers approximate for speed. So the category records how a model was derived, and plausibility is a separate question asked of the result.*

### 2.4 Side by side: cost, and what each cannot represent

## 3. Parameterizations

The layer where two tools most often disagree while both claiming PBR.

### 3.1 Why the author's parameters are not the reflection model's variables
*Two worked examples. The author's roughness is not the equation's variable: glTF 2.0 Appendix B says "the reflection roughness is given by the squared roughness of the material", and Filament devotes a section, Roughness remapping and clamping, to why. And specular color at normal incidence is never asked for; it is derived from base color and metallic.*

*The design rule behind both is Burley 2012, page 12: "Intuitive rather than physical parameters should be used", first of five principles, the others being as few parameters as possible, zero to one over their plausible range, pushable beyond it where sensible, and robust in every combination.*

### 3.2 The metallic-roughness parameterization
*The name does double duty and this subsection is about the parameterization half: three inputs, base color, metallic and roughness, and the rule that turns them into a blend of a dielectric and a metal BRDF. glTF 2.0 Appendix B writes the blend out.*

### 3.3 The specular-glossiness parameterization, and why it was retired
*The specular-color workflow that predates the metallic idea. Same reflection model, so the two can render identically; it costs one more image and lets an author state combinations no real material has. Archived by Khronos.*

### 3.4 Where metallic-roughness came from: the core of Disney principled
*Burley 2012 with its layers switched off. glTF Appendix B names it as the source of the metallic blend.*

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

## 11. Further reading

In the order worth reading them, with what each is good for and where each stops.

**1. Marschner and Shirley, *Fundamentals of Computer Graphics*, 4th ed., section 4.5.** Six pages, and the fastest route into the whole empirical picture: Lambert, Blinn-Phong, the ambient term, and the vectors they are built from. Section 10.2 repeats it with more care, 18.1.6 defines the BRDF by measurement, and chapter 24 treats reflection models on their own. Its vocabulary is the one this document follows. What it lacks: published 2016 and it predates the industry settling on metallic-roughness, so it never names GGX or metallic-roughness, and the models chapter 24 recommends are not the ones that shipped.

**2. The [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html), section 3.9.** Short, normative, and the actual delivery target. Read it for what a material is allowed to contain and what every default is. What it lacks: it is a specification, not an explanation, and it gives no intuition for any value it defines.

**3. [Physically Based Rendering in Filament](https://google.github.io/filament/Filament.html), the material system sections.** The clearest free account of the physically based half, and the one that separates the reflection model from the parameterization the way this document does, under the headings Standard model and Parameterization. Its figures are systematic sweeps rather than one-off renders. What to watch: it is one renderer's documentation, so several approximations are Filament's own choices rather than universal practice.

**4. Eck, *[Introduction to Computer Graphics](https://math.hws.edu/graphicsbook/)*, chapter 4.** Free, plain-language, and the best treatment of the five empirical coefficients, with a live demo that lets you move each one. What it lacks: it stops at the door of the physically based half and says so, so read it for the older way only.

**5. Burley, *Physically Based Shading at Disney*, SIGGRAPH 2012, section 5.** Three pages for the five design principles and the parameter list that metallic-roughness was cut down from. The primary source for why the author's parameters are not the equation's variables. What is dated: the specific functions have moved on, and Disney's own later work extends this to a BSDF.

**6. glTF 2.0 Appendix B.** The exact equations, once the four above have been read. It is the normative definition of Cook-Torrance with metallic-roughness, and it is candid about its own approximations, saying outright that its recommended way of combining diffuse and specular breaks energy conservation.

**7. Hoffman, *Background: Physics and Math of Shading*, SIGGRAPH 2013.** The derivation, from the behavior of light at a surface to the microfacet BRDF and its three factors. Read it when the three slots of 2.2.2 stop feeling arbitrary and start feeling unexplained. It asks more of the reader mathematically. Later editions of the same course update the practice around it, but this physics section remains the clearest.

**8. Pharr, Jakob and Humphreys, *[Physically Based Rendering](https://pbr-book.org/)*, 4th ed., the reflection models chapter.** Free online, and the deepest treatment here. Useful for a different and more careful taxonomy: it sorts models by where they came from, measured data, phenomenological, simulation, wave optics, geometric optics, rather than by the empirical and physically based split used here. What to expect: it is an offline renderer's textbook and very long.

**9. The [OpenPBR Surface specification](https://academysoftwarefoundation.github.io/OpenPBR/).** Where the layered supersets of 2.2.4 are heading, written as a stack of slabs. Newest of these and the one most likely to matter next; tool support is still thin.

**Two tools rather than texts.** [Disney's BRDF Explorer](https://github.com/wdas/brdf) loads reflection models as code, graphs them, applies them to a model, and puts them beside measured materials, which is the fastest way to see how two models differ. The [glTF Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/) shows a file as a conformant renderer sees it and validates it at the same time.
