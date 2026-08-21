# Config schema

The vehicle config (`blueboat_description/config/blueboat.yaml`, or any file
passed as `config_file:=`) is one YAML document:

| Key | Required | Meaning |
|---|---|---|
| `topic_namespace` | no (`blueboat`) | prefix of sensor and thruster topics: `/<ns>/<name>/...` |
| `base` | yes | the root part: `{type, name (default base_link), collision (default true)}` |
| `parts` | no (`[]`) | slot entries and free placements, see below |
| `slots` | no | ad hoc slots: `{on (instance, default base_link), name, xyz, rpy (default "0 0 0"), accepts (list, optional), default (type or none)}` |
| `hull_displacement` | USV | the box pontoons the Gazebo composition places on the `hull_displacement` link: `{length, width, height, x, y, z, segments}` |
| `buoyancy` | UUV (BlueROV2) | `{net_buoyancy, cob_offset, cob_frame, fluid_density}`, see [Buoyancy](../design/buoyancy.md) |
| `extra_bridge_topics` | no | list appended verbatim to the generated ros_gz bridge config (native syntax) |

## `parts` entries

A **slot entry** (has `slot`):

| Key | Meaning |
|---|---|
| `slot` | slot name on the carrying instance |
| `on` | instance carrying the slot (default: the base) |
| `type` | a type the slot accepts, or `none` to leave it empty |
| `name` | instance name (default: the slot name) |
| `xyz`, `rpy` | offset from the slot pose (default zero) |
| `joint` | joint type for the occupant (default: the slot's, else fixed); `continuous` for spinning parts |
| `axis` | joint axis override (default: the part's declared axis) |
| `collision` | `false` to fit the part without its contact geometry |
| `topic`, `gz_topic`, `ros_topic`, `bridge` | sensor parts only: topic base for both sides / one side, native bridge keys merged into the entry |

A **free placement** (no `slot`):

| Key | Meaning |
|---|---|
| `type`, `name` | required |
| `xyz`, `rpy` | pose relative to `parent` (`xyz` required) |
| `parent` | link to attach to (default: the base) |
| `joint`, `axis`, `collision`, topic keys | as above |

Resolution rules, including how defaults fill, are in
[Slots and assembly](../design/slots.md). Errors name the problem and fail
the build or launch.
