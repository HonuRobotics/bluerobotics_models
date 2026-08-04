# BlueBoat accessories

Accessories are configured from `config/blueboat.yaml`. Each entry is
`{type, name, xyz, rpy}`; every `type` has a xacro macro in
`urdf/accessories.xacro`. The URDF, the composed Gazebo model and the ros_gz
bridge config all regenerate at build time when the config changes.

## Catalog

| `type` | Accessory | Product page | Notes |
|--------|-----------|--------------|-------|
| `flag` | Flag | [components](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | Pole + flag primitives. |
| `basestation_antenna` | BaseStation directional antenna kit | [link](https://bluerobotics.com/store/boat/blueboat-accessories/basestation-directional-antenna-kit/) | Full unit. |
| `antenna_mast` | Antenna and accessory mast | [link](https://bluerobotics.com/store/boat/blueboat-accessories/blueboat-antenna-and-accessory-mast/) | Full mast. |
| `ping_sonar` | Ping sonar altimeter/echosounder (Ping2) | [link](https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/) | Sensor only; simulated as a single-beam range sensor. |
| `ping_mount` | Ping integration kit | [link](https://bluerobotics.com/store/boat/blueboat-accessories/blueboat-ping2-integration-kit/) | Mount only. |
| `payload_bracket` | Payload bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/payload-bracket/) | Bracket only. |
| `omniscan_450` | Cerulean Omniscan 450 side-scan sonar | [link](https://bluerobotics.com/store/the-reef/cerulean-sidescan-sonar/) | Geometry only (no acoustic model on this Gazebo). |
| `surveyor_multibeam` | Cerulean Surveyor 240-16 multibeam | [link](https://bluerobotics.com/store/sonars/echosounders/cerulean-surveyor-240-16-multibeam-echosounder/) | Geometry only, as above. |

Sensor *behavior* (the echosounder range output) lives in `blueboat_gazebo`;
this package provides geometry and frames.
