# Slots and assembly

Parts fit together without anyone knowing coordinates because parts declare
**slots**: named mount points with the part types that fit and a default
occupant. The BlueBoat chassis declares where its propellers, flag, mast,
payload bracket and Ping2 kit go; the kit's bracket declares where the Ping
goes; the Ping declares the frame its beam leaves from.

```{mermaid}
flowchart TB
  C["blueboat_chassis"]
  C -->|"slot motor_port<br/>accepts M200 ccw, T200 ccw<br/>default M200 ccw, continuous"| MP["m200_weedless_prop_ccw"]
  C -->|"slot motor_stbd<br/>default M200 cw, continuous"| MS["m200_weedless_prop_cw"]
  C -->|"slot flag<br/>default blueboat_flag"| F["blueboat_flag"]
  C -->|"slot mast<br/>accepts antenna mast<br/>default none"| M(("empty"))
  C -->|"slot payload<br/>accepts payload bracket<br/>default none"| P(("empty"))
  C -->|"slot ping_mount<br/>accepts the Ping2 bracket<br/>default the bracket"| B["blueboat_ping_singlebeam_mount"]
  B -->|"slot ping<br/>accepts ping_singlebeam<br/>default ping_singlebeam"| PG["ping_singlebeam"]
  PG -. "frame beam" .-> BEAM[/"transducer face:<br/>the Gazebo sensor goes here"/]
```

## Resolution

`bluerobotics_parts/urdf/assembly.xacro` turns a config into a vehicle:

```{mermaid}
flowchart TD
  A["instantiate the base part"] --> B["for each slot of the instance<br/>(its own, plus ad hoc slots from the config)"]
  B --> C{"config entry<br/>for this slot?"}
  C -- "none" --> D["fit the slot's default<br/>(nothing if default is none)"]
  C -- "type: none" --> E["leave it empty;<br/>the slot frame stays"]
  C -- "type: X" --> F{"X in accepts?"}
  F -- "no" --> G["ASSEMBLY ERROR"]
  F -- "yes" --> H["fit X (name defaults to the slot)"]
  D --> I["recurse: the occupant's slots"]
  H --> I
  I --> B
  A --> J["then the free placements:<br/>type, name, xyz/rpy on a parent<br/>(their slots fill too)"]
```

Rules, in words:

- The **base** part is the root; its link is the named root link (no joint).
- Every slot fills itself with its **default**, recursively, unless the
  config has an entry for it. An entry names the slot (`slot:`), the
  instance carrying it (`on:`, default the base), and `type:` an accepted
  part or `none`. The occupant's instance name defaults to the slot name.
- **Free placements** (no `slot:`) give `type`, `name`, `xyz`/`rpy` relative
  to `parent`.
- **Ad hoc slots** declared under `slots:` on any instance behave like the
  parts' own, `accepts` and `default` included.
- Mistakes fail the expansion naming the problem: a type the slot does not
  accept, an unknown slot on the base, a slot configured twice, a mistyped
  part type.
- Every fitted instance is recorded in the URDF as
  `<assembly_part type name parent/>`, an extension element urdfdom and
  Gazebo ignore, so the Gazebo composition and the bridge generator know
  the resolved loadout without re-resolving it.

## What a slot is in the URDF

A slot is a massless link `<instance>_<slot>` on a fixed joint at the slot
pose; the occupant hangs off it with its own joint (`fixed`, or the slot's
`continuous` for propellers), its attach offset folded in. So `flag` is
`base_link → base_link_flag → flag`. In TF you get a frame at every mount
point, filled or not; in Gazebo the fixed joints are lumped into `base_link`
and the names survive as SDF frames. Physically it is one rigid body either
way.

## Why defaults live in the parts

The knowledge of where a Ping2 kit bolts on is a property of the BlueBoat
hull (it has the holes) and of the bracket (it has the ring), not of any
particular user's config. Putting the slot, its accepted types and its
default where the knowledge is means every vehicle that uses the part gets it
right, the shipped config configures nothing, and a user who wants the Ping
writes nothing, while one who wants it elsewhere writes one line. Batteries
will follow the same path: the chassis declares the bays with a default
capacity, a battery is a part like any other, and the composed mass and
trim follow.

## Where to add a slot

In the part (one line in its `_info`, plus `accepts`), as a pull request,
when it corresponds to a real mounting point everyone has; in the config
(`slots:`) when it is specific to one loadout; in your own part when you
author a bracket of your own.
