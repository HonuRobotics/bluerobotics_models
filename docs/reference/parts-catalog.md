# Parts catalog and slots

Every part is a macro in `bluerobotics_parts/urdf/parts.xacro`; type names
are the directory names in `bluerobotics_parts/models/`.

## Catalog

| `type` | Part | Product page | In simulation |
|--------|------|--------------|---------------|
| `blueboat_chassis` | hulls, crossbeams and both thruster bodies | [BlueBoat](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | the base; displacement declared at the assembly |
| `m200_weedless_prop_cw`, `m200_weedless_prop_ccw` | weedless propellers | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/weedless-propeller-set/) | default motor occupants, driven by the Thruster plugin |
| `t200_prop_cw`, `t200_prop_ccw` | standard T200 propellers | [link](https://bluerobotics.com/store/rov/bluerov2-components-spares/t200-thruster-brov2-spare-r1-vp/) | alternative motor occupants |
| `t200_thruster` | T200 thruster body | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/t200-thruster-r2-rp/) | general part; the BlueBoat chassis already carries its bodies |
| `blueboat_flag` | flag | [components](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | geometry |
| `blueboat_antenna_mast` | antenna and accessory mast | [link](https://bluerobotics.com/store/boat/blueboat-antenna-and-accessory-mast/) | geometry |
| `basestation_antenna` | BaseStation directional antenna kit | [link](https://bluerobotics.com/store/boat/blueboat-accessories/basestation-directional-antenna-kit/) | geometry |
| `blueboat_payload_bracket` | payload bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/payload-bracket/) | geometry |
| `blueboat_ping_singlebeam_mount` | Ping2 integration kit bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/blueboat-ping2-integration-kit/) | geometry; declares the `ping` slot |
| `ping_singlebeam` | Ping2 echosounder | [link](https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/) | single beam range sensor at its `beam` frame |
| `omniscan_450_sidescan` | Cerulean Omniscan 450 side scan sonar | [link](https://bluerobotics.com/store/the-reef/cerulean-sidescan-sonar/) | geometry only |
| `surveyor_multibeam` | Cerulean Surveyor 240-16 multibeam | [link](https://bluerobotics.com/store/sonars/echosounders/cerulean-surveyor-240-16-multibeam-echosounder/) | geometry only |

Fourteen of the 28 cataloged parts (`bluerobotics_parts/models/parts.csv`)
are delivered so far; the rest (BlueROV2 chassis, gripper, cameras, DVL,
...) appear as they land.

## Slots

| Part | Slot | Accepts | Default | Joint |
|---|---|---|---|---|
| `blueboat_chassis` | `motor_port` | `m200_weedless_prop_ccw`, `t200_prop_ccw` | `m200_weedless_prop_ccw` | continuous |
| | `motor_stbd` | `m200_weedless_prop_cw`, `t200_prop_cw` | `m200_weedless_prop_cw` | continuous |
| | `flag` | `blueboat_flag` | `blueboat_flag` | fixed |
| | `mast` | `blueboat_antenna_mast` | none | fixed |
| | `payload` | `blueboat_payload_bracket` | none | fixed |
| | `ping_mount` | `blueboat_ping_singlebeam_mount` | `blueboat_ping_singlebeam_mount` | fixed |
| `blueboat_ping_singlebeam_mount` | `ping` | `ping_singlebeam` | `ping_singlebeam` | fixed |

Each slot is a TF frame named `<instance>_<slot>`; the occupant is named
after the slot by default.

## Frames

| Part | Frame | Meaning |
|---|---|---|
| `ping_singlebeam` | `beam` | transducer face, where the Gazebo sensor is placed (`<instance>_beam`, e.g. `ping_beam`) |

Slot poses, accepted types and defaults live in each part's `<part>_info`
macro (`bluerobotics_parts/urdf/<part>.urdf.xacro`); this page mirrors them.

## BlueROV2 parts

| Type | What | Notes |
|---|---|---|
| `bluerov2_chassis` | standard hull as one body, T200 bodies included | the assembly root; declares every slot |
| `bluerov2_heavy_chassis` | Heavy kit hull (8 thrusters) | placeholder mesh until the heavy shell is delivered |
| `t200_prop_ccw`, `t200_prop_cw` | T200 propellers | shared with the BlueBoat; drive table, continuous joints |
| `explorehd_camera` | exploreHD underwater camera | sensor part (camera) |
| `marinesitu_c3` | MarineSitu C3 stereo camera | sensor part (rgbd) |
| `ping360` | Ping360 scanning sonar | sensor part (planar gpu_lidar) |
| `dvl_a50` | Water Linked DVL A50 | sensor part (native DVL); backend loads only when fitted |
| `newton_gripper`, `sediment_sampler` | 1 DOF claws | multi body parts; cmd_pos controllers |
| `payload_skid`, `roof_rack` | payload skid, top rack | geometry only |
| `sonoptix_echo`, `omniscan_450_fs` | imaging sonars | geometry only (no acoustic model ships) |
