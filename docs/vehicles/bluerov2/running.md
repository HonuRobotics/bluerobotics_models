# Running the BlueROV2 simulation

```bash
ros2 launch bluerov2_gazebo sim.launch.xml
ros2 launch bluerov2_gazebo sim.launch.xml config_file:=/path/my_loadout.yaml
```

The launch generates every artifact of the full simulation at start
(URDF, composed model, bridge config, into directory under `$ROS_HOME`),
spawns the model as `bluerov2` into the underwater world and starts the
ROS bridge. The vehicle should settle just under the surface at its
declared trim.

Without ROS:

```bash
gz sim $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_playground.sdf
```

runs the default vehicle (the playground world includes `model://bluerov2`).
The camera, ping360 and stereo camera are rendered sensors and need a GPU.
To see the model in RViz:

```bash
ros2 launch bluerov2_description display.launch.xml
```
