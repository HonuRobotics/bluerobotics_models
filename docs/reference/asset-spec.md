# Visual asset spec

What we expect from a visual mesh delivered for the parts library, whether
from an artist or a contributor. Collision meshes are separate, simplified
STL files and are not covered here. Every rule below is enforced by how
Gazebo's glTF loader actually behaves; the parenthetical defects are real
ones found auditing the current chassis meshes.

## Files

| | |
|---|---|
| Format | glTF 2.0 binary (`.glb`), textures embedded |
| Name | `<part>.visual.glb`, next to `<part>.collision.stl` |
| Budget | about 25k triangles per part; textures 2048 px or smaller, PNG |

Name meshes, nodes and materials after the component they cover
(`acrylic_tube`, `buoyancy_foam`, `thruster_guard`), never after a color
and never a modeler default. Mesh names are addressable from SDF as
submeshes, so they are part of the interface (defect found: both chassis
meshes are named `Cube.001` and `Cube.018`, and the BlueROV2 materials are
named for their colors).

## Units, frame, origin

- Meters, at real world scale. Dimensions are checked against the
  datasheet; the BlueROV2 chassis measures its 457 x 338 x 254 mm exactly,
  and yours should hold to the same standard.
- Author to the glTF spec: +Y up, +Z forward, no baked rotation nodes. The
  part macros rotate the visual into the Z up robot frame (`gltf_up` in
  `parts.xacro`), so a file that looks correct in a standard glTF viewer
  is correct here. Do not "fix" the orientation for Gazebo yourself.
- Author the mesh in the **part frame**: the frame the part's macro
  expresses `attach`, `slots` and `frames` in. Where the origin sits
  within the part is the part author's choice (a chassis at hull center,
  a camera at its body center); the macro's `attach` vector folds it into
  the mounting joint. What matters is that mesh and macro use the same
  frame, and that the choice is stated in the part's macro comment so
  a replacement mesh can be authored to it.

## Geometry

- Authored normals with deliberate hard edges; no degenerate triangles.
- One UV set, inside [0, 1]. A second UV set only for a baked ambient
  occlusion lightmap, which is the one place Gazebo reads it.
- Export tangents whenever a normal map is present. Gazebo does not
  generate them, and normal mapping without them shades wrong (defect
  found: both chassis meshes carry normal maps and no tangents).

## Materials

Metallic roughness workflow only. **Every primitive must have a material
assigned**: one without falls back to the glTF default, which is full
metal and renders differently in every engine (defect found: a fifth of
the BlueROV2 chassis has no material).

| Map | Notes |
|---|---|
| base color | PNG; alpha channel only under the transparency rules below |
| ORM | one packed texture: occlusion in R, roughness in G, metalness in B |
| normal | tangent space, PNG; JPEG block artifacts are visible in shading |
| emissive | optional, for LEDs and lit rings; 0 to 1 only, no HDR strength |

Metalness is black on plastics and composites, white only on true metal.
A saturated metalness channel is why a model renders dark in every viewer
(defect found: the BlueBoat shipped with metalness at 1.0 across the
entire hull).

## Transparency

Gazebo supports two of glTF's three alpha modes, so transparency is
planned per material, never painted per pixel.

- **Cutouts** (vents, mesh guards, perforations): `alphaMode: MASK`,
  cutoff 0.5, binary alpha in the base color texture. Fully supported per
  pixel.
- **Glass and acrylic** (the BlueROV2 electronics tube): give the region
  its own material with a uniform `baseColorFactor` alpha and
  `alphaMode: BLEND`. Gazebo applies the uniform opacity to the whole
  material.
- **Not available**: gradient transparency painted into an alpha texture.
  And never tag an opaque part BLEND: viewers move it to the translucent
  pass, where it renders ghostly (defect found: the whole BlueBoat is one
  BLEND material for the sake of a 0.3% cutout region that MASK would
  serve better).

## Do not use

Material extensions (clearcoat, sheen, transmission, anisotropy, texture
transform), the specular glossiness workflow, Draco compression,
KTX2/Basis textures, and animations, cameras or lights inside the file.
Gazebo's loader ignores all of them, silently.

## Checklist before delivery

1. Open the file in the [Babylon sandbox](https://sandbox.babylonjs.com)
   and walk the inspector: every primitive has a material, alpha modes
   match the rules above, names are component names.
2. `f3d part.visual.glb`: renders dark means a metalness defect; renders
   ghostly means a BLEND defect.
3. Dimensions match the datasheet, and the mesh is authored in the same
   part frame the part's macro uses.
4. Tangents exported if any material has a normal map.
