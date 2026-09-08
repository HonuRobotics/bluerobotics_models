# Describing a surface: the empirical way and the physically based way

For an engineer who does not work in graphics. It compares the older way a 3D part carried its appearance, an empirical shading model with a single image, against the physically based way that glTF uses. It covers what each stores, what each asks the author to decide, how the numbers are encoded, and how to read a file of either kind.

It is deliberately general. Nothing here is specific to this project's parts, tools or conventions; those live in [model-spec.md](model-spec.md) and [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).


**Status: outline with subsections.** Section headings carry one line on what they do; notes in italic say what a subsection will establish and will be replaced. Plain text under a heading is content already agreed and is kept.

## 1. The two terms

Two independent choices: which shading model, and which format. A shading model is a reflection model plus a parameterization, and has one category. The two parts get separate subsections because the parameterization is where tools that both claim to support physically based rendering most often disagree.

### 1.1 Shading model: the package a renderer evaluates at a point on a surface
*The unit every renderer, format and authoring tool works in. A shading model is a reflection model, 1.1.1, together with a parameterization, 1.1.2: the parameters an author sets and the rule that turns them into the reflection model's variables. The list in use is short and is given in 1.1.4. Every source consulted for this document treats the package as the primary object and its two halves as anatomy; Filament's documentation, for example, states that "a material model is described mathematically by a BSDF" and then gives the reflection model and the parameters separate sections.*

#### 1.1.1 Reflection model: what is computed at a single point on a surface
*The function taking an incoming light direction and an outgoing view direction and returning how much light leaves. Its formal name is BRDF, bidirectional reflectance distribution function: a function rather than stored data, bidirectional for the two directions it takes, reflectance for the fraction it returns, distribution because the answer varies with direction. A mirror concentrates it into a narrow lobe; matte paint spreads it almost evenly. Defined by measurement in Marschner and Shirley 18.1.6: a light in one direction, a detector in the other, a reading for every pair.*

#### 1.1.2 Parameterization: how an author supplies values to the reflection model
*Every shading model is driven by values the author supplies. The distinction is whether anything sits between those values and the reflection model. For an empirical model nothing does: the coefficients in the reflection model are set directly, a diffuse color, a specular color, an exponent. A physically based reflection model runs on variables that are awkward to author directly, the reflectance at normal incidence and the width of the microfacet distribution among them, so in practice they are derived from friendlier inputs. Metallic-roughness derives them from base color, metallic and roughness; specular-glossiness derives the same variables from a different set of inputs. The set of author-facing parameters together with that derivation is what this document calls the parameterization. Filament's documentation gives the two halves their own sections, titled Standard model and Parameterization, and calls the derivation remapping.*

*A parameterization is written to produce the variables of one reflection model and pairs with that model only. Where a reflection model has one parameter set in use, the shading model and the reflection model are the same thing under two names; where it has several, which today means the microfacet model of 2.2.2 alone, the parameterization is the choice that distinguishes one shading model from another. That is why section 3 treats parameterizations on their own.*

*How many there are, and how they relate. Metallic-roughness and specular-glossiness are the two complete parameterizations in wide use. Several richer ones exist, Disney principled, Autodesk Standard Surface and OpenPBR among them, and each is metallic-roughness at its core plus optional layers on top: clearcoat, sheen, transmission, subsurface. They are supersets, not alternatives. When a material moves between tools, the core travels everywhere; each added layer travels only where both sides support it, which is how glTF handles them, as optional extensions over a fixed core.*

#### 1.1.3 The category: empirical or physically based
*A property of how the reflection model was built, not a partition of models by a test. The field has a precise term and a loose one, and both are needed.*

*The precise term is physically plausible, from Lewis (1994): the reflection model conserves energy, reflecting no more light than arrives from any direction, and is reciprocal, giving the same answer when the two directions are swapped. Marschner and Shirley 24.2, Hoffman (2013) and Burley (2012) all state the test in that form.*

*The loose term is physically based: a reflection model constructed from a physical picture of the surface, microfacets and Fresnel reflection, and constrained to be plausible. It is loose because its own practitioners use "empirical" for parts of their physically based models. Ashikhmin and Shirley describe their model as "an empirical model whose terms are chosen to enforce energy conservation and reciprocity"; Burley calls the Disney diffuse term "a novel empirical model"; Marschner and Shirley 24.2 say analytic BRDFs are as a rule "crudely approximated in an empirical fashion" and list plausibility as a desirable property of such approximations. Parameters are not part of the test in either sense: Burley's first design principle is "intuitive rather than physical parameters," and glTF folds refractive index and extinction into one user-facing color for the same reason.*

*Empirical, in this document, therefore means a model built to look acceptable rather than from a physical picture, and not constrained to be plausible: Phong and Blinn-Phong, which can reflect more light than arrives. Physically based means the rest of 1.1.4. Section 2.3 gives the models that sit on the line.*

#### 1.1.4 The shading models in use
*The list is short. Many others exist, Minnaert, Strauss and Lafortune among them, but none appear in any format compared here.*

| Shading model | Reflection model | Parameters the author sets | Category |
|---|---|---|---|
| Lambert | Lambert's cosine law | one diffuse reflectance | physically based, with the reservation in 2.2.1 |
| Phong | Phong's cosine-power lobe over Lambert | ambient, diffuse, specular, emission, shininess | empirical |
| Blinn-Phong | Blinn's half-vector variant of the same | the same five | empirical |
| Oren-Nayar | microfacet diffuse | diffuse reflectance and a roughness | physically based |
| Metallic-roughness | Cook-Torrance microfacet, 2.2.2 | base color, metallic, roughness | physically based |
| Specular-glossiness | the same reflection model | diffuse color, specular color, glossiness | physically based |
| The supersets of 3.5 | the same reflection model plus layers | metallic-roughness's three plus a layer each | physically based |

*The last three rows share one reflection model and differ only in parameterization. glTF's "metallic-roughness material model" is the fifth row under its own name for the package.*

### 1.2 Format: which file carries the result
*The other independent choice. A format can carry one shading model, several, or none. Compared in section 4.*

### 1.3 One package, five names
*The overload, stated once so it is not a surprise later. The package of 1.1 is called:*

| Name | Used by |
|---|---|
| shading model | Marschner and Shirley chapters 4 and 10, Hoffman (2013), Burley (2012), Unreal Engine, OpenPBR |
| material model | the glTF specification, Filament, Burley (2012) |
| reflection model, reflectance model, BRDF model | Marschner and Shirley chapter 24, pbrt, Burley (2012) |
| lighting model, illumination model | Eck, OpenGL-era texts, Marschner and Shirley 8.2.5 |

*All five name the same thing. This document says shading model because it is the textbook term and because glTF already uses "material" for the data object that holds a shading model's parameters (9.3), so "material model" would put the package and the data object one word apart. "Reflection model" is used by Marschner and Shirley chapter 24 and by pbrt for the package, and by this document for the BRDF half of it; the two uses agree wherever a reflection model has one parameterization, which is every row of 1.1.4 but the last three.*

*One collision is real and is with a different phrase. "Phong shading" names the Phong shading model and also a renderer technique, evaluating the lighting at every pixel of a triangle from interpolated normals rather than only at its corners. Marschner and Shirley 8.2.5 call the double use confusing; Eck uses the phrase both ways. The technique is not a choice an author makes and is not discussed in this document beyond 5.2, where "flat shading" and "smooth shading" name the normal-assignment choice that is an author's. This document writes "Phong shading model" or "Phong reflection model" in full and never "Phong shading" alone.*

## 2. The shading models in common use

Each model in 1.1.4, treated individually. Each gets its character, its cost, where it is the right choice, and what it cannot represent, with links to references and to illustrations of the reflection lobe.

### 2.1 Empirical shading models

#### 2.1.1 Phong
*Marschner and Shirley 10.2, Eck 4.1.4 for the OpenGL 1.1 form. The cosine-power lobe around the mirror direction, the exponent as the highlight-size dial, and the five coefficients of 6.1.*

#### 2.1.2 Blinn-Phong
*The half-vector variant, why it replaced Phong in hardware, and Marschner and Shirley's typical exponent values: 10 for eggshell, 100 mildly shiny, 1000 glossy, 10,000 nearly mirror.*

### 2.2 Physically based shading models

#### 2.2.1 Lambert
*Lambert's membership is the surprise. It predates the physically based movement by decades, and it has no specular term at all, where every other model in this category describes both a diffuse and a specular response. So it reads as old-fashioned and incomplete, but the test is about the math, not the era: it conserves energy and is reciprocal, so it passes. Marschner and Shirley 18.1.6 put it exactly: Lambertian surfaces "are impossible in nature for thermodynamic reasons, but mathematically they do conserve energy," while their chapter 10 calls Lambertian and Phong shading alike "heuristics designed to imitate the appearance of objects." In everyday usage, "PBR" means a complete material with a specular term, and Lambert on its own is not that. Its actual role is as a component: Burley notes that for the diffuse term "Lambert seemed to be the accepted norm," and it supplies the diffuse term inside the microfacet models, including glTF's own.*

#### 2.2.2 Cook-Torrance, and the microfacet idea
*Where roughness stops being a dial. It sets how widely the microfacet normals scatter, which sets the width of the reflection lobe.*

##### The three interchangeable terms inside it
*Specific to microfacet models and to nothing else in this document. Distribution, geometry and Fresnel, each with competing choices: GGX also written Trowbridge-Reitz, Smith, Schlick. glTF fixes one of each in its Appendix B. Hoffman: "Most papers proposing a new microfacet BRDF model are best understood as introducing a new D() and/or G() function." Burley: most plausible models not written in microfacet form "can still be interpreted as microfacet models."*

#### 2.2.3 Oren-Nayar, and other physically based diffuse models

### 2.3 Where the boundary is soft
*The category is a property of construction, so models sit on the line and are moved across it. Normalized Blinn-Phong conserves energy and is used inside physically based renderers; Hoffman's 2010 course is about "converting a non-physical model to a physically based one." glTF's own Appendix B admits its recommended way of combining diffuse and specular "breaks a fundamental property that a physically based BRDF must fulfill, energy conservation," and its sample renderer "uses non-physical simplifications that break energy-conservation and reciprocity." The test is real; the category is about intent and construction, and a physically based model in a real-time renderer is usually plausible only approximately.*

### 2.4 Side by side: cost, and what each cannot represent

## 3. Parameterizations

The parameter half of a shading model, and the layer where two renderers, or a renderer and the authoring tool that wrote the file, most often disagree while both claiming to support physically based rendering.

### 3.1 Why the author's parameters are not the reflection model's variables
*The worked example is roughness. The value an author sets is not the variable in the reflection model: glTF and Filament both square it first, because the squared form is perceptually even and the raw form crowds every shiny surface into the bottom five percent of the slider. The second example is specular color at normal incidence, which metallic-roughness never asks for and instead derives by mixing a fixed dielectric value with the base color according to metallic. Burley's five principles for choosing parameters: intuitive rather than physical, as few as possible, zero to one over their plausible range, allowed beyond it where sensible, robust in every combination.*

### 3.2 Metallic-roughness
*Three inputs, and how the metal and dielectric BRDFs are blended by the metallic value. glTF Appendix B writes the blend out.*

### 3.3 Specular-glossiness, its older lineage, and why glTF retired it
*The specular-color workflow that predates the metallic idea: diffuse color, specular color and glossiness set directly. It reaches the same reflection model, permits physically impossible combinations that metallic-roughness cannot express, and costs an extra image. Archived by Khronos.*

### 3.4 Disney principled, where metallic-roughness comes from
*Burley (2012). One color and ten scalars; the metallic blend between a dielectric model and a metal model is the part everything since has kept. glTF Appendix B names it as the source.*

### 3.5 The richer supersets, and how they reduce to metallic-roughness
*Autodesk Standard Surface, OpenPBR, Blender's Principled BSDF. Each is the three core inputs plus layers, and each layer is a glTF extension or nothing.*

## 4. Which formats carry which

The cross-cutting table, and the distinction between formats that hold geometry and formats that reference it.

### 4.1 Formats that carry geometry
*Table placeholder. glTF: metallic-roughness only in core, unlit by extension, no Phong. COLLADA: constant, Lambert, Phong, Blinn as named elements in `profile_COMMON`. OBJ and MTL: the Phong family, plus metallic-roughness through an unofficial extension. FBX: Lambert and Phong, physically based only through non-standard blocks, and proprietary so what readers implement is the practical answer. STL: no material at all. USD: metallic-roughness and a specular workflow in one model. MaterialX: any of them, since it describes shading networks and ships glTF's and USD's as nodes.*

### 4.2 Formats that reference geometry rather than carrying it
*SDF and URDF, a different role: they name a mesh file and may override its material. SDF carries the Phong family, metallic-roughness and specular-glossiness, so it is more expressive on paper than glTF. URDF carries one RGBA color and one texture filename, and is the least expressive format in this document.*

### 4.3 Expressible, and actually implemented, are different questions
*SDF names both parameterizations and Gazebo implements only metallic-roughness. A format's capability is an upper bound on what a reader will do with it.*

## 5. The shared substrate: geometry and texture coordinates

What both ways agree on. A surface is triangles, and a triangle's corners carry more than position.

### 5.1 Vertices, triangles and indices
### 5.2 Vertex attributes: position, normal, texture coordinate
*Includes hard and soft edges, which look like a rendering choice and are geometry. A hard edge exists because two faces do not share vertices, each carrying its own normal. The author controls it, it is stored in the file, and it is why vertex counts exceed corner counts. This is also where the technique word "shading" is disposed of: flat shading and smooth shading, in Eck 4.1.3 and Marschner and Shirley 10.1.3, name whether a vertex carries its face's normal or an averaged one, and have nothing to do with which shading model is evaluated.*
### 5.3 UV coordinates: an address on an image for every vertex
### 5.4 Unwrapping, and why a curved surface must be cut before it will lie flat
### 5.5 Texel density: image resolution measured on the surface rather than in the image

## 6. What each way asks the author to supply

The two practices end to end, once the vocabulary and the models are in place.

### 6.1 Under an empirical model: ambient, diffuse, specular, emission, shininess
*Five, not four. Eck 4.1.1 lists the four colors of an OpenGL 1.1 material and the shininess exponent; COLLADA's `profile_COMMON` carries the same five.*
### 6.2 What those numbers are, and what they are not
*Marschner and Shirley 24.5: a Phong specular coefficient "typically must be tuned for viewpoint in static images and tuned for a particular camera sequence for animations," against a Fresnel reflectance confined to roughly 0.03 to 0.06 for real dielectrics.*
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
*Summary table placeholder. Rows: shading model, Blinn-Phong or Lambert against metallic-roughness on Cook-Torrance with GGX; category, empirical against physically based; parameters set directly against derived through a parameterization; author-supplied values; the element carrying it in a file, `<phong>` inside `profile_COMMON` against `pbrMetallicRoughness`; formats that can carry it.*

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
*Where glTF's `material` object is met: the data object holding one shading model's parameters, as distinct from the shading model itself (1.3).*
### 9.4 The two containers: a `.gltf` with its files beside it, against a single `.glb`

## 10. Glossary

Every term used above, defined in one place for lookup rather than for reading in order.

### 10.1 The terminology of section 1
*Shading model with its four synonym families; BRDF; parameterization; physically plausible; physically based; empirical; format; and "shading" as the technique word of 5.2.*
### 10.2 The texture words
### 10.3 The geometry words
### 10.4 The storage words

## 11. References

*Marschner and Shirley, Fundamentals of Computer Graphics, 4th ed., chapters 4, 8, 10, 18 and 24. Eck, Introduction to Computer Graphics, chapter 4 and appendix B. Pharr, Jakob and Humphreys, Physically Based Rendering, 4th ed., chapter 9. Hoffman, "Background: Physics and Math of Shading," SIGGRAPH 2013 course notes. Burley, "Physically Based Shading at Disney," SIGGRAPH 2012 course notes. Lewis, "Making Shaders More Physically Plausible," 1994. Google, Filament: Physically Based Rendering in Filament. Khronos, glTF 2.0 specification, section 3.9 and Appendix B. Academy Software Foundation, OpenPBR Surface specification.*
