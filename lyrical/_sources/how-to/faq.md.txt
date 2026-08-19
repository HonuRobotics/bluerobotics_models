# Troubleshooting / FAQ

## The vehicle moves sideways instead of forward

Thrust commands latch, and sequential one-shot publications stagger thruster
onset, applying a momentary unbalanced wrench that yaws the vehicle before it
translates. Command all thrusters **in parallel** — see
[Driving](../vehicles/bluerov2/driving.md).

## "Cannot locate rosdep definition"

Run `rosdep update` first — fresh containers ship without the database.

## No camera images

Rendered sensors need a usable render path. On desktops, run inside an X
session; headless machines need working EGL (CI installs
`libegl1 libgl1 libgl1-mesa-dri libglvnd0`).

## Two simulations interfere with each other

Isolate them: set a unique `GZ_PARTITION` per Gazebo instance and a unique
`ROS_DOMAIN_ID` per ROS graph.
