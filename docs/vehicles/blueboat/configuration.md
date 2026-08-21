# Configuring the BlueBoat

The BlueBoat needs no configuration: every **slot** the parts declare fills
itself with its default, which is the standard boat. Configuration is how
you change that: pick another option for a slot, empty it, fill a slot that
has no default, or add a part at a free pose. One YAML file drives the URDF,
the composed Gazebo model and the ros_gz bridge config.

## Where the config lives and how it is applied

The package ships `blueboat_description/config/blueboat.yaml` (which
configures nothing). Two ways to use your own:

- **Without rebuilding** (works from a source build or an installed deb):
  ```bash
  ros2 launch blueboat_gazebo sim.launch.xml config_file:=/path/my_loadout.yaml
  ros2 launch blueboat_description display.launch.xml config_file:=/path/my_loadout.yaml
  ```
  The launch regenerates every artifact from the file at start.
- **As the new default** of your workspace: edit `config/blueboat.yaml` and
  `colcon build`; the installed URDF, `model://blueboat` and the
  bridge config regenerate.

## The slots

The chassis declares (table in [Parts catalog and slots](../../reference/parts-catalog.md)):

| Slot | Accepts | Default |
|---|---|---|
| `motor_port`, `motor_stbd` | `m200_weedless_prop_ccw`/`_cw`, `t200_prop_ccw`/`_cw` | the M200 weedless props |
| `flag` | `blueboat_flag` | `blueboat_flag` |
| `mast` | `blueboat_antenna_mast` | none |
| `payload` | `blueboat_payload_bracket` | none |
| `ping_mount` | `blueboat_ping_singlebeam_mount` | the bracket (which fits the Ping in its own `ping` slot) |

## Changing the loadout

```yaml
topic_namespace: blueboat
base: {type: blueboat_chassis, name: base_link}
parts:
  - {slot: motor_port, type: t200_prop_ccw}          # another accepted option
  - {slot: motor_stbd, type: t200_prop_cw}
  - {slot: mast, type: blueboat_antenna_mast}        # fill a slot that has no default
  - {slot: ping_mount, type: none}                   # leave a slot empty (the Ping goes with it)
  - {type: surveyor_multibeam, name: multibeam, xyz: "0.35 0 -0.08", rpy: "0 0 0"}  # free placement
hull_displacement: {length: 1.05, width: 0.18, height: 0.18, x: 0.027, y: 0.361, z: 0.059, segments: 6}
```

- A **slot entry** names the slot and the `type` to fit, which must be one
  the slot accepts, or `none`. `on:` names the instance carrying the slot
  when it is not the base (for example `{slot: ping, on: ping_mount, ...}`).
  The occupant is named after the slot unless you give it a `name`.
- A **free placement** gives `type`, `name`, `xyz`/`rpy` relative to
  `parent` (default `base_link`). The part's own slots still fill with their
  defaults.
- An **ad hoc slot** can be declared under `slots:` on any instance and then
  used like the parts' own:
  ```yaml
  slots:
    - {on: base_link, name: camera, xyz: "0.45 0 0.2", rpy: "0 0 0"}
  ```
- Per sensor part, `topic`, `gz_topic`, `ros_topic` and `bridge:` override
  the topic names and the bridge entry (see [Config schema](../../reference/config-schema.md)).

Mistakes fail the build or the launch with a message naming the problem:
a type the slot does not accept, an unknown slot, a slot configured twice,
a mistyped part type.

## Checking the result

```bash
ros2 launch blueboat_description display.launch.xml config_file:=my_loadout.yaml   # RViz: parts and frames
ros2 run blueboat_gazebo configure_vehicle.py --config my_loadout.yaml --out-dir /tmp/boat
grep assembly_part /tmp/boat/blueboat.urdf                                          # the resolved parts list
```

The generated URDF carries one `<assembly_part type name parent/>` line per
fitted part; the Gazebo model and the bridge config next to it are derived
from the same list.
