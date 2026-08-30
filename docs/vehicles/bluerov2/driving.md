# Driving the BlueROV2

Thrust commands are **latched**: each thruster holds its last command until a
new one arrives. The horizontal thrusters (1-4) are vectored at 45 degrees, so
single-axis motion needs a mix with these signs (thrust in newtons):

| motion | t1 | t2 | t3 | t4 | t5 | t6 |
|--------|----|----|----|----|----|----|
| surge +x (forward) | - | - | + | + | 0 | 0 |
| sway +y (left) | - | + | - | + | 0 | 0 |
| yaw +z (counterclockwise) | - | + | + | - | 0 | 0 |
| heave +z (up) | 0 | 0 | 0 | 0 | - | - |

Each propeller part in the loadout gets a thrust topic named after it,
`/<namespace>/<name>/thrust`; the default loadout fits `thruster_1` ..
`thruster_6`.

## Over ROS

Each thruster plugin subscribes to a gz transport topic. Each of those gz
topics is bridged to ROS and indexed by number, starting at 1, e.g.,

```bash
ros2 topic pub /bluerov2/thruster_1/thrust std_msgs/msg/Float64 "data: -10.0" -1
```

## Over Gazebo transport

Command the mix **together** (`&` + `wait` publishes in parallel):

```bash
# surge forward at ~28 N
gz topic -t /bluerov2/thruster_1/thrust -m gz.msgs.Double -p 'data: -10.0' &
gz topic -t /bluerov2/thruster_2/thrust -m gz.msgs.Double -p 'data: -10.0' &
gz topic -t /bluerov2/thruster_3/thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /bluerov2/thruster_4/thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
```

```{admonition} Command all thrusters together
:class: warning

Bringing thrusters up one command at a time leaves the wrench unbalanced
while the remaining commands arrive, yawing the vehicle off its heading
before it translates. Controllers that publish continuously (teleop,
ArduPilot, MAVROS) are unaffected.
```
Stop by publishing `data: 0.0` to all thrusters the same way.
