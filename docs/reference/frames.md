# Frames

Published as TF by `robot_state_publisher` from the generated URDF (default
BlueBoat loadout):

| Frame | Kind | Notes |
|---|---|---|
| `base_link` | root link | the chassis part, in the frame the modeler delivered: origin at the mesh centroid, x forward, y left, z up; floats with its origin at the waterline |
| `motor_port`, `motor_stbd` | links, continuous joints `motor_*_joint` | propellers, spinning about x |
| `flag`, `ping_mount`, `ping` | links, fixed joints | one frame per fitted part, named after its slot or its `name` |
| `base_link_motor_port`, `base_link_motor_stbd`, `base_link_flag`, `base_link_mast`, `base_link_payload`, `base_link_ping_mount`, `ping_mount_ping` | massless links | one per slot a part declares, whether filled or not |
| `ping_beam` | massless link | the Ping's transducer face; `frame_id` of its range messages |
| `hull_displacement` | massless link | carries the pontoon buoyancy collisions |

In Gazebo every fixed joint is lumped into `base_link`; the names survive as
SDF frames, which is how sensors are placed. See
[Gazebo composition](../design/gazebo-composition.md).
