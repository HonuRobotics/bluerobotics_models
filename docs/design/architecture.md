# Architecture

URDF is the source of truth. A **part** is a URDF xacro macro; a **vehicle**
is an assembly of parts resolved from a config and the parts' own slot
tables; everything Gazebo needs is generated from that assembly. Nothing
converts formats at runtime, and ROS and Gazebo see the same geometry.

```{mermaid}
flowchart LR
  subgraph delivery ["modeler delivery (bluerobotics_parts/models)"]
    GLB["part.visual.glb"]
    SDF["model.sdf (collision primitives)"]
  end
  SDF -- "sdf_to_part.py, once" --> PART["urdf/part.urdf.xacro<br/>the part: link, inertia, visual, collision,<br/>attach, slots, frames"]
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
  hand maintained. It can be bootstrapped from a modeler's SDF delivery or
  written from scratch; downstream cannot tell. Each part states its own
  mass, inertia and center of gravity, and declares where other parts fit
  (slots) and where it senses (frames).
- **Assembly** ([Slots and assembly](slots.md)): `assembly.xacro` instantiates
  the base part and fills every slot, recursively, with its default unless
  the config says otherwise. The default vehicle is therefore defined by the
  parts, and a config only states differences. The resolved parts list is
  recorded in the URDF as `<assembly_part>` elements.
- **Buoyancy** ([Buoyancy](buoyancy.md)): mass properties are composed from
  the parts; displacement is declared at the assembly (box pontoons for a
  USV, a trim target for a UUV).
- **Gazebo composition** ([Gazebo composition](gazebo-composition.md)):
  `blueboat_gazebo` merge includes the URDF and adds plugins; sensors are
  emitted by running the same assembly resolution with Gazebo emitters and
  posed at the parts' frames; the bridge config is generated from the
  manifest. Build time for the installed defaults, launch time for
  `config_file:=`.

## Why it works this way

**The problem is transcription, not format.** The modeler's tooling exports
SDF; the description packages consume URDF. When a person bridges that gap
by retyping geometry, that hand step is the only place defects can enter. A
contributed part once arrived with cylinders of radius 0.41 m on a 1.2 m
hull, collision names containing spaces, geometry yawed 180 degrees, and SDF
syntax pasted into a URDF file where it could not parse. None of it was
detectable until the whole vehicle assembled, because there was no smaller
unit to test. So the conversion is a tool, a part is the unit, and a review
world shows every part alone.

**SDF first was prototyped and rejected.** Parts as standalone SDF models,
composed with `<include merge="true">` and converted for ROS by
`sdformat_urdf`, is what [Gazebo's interoperability docs](https://gazebosim.org/docs/latest/ros2_interop/)
recommend, and it works. It was rejected on ecosystem grounds: robots that
ship to both ROS and Gazebo (`clearpath_common`, `turtlebot4`,
`Universal_Robots_ROS2_Description`) are URDF first without exception, and a
young converter on the critical path of every description would make its
bugs ours. The URDF stays canonical; SDF deliveries are an optional on ramp
and move to a side branch once converted.

**Defaults live in the parts.** The previous design kept a hand written
"standalone" vehicle and a separate programmatic path and declared them
deliberately out of sync. Slots with defaults remove the split: the zero
configuration vehicle and the configurable one are the same resolution,
with an empty config.

**The structure is Clearpath's.** [`clearpath_common`](https://github.com/clearpathrobotics/clearpath_common)
is the closest analogue, a family of configurable robots for ROS and Gazebo
built from a shared parts library plus a YAML driven generator. The
additions here are the slot tables and the bootstrap tool, which they do not
need because their geometry does not arrive from an artist exporting SDF.
