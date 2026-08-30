# BlueROV2 sensors

Every sensor comes from a part; empty its slot and the topic disappears,
rename the instance and the topic follows. Topic bases are
`/<namespace>/<instance>/...`, overridable per part in the config.

| Topic | Type | From | Fitted |
|---|---|---|---|
| `/bluerov2/camera/image`, `.../camera_info` | `Image` / `CameraInfo` | `explorehd_camera` | default |
| `/bluerov2/stereo/{image,depth_image,points,camera_info}` | `Image` / `PointCloud2` / `CameraInfo` | `marinesitu_c3` | camera slot option |
| `/bluerov2/sonar/scan` | `LaserScan` | `ping360` (planar gpu_lidar; no acoustics) | `sonar` slot |
| `/bluerov2/dvl/velocity` | `marine_acoustic_msgs/msg/Dvl` | `dvl_a50` (native DVL sensor) | `dvl` slot |
| `/bluerov2/gripper/cmd_pos` | `Float64` (subscribes) | `newton_gripper` / `sediment_sampler` | `gripper` slot |

The imaging sonars (`sonoptix_echo`, `omniscan_450_fs`) are
geometry only: no acoustic model ships. Sensor messages carry the part's
own link as `frame_id`, which TF resolves; cameras deliberately use the
body frame (x forward), not a REP 145 optical frame.
