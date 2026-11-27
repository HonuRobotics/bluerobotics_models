# Sensors

Sensors are parts fitted into slots. The concepts live in
[Slots and assembly](../../developers/design/slots.md), the vehicle's slots and their
accepted types in the [configuration page](configuration.md), and new
sensors can be added following the
[Add a sensor part](../../developers/add-sensor-part.md) walkthrough.

## Available sensors

| Sensor | Part | Slot | Fitted in the shipped config |
|---|---|---|---|
| Ping2 echosounder | `ping_singlebeam` | `ping` (on the integration kit bracket, itself in the chassis `ping_mount` slot) | no |
| Omniscan 450 SS sidescan | `omniscan_450_sidescan` | free placed | no (`blueboat_sonar.yaml`) |
| Surveyor 240-16 profiler | `surveyor_multibeam` | free placed | no (`blueboat_sonar.yaml`) |

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

### Sonars

The sonar parts (`sonoptix_echo_multibeam`, `omniscan_450_sidescan`, `surveyor_multibeam`) fit either vehicle. gz-maritime's gz_sonar simulates them, which needs `gz-maritime-sonar-system` in the world, and kai_sonar_bridge, started by the launch, brings them to ROS 2. `blueboat_sonar.yaml` fits a sidescan (`sidescan`) and a profiler (`profiler`) under the middle of the boat; the topics follow those names.

| ROS Topic | Description | Message type |
|---|---|---|
| `/<name>/sidescan/port/image`, `/<name>/sidescan/stbd/image` | Sidescan (Omniscan 450 SS): one line per side per ping, stamped in `<name>/sidescan_port_acoustic` and `<name>/sidescan_stbd_acoustic` | [marine_acoustic_msgs/msg/ProjectedSonarImage](https://github.com/apl-ocean-engineering/hydrographic_msgs/blob/main/marine_acoustic_msgs/msg/ProjectedSonarImage.msg) |
| `/<name>/profiler/detections` | Profiler (Surveyor 240-16): soundings, a travel time and an angle each, stamped in `<name>/profiler_beam_acoustic` (X forward, Y starboard, Z down) | [marine_acoustic_msgs/msg/SonarDetections](https://github.com/apl-ocean-engineering/hydrographic_msgs/blob/main/marine_acoustic_msgs/msg/SonarDetections.msg) |
| `.../image/view`, `.../detections/points` | The same data drawn for looking at: each side's waterfall, and the soundings as a point cloud | [sensor_msgs/msg/Image](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/Image.html), [sensor_msgs/msg/PointCloud2](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/PointCloud2.html) |

Images are stamped in a part's `_acoustic` frame, whose Z axis is the beam's look direction, as `ProjectedSonarImage` expects; the conventions are in the [sonar design](https://honurobotics.github.io/gz-maritime/lyrical/design/sonar.html#messages), and a part's `sonar:` entry sets its parameters ([Add a sonar](https://honurobotics.github.io/gz-maritime/lyrical/how-to/sonar-add.html)).

`<name>` is the instance name, `blueboat` for the default instance, or
whatever the boat was spawned as ([Several vehicles](../../walkthroughs/namespaces.md)).
A part topic follows the part's own name (`ping` above), so a part renamed
or removed in the config moves or drops its topics
([Configuration](configuration.md)). Sensor messages carry a frame the
part declares as `frame_id` (`ping_beam`, the transducer face), under the
instance name (`<name>/ping_beam`), which is how TF carries it; the sonars' frames are above. Rendered
sensors need a GPU (headless EGL works).

#### Sonar settings

A sonar part's entry in the vehicle config takes a `sonar:` dict that sets the sensor's parameters:

```yaml
- {type: omniscan_450_sidescan, name: sidescan, xyz: "0.2 0 -0.08", rpy: "0 0 0",
   sonar: {rate: 5, range_max: 30}}
```

- `rate` is the pings per second (10 if unset); lowering it is the first thing to try when the simulation runs slower than real time.
- Every other key is one of gz_sonar's `<gz:sonar>` parameters, such as `range_min`, `range_max`, `samples`, `beams`, `gain`, `noise_floor`, `speckle` and `labels`; the [sonar design](https://honurobotics.github.io/gz-maritime/lyrical/design/sonar.html) lists them all with their defaults. On the sidescan the dict applies to both sides.
- A key that is not a sonar parameter is refused when the model is generated, at build or launch, with the nearest known key as a hint (`range_mx`: "did you mean 'range_max'?").
- Values are checked when the world loads: a value the sonar cannot use (`samples: 76.5`, `labels: maybe`) refuses that one sensor, with an error in the Gazebo server's log, and the sonar's topics never appear.
