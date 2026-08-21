# Add a sensor part

A sensor is a part like any other, plus what the simulator needs to make it
sense. The split keeps the description Gazebo free:

1. **The part declares its sensing frame.** In `<part>_info`, a `frames`
   entry at the sensing origin, oriented as the sensor looks (the Ping
   declares `beam` at its transducer face). It becomes the URDF link
   `<name>_beam`, carried in TF, and survives Gazebo's lumping as a frame.
2. **`blueboat_gazebo` knows the part type.** In `model.sdf.xacro`, the
   `gz_part` emitter has one branch per sensor type. Add one for yours: a
   `<sensor>` block on a massless link posed `relative_to="${name}_<frame>"`,
   with `<frame_id>` set to that frame and the topic from `topic_base`
   (the Ping branch is the template). The emitter runs inside the same
   assembly resolution that built the URDF, so it fires for every instance
   of the type, defaults and free placements alike.
3. **The bridge knows the topics.** In `scripts/generate_bridge_config.py`,
   add the type to `PART_TOPICS`: one `(suffix, ros type, gz type, direction)`
   per topic the sensor produces. The generator reads the fitted instances
   from the URDF manifest, so again no per vehicle edit.
4. **Fit it**: in a slot (add the type to the slot's `accepts`, make it the
   `default` if it should come standard) or free placed.

The tests guard the contract: every sensor's `frame_id` must be a TF frame,
every sensor's frame must survive URDF to SDF conversion, and the Gazebo
topics must equal the bridge's, for the default, a full catalog and a
renamed instance config. Run `colcon test --packages-select blueboat_gazebo`.
