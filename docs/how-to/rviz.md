# View in RViz

```bash
ros2 launch blueboat_description display.launch.xml                  # default loadout
ros2 launch blueboat_description display.launch.xml config_file:=my_loadout.yaml
```

The xacro is expanded at launch time, so a custom loadout needs no rebuild.
The launch starts `robot_state_publisher`, `joint_state_publisher_gui`
(sliders for the propeller joints) and RViz with the packaged config.

What TF shows: `base_link` (the chassis), one frame per fitted part
(`motor_port`, `flag`, `ping_mount`, `ping`, ...), one per slot the parts
declare (`base_link_motor_port`, `base_link_mast`, `ping_mount_ping`, ...),
the parts' reference frames (`ping_beam`) and `hull_displacement`. In Gazebo
the fixed joint frames are lumped into `base_link`; in RViz they stay
separate frames, which is the point.

Running next to Gazebo (`sim.launch.xml`), `/joint_states` arrives over the
bridge and RViz animates the propellers.
