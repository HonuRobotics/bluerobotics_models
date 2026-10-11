# BlueBoat Chassis Audit

> **Reproduced source document, not project truth.** This is one of the "Visual asset audit · bluerobotics_models" reports, produced with Claude on 2026-09-03 and delivered as a browser artifact. The text below is reproduced from that artifact unedited, including its errors, so that the audit trail has a fixed copy to cite. Its measurements were re-checked and its verdicts re-judged in [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md), section 6.2; read that before acting on anything here. In particular the tangents row is not a defect, the ORM row is over-strict, the 1.146 m hull length is not the published figure, and the headline PASS count does not match the rows.

Visual asset audit · bluerobotics_models

`blueboat_chassis.visual.glb` · 2.99 MB · Khronos glTF Blender I/O v5.1.20

audited 2026-09-03 against `docs/reference/asset-spec.md`

Geometry and scale are solid; the materials need one focused pass. A saturated metalness channel makes the whole boat render dark, and the hull-wide BLEND alpha makes it render ghostly. Both are quick fixes.

10 PASS · 3 PARTIAL · 5 FAIL

## Files

| Requirement | Measured | Status |
|---|---|---|
| GLB, textures embedded | glTF 2.0 binary; all 3 textures embedded | PASS |
| Component names | Mesh is `Cube.001`; material is the generic `USV Mat`<br>Texture names are good (`Albedo-Blueboat-USV-Blue-Color` etc.) | FAIL |
| ≤ 25k triangles | 10,668 triangles, 10,455 vertices, uint16 indices | PASS |
| Textures ≤ 2048 px, PNG | All three are 2048². Base color is PNG, but normal and metallic/roughness maps are JPEG<br>JPEG blocking is visible in normal-mapped shading | PARTIAL |

## Units, frame, origin

| Requirement | Measured | Status |
|---|---|---|
| Meters, real scale | 1.192 × 0.925 × 0.692 m (L × W × H); real hull is 1.146 m long | PASS |
| Y up, no baked rotation | Spec conforming; no rotation nodes; `gltf_up` in the macro handles Gazebo | PASS |
| Authored in the part frame | Origin at hull center (X and Z symmetric), matching the chassis macro | PASS |

## Geometry

| Requirement | Measured | Status |
|---|---|---|
| Authored normals | All unit length; hard edges present (54% unique positions from split verts) | PASS |
| No degenerate triangles | 2 zero-area triangles | PARTIAL |
| One UV set in [0, 1] | Single TEXCOORD_0, u ∈ [0, 0.98], v ∈ [0, 1] | PASS |
| Tangents with normal map | Normal map present, TANGENT attribute absent — Gazebo will not generate them | FAIL |

## Materials

| Requirement | Measured | Status |
|---|---|---|
| Every primitive has a material | 1 primitive, 1 material assigned | PASS |
| Metalness black on plastics | Metalness is 1.0 on 100% of pixels, factor defaults to 1.0 — the polyethylene boat is declared solid metal<br>This is why it renders dark in every PBR viewer and in Gazebo | FAIL |
| ORM packed, occlusion in R | Metal/rough texture exists (rough mean 0.93) but no occlusion anywhere, R channel unused, and no UV1 lightmap | FAIL |
| Normal map: tangent space, PNG | Valid tangent-space map (mean RGB 0.50/0.50/0.96) but JPEG | PARTIAL |
| Emissive for lit elements | None; the part has no LEDs | N/A |

## Transparency

| Requirement | Measured | Status |
|---|---|---|
| MASK for cutouts, BLEND only for uniform glass | The entire hull is one BLEND + double-sided material, serving a cutout region of 0.3% of the texture (0.2% partial pixels — effectively binary)<br>Ghostly in spec viewers; alpha silently ignored by Gazebo. MASK at cutoff 0.5 serves this content exactly | FAIL |

## Avoid list

| Requirement | Measured | Status |
|---|---|---|
| No extensions, Draco, KTX2, animations, cameras, lights | All absent; `extensionsUsed` is empty | PASS |

## Fixes, in priority order

1. Blacken the metalness channel on plastic (or set `metallicFactor: 0` as a stopgap). Highest visual impact.
2. Switch the material from BLEND to MASK, cutoff 0.5. Fixes the ghost look and makes the cutouts actually render in Gazebo.
3. Export tangents so the normal map shades correctly.
4. Re-export normal and ORM maps as PNG, and bake occlusion into the ORM R channel while re-authoring it.
5. Rename `Cube.001` and `USV Mat` to component names.
6. Remove the 2 degenerate triangles during the same pass.

`bluerobotics_parts/models/blueboat_chassis/blueboat_chassis.visual.glb` · measured with a direct GLB parse (accessors, textures, channels) · companion report: BlueROV2 Chassis Audit
