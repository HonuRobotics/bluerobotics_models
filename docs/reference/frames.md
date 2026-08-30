# Frames

Published as TF by `robot_state_publisher` from the generated URDF. The
frames follow the loadout: what exists is determined by the fitted parts,
and the names follow three patterns.

| Pattern | Kind | Meaning |
|---|---|---|
| `base_link` | root link | the chassis part: origin at the mesh centroid, x forward, y left, z up ([REP 103](https://www.ros.org/reps/rep-0103.html)); floats with its origin at the waterline |
| `<instance>` | link | one frame per fitted part, named after its slot or its `name` (`motor_port`, `thruster_1`, `ping`, `camera`); spinning parts sit on their continuous joint `<instance>_joint` |
| `<parent>_<slot>` | massless link | one per slot a part declares, whether filled or not (`base_link_motor_port`, `base_link_camera`, `ping_mount_ping`) |
| `<instance>_<frame>` | massless link | frames the part itself declares (`ping_beam`, the transducer face); sensor messages carry them as `frame_id`, resolved by TF |

The displacement volume is not in the URDF or TF: each Gazebo package adds
it to the composed model as a dedicated link (`hull_displacement` on the
boat, `buoyancy_displacement` on the ROV).

In Gazebo every fixed joint is lumped into `base_link`; the names survive as
SDF frames, which is how sensors are placed. See
[Gazebo composition](../design/gazebo-composition.md).
