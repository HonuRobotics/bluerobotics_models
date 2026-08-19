# Package layout

| Package | Purpose |
|---------|---------|
| [`bluerobotics_parts`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/bluerobotics_parts) | Every part — mesh, delivered SDF and xacro macro. Shared by all vehicles |
| [`bluerov2_description`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/bluerov2_description) | BlueROV2 assemblies, RViz; pure description, no simulator code |
| [`bluerov2_gazebo`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/bluerov2_gazebo) | Composed Gazebo model (thrusters, hydrodynamics, sensors, grippers), world, launch and ros_gz bridge |
| [`blueboat_description`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/blueboat_description) | BlueBoat assemblies, RViz; no simulator code |
| [`blueboat_gazebo`](https://github.com/HonuRobotics/bluerobotics_models/tree/lyrical/blueboat_gazebo) | Composed BlueBoat model (twin thrusters, hydrodynamics, echosounder), surface-water world, launch and ros_gz bridge |

The split follows a convention common to ROS robot repositories: description
packages hold geometry and frames only, gazebo packages compose them with
simulation behavior (plugins, sensors, worlds, bridges), and the shared parts
package feeds both vehicles.
