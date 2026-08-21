# Configure an installed vehicle

From a binary (deb) install nothing under `/opt/ros` should be edited, and
there is no workspace to rebuild. The vehicle is still fully configurable:
every artifact (URDF, composed Gazebo model, ros_gz bridge config) is
generated from a config file on demand, by the same tools the build uses.

## The launch does it for you

```bash
ros2 launch blueboat_gazebo sim.launch.xml config_file:=/path/my_loadout.yaml
ros2 launch blueboat_description display.launch.xml config_file:=/path/my_loadout.yaml
```

`sim.launch.xml` runs `configure_vehicle.py` into a temporary directory at
start, spawns that model and starts the bridge on that config. The default
(no argument) is the baked default vehicle.

## Generate the artifacts yourself

For anything beyond the stock launch (your own world and launch files, a
model to hand to somebody else):

```bash
ros2 run blueboat_gazebo configure_vehicle.py --config my_loadout.yaml --out-dir ~/my_models/blueboat
```

writes `blueboat.urdf`, `model.sdf`, `model.config` and `ros_gz_bridge.yaml`.
The directory is a Gazebo model: with `~/my_models` prepended to
`GZ_SIM_RESOURCE_PATH` it is `model://blueboat`, shadowing the installed
default, so a world can `<include>` it, or spawn it with
`ros2 run ros_gz_sim create -world <world> -file ~/my_models/blueboat/model.sdf -name blueboat -z 0.05`.
Start the bridge on the generated config
(`ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$HOME/my_models/blueboat/ros_gz_bridge.yaml`)
and `robot_state_publisher` on the generated URDF. The three files come from
one resolution of the config, so they agree with each other.

## Overlay workspace

The third option, for anything long lived: an overlay workspace that builds
only `blueboat_description` with your edited `config/blueboat.yaml` on top
of the installed packages. The build regenerates the URDF, the composed model
and the bridge config consistently, and `model://blueboat` resolves to
your overlay.
