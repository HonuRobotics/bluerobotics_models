# Architecture

URDF is the source of truth. A **part** is a URDF xacro macro; a **vehicle**
is an assembly of parts resolved from a config and the parts' own slot
tables; everything Gazebo needs is generated from that assembly. Nothing
converts formats at runtime, and ROS and Gazebo see the same geometry.

```{mermaid}
flowchart LR
  GLB["models/part.visual.glb"]
  PART["urdf/part.urdf.xacro<br/>the part: link, inertia, visual, collision,<br/>attach, slots, frames"]
  GLB -. "referenced by the visual" .-> PART
  CFG["config/blueboat.yaml<br/>base, overrides, hull displacement"] --> ASM["assembly.xacro<br/>slots fill with defaults,<br/>config overrides and adds"]
  PART --> ASM
  ASM --> URDF["blueboat.urdf<br/>+ assembly_part manifest"]
  URDF --> ROS["ROS: robot_state_publisher, RViz, TF"]
  URDF -- "merge include" --> MODEL["model.sdf<br/>+ thrusters, hydrodynamics, sensors"]
  URDF -- "manifest" --> BRIDGE["ros_gz_bridge.yaml"]
  MODEL --> GZ["Gazebo"]
  BRIDGE --> GZ
```

## The pieces

- **Parts** ([Parts](parts.md)): one file per part in `bluerobotics_parts/urdf/`,
  hand maintained. Each part states its own mass, inertia and center of
  gravity, and declares where other parts fit (slots) and where it senses
  (frames).
- **Assembly** ([Slots and assembly](slots.md)): `assembly.xacro` instantiates
  the base part and fills every slot, recursively, with its default unless
  the config says otherwise. The default vehicle is therefore defined by the
  parts, and a config only states differences. The resolved assembly is
  recorded in the URDF as `<assembly_part>` and `<assembly_slot>` elements,
  and the config is checked against it.
- **Buoyancy** ([Buoyancy](buoyancy.md)): mass properties are composed from
  the parts; displacement is declared at the assembly (box pontoons for a
  USV, a trim target for a UUV).
- **Gazebo composition** ([Gazebo composition](gazebo-composition.md)):
  `blueboat_gazebo` merge includes the URDF and adds plugins; sensors and
  thrusters are emitted by running the same assembly resolution with Gazebo
  emitters, posed at the parts' frames and driving the propellers' joints;
  the bridge config is generated from the manifest. Build time for the installed defaults, launch time for
  `config_file:=`.

## Why it works this way

**A part is the unit.** Defects in geometry, naming or inertia are
invisible once a whole vehicle is assembled; keeping each part a small,
self contained file with its own review world (`parts_check.sdf`) makes
them visible one part at a time.

**URDF is canonical.** Robots that ship to both ROS and Gazebo
(`clearpath_common`, `turtlebot4`, `Universal_Robots_ROS2_Description`)
are URDF first without exception; Gazebo consumes the same description
through a merge include, so both sides always see identical geometry.

**Defaults live in the parts.** The previous design kept a hand written
"standalone" vehicle and a separate programmatic path and declared them
deliberately out of sync. Slots with defaults remove the split: the zero
configuration vehicle and the configurable one are the same resolution,
with an empty config.

**The structure is Clearpath's.** [`clearpath_common`](https://github.com/clearpathrobotics/clearpath_common)
is the closest analogue, a family of configurable robots for ROS and Gazebo
built from a shared parts library plus a YAML driven generator. The
addition here is the slot tables.
