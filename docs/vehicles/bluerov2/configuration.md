# Configuration

The vehicle config (`bluerov2_description/config/bluerov2.yaml`, or any file passed as `config_file:=`) lists the fitted parts. The shipped config sets `slot_defaults: false` and fits the chassis, its six propellers and their T200 bodies, and the exploreHD camera. With `slot_defaults: true`, or the key left out, every slot fills itself with the default in the table below, and the config states differences only.

## Variants

The vehicle comes in two variants. The **standard** BlueROV2 carries six
thrusters: four vectored horizontals and two verticals. The **Heavy**
carries eight: the same horizontals plus four corner verticals, which add
roll and pitch authority and more lift for payload. The variant is picked
by the base part:

```yaml
base: {type: bluerov2_chassis, name: base_link}        # standard
base: {type: bluerov2_heavy_chassis, name: base_link}  # heavy
```

With the heavy hull, widen the buoyancy footprint to `"0.457 0.575"`. With
`slot_defaults: false`, also list the two extra verticals and their bodies:

```yaml
  - {slot: thruster_7, type: t200_prop_cw}        # rear right vertical
  - {slot: thruster_8, type: t200_prop_ccw}       # rear left vertical
  - {slot: thruster_body_7, type: t200_thruster}
  - {slot: thruster_body_8, type: t200_thruster}
```

On the heavy hull, thruster_5 and thruster_6 are the front right and front
left corner verticals.

## Buoyancy

A real vehicle is trimmed with foam and ballast to float slightly
positive, so a dead vehicle surfaces on its own. The config declares that
trim directly instead of asking you to tune volumes:

- `net_buoyancy`: kilograms of lift beyond neutral (positive floats up). The shipped default is 0.0, so the vehicle holds whatever depth it is spawned at; set it a little positive (0.002 is about right) to model a real trim that surfaces a dead vehicle.
- `cob_offset` and `cob_frame`: where the center of buoyancy sits,
  relative to the assembly's center of mass (`com`) or to `base_link`;
  keeping it above the center of mass is what makes the vehicle passively
  stable in roll and pitch.
- `fluid_density` and `footprint`: the water and the horizontal size of
  the displaced volume.

The Gazebo composition realizes the declaration as a dedicated
displacement volume solved from the assembled mass, so the declared trim
holds when the config changes ([Buoyancy](../../design/buoyancy.md)).

## Payload

Everything else is payload: sensors and actuators fitted into slots, one
config entry each. The fitted options and their topics live in
[Sensors](sensors.md) and [Actuators](actuators.md); the slots are:

| Slot | Accepts | Default |
|---|---|---|
| `thruster_1` .. `thruster_6` (`_8` heavy) | the matching T200 propeller | fitted |
| `camera` | `explorehd_camera`, `marinesitu_c3` | `explorehd_camera` |
| `sonar` | `ping360` | empty |
| `dvl` | `dvl_a50` | empty |
| `gripper` | `newton_gripper`, `sediment_sampler` | empty |
| `payload` | `payload_skid` | empty |
| `rack` | `roof_rack` | empty |

Subsea manipulation is out of scope for now, so the `gripper` slot stays empty.

Slot entries, free placements, ad hoc slots and topic overrides follow
the same schema as the BlueBoat
([Configuration keys](../../reference/parts-catalog.md#configuration-keys)); the instance key is
`of:`, not `on:`. Mistakes fail the build or the launch with a message
naming the problem.
