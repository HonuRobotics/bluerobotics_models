# Configuration

The BlueROV2 needs no configuration: every slot the parts declare fills
itself with its default. The loadout config
(`bluerov2_description/config/bluerov2.yaml`, or any file passed as
`config_file:=`) states differences only.

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

With the heavy hull, widen the buoyancy footprint to `"0.457 0.575"`.

## Buoyancy

A real vehicle is trimmed with foam and ballast to float slightly
positive, so a dead vehicle surfaces on its own. The config declares that
trim directly instead of asking you to tune volumes:

- `net_buoyancy`: kilograms of lift beyond neutral (positive floats up;
  the default is 0.002, essentially neutral with almost no freeboard).
- `cob_offset` and `cob_frame`: where the center of buoyancy sits,
  relative to the assembly's center of mass (`com`) or to `base_link`;
  keeping it above the center of mass is what makes the vehicle passively
  stable in roll and pitch.
- `fluid_density` and `footprint`: the water and the horizontal size of
  the displaced volume.

The Gazebo composition realizes the declaration as a dedicated
displacement volume solved from the assembled mass, so the declared trim
holds when the loadout changes ([Buoyancy](../../design/buoyancy.md)).

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

Slot entries, free placements, ad hoc slots and topic overrides follow
the same schema as the BlueBoat
([Config schema](../../reference/config-schema.md)); the instance key is
`of:`, not `on:`. Mistakes fail the build or the launch with a message
naming the problem.
