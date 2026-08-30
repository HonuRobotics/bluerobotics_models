# Sensors

Sensors are parts fitted into slots. The concepts live in
[Slots and assembly](../../design/slots.md), the vehicle's slots and their
accepted types in the [configuration page](configuration.md), and new
sensors can be added following the
[Add a sensor part](../../how-to/add-sensor-part.md) guide.

## Available sensors

| Sensor | Part | Slot | Fitted by default |
|---|---|---|---|
| Ping2 echosounder | `ping_singlebeam` | `ping` (on the integration kit bracket, itself in the chassis `ping_mount` slot) | yes |

## Sensors ROS API

### Echosounder

The Ping2 single beam echosounder is modeled as a one ray downward
`gpu_lidar` returning the range to the seabed (real Ping2 range is about
0.5 to 100 m); its face sits below the waterline on the inner side of the
starboard hull.

| ROS Topic | Description | Message type |
|---|---|---|
| `/blueboat/ping/range` | Range to the seabed; bridged lazily, the Gazebo subscription starts with the first ROS subscriber | [sensor_msgs/msg/LaserScan](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/LaserScan.html) |

```bash
ros2 topic echo /blueboat/ping/range --once
```

Topic bases follow `/<namespace>/<instance>/...`: empty a slot and its
topics disappear, rename the instance and they follow, and per part
`topic` / `gz_topic` / `ros_topic` overrides in the config rename the
base. Sensor messages carry a frame the part declares as `frame_id`
(`ping_beam`, the transducer face), carried in TF. Rendered sensors need
a GPU (headless EGL works).
