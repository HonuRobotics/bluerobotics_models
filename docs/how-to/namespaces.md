# Topic namespaces and several simulations

Sensor and thruster topics live under `/<topic_namespace>/...`, set in the
loadout config (`topic_namespace: blueboat` by default). Per sensor part,
`topic`, `gz_topic` and `ros_topic` override the base name.

Running several vehicles in one world is not supported yet: the model name
is baked into the bridge's thruster topics (`/model/blueboat/joint/...`) and
into the playground's buoyancy enable list. Run several **simulations**
instead: give each Gazebo instance its own `GZ_PARTITION` and each ROS graph
its own `ROS_DOMAIN_ID`.
