# GLB content inventory: mesh and texture

Measured 2026-09-07 over the fifteen delivered `bluerobotics_parts/models/*/*.visual.glb`, on the files as committed. This document is the evidence behind the T4 budget row of [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md) and the input to section 10, decisions 4 (texture format and size caps) and 5 (triangle budget). It measures; it does not judge. Nothing here is a rule, and no threshold in it has been agreed.

The question it answers is what is actually inside the files: how much of each one is geometry and how much is texture, what resolution each map is, and how that resolution relates to the surface it covers. The last part is the reason the inventory exists. A pixel count on its own says nothing about whether a map is over- or under-sampled, because the same 2048 texture is a different resolution on a 1.2 m hull than on a 50 mm sonar. The measure that compares across parts is texels per millimeter of surface, and it is the one number here that the existing audits never had.

## Glossary

The first four words are used interchangeably in most conversations about textures, which causes confusion. The last four name what the Prims and Mats columns count: primitives and materials, plus the mesh that groups them and the node that places it. They are also the vocabulary of the review's unresolved question about what "one mesh" means, whose four candidate answers are one file, one node, one mesh and one primitive (section 10, decision 15).

Everything in a glTF file refers to everything else by integer array index, so where an entry below says one thing points at another, what is in the file is a number: `"material": 0` on a primitive means `materials[0]`, and `"mesh": 0` on a node means `meshes[0]`. There are no names or pointers in these references; the names that do exist are labels, and nothing resolves by them.

- **image** — the encoded PNG or JPEG bytes held in the file, glTF's `images` array. An image has a pixel size and a format and nothing else; it does not know what it will be used for. This is what the Imgs column counts and what Tex KB weighs.
- **texture** — one image plus one sampler, which is glTF's `textures` array. The sampler says how the image is filtered and wrapped when it is read, so a texture is a way of reading an image, and two textures can share one image and read it differently. "Texture" is also the ordinary English word for the whole subject, and it is used that way below in phrases like texture memory and texture budget.
- **map** — a texture used for a particular purpose in a material: base color map, normal map, metallic-roughness map. This is where the meaning lives, because the purpose is what makes a pixel count adequate or not. The same 512-pixel image is a serviceable base color map and an unusably coarse normal map. glTF defines exactly five purposes and names each material property after what the property holds rather than after the job it does, so `baseColorTexture` is the property holding the texture used for base color, `normalTexture` the one holding the texture used as a normal map, and so on through `metallicRoughnessTexture`, `occlusionTexture` and `emissiveTexture`. Their names end in "Texture" for that reason. They are properties of the material, not textures themselves, and what fills one is a reference to an entry in the `textures` array.
- **texel** — one pixel of a map, counted where it lands on the surface rather than where it sits in the image. Texels/mm is a property of the map, not of the image, because it depends on the UV layout as much as on the pixel count.
- **node** — an entry in the scene graph, carrying a transform and optionally pointing at a mesh. Its name is what Gazebo uses to name the submesh.
- **mesh** — glTF's `meshes` array: a named group of primitives, with no transform of its own. The node that points at it supplies the placement.
- **primitive** — one draw call's worth of geometry inside a mesh: a set of vertex attributes, an index buffer and at most one material. A part with two materials must have two primitives, because glTF gives no other way to express it.
- **material** — a block of PBR parameters: the factors, the alpha mode, and the five map properties above. A primitive names at most one material, and all of its triangles are shaded with that one; a primitive naming none renders as white metal.

There is no word here for the five material properties taken as a set, and this document does not coin one. They are referred to as the five map types, which is what the columns of the second table are. In particular "slot" is left alone: everywhere else in these docs it means a mounting point a chassis declares for a part, and borrowing it here would put two unrelated meanings in one document set.

So texture and map are not synonyms in general. In these fifteen files they happen to coincide exactly: 33 images, 33 textures, 33 maps, with no image shared between two maps and no texture read two ways. That is a fact about the current library, not a rule, and it is why the Imgs column and the map-type table agree. A redelivery that packed occlusion, roughness and metalness into one image, as [model-spec.md](model-spec.md) section 8 allows, would break the correspondence at once: one image, one texture, two maps.

## How the numbers were made

`bluerobotics_parts/scripts/glb_inventory.py` parses the JSON chunk, reads the accessors and decodes the embedded images. It runs on the host, needs no Gazebo and no GPU, and regenerates every table below:

```bash
cd bluerobotics_parts
scripts/glb_inventory.py models/*/*.visual.glb        # the tables
scripts/glb_inventory.py --json models/*/*.visual.glb # the raw measurements
```

Definitions of the derived columns, which are new here; the vocabulary itself is above:

- Tex KB and Geom KB split each file at the embedded images. Geometry here is everything that is not an image: the accessors, the JSON chunk and the container.
- Decoded MB is the uncompressed RGBA footprint of every image in the file, width times height times four. It is what the GPU spends and what the encoded byte count in the file hides. Base color and normal maps carry mipmaps on top of it, roughly a third again; roughness and metalness maps do not, since gz-rendering builds none for them (review section 1.4).
- Texels/mm is the square root of texels per square millimeter of surface, area-weighted across the primitives of the part, measured against the largest map on each material. Largest rather than base color because the BlueROV2 frame carries a 1×1 base color bake beside a 2048 normal map, and the 2048 is what the surface is really sampled at.
- UV fill is the fraction of the map the UV shells land on. A low fill at a high pixel count is texture memory paid for and not used. It assumes no overlapping shells, so a part that deliberately reuses one region for several faces will read low.
- Extent is the axis-aligned bounding box in the file's own Y-up frame, so length on X, height on Y, width on Z.

## The inventory

### Per part: geometry and texture content

| Part | File KB | Prims | Verts | Tris | Index | Attributes | Mats | Imgs | Tex KB | Tex % | Geom KB |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|
| basestation_antenna | 43 | 1 | 979 | 942 | uint16 | NRM, POS, UV0 | 1 | 3 | 5 | 12 | 38 |
| blueboat_antenna_mast | 141 | 1 | 2,781 | 2,756 | uint16 | NRM, POS, UV0 | 1 | 3 | 37 | 26 | 105 |
| blueboat_chassis | 2917 | 1 | 10,455 | 10,668 | uint16 | NRM, POS, UV0 | 1 | 3 | 2526 | 87 | 391 |
| blueboat_flag | 15 | 1 | 298 | 164 | uint16 | NRM, POS, UV0 | 1 | 1 | 3 | 23 | 12 |
| blueboat_payload_bracket | 69 | 1 | 1,814 | 1,703 | uint16 | NRM, POS, UV0 | 1 | 1 | 1 | 1 | 68 |
| blueboat_ping_singlebeam_mount | 33 | 1 | 827 | 806 | uint16 | NRM, POS, UV0 | 1 | 1 | 1 | 3 | 32 |
| bluerov2_chassis | 1299 | 7 | 31,695 | 21,776 | uint16 | NRM, POS, UV0 | 6 | 2 | 174 | 13 | 1125 |
| m200_weedless_prop_ccw | 42 | 1 | 431 | 388 | uint16 | NRM, POS, UV0 | 1 | 3 | 25 | 58 | 18 |
| m200_weedless_prop_cw | 42 | 1 | 431 | 388 | uint16 | NRM, POS, UV0 | 1 | 3 | 25 | 58 | 18 |
| omniscan_450_sidescan | 38 | 1 | 804 | 748 | uint16 | NRM, POS, UV0 | 1 | 2 | 7 | 17 | 31 |
| ping_singlebeam | 28 | 1 | 496 | 422 | uint16 | NRM, POS, UV0 | 1 | 2 | 8 | 30 | 20 |
| surveyor_multibeam | 44 | 1 | 907 | 725 | uint16 | NRM, POS, UV0 | 1 | 3 | 9 | 21 | 34 |
| t200_prop_ccw | 34 | 1 | 302 | 260 | uint16 | NRM, POS, UV0 | 1 | 2 | 22 | 63 | 13 |
| t200_prop_cw | 34 | 1 | 302 | 260 | uint16 | NRM, POS, UV0 | 1 | 2 | 22 | 63 | 13 |
| t200_thruster | 100 | 1 | 1,767 | 1,860 | uint16 | NRM, POS, UV0 | 1 | 2 | 32 | 32 | 68 |
| **total (15)** | **4880** | **21** | **54,289** | **43,866** | | | **20** | **33** | **2896** | **59** | **1984** |

### Per part: texture resolution by map type

| Part | Base color | Normal | Metallic-roughness | Occlusion | Emissive | Decoded MB | Texels/mm | UV fill % | Extent mm (X x Y x Z) |
|---|---|---|---|---|---|---:|---:|---:|---|
| basestation_antenna | 128x256 JPEG | 128x256 JPEG | 128x256 JPEG | -- | -- | 0.4 | 0.2 | 16 | 121 x 953 x 140 |
| blueboat_antenna_mast | 512 JPEG | 512 JPEG | 512 JPEG | -- | -- | 3.0 | 1.0 | 34 | 74 x 862 x 81 |
| blueboat_chassis | 2048 PNG | 2048 JPEG | 2048 JPEG | -- | -- | 48.0 | 1.1 | 75 | 1192 x 692 x 925 |
| blueboat_flag | 256 JPEG | -- | -- | -- | -- | 0.2 | 0.7 | 67 | 17 x 1004 x 305 |
| blueboat_payload_bracket | 64 JPEG | -- | -- | -- | -- | 0.0 | 0.2 | 74 | 75 x 50 x 300 |
| blueboat_ping_singlebeam_mount | 128 JPEG | -- | -- | -- | -- | 0.1 | 0.4 | 50 | 241 x 55 x 44 |
| bluerov2_chassis | 1 PNG | 2048 JPEG | -- | -- | -- | 16.0 | 3.7 | 91 | 457 x 255 x 344 |
| m200_weedless_prop_ccw | 512 JPEG | 512 JPEG | 512 JPEG | -- | -- | 3.0 | 3.1 | 54 | 68 x 110 x 43 |
| m200_weedless_prop_cw | 512 JPEG | 512 JPEG | 512 JPEG | -- | -- | 3.0 | 3.1 | 54 | 68 x 110 x 43 |
| omniscan_450_sidescan | 256 JPEG | -- | 256 JPEG | -- | -- | 0.5 | 0.7 | 64 | 333 x 32 x 62 |
| ping_singlebeam | 256 JPEG | 256 JPEG | -- | -- | -- | 0.5 | 2.0 | 67 | 50 x 71 x 41 |
| surveyor_multibeam | 256 JPEG | 256 JPEG | 256 JPEG | -- | -- | 0.8 | 0.8 | 81 | 191 x 56 x 91 |
| t200_prop_ccw | 512 JPEG | 512 JPEG | -- | -- | -- | 2.0 | 4.3 | 65 | 31 x 73 x 70 |
| t200_prop_cw | 512 JPEG | 512 JPEG | -- | -- | -- | 2.0 | 4.3 | 65 | 31 x 73 x 70 |
| t200_thruster | 512 JPEG | 512 JPEG | -- | -- | -- | 2.0 | 1.9 | 69 | 113 x 97 x 97 |
| **total** | | | | | | **81.5** | | | |

### Every embedded image

| Part | Map | Image name | Format | Pixels | KB | Decoded KB |
|---|---|---|---|---|---:|---:|
| basestation_antenna | normal | Normal - Directional_Antenna | JPEG | 128x256 | 3 | 128 |
| basestation_antenna | baseColor | Albedo - Directional_Antenna | JPEG | 128x256 | 1 | 128 |
| basestation_antenna | metallicRoughness | Metallic - Directional_Antenna-Roughness - Direction_Antenna | JPEG | 128x256 | 1 | 128 |
| blueboat_antenna_mast | normal | Normal - Antenna | JPEG | 512 | 25 | 1024 |
| blueboat_antenna_mast | baseColor | Albedo - Antenna | JPEG | 512 | 7 | 1024 |
| blueboat_antenna_mast | metallicRoughness | Roughness - Antenna | JPEG | 512 | 5 | 1024 |
| blueboat_chassis | normal | Normal-USV | JPEG | 2048 | 280 | 16384 |
| blueboat_chassis | baseColor | Albedo-Blueboat-USV-Blue-Color | PNG | 2048 | 2182 | 16384 |
| blueboat_chassis | metallicRoughness | Metallic-USV.png-Roughness-Blue-USV | JPEG | 2048 | 65 | 16384 |
| blueboat_flag | baseColor | Albedo-Flag | JPEG | 256 | 3 | 256 |
| blueboat_payload_bracket | baseColor | Albedo-payload_bracket | JPEG | 64 | 1 | 16 |
| blueboat_ping_singlebeam_mount | baseColor | Albedo - Ping_Mount | JPEG | 128 | 1 | 64 |
| bluerov2_chassis | normal | Normal-BlueROV2 | JPEG | 2048 | 174 | 16384 |
| bluerov2_chassis | baseColor | baked_white_basecolor | PNG | 1 | 0 | 0 |
| m200_weedless_prop_ccw | normal | Normal-Propeller.png | JPEG | 512 | 15 | 1024 |
| m200_weedless_prop_ccw | baseColor | Albedo-Propeller.png | JPEG | 512 | 5 | 1024 |
| m200_weedless_prop_ccw | metallicRoughness | Roughness-Propeller.png | JPEG | 512 | 5 | 1024 |
| m200_weedless_prop_cw | normal | Normal-Propeller | JPEG | 512 | 15 | 1024 |
| m200_weedless_prop_cw | baseColor | Albedo-Propeller | JPEG | 512 | 5 | 1024 |
| m200_weedless_prop_cw | metallicRoughness | Roughness-Propeller | JPEG | 512 | 5 | 1024 |
| omniscan_450_sidescan | baseColor | Albedo - Side_Scan_Sonar | JPEG | 256 | 5 | 256 |
| omniscan_450_sidescan | metallicRoughness | Metallic - Side_Scan_Sonar-Roughness - Side_Scan_Sonar | JPEG | 256 | 2 | 256 |
| ping_singlebeam | normal | Normal - Sonar.png | JPEG | 256 | 6 | 256 |
| ping_singlebeam | baseColor | Albedo - Sonar | JPEG | 256 | 3 | 256 |
| surveyor_multibeam | normal | Normal - Surveyor | JPEG | 256 | 6 | 256 |
| surveyor_multibeam | baseColor | Albedo - Surveyor | JPEG | 256 | 2 | 256 |
| surveyor_multibeam | metallicRoughness | Metallic - Surveyor-Roughness - Surveyor | JPEG | 256 | 2 | 256 |
| t200_prop_ccw | normal | Normal-Thruster-Prop.png | JPEG | 512 | 17 | 1024 |
| t200_prop_ccw | baseColor | Albedo-Thruster-Prop.png | JPEG | 512 | 5 | 1024 |
| t200_prop_cw | normal | Normal-Thruster-Prop.png | JPEG | 512 | 17 | 1024 |
| t200_prop_cw | baseColor | Albedo-Thruster-Prop.png | JPEG | 512 | 5 | 1024 |
| t200_thruster | normal | Normal-Thruster.png | JPEG | 512 | 27 | 1024 |
| t200_thruster | baseColor | Albedo-Thruster | JPEG | 512 | 5 | 1024 |

## What the numbers say

Geometry is not the cost. All 43,866 triangles in the library occupy 1,984 KB, about 46 bytes each; the 33 images occupy 2,896 KB, 59 percent of every byte stored. Decoded, that asymmetry becomes the whole story: 81.5 MB of texture against a library that is 4.8 MB on disk, a factor of seventeen. Geometry decodes to roughly what it is stored as. This is the measurement behind the review's claim that texture resolution is the lever and vertex count is not.

Two files are the library. `blueboat_chassis` and `bluerov2_chassis` are 86 percent of the stored bytes and 79 percent of the decoded texture. Every other part together is under 700 KB. Any budget that binds on the thirteen accessories and not on the two chassis will change nothing.

The geometry is uniform to a degree worth recording. Every primitive in every file carries POSITION, NORMAL and TEXCOORD_0, indexed as uint16, and nothing else: no TANGENT anywhere, no second UV set, no vertex colors, no morph targets. Fourteen of the fifteen files are one node holding one mesh holding one primitive with one material. The exception is `bluerov2_chassis`, seven primitives across six materials under the node `Frame.001`, one of them (4,776 triangles, 22 percent of the part) carrying no material at all. That file is also the only one with two scenes.

The map types in use are narrower than the specification discusses. Fifteen base color maps, eleven normal, seven metallic-roughness, and no occlusion or emissive map anywhere in the library. The ORM packing allowance in [model-spec.md](model-spec.md) section 8 therefore describes something no delivered file does, and the occlusion-in-red convention has never been exercised.

Format is nearly uniform and probably unintentional: 31 JPEG against 2 PNG. The two PNGs are the `blueboat_chassis` base color, the only map in the library that carries alpha, and the 1×1 white bake inside `bluerov2_chassis`. Every normal map in the library is JPEG. Section 7.2 of the review established why — under the exporter's default the output format is inherited from the source image — which makes this a texture-authoring decision rather than an export-dialog one, and is the reason decision 4 cannot be settled by picking a checkbox.

### Map sizes are chosen by habit, not by part

The sizes cluster tightly: six base color maps at 512, four at 256, and the two chassis at 2048. Against surface area, that allocation is close to arbitrary. Texel density runs from 0.20 to 4.33 texels/mm, a spread of twenty-one to one, and it runs opposite to part size. The most densely textured parts in the library are the smallest, the two T200 propellers at 91 cm² and 4.3 texels/mm, and the least dense is the largest accessory, the basestation antenna at 1,349 cm² and 0.2. The chassis, the part a viewer looks at longest and closest, sits mid-pack at 1.1. What the numbers describe is a 512-pixel house default applied regardless of what it covers, with the two chassis promoted to 2048 by hand.

UV fill varies the same way and compounds it: 16 percent on the basestation antenna, which spends five sixths of its map on nothing, against 91 percent on the BlueROV2 frame and 75 percent on the BlueBoat hull.

### What a cap would actually do

Decoded texture memory under a flat per-map pixel cap, everything else unchanged:

| Rule | Decoded texture | Change |
|---|---:|---|
| Today | 81.5 MB | -- |
| Cap every map at 2048 | 81.5 MB | nothing; nothing exceeds it |
| Cap every map at 1024 | 33.5 MB | 59 percent saved, entirely from three chassis textures |
| Cap every map at 512 | 21.5 MB | a further 12 MB, spread over five parts |
| Cap every map at 256 | 7.2 MB | |

The 2048 cap already in the draft is not a constraint, since it is exactly the size of the largest maps delivered. Capping the two chassis at 1024 and leaving every other file untouched produces the same 33.5 MB as capping the whole library, because they hold the only 2048 maps that exist.

A density target is the other candidate rule, and it is the one that matches the intent, but it is expensive if applied as a floor rather than a ceiling. Sizing every part to a uniform target, rounded to a power of two and capped at 2048, gives 29 MB at 0.5 texels/mm, 116 MB at 1.0, and 225 MB at 2.0. Only the first is below where the library is today, because most parts currently sit under 1 texel/mm. That is the honest shape of the trade: the library is not over-textured on average, it is unevenly textured, and leveling it up costs more memory than the two chassis are costing now.

### For the triangle budget

The draft's 25,000 triangles binds on nothing. The largest part is `bluerov2_chassis` at 21,776, the next is `blueboat_chassis` at 10,668, and every one of the thirteen accessories is under 3,000. Triangle density per unit of surface spans 0.2 to 3.7 triangles per cm² and, like texel density, tracks nothing in particular. A budget stated in triangles will not constrain the files it should and will not catch the defect the library actually has, which is 22 percent of the BlueROV2 frame carrying no material.

## The two COLLADA parts, for scale

`ping360.dae` and `bluerov2_heavy.dae` are the two parts not yet on the GLB pipeline (review section 9.5). They are not in the tables above because the tool reads glTF, but they belong in any conversation about budgets:

| Part | Format | Bytes | Triangles | Bytes/triangle | Textures |
|---|---|---:|---:|---:|---|
| ping360 | COLLADA | 4,102 KB | 39,998 | 103 | none |
| bluerov2_heavy_chassis | COLLADA | 24,669 KB | 168,384 | 147 | none |
| all fifteen GLB parts | GLB | 4,880 KB | 43,866 | 46 (geometry only) | 33 embedded |

The two of them together are 28.8 MB and 208,382 triangles: six times the bytes and nearly five times the triangles of the entire GLB library, with no textures at all. Whatever budget the team settles on, these two are the files it will bind on first, and re-exporting them is a larger job than any threshold discussion.

## What this inventory does not measure

It reads the file, not the render. It does not decode pixels beyond the image header, so it says nothing about the saturated metalness channels or the constant-color albedos that the review measures in section 4. It does not detect overlapping UV shells, so UV fill is an upper bound on waste. It does not model mipmaps, samplers or the format the driver finally uploads, so decoded MB is a comparable figure rather than a prediction of VRAM. And, as the review says of this whole row, it cannot say what any of these numbers ought to be. Establishing that means measuring load time, memory and frame rate in Gazebo on the hardware we run, with geometry cost separated from texture cost, and that work has not been done.
