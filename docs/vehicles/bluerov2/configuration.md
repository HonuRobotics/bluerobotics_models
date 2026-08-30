# Configuration

The BlueROV2 needs no configuration: every slot the parts declare fills
itself with its default. The loadout config
(`bluerov2_description/config/bluerov2.yaml`, or any file passed as
`config_file:=`) states differences only.

| Slot | Accepts | Default |
|---|---|---|
| `thruster_1` .. `thruster_6` (`_8` heavy) | the matching T200 propeller | fitted |
| `camera` | `explorehd_camera`, `marinesitu_c3` | `explorehd_camera` |
| `sonar` | `ping360` | empty |
| `dvl` | `dvl_a50` | empty |
| `gripper` | `newton_gripper`, `sediment_sampler` | empty |
| `payload` | `payload_skid` | empty |
| `rack` | `roof_rack` | empty |

- The **variant** is the base part: `base: {type: bluerov2_chassis}` or
  `bluerov2_heavy_chassis` (set `buoyancy.footprint` to `"0.457 0.575"`
  with the heavy hull).
- Slot entries, free placements, ad hoc slots and topic overrides follow
  the same schema as the BlueBoat ([Config schema](../../reference/config-schema.md));
  the instance key is `of:`, not `on:`.
- The **buoyancy declaration** (`buoyancy:` block: `net_buoyancy` in kg,
  `cob_offset`, `cob_frame`, `fluid_density`, `footprint`) is realized by
  the Gazebo composition as a dedicated displacement link solved from the
  assembled mass, so the declared trim holds across loadout changes
  ([Buoyancy](../../design/buoyancy.md)).

Mistakes fail the build or the launch with a message naming the problem.
