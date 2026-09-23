# Installation - Drydock

These step-by-step instructions are intended to be complete and unambiguous so that a user can set up a repeatable development envirnment locally.

Overall the approach is....
- Docker OS: Uses the [drydock](https://github.com/HonuRobotics/drydock) project, `maritime` container to create a portable base envionment with Ubuntu, Gazebo, ROS and many build an run-time utilities.
- ROS workspace install: Install the repositories of this project all in a single workspace: `maritime_ws`.

This source install puts things in specific places, sometimes for specific reasons (all in a workspace) and sometimes just because we have to have a detailed example to make the environment and naming consistent to aid in debugging.

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

The build should finish cleanly.  There may be cmake deprecation warnings that can (usuall?) be ignored.

Next step is to run a simulation. 


