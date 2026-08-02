# BlueROV2 accessories

Accessories are configured from `config/bluerov2.yaml`. Each entry is
`{type, name, xyz, rpy}`; every `type` has a xacro macro in
`urdf/accessories.xacro`. The URDF is regenerated at build time when the
config or any xacro changes.

Meshes are **temporary placeholders** (reused open-source where a permissive one
exists, otherwise a sized primitive). The 3D artist will deliver the finals as
**glTF/GLB with metallic-roughness (+ normal) PBR**; each swaps in by replacing
the mesh file, no code change.

## Base variant (not a bolt-on accessory)

The **Heavy kit** is a base configuration, selected by `variant: standard | heavy`
in the config: `heavy` swaps the base frame mesh and uses the **8-thruster
vectored** layout (poses taken from the reference `bluerov2_heavy` model), rather
than the 6-thruster standard. [Heavy kit](https://bluerobotics.com/store/rov/bluerov2-accessories/brov2-heavy-kit/)

## Catalog

| `type` | Accessory | Product page | Modeling notes |
|--------|-----------|--------------|----------------|
| `ping360` | Ping360 scanning imaging sonar | [link](https://bluerobotics.com/store/sonars/imaging-sonars/ping360-sonar-r1-rp/) | **Sensor only**, no cables/hardware. |
| `payload_skid` | BlueROV2 payload skid | [link](https://bluerobotics.com/store/rov/bluerov2-accessories/brov-payload-skid/) | Full skid. |
| `roof_rack` | BlueROV2 roof rack | [link](https://bluerobotics.com/store/rov/bluerov2-accessories/rov-roof-rack/) | Full rack. |
| `sonoptix_echo` | Sonoptix ECHO multibeam imaging sonar | [link](https://bluerobotics.com/store/sonars/imaging-sonars/sonoptix-echo/) | Full unit. |
| `explorehd_camera` | DeepWater exploreHD USB camera | [link](https://bluerobotics.com/store/sensors-cameras/cameras/deepwater-exploration-explorehd-usb-camera/) | Full unit. |
| `dvl_a50` | Water Linked DVL-A50 | [link](https://bluerobotics.com/store/the-reef/dvl-a50/) | Full unit. |
| `omniscan_450_fs` | Cerulean Omniscan 450 FS imaging sonar | [link](https://bluerobotics.com/store/sonars/imaging-sonars/cerulean-omniscan-450-fs-imaging-sonar/) | Full unit. |
| `marinesitu_c3` | MarineSitu C3 stereo camera | [link](https://bluerobotics.com/store/the-reef/marinesitu-c3-stereo-camera/) | Full unit. |
| `newton_gripper` | Newton subsea gripper | [link](https://bluerobotics.com/store/thrusters/grippers/newton-gripper-asm-r2-rp/) | 1-DOF claw: body + two jaws on revolute joints. |
| `sediment_sampler` | Newton sediment sampler attachment | [link](https://bluerobotics.com/store/thrusters/grippers/newton-sediment-sampler-attachment/) | Same 1-DOF claw with blue cup end links. |

Sensor and claw *behavior* (camera streams, Ping360 scan approximation, DVL,
claw position controllers) lives in `bluerov2_gazebo`; this package provides
geometry + frames. The imaging sonars (`sonoptix_echo`, `omniscan_450_fs`)
are geometry-only for now (no acoustic model on this Gazebo).

Artist notes for the claws: model `newton_gripper` as **four meshes** (the
black cylinder, the shaft with the blue ball link, and the two jaws);
`sediment_sampler` is **just the two jaws with the blue cups**, sharing the
cylinder and shaft.

## Placeholder mesh provenance

**Reused open meshes (temporary, permissive):**
- Heavy frame: `meshes/bluerov2_heavy.dae` from [IOES-Lab/dave](https://github.com/IOES-Lab/dave) (`ros2`), **Apache-2.0**.
- `ping360`: `meshes/accessories/ping360.dae` from [CentraleNantesROV/bluerov2](https://github.com/CentraleNantesROV/bluerov2), **Apache-2.0**.

**Primitive placeholders** (no permissively-licensed *real* mesh exists; box/
cylinder sized from the product page; generic stand-in sonars exist but are the
wrong device, so a correctly-sized primitive is the more honest placeholder):
`payload_skid`, `roof_rack`, `sonoptix_echo`, `explorehd_camera`, `dvl_a50`,
`omniscan_450_fs`, `marinesitu_c3`, `newton_gripper`, `sediment_sampler`.
