# BlueBoat parts, slots and loadouts

The BlueBoat is assembled from the part library in
[`bluerobotics_parts`](../bluerobotics_parts). Parts declare **slots**: named
places where other parts fit, with the part types that fit and a default
occupant. Every slot fills itself with its default unless the config says
otherwise, so the zero configuration BlueBoat is complete: chassis, two
outboards, flag and the Ping2 integration kit (bracket plus Ping). The URDF,
the composed Gazebo model and the ros_gz bridge config all regenerate from
the config at build time.

## Slots on the chassis

Declared in `bluerobotics_parts/urdf/blueboat_chassis.urdf.xacro`; each is a
TF frame named `base_link_<slot>` and the occupant's instance is named after
the slot.

| Slot | Where | Accepts | Default |
|------|-------|---------|---------|
| `motor_port`, `motor_stbd` | propeller centers in the stern pods (continuous joints) | `m200_weedless_prop_ccw`/`_cw`, `t200_prop_ccw`/`_cw` | the M200 weedless props |
| `flag` | aft crossbeam, port side | `blueboat_flag` | `blueboat_flag` |
| `mast` | top of the aft crossbeam, centerline | `blueboat_antenna_mast` | none |
| `payload` | top of the forward crossbeam | `blueboat_payload_bracket` | none |
| `ping_mount` | inner face of the starboard hull, low, mid hull | `blueboat_ping_singlebeam_mount` | the bracket |

The bracket in turn declares `ping` (accepts `ping_singlebeam`, default
`ping_singlebeam`), so fitting the bracket fits the Ping. The Ping declares
the reference frame `beam` at its transducer face; the Gazebo sensor is
placed there.

## Changing the loadout

`config/blueboat.yaml`, `parts:` entries:

```yaml
parts:
  - {slot: motor_port, type: t200_prop_ccw}                   # another accepted option
  - {slot: ping_mount, type: none}                            # leave a slot empty (and its Ping)
  - {slot: mast, type: blueboat_antenna_mast}                 # fill a slot that has no default
  - {slot: ping, on: ping_mount, type: ping_singlebeam, topic: sonar}   # a slot on another part
  - {type: omniscan_450_sidescan, name: sidescan, xyz: "0.2 0.22 -0.03", rpy: "0 0 0"}  # free placement
slots:
  - {on: base_link, name: camera, xyz: "0.45 0 0.2", rpy: "0 0 0"}   # an ad hoc slot
```

A slot entry names the slot and, with `on:`, the instance carrying it
(default `base_link`); `type:` must be in the slot's accepts list, or `none`.
A free placement gives `type`, `name`, `xyz`/`rpy` relative to `parent`
(default `base_link`). Ad hoc slots declared under `slots:` work like the
parts' own. A type a slot does not accept, an unknown slot, or a slot
configured twice fails the build naming the problem; the same goes for a
mistyped part type.

## Catalog

Every `type` below is a part in `bluerobotics_parts/urdf/parts.xacro`.

| `type` | Part | Product page | In simulation |
|--------|------|--------------|---------------|
| `blueboat_chassis` | hull with both thruster bodies | [BlueBoat](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | the base; displacement declared at the assembly |
| `m200_weedless_prop_cw`, `m200_weedless_prop_ccw` | weedless propellers | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/weedless-propeller-set/) | spin on the motor joints, driven by the Thruster plugin |
| `t200_prop_cw`, `t200_prop_ccw` | standard T200 propellers | [link](https://bluerobotics.com/store/rov/bluerov2-components-spares/t200-thruster-brov2-spare-r1-vp/) | alternative occupants of the motor slots |
| `blueboat_flag` | flag | [components](https://bluerobotics.com/store/boat/blueboat-components-spares/blueboat-components/) | geometry |
| `blueboat_antenna_mast` | antenna and accessory mast | [link](https://bluerobotics.com/store/boat/blueboat-antenna-and-accessory-mast/) | geometry |
| `basestation_antenna` | BaseStation directional antenna kit | [link](https://bluerobotics.com/store/boat/blueboat-accessories/basestation-directional-antenna-kit/) | geometry |
| `blueboat_payload_bracket` | payload bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/payload-bracket/) | geometry |
| `blueboat_ping_singlebeam_mount` | Ping2 integration kit bracket | [link](https://bluerobotics.com/store/boat/blueboat-accessories/blueboat-ping2-integration-kit/) | geometry; offers the `ping` slot |
| `ping_singlebeam` | Ping2 echosounder | [link](https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/) | single-beam range sensor (`/<ns>/<name>/range`) at its `beam` frame |
| `omniscan_450_sidescan` | Cerulean Omniscan 450 side-scan sonar | [link](https://bluerobotics.com/store/the-reef/cerulean-sidescan-sonar/) | geometry only (no acoustic model on this Gazebo) |
| `surveyor_multibeam` | Cerulean Surveyor 240-16 multibeam | [link](https://bluerobotics.com/store/sonars/echosounders/cerulean-surveyor-240-16-multibeam-echosounder/) | geometry only, as above |
| `t200_thruster` | T200 thruster body | [link](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/t200-thruster-r2-rp/) | general part (the BlueBoat chassis already carries its thruster bodies) |

Sensor *behavior* (the echosounder range output) lives in `blueboat_gazebo`;
this package provides geometry and frames. Parts delivered later appear here
as the catalog grows; batteries will slot in the same way.
