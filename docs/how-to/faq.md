# Troubleshooting / FAQ

## xacro fails with "ASSEMBLY ERROR: ..."

The loadout config asked for something the parts cannot do: a type the slot
does not accept (the message lists what it accepts), an unknown slot on the
base, or a slot configured twice. "unknown macro name: xacro:<type>" means a
mistyped part type. Fix the config; see
[Configuring the BlueBoat](../vehicles/blueboat/configuration.md).

## The boat moves sideways instead of forward

Thrust commands latch, and sequential one shot publications stagger thruster
onset, applying a momentary unbalanced wrench that yaws the vehicle before it
translates. Command both thrusters **in parallel**; see
[Driving](../vehicles/blueboat/driving.md).

## No ranges on /blueboat/ping/range

Rendered sensors need a usable render path. On desktops, run inside an X
session; headless machines need working EGL (CI installs
`libegl1 libgl1 libgl1-mesa-dri libglvnd0`). The bridge is lazy: ranges flow
once something subscribes on the ROS side.

## "Cannot locate rosdep definition"

Run `rosdep update` first; fresh containers ship without the database.

## Two simulations interfere with each other

Isolate them: set a unique `GZ_PARTITION` per Gazebo instance and a unique
`ROS_DOMAIN_ID` per ROS graph.

## robot_state_publisher warns about the root link inertia

Expected and harmless: KDL only publishes TF and ignores inertia; Gazebo
reads it through sdformat. Do not add a dummy root link: Gazebo's URDF
conversion would lump `base_link` into it and break every plugin that
references `base_link`.
