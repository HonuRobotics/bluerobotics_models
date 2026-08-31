# Installation

## From source

Into a colcon workspace:

```bash
mkdir -p ~/ws/src
cd ~/ws/src
git clone https://github.com/HonuRobotics/bluerobotics_models.git
cd ~/ws
rosdep update
rosdep install --from-paths src --ignore-packages-from-source --default-yes
colcon build --merge-install
source install/setup.bash
```

```{tip}
`rosdep update` refreshes the dependency database; skipping it in fresh
containers is the usual cause of "Cannot locate rosdep definition" errors.
```

The project standard is `colcon build --merge-install` (one deb style prefix,
the layout users get from binary installs). The default isolated layout also
works if you prefer it.

The build generates the default vehicle artifacts from each vehicle's config
(the URDF, the composed Gazebo model, the ros_gz bridge config); see
[Design](../design/architecture.md) for what is generated where.

## From ROS packages (debs)

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
time. See [Configuring an installed vehicle](../how-to/installed-vehicle.md).
