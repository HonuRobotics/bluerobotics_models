# BlueROV2 sensors

Sensors are parts fitted into slots. The concepts live in
[Slots and assembly](../../design/slots.md), the vehicle's slots and their
accepted types in [Configuring the BlueROV2](configuration.md), and new
sensors can be added following the
[Add a sensor part](../../how-to/add-sensor-part.md) guide. The grippers
live with the [actuators](actuators.md).

## Available sensors

| Sensor | Part | Slot | Fitted by default |
|---|---|---|---|
| exploreHD camera | `explorehd_camera` | `camera` | yes |
| MarineSitu C3 stereo camera | `marinesitu_c3` | `camera` | no |
| Ping360 scanning sonar | `ping360` | `sonar` | no |
| A50 DVL | `dvl_a50` | `dvl` | no |

## Sensors ROS API

### Cameras (`explorehd_camera`, default `camera` slot)

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/camera/image` | Camera image | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |
| `/bluerov2/camera/camera_info` | Camera intrinsics | [sensor_msgs/msg/CameraInfo](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/CameraInfo.html) |

### Stereo camera (`marinesitu_c3`, `camera` slot)

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/stereo/image` | RGB image | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |
| `/bluerov2/stereo/depth_image` | Depth image | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |
| `/bluerov2/stereo/points` | Point cloud | [sensor_msgs/msg/PointCloud2](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/PointCloud2.html) |
| `/bluerov2/stereo/camera_info` | Camera intrinsics | [sensor_msgs/msg/CameraInfo](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/CameraInfo.html) |

### Scanning sonar (`ping360`, `sonar` slot)

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/sonar/scan` | Horizontal range scan (modelled as a planar gpu_lidar; no acoustics) | [sensor_msgs/msg/LaserScan](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/LaserScan.html) |

### DVL (`dvl_a50`, `dvl` slot)

| ROS Topic | Description | Message type |
|---|---|---|
| `/bluerov2/dvl/velocity` | Bottom track velocity | [marine_acoustic_msgs/msg/Dvl](https://github.com/apl-ocean-engineering/hydrographic_msgs/blob/main/marine_acoustic_msgs/msg/Dvl.msg) |

Topic bases follow `/<namespace>/<instance>/...`: empty a slot and its
topics disappear, rename the instance and they follow, and per part
`topic` / `gz_topic` / `ros_topic` overrides in the config rename the
base. Sensor messages carry the part's own link as `frame_id`, which TF
resolves; cameras deliberately use the body frame (x forward), not a
REP 145 optical frame.
