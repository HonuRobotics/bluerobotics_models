# Requirements

| | Supported |
|---|---|
| OS | Ubuntu 26.04 |
| ROS 2 | Lyrical |
| Gazebo | Jetty, installed as ROS 2 Lyrical's `ros_gz` dependency (the default pairing); no separate Gazebo install needed |
| GPU | Required for rendered sensors (cameras, sonars, the BlueBoat echosounder). Headless EGL works in CI; on desktops an X session is typically needed |
