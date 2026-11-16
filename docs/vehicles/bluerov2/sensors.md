# Sensors

Sensors are parts fitted into slots. The concepts live in
[Slots and assembly](../../design/slots.md), the vehicle's slots and their
accepted types in the [configuration page](configuration.md), and new
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

### Camera

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/camera/image` | Camera image | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |
| `/<name>/camera/camera_info` | Camera intrinsics | [sensor_msgs/msg/CameraInfo](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/CameraInfo.html) |

### Stereo camera

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/stereo/image` | RGB image | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |
| `/<name>/stereo/depth_image` | Depth image | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |
| `/<name>/stereo/points` | Point cloud | [sensor_msgs/msg/PointCloud2](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/PointCloud2.html) |
| `/<name>/stereo/camera_info` | Camera intrinsics | [sensor_msgs/msg/CameraInfo](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/CameraInfo.html) |

### Scanning sonar

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/sonar/scan` | Horizontal range scan (modelled as a planar gpu_lidar; no acoustics) | [sensor_msgs/msg/LaserScan](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/LaserScan.html) |

### DVL

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/dvl/velocity` | Bottom track velocity | [marine_acoustic_msgs/msg/Dvl](https://github.com/apl-ocean-engineering/hydrographic_msgs/blob/main/marine_acoustic_msgs/msg/Dvl.msg) |

`<name>` is the instance name, `bluerov2` for the default instance, or
whatever the vehicle was spawned as ([Several vehicles](../../how-to/namespaces.md)).
A part topic follows the part's own name (`camera` above), so a part
renamed or removed in the config moves or drops its topics
([Configuration](configuration.md)). Sensor messages carry the part's own
link as `frame_id`, under the instance name (`<name>/camera`), which is
how TF carries it; cameras deliberately use the body frame (x forward),
not a REP 145 optical frame.
