# Change the fitted parts

Recipes for the vehicle config. The concepts (slots, defaults, free
placement) are explained in [Configuring the BlueBoat](../vehicles/blueboat/configuration.md);
the full key list is in {ref}`Configuration keys <configuration-keys>`.

Start from a copy of the shipped config:

```bash
cp $(ros2 pkg prefix --share blueboat_description)/config/blueboat.yaml my_vehicle.yaml
```

and try it without rebuilding: `ros2 launch blueboat_gazebo sim.launch.xml config_file:=$PWD/my_vehicle.yaml`.

## Fit the other propellers

```yaml
parts:
  - {slot: motor_port, type: t200_prop_ccw}
  - {slot: motor_stbd, type: t200_prop_cw}
```

## Leave the Ping2 kit off

```yaml
parts:
  - {slot: ping_mount, type: none}
```

The bracket goes, and with it the Ping it carries: no sensor, no bridge
entry, no frame.

## Add the antenna mast or the payload bracket

```yaml
parts:
  - {slot: mast, type: blueboat_antenna_mast}
  - {slot: payload, type: blueboat_payload_bracket}
```

## Rename the Ping topics

```yaml
parts:
  - {slot: ping, of: ping_mount, type: ping_singlebeam, topic: sonar}
```

gives `/blueboat/sonar/range` on both sides; `gz_topic` / `ros_topic` set one
side only, `bridge: {...}` passes native ros_gz_bridge keys through.

## Add a part somewhere specific

```yaml
parts:
  - {type: surveyor_multibeam, name: multibeam, xyz: "0.35 0 -0.08", rpy: "0 0 0"}
  - {type: ping_singlebeam, name: bow_ping, xyz: "0.5 0 -0.05"}   # a second Ping, free placed
```

`xyz`/`rpy` are relative to `parent` (default `base_link`). The second Ping
gets its own sensor, frame `bow_ping_beam` and topic `/blueboat/bow_ping/range`.

## Declare your own mount point

```yaml
slots:
  - {of: base_link, name: camera, xyz: "0.45 0 0.2", rpy: "0 0 0", accepts: [surveyor_multibeam]}
parts:
  - {slot: camera, type: surveyor_multibeam, name: bow_sonar}
```

An ad hoc slot behaves like the parts' own: it becomes the frame
`base_link_camera`, `accepts` is checked, `default` is honored.

## See what you got

```bash
ros2 run blueboat_gazebo configure_vehicle.py --config my_vehicle.yaml --out-dir /tmp/boat
grep assembly_part /tmp/boat/blueboat.urdf
```

Every fitted part, defaults included, is one `<assembly_part>` line.
