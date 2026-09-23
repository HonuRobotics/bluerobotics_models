# Requirements

| | Supported |
|---|---|
| OS | Ubuntu 26.04 |
| ROS 2 | [Lyrical](https://docs.ros.org/en/lyrical/) |
| Gazebo | [Jetty](https://gazebosim.org/docs/jetty), installed as ROS 2 Lyrical's `ros_gz` dependency (the default pairing); no separate Gazebo install needed |


## Docker container: drydock

The [drydock](https://github.com/HonuRobotics/drydock) project is the standard, repeatable, documented development environment for the [gz-maritme](https://github.com/HonuRobotics/gz-maritime) project and hence this project.

### drydock maritime: build, run and join

Follow the quick start instructions for [drydock](https://github.com/HonuRobotics/drydock) project, specifically the `maritime` container.


Build the container and then open a bash shell inside the container:
```
git clone https://github.com/HonuRobotics/drydock.git && cd drydock
./drydock build maritime      # build the project described in projects/maritime
./drydock run maritime        # starts the container, opens a shell
```

If you need an additonal bash shell, join the running container:
```
./drydock join maritime
```

See `./drydock -h` for more options.

Once you are running in the container shell, proceed wtih source installation here: [installation.md](installation.md).


