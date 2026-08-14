# All up round mass and buoyancy

The all up round (AUR) properties of a vessel are the properties of the assembled vehicle as it goes in the water: hull, thrusters, accessories, batteries, ballast and everything else in the configuration being simulated. This document defines how those properties are obtained and where each value lives.

## Design

Mass properties and displacement are treated differently, deliberately:

| Property | How it is obtained |
|---|---|
| Mass, moment of inertia, center of mass | **Derived.** Composed from the parts; each part's xacro macro is the source for its own values |
| Displacement and center of buoyancy | **Declared** at the assembly. A UUV declares a net buoyant balance in kilograms and a center of buoyancy offset. A USV declares hull collision geometry, independent of what the parts carry |

Each part carries its own mass, inertia tensor and center of gravity pose, and the assembly composes them. Tooling at the assembly level reports the aggregate, so the as configured vehicle can be inspected. Mass, inertia and center of mass are never declared at the assembly.

Deriving mass keeps one source of truth per part: a loadout change, such as adding a battery or fitting a sensor, propagates on its own. Displacement cannot work that way. For a UUV, net buoyancy is something the operator trims deliberately with foam and lead, so the simulation states it directly and holds it across loadout changes. For a USV, the vessel floats where displacement equals weight; the displacing shape must be the hull and only the hull, so that fitting a bracket does not change the draft by however much collision geometry the bracket happens to carry.

## The two cases are not symmetric

**UUV: flotation is a free parameter.** A submerged vehicle is trimmed to an intent: neutral, or slightly positive so a control failure surfaces it. Mass is what it is, and net buoyancy is what we trimmed it to; the two are stated independently. Where the forces act matters as much as their size: a center of buoyancy above the center of mass rights the vehicle, and the offset sets how stiffly.

**USV: flotation is an outcome.** The vessel settles where displacement equals weight, so net buoyancy at rest is zero by definition. Draft, trim and list follow from the composed mass properties; the declared hull geometry sets the waterline through the buoyancy plugin. The UUV parameters below are not used.

## The UUV parameters

`config/bluerov2.yaml` accepts an optional `buoyancy:` block:

```yaml
buoyancy:
  net_buoyancy: 0.002        # kg, positive floats up
  cob_offset: "0 0 0.046"    # m, center of buoyancy relative to the center of mass
```

Both keys are optional; the values above are the defaults (a two gram fail safe rise, center of buoyancy 46 mm above the center of mass).

`net_buoyancy` is a displaced mass in kilograms rather than a fraction: it is the quantity an operator actually handles, and it does not scale silently when the vehicle gets heavier.

`cob_offset` is the BG vector: where the buoyant force acts relative to where weight acts. It sets the righting stiffness directly, since the righting moment of a submerged vehicle is (m + b) g BG sin(theta). It is declared relative to the center of mass so a loadout change preserves both the mass and the tuned handling. Keep the z component positive; a center of buoyancy at or below the center of mass is unstable.

The generation composes the total mass and center of mass from the same data that builds the links, then solves the height and full 3D center of the `base_link` collision box so both declarations hold for the configured loadout. Accessories that carry collision volume displace too; the box makes up the difference, derived from the same tables on every build, with each accessory's collision taken as displacing at its mount pose. A declaration that cannot be met, because it would need a non positive box volume, fails the build loudly.

Design note: ignoring part collisions entirely through the buoyancy plugin's per link `<enable>` was considered and set aside. The enable list lives in the world file, which stays vehicle agnostic, and scoped link names would couple it to the internals of one model. Worth revisiting if worlds become generated artifacts.

## Where each value lives

Every part is delivered with a xacro macro that instantiates its link: visual, inertia, and optionally collision. The macro is the source of truth for that part's **mass, inertia tensor and center of gravity pose**, taken from physical reality rather than from primitive geometry. Collision is optional per part; where it exists, it starts as a translation of the collision geometry in the part's `model.sdf`.

Assemblies are composed from a parts level YAML, generalizing the `accessories:` list in `bluerov2_description/config/bluerov2.yaml`. The YAML selects which parts make up a configuration, declares the buoyancy block, and the models are generated from it. The chassis is not always included; membership is a choice the file expresses.

The delivery contract for a part is in [bluerobotics_parts/README.md](bluerobotics_parts/README.md).

## Out of scope

- Assembly declared mass, inertia or center of mass; mass properties are always derived.
- A displacement primitive independent of the `<collision>` mechanism. The buoyancy plugin's only input is collision geometry, so displacement is communicated that way.
- Power, energy, state of charge, endurance, electrical faults.
- Identified hydrodynamic coefficients; drag remains placeholder values.
- Enabling added mass.
- Dynamic mass change during a run (shedding ballast, releasing a payload); composition is at build time.
- Where the parts level YAML lives relative to the existing per vehicle config; handled separately.

## Known constraints

- **URDF cannot express `<fluid_added_mass>`.** It lives in an SDF `<inertial>`, so the ROS and Gazebo paths will see different things unless handled deliberately.
- **`bluerov2_gazebo/model.sdf.xacro` records added mass as intentionally zero** because of the summation approach; that constraint stands.
- **Graded buoyancy (floating vessels) accepts only box and sphere collisions**, and the buoyancy geometry doubles as contact geometry.
- **Sensors need their own links** for TF frames.
- **The parts library is empty today.** `bluerobotics_parts/models/` holds placeholder directories and `parts.csv`; nothing here is blocked by existing content, which is why the delivery contract is worth settling now.
