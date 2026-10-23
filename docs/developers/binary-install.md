# Binary install (future)

Parked for later. Binary packages are a work in progress and are not part of the tested workflow while the repositories are changing quickly; the supported path is the source build in [Set up the drydock workspace](../quickstarts/setup.md).

## Install from ROS packages (debs)

Binary packages (`ros-<distro>-blueboat-gazebo`, `ros-<distro>-bluerov2-gazebo`,
the `*-description` packages, `ros-<distro>-bluerobotics-parts`, ...) are
planned for the ROS build farm and are not published yet. When they are,
installation is one package per vehicle you want:

```bash
sudo apt install ros-lyrical-blueboat-gazebo ros-lyrical-bluerov2-gazebo
source /opt/ros/lyrical/setup.bash
ros2 launch blueboat_gazebo sim.launch.xml    # the boat
ros2 launch bluerov2_gazebo sim.launch.xml    # or the ROV
```

Nothing under `/opt/ros` is meant to be edited. The default vehicle is baked
into the packages; a custom config is a YAML file anywhere on disk passed
to the launch (`config_file:=`), which regenerates every artifact at launch
time. See [Configure an installed vehicle](#configure-an-installed-vehicle).

## Configure an installed vehicle

From a binary (deb) install nothing under `/opt/ros` should be edited, and
there is no workspace to rebuild. The vehicle is still fully configurable:
every artifact (URDF, composed Gazebo model, ros_gz bridge config) is
generated from a config file on demand, by the same tools the build uses
(writing the config: [Change the fitted parts](../walkthroughs/change-parts.md)).

### The launch does it for you

```bash
ros2 launch blueboat_gazebo sim.launch.xml config_file:=/path/my_vehicle.yaml
ros2 launch blueboat_description display.launch.xml config_file:=/path/my_vehicle.yaml
```

`sim.launch.xml` runs `configure_vehicle.py` into a per config directory under `$ROS_HOME` at
start, spawns that model and starts the bridge on that config. The default
(no argument) is the baked default vehicle.

### Generate the artifacts yourself

For anything beyond the stock launch (your own world and launch files, a
model to hand to somebody else):

```bash
ros2 run blueboat_gazebo configure_vehicle.py --config my_vehicle.yaml --out-dir ~/my_models/blueboat
```

writes `blueboat.urdf`, `blueboat.gazebo.urdf` (the copy the model merges,
glTF visuals pre-rotated for Gazebo), `model.sdf`, `model.config` and
`ros_gz_bridge.yaml`, plus `vehicle.yaml`, the config as used. Add
`--name <name>` to generate an instance under another name (model name and
topic namespace at once).
The directory is a Gazebo model: with `~/my_models` prepended to
`GZ_SIM_RESOURCE_PATH` it is `model://blueboat`, shadowing the installed
default, so a world can `<include>` it, or spawn it with
`ros2 run ros_gz_sim create -world <world> -file ~/my_models/blueboat/model.sdf -name blueboat -z 0.05`.
The `model://` name is the directory's name, so an instance generated with
`--name boat_b` belongs in a directory called `boat_b` (`~/my_models/boat_b`)
to be `model://boat_b`.
Start the bridge on the generated config
(`ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$HOME/my_models/blueboat/ros_gz_bridge.yaml`)
and `robot_state_publisher` on the generated URDF. The three files come from
one resolution of the config, so they agree with each other.

### Overlay workspace

The third option, for anything long lived: an overlay workspace that builds
only `blueboat_description` with your edited `config/blueboat.yaml` on top
of the installed packages. The build regenerates the URDF, the composed model
and the bridge config consistently, and `model://blueboat` resolves to
your overlay.
