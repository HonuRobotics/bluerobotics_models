# Topics

BlueBoat, default loadout, default `topic_namespace: blueboat`. The bridge
config that realizes the ROS side is generated from the loadout
(`blueboat_gazebo/config/ros_gz_bridge.yaml`).

## ROS

| Topic | Type | Direction | Available with |
|---|---|---|---|
| `/blueboat/motor_port/thrust` | `std_msgs/msg/Float64` | subscribes | the port propeller (default) |
| `/blueboat/motor_stbd/thrust` | `std_msgs/msg/Float64` | subscribes | the starboard propeller (default) |
| `/blueboat/ping/range` | `sensor_msgs/msg/LaserScan` | publishes (lazy) | the Ping2 (default) |
| `/joint_states` | `sensor_msgs/msg/JointState` | publishes | always |
| `/clock` | `rosgraph_msgs/msg/Clock` | publishes | always |
| `/robot_description`, `/tf`, `/tf_static` | | publishes | `robot_state_publisher` (started by the launch) |

## Gazebo transport

| Topic | Type | Direction |
|---|---|---|
| `/blueboat/motor_<side>/thrust` | `gz.msgs.Double` | command |
| `/blueboat/motor_<side>/thrust/ang_vel` | `gz.msgs.Double` | feedback |
| `/blueboat/ping/range` | `gz.msgs.LaserScan` | publishes |
| `/blueboat/joint_states` | `gz.msgs.Model` | publishes |

Every topic a part has follows `/<namespace>/<instance name>/<suffix>` on
both sides (`/thrust` for a propeller, `/range` for the Ping). Per part,
`topic` / `gz_topic` / `ros_topic` in the config rename the base; a second
instance gets `/<ns>/<its name>/...`.
