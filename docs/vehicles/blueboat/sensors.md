# BlueBoat sensors

## Ping2 echosounder (fitted by default)

The Ping2 single beam echosounder is modeled as a one ray downward
`gpu_lidar` returning the range to the seabed (real Ping2 range is about
0.5 to 100 m).

| | |
|---|---|
| ROS topic | `/blueboat/ping/range`, `sensor_msgs/msg/LaserScan` (bridged lazily: the Gazebo subscription starts with the first ROS subscriber) |
| gz topic | `/blueboat/ping/range`, `gz.msgs.LaserScan` |
| frame | `ping_beam`: the transducer face, a frame the Ping part declares, carried in TF |
| placement | the Ping sits in the `ping` slot of the integration kit bracket, itself in the chassis `ping_mount` slot on the inner face of the starboard hull, so its face is below the waterline |

```bash
ros2 topic echo /blueboat/ping/range --once
```

The sensor follows the part: move the bracket, rename the Ping, or put a
second Ping on a free mount, and the sensor, its frame and its topics follow
without any other edit, because the Gazebo model and the bridge config are
derived from the same resolved loadout as the URDF
([Gazebo composition](../../design/gazebo-composition.md)).

To rename its topics or leave it off, see [Configuration](configuration.md).
Rendered sensors need a GPU (headless EGL works).

## Side scan and multibeam sonars

`omniscan_450_sidescan` (Cerulean Omniscan 450) and `surveyor_multibeam`
(Cerulean Surveyor 240-16) are in the parts catalog as geometry only: no
acoustic model ships for this Gazebo, so they can be fitted for mass and
looks but publish nothing.

## Adding a sensor part

A new sensor is a part with a sensing frame plus a Gazebo sensor block and a
bridge entry keyed by its part type; see
[Add a sensor part](../../how-to/add-sensor-part.md).
