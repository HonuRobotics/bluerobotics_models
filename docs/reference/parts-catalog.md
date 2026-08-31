# Parts catalog and slots

Every part is a macro in `bluerobotics_parts/urdf/parts.xacro`; type names
are the directory names in `bluerobotics_parts/models/`. The chassis are
parts too: an assembly is a chassis plus whatever its slots carry.

## Catalog

| `type` | Part | Product page | In simulation |
|--------|------|--------------|---------------|
| `blueboat_chassis` | BlueBoat hulls, crossbeams and both thruster bodies | [BlueBoat](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | assembly root; displacement declared at the assembly |
| `bluerov2_chassis` | BlueROV2 standard hull (frame, tanks, foam) | [BlueROV2](https://bluerobotics.com/store/rov/bluerov2/) | assembly root; declares every slot including thruster bodies and propellers |
| `bluerov2_heavy_chassis` | BlueROV2 Heavy kit hull | [Heavy kit](https://bluerobotics.com/store/rov/bluerov2-accessories/brov2-heavy-kit/) | as the standard chassis with eight thruster and body slots |
| `m200_weedless_prop_cw`, `m200_weedless_prop_ccw` | weedless propellers | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/weedless-propeller-set/) | default BlueBoat motor occupants, driven by the Thruster plugin |
| `t200_prop_cw`, `t200_prop_ccw` | standard T200 propellers | [link](https://bluerobotics.com/store/rov/bluerov2-components-spares/t200-thruster-brov2-spare-r1-vp/) | default ROV propellers; alternative BlueBoat motor occupants |
| `t200_thruster` | T200 thruster body | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/t200-thruster-r2-rp/) | default occupant of the ROV thruster body slots; the BlueBoat chassis already carries its bodies |
| `blueboat_flag` | flag | [components](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | geometry |
| `blueboat_antenna_mast` | antenna and accessory mast | [link](https://bluerobotics.com/store/boat/blueboat-antenna-and-accessory-mast/) | geometry |
| `basestation_antenna` | BaseStation directional antenna kit | [link](https://bluerobotics.com/store/boat/blueboat-accessories/basestation-directional-antenna-kit/) | geometry |
| `blueboat_payload_bracket` | payload bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/payload-bracket/) | geometry |
| `blueboat_ping_singlebeam_mount` | Ping2 integration kit bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/blueboat-ping2-integration-kit/) | geometry; declares the `ping` slot |
| `ping_singlebeam` | Ping2 echosounder | [link](https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/) | single beam range sensor at its `beam` frame |
| `ping360` | Ping360 scanning sonar | [link](https://bluerobotics.com/store/sonars/imaging-sonars/ping360-sonar-r1-rp/) | planar scanning sensor |
| `dvl_a50` | Water Linked DVL A50 | [link](https://bluerobotics.com/store/the-reef/dvl-a50/) | native DVL sensor; its backend loads only when fitted |
| `explorehd_camera` | exploreHD underwater camera | [link](https://bluerobotics.com/store/sensors-cameras/cameras/deepwater-exploration-explorehd-usb-camera/) | camera sensor |
| `marinesitu_c3` | MarineSitu C3 stereo camera | [link](https://bluerobotics.com/store/the-reef/marinesitu-c3-stereo-camera/) | rgbd sensor; macro pending delivery |
| `newton_gripper` | Newton gripper | [link](https://bluerobotics.com/store/thrusters/grippers/newton-gripper-asm-r2-rp/) | one DOF claw with a position controller; macro pending delivery |
| `sediment_sampler` | Newton sediment sampler attachment | [link](https://bluerobotics.com/store/thrusters/grippers/newton-sediment-sampler-attachment/) | one DOF claw with a position controller |
| `payload_skid` | BlueROV2 payload skid | [link](https://bluerobotics.com/store/rov/bluerov2-accessories/brov-payload-skid/) | geometry |
| `roof_rack` | ROV roof rack | [link](https://bluerobotics.com/store/rov/bluerov2-accessories/rov-roof-rack/) | geometry |
| `omniscan_450_sidescan` | Cerulean Omniscan 450 side scan sonar | [link](https://bluerobotics.com/store/the-reef/cerulean-sidescan-sonar/) | geometry only |
| `surveyor_multibeam` | Cerulean Surveyor 240-16 multibeam | [link](https://bluerobotics.com/store/sonars/echosounders/cerulean-surveyor-240-16-multibeam-echosounder/) | geometry only |

Parts whose final mesh has not landed yet use placeholder geometry; a
`type` marked pending delivery cannot be fitted until its macro lands.

## Slots

Each slot is a TF frame named `<instance>_<slot>`; the occupant is named
after the slot by default.

### BlueBoat chassis

| Part | Slot | Accepts | Default | Joint |
|---|---|---|---|---|
| `blueboat_chassis` | `motor_port` | `m200_weedless_prop_ccw`, `t200_prop_ccw` | `m200_weedless_prop_ccw` | continuous |
| | `motor_stbd` | `m200_weedless_prop_cw`, `t200_prop_cw` | `m200_weedless_prop_cw` | continuous |
| | `flag` | `blueboat_flag` | `blueboat_flag` | fixed |
| | `mast` | `blueboat_antenna_mast` | none | fixed |
| | `payload` | `blueboat_payload_bracket` | none | fixed |
| | `ping_mount` | `blueboat_ping_singlebeam_mount` | `blueboat_ping_singlebeam_mount` | fixed |
| `blueboat_ping_singlebeam_mount` | `ping` | `ping_singlebeam` | `ping_singlebeam` | fixed |

### BlueROV2 chassis

| Part | Slot | Accepts | Default | Joint |
|---|---|---|---|---|
| `bluerov2_chassis` | `thruster_1` … `thruster_6` | `t200_prop_ccw` or `t200_prop_cw` per position | the matching propeller | continuous |
| | `thruster_body_1` … `thruster_body_6` | `t200_thruster` | `t200_thruster` | fixed |
| | `camera` | `explorehd_camera`, `marinesitu_c3` | `explorehd_camera` | fixed |
| | `sonar` | `ping360` | none | fixed |
| | `dvl` | `dvl_a50` | none | fixed |
| | `gripper` | `newton_gripper`, `sediment_sampler` | none | fixed |
| | `payload` | `payload_skid` | none | fixed |
| | `rack` | `roof_rack` | none | fixed |

`bluerov2_heavy_chassis` extends the pattern to `thruster_1` …
`thruster_8` and `thruster_body_1` … `thruster_body_8` and keeps the same
accessory slots.

(configuration-keys)=
## Configuration keys

The vehicle config (`<vehicle>_description/config/<vehicle>.yaml`, or any
file passed as `config_file:=`) is one YAML document, identical in shape
for both vehicles:

| Key | Required | Meaning |
|---|---|---|
| `topic_namespace` | no (the vehicle name) | prefix of every part topic: `/<ns>/<name>/...` |
| `base` | yes | the root part: `{type, name (default base_link), collision (default true)}` |
| `parts` | no (`[]`) | slot entries and free placements, see below |
| `slots` | no | ad hoc slots: `{of (instance, default base_link), name, xyz, rpy (default "0 0 0"), accepts (list, optional), default (type or none), joint}` |
| `hull_displacement` | BlueBoat | the box pontoons the Gazebo composition places on the `hull_displacement` link: `{length, width, height, x, y, z, segments}` |
| `buoyancy` | BlueROV2 | `{net_buoyancy (kg), cob_offset, cob_frame (com/base_link), fluid_density, footprint}`, realized as a dedicated displacement link solved from the assembled mass; see [Buoyancy](../design/buoyancy.md) |
| `extra_bridge_topics` | no | list appended verbatim to the generated ros_gz bridge config (native syntax) |

A **slot entry** in `parts` (has `slot`):

| Key | Meaning |
|---|---|
| `slot` | slot name on the carrying instance |
| `of` | instance carrying the slot (default: the base). Not `on`: YAML reads a bare `on` as `true` |
| `type` | a type the slot accepts, or `none` to leave it empty |
| `name` | instance name (default: the slot name); must be unique across the vehicle |
| `xyz`, `rpy` | offset from the slot pose (default zero) |
| `joint` | joint type for the occupant (default: the slot's, else `continuous` for a propeller, else `fixed`) |
| `axis` | joint axis override (default: the part's own spin axis) |
| `collision` | `false` to fit the part without its contact geometry |
| `topic`, `gz_topic`, `ros_topic`, `bridge` | parts with topics (propellers, sensors): topic base for both sides / one side, native bridge keys merged into the entry |

A **free placement** (no `slot`):

| Key | Meaning |
|---|---|
| `type`, `name` | required |
| `xyz`, `rpy` | pose relative to `parent` (`xyz` required) |
| `parent` | link to attach to (default: the base) |
| `joint`, `axis`, `collision`, topic keys | as above |

Resolution rules, including how defaults fill, are in
[Slots and assembly](../design/slots.md). Errors name the problem and fail
the build or launch; a key outside these tables is reported as a typo.
Avoid the other YAML 1.1 boolean words (`yes`, `no`, `off`, `y`, `n`) as
bare values too, or quote them.

## Frames

Published as TF by `robot_state_publisher` from the generated URDF. The
frames follow the fitted parts, with the same naming patterns on both vehicles:

| Pattern | Kind | Meaning |
|---|---|---|
| `base_link` | root link | the chassis part: origin at the mesh centroid, x forward, y left, z up ([REP 103](https://www.ros.org/reps/rep-0103.html)); floats with its origin at the waterline |
| `<instance>` | link | one frame per fitted part, named after its slot or its `name` (`motor_port`, `thruster_1`, `ping`, `camera`); spinning parts sit on their continuous joint `<instance>_joint` |
| `<parent>_<slot>` | massless link | one per slot a part declares, whether filled or not (`base_link_motor_port`, `base_link_camera`, `ping_mount_ping`) |
| `<instance>_<frame>` | massless link | frames the part itself declares (`ping_beam`, the transducer face); sensor messages carry them as `frame_id`, resolved by TF |

The displacement volume is not in the URDF or TF: each Gazebo package adds
it to the composed model as a dedicated link (`hull_displacement` on the
boat, `buoyancy_displacement` on the ROV). In Gazebo every fixed joint is
lumped into `base_link`; the names survive as SDF frames, which is how
sensors are placed. See
[Gazebo composition](../design/gazebo-composition.md).

Slot poses, accepted types and defaults live in each part's `<part>_info`
macro (`bluerobotics_parts/urdf/<part>.urdf.xacro`); this page mirrors them.
