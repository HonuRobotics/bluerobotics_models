# Architecture

URDF is the source of truth. Geometry originates in CAD, is exported by the
modeller as SDF, and is converted into URDF by a script rather than by hand.

```
modeller  ──▶  <part>.glb + model.sdf  ──▶  import script  ──▶  <part>.urdf.xacro
                                                                      │
                                          assemblies (xacro) ◀────────┘
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                    ROS: URDF direct                    Gazebo: merge-includes the URDF
```

Nothing converts formats at runtime. Both consumption paths see the URDF the
build produces.

## Assemblies

Developers write a xacro macro per part; assemblies instantiate them and add the
joints. Joints belong to whatever composes the parts, never to a part itself —
both `fixed` mounts and the `continuous` joints that spin propellers.

```xml
<xacro:macro name="t200_housing" params="name parent *origin">
  <link name="${name}">
    <inertial>…</inertial>
    <visual>
      <geometry>
        <mesh filename="package://bluerobotics_parts/models/t200_housing/t200_housing.glb"/>
      </geometry>
    </visual>
    <!-- BEGIN GENERATED COLLISIONS -->
    <!-- END GENERATED COLLISIONS -->
  </link>
  <joint name="${name}_joint" type="fixed">
    <parent link="${parent}"/><child link="${name}"/>
    <xacro:insert_block name="origin"/>
  </joint>
</xacro:macro>
```

Each vehicle offers a simple, complete standalone configuration and a
programmatic method (xacro and yaml) for more complex ones. Simple things
simple: reuse the checked-in default robot, no config. Complex things possible:
the programmatic path for custom loadouts. The two are deliberately **not kept
in sync** — the standalone configuration is conceptually the programmatic one
with every option turned off, but nothing enforces that, and promising it would
create a maintenance obligation with no payoff.

## Why it works this way

**The problem is transcription, not format.** The modeller's tooling exports
SDF; the description packages consume URDF. When a person bridges that gap by
retyping geometry, that hand step is the only place defects can enter. A
contributed part once arrived with cylinders of radius 0.41 m on a 1.2 m hull,
collision names containing spaces, geometry yawed 180°, and SDF syntax pasted
into a URDF file where it could not parse — committed commented out, with "TODO:
Verify I'm doing this right". The task as posed had no obvious right answer,
which is why it should not be posed to a person. None of it was detectable until
the whole vehicle assembled, because there was no smaller unit to test.

**SDF-first was prototyped and rejected.** Parts as standalone SDF models,
composed with `<include merge="true">` and converted for ROS by `sdformat_urdf`,
is what [Gazebo's interoperability
docs](https://gazebosim.org/docs/latest/ros2_interop/) recommend, and it works —
verified end to end. It was rejected on ecosystem grounds: benchmarking robots
that ship to both ROS and Gazebo (`clearpath_common` 130 xacro / 0 SDF,
`turtlebot4` 8 / 0, `Universal_Robots_ROS2_Description` 8 / 0), nobody is
SDF-first. Putting a young, thinly-maintained converter on the critical path for
every robot description would make its bugs ours to find. The asset-pipeline
problem it solved is better handled by a script we own.

**The structure is Clearpath's.**
[`clearpath_common`](https://github.com/clearpathrobotics/clearpath_common) is
the closest analogue — a family of configurable robots targeting both ROS and
Gazebo, built from a shared parts library plus a yaml-driven generator. The
addition here is the import script, which they do not need because their
geometry does not arrive from an artist exporting SDF.
