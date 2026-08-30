# BlueROV2 sensors

Sensors are parts fitted into slots. The concepts live in
[Slots and assembly](../../design/slots.md), the vehicle's slots and their
accepted types in [Configuring the BlueROV2](configuration.md), and new
sensors can be added following the
[Add a sensor part](../../how-to/add-sensor-part.md) guide.

## Default configuration

The default loadout carries one sensor, the exploreHD camera in the
`camera` slot:

| Topic | Type | From |
|---|---|---|
| `/bluerov2/camera/image`, `.../camera_info` | `Image` / `CameraInfo` | `explorehd_camera` |

## Available sensors

The other sensor parts fit through the loadout config:

| Topic | Type | From | Slot |
|---|---|---|---|
| `/bluerov2/stereo/{image,depth_image,points,camera_info}` | `Image` / `PointCloud2` / `CameraInfo` | `marinesitu_c3` | `camera` (instead of the default) |
| `/bluerov2/sonar/scan` | `LaserScan` | `ping360` (planar gpu_lidar; no acoustics) | `sonar` |
| `/bluerov2/dvl/velocity` | `marine_acoustic_msgs/msg/Dvl` | `dvl_a50` (native DVL sensor) | `dvl` |
| `/bluerov2/gripper/cmd_pos` | `Float64` (subscribes) | `newton_gripper` / `sediment_sampler` | `gripper` |

Each is one slot entry. This loadout produces the `stereo`, `sonar` and
`dvl` rows above:

```yaml
topic_namespace: bluerov2
base: {type: bluerov2_chassis, name: base_link}
parts:
  - {slot: camera, type: marinesitu_c3, name: stereo}   # instead of the default camera
  - {slot: sonar, type: ping360, name: sonar}
  - {slot: dvl, type: dvl_a50, name: dvl}
```

The imaging sonars (`sonoptix_echo`, `omniscan_450_fs`) are geometry only:
no acoustic model ships.

## Sensors API

Topic bases follow `/<namespace>/<instance>/...`: empty a slot and its
topics disappear, rename the instance and they follow, and per part
`topic` / `gz_topic` / `ros_topic` overrides in the config rename the
base. Sensor messages carry the part's own link as `frame_id`, which TF
resolves; cameras deliberately use the body frame (x forward), not a
REP 145 optical frame.
