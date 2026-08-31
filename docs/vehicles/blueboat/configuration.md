# Configuration

The BlueBoat needs no configuration: every slot the parts declare fills
itself with its default. The vehicle config
(`blueboat_description/config/blueboat.yaml`, or any file passed as
`config_file:=`) states differences only.

## Hull displacement

The boat floats on graded buoyancy acting on a declared displacement,
not on the meshes: the config states box pontoons
(`hull_displacement:` block: `length`, `width`, `height`, the pontoon
positions `x`/`y`/`z`, and `segments`) which the Gazebo composition
realizes as a dedicated displacement link. Splitting each pontoon into
segments models a pitched waterplane, and the boat self settles to a
draft of roughly `mass / (water_density * 2 * length * width)`
([Buoyancy](../../design/buoyancy.md)).

## Payload

Everything else is payload: sensors and actuators fitted into slots, one
config entry each. The fitted options and their topics live in
[Sensors](sensors.md) and [Actuators](actuators.md); the slots are:

| Slot | Accepts | Default |
|---|---|---|
| `motor_port`, `motor_stbd` | `m200_weedless_prop_ccw`/`_cw`, `t200_prop_ccw`/`_cw` | the M200 weedless props |
| `flag` | `blueboat_flag` | `blueboat_flag` |
| `mast` | `blueboat_antenna_mast` | none |
| `payload` | `blueboat_payload_bracket` | none |
| `ping_mount` | `blueboat_ping_singlebeam_mount` | the bracket (which fits the Ping in its own `ping` slot) |

Slot entries, free placements, ad hoc slots and topic overrides are
described in the {ref}`Configuration keys <configuration-keys>` and
walked through in [Change the fitted parts](../../how-to/change-parts.md); the
instance key is `of:`, not `on:`. Mistakes fail the build or the launch
with a message naming the problem.
