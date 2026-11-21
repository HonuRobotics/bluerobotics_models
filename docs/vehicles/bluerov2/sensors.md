# Sensors

Sensors are parts fitted into slots. The concepts live in
[Slots and assembly](../../developers/design/slots.md), the vehicle's slots and their
accepted types in the [configuration page](configuration.md), and new
sensors can be added following the
[Add a sensor part](../../developers/add-sensor-part.md) walkthrough. The grippers
live with the [actuators](actuators.md).

The sensors have no visual: the cameras, sonars and DVL work from their part frames, and the parts will gain glTF visuals when they are commissioned.

## Available sensors

| Sensor | Part | Slot | Fitted in the shipped config |
|---|---|---|---|
| exploreHD camera | `explorehd_camera` | `camera` | yes |
| MarineSitu C3 stereo camera | `marinesitu_c3` | `camera` | no |
| Ping360 scanning sonar | `ping360` | `sonar` | no |
| A50 DVL | `dvl_a50` | `dvl` | no |
| Sonoptix ECHO imaging sonar | `sonoptix_echo_multibeam` | free placed | no (`bluerov2_sonar.yaml`) |

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
| `/<name>/sonar/scan` | Horizontal range scan (modeled as a planar gpu_lidar; no acoustics) | [sensor_msgs/msg/LaserScan](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/LaserScan.html) |

### DVL

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/dvl/velocity` | Bottom track velocity | [marine_acoustic_msgs/msg/Dvl](https://github.com/apl-ocean-engineering/hydrographic_msgs/blob/main/marine_acoustic_msgs/msg/Dvl.msg) |

### Sonars

The sonar parts (`sonoptix_echo_multibeam`, `omniscan_450_sidescan`, `surveyor_multibeam`) fit either vehicle. gz-maritime's gz_sonar simulates them, which needs `gz-maritime-sonar-system` in the world, and kai_sonar_bridge, started by the launch, brings them to ROS 2. `bluerov2_sonar.yaml` fits a forward imaging sonar (`sonar_forward`), pitched down 15°; the topic follows that name.

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/sonar_forward/image` | Imaging sonar (Sonoptix ECHO): one fan per ping, stamped in `<name>/sonar_forward_acoustic` | [marine_acoustic_msgs/msg/ProjectedSonarImage](https://github.com/apl-ocean-engineering/hydrographic_msgs/blob/main/marine_acoustic_msgs/msg/ProjectedSonarImage.msg) |
| `/<name>/sonar_forward/image/view` | The same fan drawn as an image, for looking at | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html) |

Images are stamped in a part's `_acoustic` frame, whose Z axis is the beam's look direction, as `ProjectedSonarImage` expects; the conventions are in the [sonar design](https://honurobotics.github.io/gz-maritime/lyrical/design/sonar.html#messages), and a part's `sonar:` entry sets its parameters ([Add a sonar](https://honurobotics.github.io/gz-maritime/lyrical/how-to/sonar-add.html)).

`<name>` is the instance name, `bluerov2` for the default instance, or
whatever the vehicle was spawned as ([Several vehicles](../../walkthroughs/namespaces.md)).
A part topic follows the part's own name (`camera` above), so a part
renamed or removed in the config moves or drops its topics
([Configuration](configuration.md)). Sensor messages other than the sonars' carry the part's own
link as `frame_id`, under the instance name (`<name>/camera`), which is
how TF carries it; cameras deliberately use the body frame (x forward),
not a REP 145 optical frame.
