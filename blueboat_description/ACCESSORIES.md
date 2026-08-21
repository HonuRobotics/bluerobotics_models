# BlueBoat parts and loadouts

The BlueBoat is assembled from the part library in
[`bluerobotics_parts`](../bluerobotics_parts): `config/blueboat.yaml` lists
the parts and where they mount, and the URDF, the composed Gazebo model and
the ros_gz bridge config all regenerate from it at build time. The shipped
config is the default loadout (chassis, two outboards, flag, Ping2 kit) and
needs no editing to use the boat.

## Sockets on the chassis

The chassis part declares these mount points (frames `base_link_<socket>`,
see `bluerobotics_parts/urdf/blueboat_chassis.urdf.xacro`):

| Socket | Where | Typical part |
|--------|-------|--------------|
| `motor_port`, `motor_stbd` | propeller centers in the stern pods | `m200_weedless_prop_ccw` / `_cw` (`joint: continuous`) |
| `mast_socket` | top of the aft crossbeam, centerline | `blueboat_antenna_mast` |
| `flag_socket` | aft crossbeam, port side | `blueboat_flag` |
| `payload` | top of the forward crossbeam | `blueboat_payload_bracket` |
| `ping_mount` | inner face of the starboard hull, low, mid hull | `blueboat_ping_singlebeam_mount`, then `ping_singlebeam` on its `sensor` socket |

Any part can also be placed at an explicit `xyz`/`rpy` relative to its
parent link, and parts can parent to other parts (`parent: ping_mount`).

## Catalog

Every `type` below is a macro in `bluerobotics_parts/urdf/parts.xacro`.

| `type` | Part | Product page | In simulation |
|--------|------|--------------|---------------|
| `blueboat_chassis` | hull with both thruster bodies | [BlueBoat](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | the base; displacement declared at the assembly |
| `m200_weedless_prop_cw`, `m200_weedless_prop_ccw` | weedless propellers | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/weedless-propeller-set/) | spin on the motor joints, driven by the Thruster plugin |
| `blueboat_flag` | flag | [components](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | geometry |
| `blueboat_antenna_mast` | antenna and accessory mast | [link](https://bluerobotics.com/store/boat/blueboat-antenna-and-accessory-mast/) | geometry |
| `basestation_antenna` | BaseStation directional antenna kit | [link](https://bluerobotics.com/store/boat/blueboat-accessories/basestation-directional-antenna-kit/) | geometry |
| `blueboat_payload_bracket` | payload bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/payload-bracket/) | geometry |
| `blueboat_ping_singlebeam_mount` | Ping2 integration kit bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/blueboat-ping2-integration-kit/) | geometry; offers the `sensor` socket |
| `ping_singlebeam` | Ping2 echosounder | [link](https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/) | single-beam range sensor (`/<ns>/<name>/range`) |
| `omniscan_450_sidescan` | Cerulean Omniscan 450 side-scan sonar | [link](https://bluerobotics.com/store/the-reef/cerulean-sidescan-sonar/) | geometry only (no acoustic model on this Gazebo) |
| `surveyor_multibeam` | Cerulean Surveyor 240-16 multibeam | [link](https://bluerobotics.com/store/sonars/echosounders/cerulean-surveyor-240-16-multibeam-echosounder/) | geometry only, as above |
| `t200_thruster`, `t200_prop_cw`, `t200_prop_ccw` | T200 thruster body and propellers | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/t200-thruster-r2-rp/) | general parts (the BlueBoat chassis already carries its thruster bodies) |

Sensor *behavior* (the echosounder range output) lives in `blueboat_gazebo`;
this package provides geometry and frames. Parts delivered later appear here
as the catalog grows.
