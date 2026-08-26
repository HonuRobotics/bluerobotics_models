# Package layout

| Package | Purpose |
|---------|---------|
| [`bluerobotics_parts`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/bluerobotics_parts) | the part library: one URDF xacro macro per part (`urdf/`), the modeler deliveries (`models/`: `.glb` meshes and `model.sdf`), the assembly dispatcher, the bootstrap and review tools |
| [`blueboat_description`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/blueboat_description) | the BlueBoat assembled from the parts: loadout config, the vehicle xacro, RViz launch; pure description, no simulator code |
| [`blueboat_gazebo`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/blueboat_gazebo) | Gazebo composition (thrusters, hydrodynamics, sensors), worlds, the sim launch, the generated ros_gz bridge config, `configure_vehicle.py` |
| [`bluerov2_description`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/bluerov2_description) | BlueROV2 description, assembled from the parts (standard and heavy) |
| [`bluerov2_gazebo`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/bluerov2_gazebo) | BlueROV2 Gazebo composition, world, launch and bridge |

## Generated artifacts

| Artifact | Generated | From |
|---|---|---|
| `blueboat_description/urdf/blueboat.urdf` | at build | the config and the parts (carries the `<assembly_part>` manifest) |
| `blueboat_gazebo/models/blueboat/blueboat.urdf` | at build | the same xacro with `gltf_up:=z` (glTF visuals pre-rotated for Gazebo) |
| `blueboat_gazebo/models/blueboat/model.sdf` (`model://blueboat`) | at build | the same config, merging that URDF and adding the hull displacement link, plugins and sensors |
| `blueboat_gazebo/config/ros_gz_bridge.yaml` | at build | the config and the URDF manifest |
| the same three | at launch, into a temp dir | `sim.launch.xml config_file:=` via `configure_vehicle.py` |
| `bluerobotics_parts/worlds/parts_check.sdf` | by a person, committed | the part macros (`parts_check_world.py`) |
| `bluerobotics_parts/urdf/<part>.urdf.xacro` | once, by a person, then maintained by hand | a modeler delivery (`sdf_to_part.py`) or written from scratch |

Each package keeps a short README pointing here; this site is the
documentation.
