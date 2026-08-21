# BlueBoat

The BlueBoat is a twin hull differential drive unmanned surface vessel. In
simulation it floats on graded buoyancy, is driven by thrust commands to its
two outboard propellers, and carries the Ping2 echosounder.

## The default loadout

Launched with no configuration, the boat is assembled from these parts:

| Instance | Part | Fitted in |
|---|---|---|
| `base_link` | `blueboat_chassis`: both hulls, crossbeams and the thruster bodies | the root |
| `motor_port`, `motor_stbd` | `m200_weedless_prop_ccw` / `_cw` | the chassis `motor_port` / `motor_stbd` slots, spinning |
| `flag` | `blueboat_flag` | the chassis `flag` slot |
| `ping_mount` | `blueboat_ping_singlebeam_mount` (the Ping2 integration kit bracket) | the chassis `ping_mount` slot |
| `ping` | `ping_singlebeam` (the Ping2) | the bracket's `ping` slot |

Every one of those comes from a **slot** the parts declare, filled with the
slot's default. The antenna mast, the payload bracket, alternative
propellers, side scan and multibeam sonars are in the catalog and one line
away; see [Configuration](configuration.md).

```{toctree}
:maxdepth: 1

running
driving
sensors
configuration
```
