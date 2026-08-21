# Requirements

| | Supported |
|---|---|
| OS | Ubuntu 26.04 |
| ROS 2 | Lyrical |
| Gazebo | Jetty (via `ros_gz`) |
| GPU | Required for rendered sensors (cameras, sonars, the BlueBoat echosounder). Headless EGL works in CI; on desktops an X session is typically needed |

Both colcon install layouts work; the project standard used throughout these
docs is `--merge-install`.
