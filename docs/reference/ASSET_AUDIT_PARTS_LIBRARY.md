# Parts Library Audit

> **Reproduced source document, not project truth.** This is one of the "Visual asset audit · bluerobotics_models" reports, produced with Claude on 2026-09-03 and delivered as a browser artifact. The text below is reproduced from that artifact unedited, including its errors, so that the audit trail has a fixed copy to cite. Its measurements were re-checked and its verdicts re-judged in [VISUAL_ASSET_PIPELINE_REVIEW.md](VISUAL_ASSET_PIPELINE_REVIEW.md), section 6.1; read that before acting on anything here. In particular the tangents column is not a defect, the report covers 13 parts rather than the 12 its subtitle claims, and "26 images" is 28.

Visual asset audit · bluerobotics_models

the 12 GLB parts beyond the two chassis · `bluerobotics_parts/models/`

audited 2026-09-03 against `docs/reference/asset-spec.md` · companion reports: BlueBoat Chassis Audit, BlueROV2 Chassis Audit

The small parts are in better shape than the chassis — their defects are pipeline settings, not modeling. No orphan primitives, no BLEND misuse, no degenerate triangles, tidy budgets, and consistently good material names. But one exporter preset (tangents off, JPEG on) touched every file, and the saturated metalness bug struck three more parts. Fix the preset once and re-export, and most of this table turns green.

## Per part

| Part | Tris | Mesh name | Textures | Metalness | Tangents |
|---|---|---|---|---|---|
| t200_thruster | 1,860 | Cylinder.017 | 2 × 512² JPEG | PASS | MISSING |
| t200_prop_cw | 260 | Cylinder.016 | 2 × 512² JPEG | PASS | MISSING |
| t200_prop_ccw | 260 | Cylinder.015 | 2 × 512² JPEG | PASS | MISSING |
| m200_weedless_prop_cw | 388 | Cylinder.009 | 3 × 512² JPEG | PASS | MISSING |
| m200_weedless_prop_ccw | 388 | Cylinder.010 | 3 × 512² JPEG | PASS | MISSING |
| blueboat_antenna_mast | 2,756 | Cylinder.001 | 3 × 512² JPEG | PASS | MISSING |
| basestation_antenna | 942 | Cube.003 | 3 × 128×256 JPEG | SATURATED | MISSING |
| surveyor_multibeam | 725 | Cube.002 | 3 × 256² JPEG | SATURATED | MISSING |
| omniscan_450_sidescan | 748 | Cube.005 | 2 × 256² JPEG | SATURATED | NO NORMAL MAP |
| ping_singlebeam | 422 | Cylinder.004 | 2 × 256² JPEG | PASS | MISSING |
| blueboat_ping_singlebeam_mount | 806 | Cube.002 | 1 × 128² JPEG | PASS | NO NORMAL MAP |
| blueboat_payload_bracket | 1,703 | Cube.002 | 1 × 64² JPEG | PASS | NO NORMAL MAP |
| blueboat_flag | 164 | Cylinder.011 | 1 × 256² JPEG | PASS | NO NORMAL MAP |

## Units, frame, dimensions

| Part | Measured (mm) | Check |
|---|---|---|
| t200_thruster | 112.8 × 97.1 × 96.6 | Datasheet says 113 mm long, ~100 mm diameter — matches — PASS |
| t200_prop_cw / ccw | 73.0 mm disc, both | Identical dims, mirrored centers — a proper handed pair — PASS |
| m200_weedless_prop_cw / ccw | 110.3 mm disc, both | Identical dims, mirrored — proper pair — PASS |
| basestation_antenna | 121 × 953 × 140 | ~1 m directional antenna, plausible — PASS |
| blueboat_antenna_mast | 74 × 862 × 81 | Plausible mast height — PASS |
| blueboat_flag | 17 × 1004 × 305 | ~1 m pole with flag, plausible — PASS |
| ping_singlebeam | 50 × 71 × 41 | 50 mm housing diameter matches the Ping — PASS |
| omniscan_450_sidescan | 333 × 32 × 62 | Plausible — PASS |
| surveyor_multibeam | 191 × 56 × 91 | Plausible — PASS |
| blueboat_payload_bracket | 75 × 50 × 300 | Plausible — PASS |
| blueboat_ping_singlebeam_mount | 241 × 55 × 44 | Plausible — PASS |

All 12 parts are authored Y up with heights on the Y axis, consistent with the chassis convention. One observation: the three T200 files carry a small baked node translation (2.8 mm in x, −2.9 mm in z), identical across thruster and both props — it looks like a deliberate axis alignment, but it is the only place in the library where the file's node transform is not identity, and worth a comment in the part macro so nobody "cleans" it away.

## Where the library is already clean

| Requirement | Measured across all 12 | Status |
|---|---|---|
| Every primitive has a material | No orphan primitives anywhere (unlike the BlueROV2 chassis) | PASS |
| No BLEND misuse | Every material OPAQUE (unlike the BlueBoat chassis) | PASS |
| No degenerate triangles | Zero across all 12 files | PASS |
| Authored normals | Unit length in every primitive of every file | PASS |
| UVs in [0, 1] | All files in range (unlike the BlueROV2's 1.02 spill) | PASS |
| Triangle budgets | 164 to 2,756 per part; whole library is 10.7k tris | PASS |
| Material names | Consistently component names: Thruster, Antenna, Sonar, Payload-Bracket… | PASS |
| Avoid list | No extensions, Draco, KTX2, animations, cameras or lights in any file | PASS |

## Systemic defects (pipeline, not per part)

1. **Normal maps without tangents** — 9 of 12 files. Every part that carries a normal map lacks the TANGENT attribute. One exporter checkbox, missed on every export. Gazebo does not generate tangents.
2. **Every texture is JPEG** — 12 of 12 files, 26 images. Not one PNG in the library. Acceptable for base color, visibly wrong for normal maps (8×8 block artifacts appear in shading).
3. **Saturated metalness** — 3 parts. basestation_antenna, surveyor_multibeam and omniscan_450_sidescan have their metalness channel at ~1.0, the same renders-dark bug as the BlueBoat hull. Plastic housings declared solid metal.
4. **Blender default mesh names** — 12 of 12. Cube.002, Cylinder.017… while the material names show the naming discipline existed; it just never reached the meshes.

## Fixes, in priority order

1. Fix the export preset once — tangents on, PNG for normal maps — and re-export all 12. This clears the two biggest columns in one pass.
2. Blacken the metalness channel on the three saturated parts (or set `metallicFactor: 0` as a stopgap).
3. Rename meshes to component names during the re-export pass.
4. Migrate the two DAE stragglers — `ping360.dae` and `bluerov2_heavy.dae` — into the same GLB pipeline so the whole library is one format.

`bluerobotics_parts/models/*/*.visual.glb` · all files Khronos glTF Blender I/O v5.1.20 · measured with a direct GLB parse (accessors, textures, channels)
