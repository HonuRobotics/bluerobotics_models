# Set up the drydock workspace

| | Supported |
|---|---|
| OS | Ubuntu 26.04 |
| ROS 2 | [Lyrical](https://docs.ros.org/en/lyrical/) |
| Gazebo | [Jetty](https://gazebosim.org/docs/jetty), installed as ROS 2 Lyrical's `ros_gz` dependency (the default pairing); no separate Gazebo install needed |

The [drydock](https://github.com/HonuRobotics/drydock) project is the standard, repeatable, documented development environment for the [gz-maritime](https://github.com/HonuRobotics/gz-maritime) project and hence this project. It is the only environment these quickstarts are written and tested against.

These step-by-step instructions are intended to be complete and unambiguous so that a user can set up a repeatable development envirnment locally.

Overall the approach is as follows:

- Docker OS: Uses the [drydock](https://github.com/HonuRobotics/drydock) project, `maritime` container to create a portable base envionment with Ubuntu, Gazebo, ROS and many build an run-time utilities.
- ROS workspace install: Install the repositories of this project all in a single workspace: `maritime_ws`.

```{note}
These docs use `~/maritime_ws` as the workspace path, with `src/`, `tools/` and `thirdparty/` inside it, and every command on every page is written against that layout. New users should follow the convention so that commands copy and paste as written. The location is a local decision: experienced users can put the workspace anywhere and substitute their own path.
```

## On Host: Setup workspace, clone drydock source, and build image

Setup directories in a new workspace:

```bash
mkdir -p ~/maritime_ws/src
mkdir -p ~/maritime_ws/tools
mkdir -p ~/maritime_ws/thirdparty
touch ~/maritime_ws/tools/COLCON_IGNORE
touch ~/maritime_ws/thirdparty/COLCON_IGNORE
```

Clone  [drydock](https://github.com/HonuRobotics/drydock) into the tools directory

```bash
cd ~/maritime_ws/tools
git clone https://github.com/HonuRobotics/drydock.git
```

Build the `maritime` image

```bash
cd ~/maritime_ws/tools/drydock
./drydock build maritime
```
### On Host: Clone source for this project

```bash
cd ~/maritime_ws/src
git clone https://github.com/HonuRobotics/gz-maritime.git
git clone https://github.com/HonuRobotics/ehukai.git
git clone https://github.com/HonuRobotics/bluerobotics_models.git
git clone https://github.com/HonuRobotics/holybro_models.git
```

### On Host: Start bash session within drydock maritime container 

```bash
cd ~/maritime_ws/tools/drydock
./drydock run maritime
```

### In Container: Build the project

```bash
cd ~/maritime_ws
colcon build --merge-install
source install/setup.bash 
```

The build should finish cleanly.  There may be cmake deprecation warnings that can (usually?) be ignored.

The project standard is `colcon build --merge-install` (one deb style prefix,
the layout users get from binary installs). The default isolated layout also
works if you prefer it.

The build generates the default vehicle artifacts from each vehicle's config
(the URDF, the composed Gazebo model, the ros_gz bridge config); see
[Design](../developers/design/architecture.md) for what is generated where.

If you need an additional shell, join the running container with `./drydock join maritime` (see `./drydock -h` for more options).

Next: [First simulation](first-simulation.md).
