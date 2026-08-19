# Installation

Binary packages (`apt install ros-<distro>-bluerov2-*`) are planned; for now,
install from source into a colcon workspace:

```bash
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
