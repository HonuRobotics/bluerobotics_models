# BlueROV2 asset provenance

The meshes under `meshes/` are **temporary third-party placeholders**. They will
be replaced by our own PBR-textured assets produced by a 3D artist.

| File | Source | License |
|------|--------|---------|
| `meshes/bluerov2.dae` | [IOES-Lab/dave](https://github.com/IOES-Lab/dave) (`ros2` branch), `models/dave_robot_models/meshes/bluerov2/bluerov2.dae` | Apache-2.0 |
| `meshes/t200/ccw_prop.dae` | IOES-Lab/dave, `models/dave_robot_models/meshes/t200/ccw_prop.dae` | Apache-2.0 |
| `meshes/t200/cw_prop.dae` | IOES-Lab/dave, `models/dave_robot_models/meshes/t200/cw_prop.dae` | Apache-2.0 |
| `meshes/bluerov2_heavy.dae` | IOES-Lab/dave, `models/dave_robot_models/meshes/bluerov2_heavy/bluerov2_heavy.dae` | Apache-2.0 |
| `meshes/accessories/ping360.dae` | [CentraleNantesROV/bluerov2](https://github.com/CentraleNantesROV/bluerov2), `bluerov2_description/meshes/ping360_sonar.dae` (rescaled 0.01 at reference time) | Apache-2.0 |

DAVE is Apache-2.0 licensed, matching this repository, so redistribution is
permitted. The upstream BlueROV2 mesh was originally authored in Blender by
Blue Robotics and re-exported by the DAVE / orca4 communities.

Notes:
- The `.dae` files carry COLLADA-embedded solid/Phong materials only; there are
  **no PBR texture maps** (albedo/normal/metalness/roughness). We will author
  those ourselves.
- Reference model structure (link poses, inertias, thruster layout) was taken
  from DAVE's `bluerov2/model.sdf`.
