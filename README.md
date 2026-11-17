# Blue Robotics models

ROS 2 / Gazebo Sim model packages for Blue Robotics vehicles: the BlueROV2
underwater vehicle (standard and Heavy configurations) and the BlueBoat USV.
Targets **ROS 2 Lyrical + Gazebo Jetty** (the default pairing on Ubuntu 26.04),
via `ros_gz`.

**Documentation: <https://honurobotics.github.io/bluerobotics_models/>**

The site covers quickstarts, walkthroughs, a reference manual for each vehicle and the design of the parts pipeline.

## Quick start

Start with the [Quickstarts](https://honurobotics.github.io/bluerobotics_models/lyrical/quickstarts/index.html): they set up the drydock container and a source build, then run the BlueBoat and the BlueROV2, first on their own and then under ArduPilot SITL.

## Contributing

Developer workflow (build, tests, pre-commit hooks, conventions):
see [CONTRIBUTING.md](CONTRIBUTING.md).

## Blender assemblies (Git LFS)

The Blender assemblies in `bluerobotics_parts/assemblies/` are stored with Git LFS. Nothing builds from them, so a plain clone is enough to build and run. To get the files themselves, install Git LFS and, in the clone, run `git lfs install` and then `git lfs pull`. If Git LFS was already installed when you cloned, they came down with the clone; set `GIT_LFS_SKIP_SMUDGE=1` when cloning to skip them.

## License

Apache-2.0 (see [LICENSE](LICENSE)). Reused third-party meshes are credited in
[NOTICE](NOTICE) and `bluerov2_description/ASSETS.md`.
