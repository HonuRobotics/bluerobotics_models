# Simulation topics

The topics each fitted part provides are documented per vehicle, in the
Actuators and Sensors pages
([BlueBoat](../vehicles/blueboat/actuators.md),
[BlueROV2](../vehicles/bluerov2/actuators.md)). Independently of the
loadout, `sim.launch.xml` always provides:

| ROS Topic | Description | Message type |
|---|---|---|
| `/joint_states` | Joint positions and velocities (the spinning propellers, the gripper jaws), bridged for `robot_state_publisher` | [sensor_msgs/msg/JointState](https://docs.ros.org/en/rolling/p/sensor_msgs/interfaces/msg/JointState.html) |
| `/clock` | Simulation time | [rosgraph_msgs/msg/Clock](https://docs.ros.org/en/rolling/p/rosgraph_msgs/interfaces/msg/Clock.html) |
| `/robot_description`, `/tf`, `/tf_static` | The generated URDF and its frames, published by `robot_state_publisher` | |

On the Gazebo side the joint states originate at
`/<namespace>/joint_states` (`gz.msgs.Model`). The bridge config that
realizes the ROS side is generated from the loadout next to the other
artifacts ([Gazebo composition](../design/gazebo-composition.md)).

Every topic a part has follows `/<namespace>/<instance name>/<suffix>` on
both sides (`/thrust` for a propeller, `/range` for the Ping). Per part,
`topic` / `gz_topic` / `ros_topic` in the config rename the base; a second
instance gets `/<ns>/<its name>/...`.
