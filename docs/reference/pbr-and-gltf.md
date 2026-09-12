# PBR, and why glTF is inseparable from it

Background reading, with a short encoding reference you can skip on a first pass. It explains what physically based rendering is, how it differs from the Collada and image-file models this project used before, and why adopting glTF means adopting PBR whether or not that was the intention. For the rules that follow from all this, see [model-spec.md](model-spec.md). For the evidence behind them, see [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md).

## The shift in one sentence

The old way was to paint what a surface should look like. PBR is to describe what a surface is made of, and let the renderer work out what it looks like.

Everything else follows. A file that describes the material can be dropped into daylight, a floodlit test tank, or thirty meters of water and be right in all three without re-authoring. A file that describes the appearance is only right under the lighting the artist had in mind.

## What we had before: Collada plus an image

A `.dae` file referencing a PNG carries a material built on the Phong or Blinn model. Its parameters are a diffuse color, a specular color, a shininess exponent, and an ambient term.

Those parameters are not properties of anything real. A shininess of 32 is not a measurement, it is a dial that produces an acceptable highlight under assumed lighting in one renderer. Three consequences followed, and this project has felt all of them:

- **Lighting gets baked into the texture.** Shadows in crevices, a bright edge along the top of a hull, a suggestion of reflection. All painted in, because the material model could not produce them. Move the light and the asset is wrong in a way no setting can fix.
- **Every engine interprets the numbers differently.** There is no standard for what a specular color of 0.5 means, so an asset tuned in one tool looks different in the next.
- **One image was the whole material.** Color was the only property that mattered, which is why "a mesh and its texture" was a reasonable mental model.

That mental model is the first Main Issue in the review, and it is the root of most of what went wrong.

## What PBR replaces it with

The metallic-roughness model describes a surface with six properties, each corresponding, at least approximately, to something physical.

Three words are easy to conflate, and the table below is unreadable without them. glTF defines each precisely. An **image** is "a two dimensional array of pixels encoded as a standardized bitstream", which for us means a PNG or a JPEG. A **sampler** is "an object that controls how image data is sampled", meaning the filtering and wrapping rules. A **texture** is "an object that combines an image and its sampler". A material never points at an image directly; it points at a texture, and the texture points at an image. A **material** is "a parametrized approximation of visual properties of the real-world object being represented by a mesh primitive", which in practice means a named set of values, some of them plain numbers and some of them references to textures.

Those nest, and the nesting is the whole structure:

```
primitive  ->  material  ->  texture  ->  image
                                     \->  sampler
```

A primitive names one material. That material holds plain numbers directly, and points at textures for anything that varies across the surface. Each texture combines one image with one sampler. So the files in a delivery are image files, and nothing in a material reaches an image without a texture in between.

One more piece of vocabulary, kept deliberately apart from the last, because running the two together is what made the sentence you are replacing incomprehensible:

- A **property** is one of the material's six inputs: base color, metallic, roughness, normal, occlusion, emissive. This is the specification's own word; it introduces the model as "defined by the following properties".
- A **channel** is one component of a pixel, the R, G, B or A of an image. Nothing else in this document is called a channel.

Every property takes its value in one of three ways: from a texture, from a factor written as plain numbers in the material, or from both, in which case the factor multiplies what the texture supplies. A property given neither keeps its default. Two properties may share one image by reading different channels of it, which is exactly how metallic and roughness are stored.

| Property | What it means | Where its value comes from | Encoding |
|---|---|---|---|
| Base color | The surface's own color, with no lighting in it at all | `baseColorTexture`, whose image has four channels at 8 bits each, and/or `baseColorFactor`, four numbers from 0 to 1 | Image sRGB, factor linear |
| Metallic | Whether this is metal. In reality nearly binary, so the map is close to a mask | The blue channel of `metallicRoughnessTexture`, and/or `metallicFactor`, one number from 0 to 1 | Linear |
| Roughness | How scattered the reflection is. Low is mirror-like, high is matte | The green channel of that same `metallicRoughnessTexture`, and/or `roughnessFactor`, one number from 0 to 1 | Linear |
| Normal | Fine surface detail, faked without adding geometry | `normalTexture`, whose image has three channels holding a vector rather than a color, in tangent space | Linear |
| Occlusion | How much ambient light reaches into a crevice | The red channel of `occlusionTexture`, 0 fully occluded to 1 unoccluded | Linear |
| Emissive | Light the surface gives off by itself | `emissiveTexture`, three channels at 8 bits each, and/or `emissiveFactor`, three numbers from 0 to 1 | Image sRGB, factor linear |

Occlusion, roughness and metalness are designed to share one image, packed into its red, green and blue channels, which is why a delivery holds fewer image files than the material has properties. That image may carry more than 8 bits per channel, while base color and emissive must be 8-bit. glTF sets no hard limit on image dimensions, but clients are told to resize images whose sides are not powers of two on hardware that handles them poorly, so powers of two stay the safe choice. Every image in this library already is one.

### The four terms in that table (reference)

**Factor.** A number, or a small group of numbers, stored as plain values in the material itself rather than in an image, each from 0 to 1. Where both a factor and a texture are given, the factor multiplies the texture, so it acts as a uniform tint or level across the whole material. Where no texture is given the texture is taken to be 1.0, and the factor alone decides the value. This is why `metallicFactor` on its own can make an entire part metal with no texture involved, which is the defect in four of our files.

A fair question is whether a factor is just a 1x1 image. It is not, and the difference matters twice over. A factor is decoded by nobody: it is already linear, whereas a base color image is sRGB and must be decoded before it is multiplied in, so the same value in the two places produces different results. And a factor is not a texture, so it does not satisfy a consumer that insists on one. That distinction is exactly why the fix for the RViz crash was to bake a 1x1 white image into the file rather than simply set a factor: RViz needed a base color texture to exist, and a factor would not have done.

**Linear.** The stored number is proportional to the physical quantity, so 0.5 means half. Used for everything the shader computes with: metalness, roughness, occlusion and normals. Averaging two linear values gives a meaningful result, which matters because that is what filtering and mipmapping do.

**sRGB.** A deliberately non-linear encoding for images meant to be seen as color. It spends more of the available 8 bits on darker tones, where human vision discriminates better. A renderer must decode it to linear before any lighting math and re-encode on output. It applies to base color and emissive only. Treating the other maps as sRGB is not a subtle error: it is what made Gazebo render every mesh too dark until it was fixed in 2023. Note also that glTF ignores any color profile or gamma embedded in a PNG or JPEG, so the encoding is decided by how the material refers to the image, never by the image file itself.

One trap worth naming: the base color texture is sRGB but the base color factor is linear. The renderer decodes the texture first, then multiplies. A factor picked by eye against an sRGB swatch will not do what it appears to.

**Tangent space.** The coordinate frame a normal map is expressed in, defined at each point by the surface normal and the directions the UV coordinates run. Storing the vectors relative to the surface, rather than to the model, is what lets one normal map be reused across different surfaces and survive the object being bent or animated. glTF stores the vector as RGB, red for X, green for Y, blue for Z, each mapped from the 0 to 1 range of the image into the -1 to 1 range of a vector component. That mapping is why an unperturbed normal map is the characteristic pale blue: it is the color of the vector pointing straight out of the surface.

The renderer takes those and computes the shading with a bidirectional reflectance distribution function, a BRDF. The glTF specification publishes the exact one in an appendix, so the computation is defined rather than left to each implementation.

Metallic and roughness replace the whole diffuse-plus-specular-plus-shininess apparatus. You no longer pick a specular color at all, because the model already knows that non-metals reflect white and metals reflect their own color.

## The differences that actually bite

Moving from the old model to this one is not a format conversion. Four things change in how a material is authored:

**Metallic is not a style choice.** It is a statement about what the object is. Get it wrong and the result is not slightly off, it is unrecognizable: a plastic hull declared metallic renders dark and lifeless under every light. This is not hypothetical. Four of the fifteen delivered parts in this library currently have it wrong, including both chassis.

**Defaults are aggressive.** In glTF a material that says nothing is white, fully metallic and fully rough. Silence does not mean neutral, it means rough metal. A primitive with no material assigned at all gets exactly that, which is why an unassigned region shows up as a pale metallic patch rather than disappearing.

**Lighting must come out of the base color.** Painted-in shadows and highlights now fight the renderer's own lighting, and the result is worse than either alone. Base color should look flat and slightly boring in isolation. If it looks good on its own, it probably has lighting baked in.

**A material is a set, not an image.** Where one PNG used to be the whole story, a material is now several maps with defined roles, plus scalar factors that multiply them. In this library, textures are 59 percent of every byte stored, which is a direct consequence.

## Why glTF and PBR cannot be separated

It would be reasonable to assume glTF is a container format that happens to support PBR. It is not.

**glTF 2.0 has exactly one material model, and it is metallic-roughness.** The specification says so directly: "glTF defines materials using a common set of parameters that are based on widely used material representations from Physically Based Rendering (PBR). Specifically, glTF uses the metallic-roughness material model." There is no Phong material to fall back to. The one alternative workflow that ever existed, specular-glossiness, is now in the archived section of the Khronos extension registry.

More than that, glTF fixes the *encoding*, not just the concept. Two tools both claiming to support PBR can still disagree about everything that matters. glTF settles it normatively: which channel holds what, with occlusion in red, roughness in green and metalness in blue; which images are color and which are data, with base color and emissive in sRGB and everything else linear; that normal maps are tangent space with the OpenGL convention; that scalar factors multiply their maps; and what every default is when a field is absent.

A glTF material is therefore portable where a vague agreement to "use PBR" is not.

The practical consequence for this project. Choosing glTF was not choosing a new file container for the meshes we already had. It was adopting a different way of describing surfaces, one where the old habits, painting in highlights, tuning a specular value, treating one image as the material, are not merely discouraged but unrepresentable. The parts that were converted without that shift in mind are the ones this review found defects in.

## Where to go next

- [model-spec.md](model-spec.md) states what a delivered model must satisfy, including the material rules.
- [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md) has the evidence, the measurements of the current library, and what our two renderers actually do with a PBR material, which is less than the specification describes.
- The [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) is readable, and its materials chapter is short.
- The [Khronos glTF Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/) will show any file as a conformant renderer sees it, and runs the validator at the same time.
