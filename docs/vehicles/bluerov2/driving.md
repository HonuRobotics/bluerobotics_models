# Driving the BlueROV2

Commands are **latched**: each thruster holds its last command until a new
one arrives. The horizontal thrusters (1-4) are vectored at 45 degrees, so
single-axis motion needs a mix with these signs:

| motion | t1 | t2 | t3 | t4 | t5 | t6 |
|--------|----|----|----|----|----|----|
| surge +x (forward) | - | - | + | + | 0 | 0 |
| sway +y (left) | - | + | - | + | 0 | 0 |
| yaw +z (counterclockwise) | - | + | + | - | 0 | 0 |
| heave +z (up) | 0 | 0 | 0 | 0 | - | - |

Each propeller part in the loadout gets its topics named after it,
`/<namespace>/<name>/...`; the default loadout fits `thruster_1` ..
`thruster_6`.

## Over ROS

The primary interface is the normalized throttle, `<name>/throttle`
(`std_msgs/msg/Float64`, -1..1): the convention real drivers and
autopilots use (ArduPilot scales every motor output to -1..1; an ESC
cannot honor a force setpoint, since actual thrust depends on battery
voltage and propeller state). The command maps linearly onto the thrust
limits the propeller part declares (about +51 / -40 N for the T200) and lands on
the same latched plugin input as the thrust topic; note the real thrust to
throttle curve is not linear, so half throttle is more than half real
world thrust.

```bash
ros2 topic pub /bluerov2/thruster_1/throttle std_msgs/msg/Float64 "data: -0.2" -1
```

The low level `<name>/thrust` topic (newtons, clamped to the same limits)
stays bridged for controllers that think in forces:

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
