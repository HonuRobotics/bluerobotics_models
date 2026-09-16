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
| `/<name>/ping/range` | Range to the seabed; bridged lazily, the Gazebo subscription starts with the first ROS subscriber | [sensor_msgs/msg/LaserScan](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/LaserScan.html) |

```bash
ros2 topic echo /blueboat/ping/range --once
```

`<name>` is the instance name, `blueboat` for the default instance, or
whatever the boat was spawned as ([Several vehicles](../../how-to/namespaces.md)).
A part topic follows the part's own name (`ping` above), so a part renamed
or removed in the config moves or drops its topics
([Configuration](configuration.md)). Sensor messages carry a frame the
part declares as `frame_id` (`ping_beam`, the transducer face), under the
instance name (`<name>/ping_beam`), which is how TF carries it. Rendered
sensors need a GPU (headless EGL works).
