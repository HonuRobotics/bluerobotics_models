# All-up-round mass and buoyancy

Status: draft design, for review. **Functional scope only** — what the feature does and why. Implementation is deliberately deferred.

Revised after review with Carlos. The earlier draft proposed declaring mass, inertia and center of mass at the assembly level; that is no longer the design. See [What changed in review](#what-changed-in-review).

---

## Proposal

The all-up-round (AUR) properties of a vessel are the properties of the assembled vehicle as it goes in the water: hull, thrusters, accessories, batteries, ballast, cabling and everything else, in the configuration being simulated.

Mass properties and displacement are treated differently, and deliberately so:

| Property | How it is obtained |
|---|---|
| Mass, moment of inertia, center of mass | **Derived** — composed from the parts, whose own values are the source of truth. The source of truth for a part's inertia (approximated to its physical characteristics) is the xacro macro file in the part directory |
| Displacement and center of buoyancy | **Declared** at the assembly. For underwater vehicles (UUVs) the key design parameter is the overall buoyant balance, stated as a displaced mass in kilograms. For surface vehicles (USVs) the details of the collision geometry — used to calculate the displacement, and from it the buoyancy force magnitude — need to be specified independent of the part collision geometry. This uses `<collision>` tags to communicate the geometry primitives to the buoyancy (or surface) plugin |

Each part carries its own mass, inertia tensor and center-of-gravity pose, and the assembly's mass properties follow from composing them. Tools and utilities evaluate the aggregate at the assembly level, so that users can answer the questions — what is the mass, inertia tensor and location of the center of mass — for the AUR vessel.

Displacement is the half that is declared, and for both vehicle types the declaration is at the assembly rather than implied by the parts. For a UUV that declaration is a net force: buoyancy is something the operator trims deliberately, so the simulation states it directly. For a USV the declaration is geometry: the vessel floats where displacement equals weight, so what has to be stated is the shape that displaces the water, independent of whatever collision geometry the parts happen to carry.

## Why

For vehicles that float at the surface or subsea, the point of contact between sim and real is the assembled vehicle. That is where a user measures mass, and where they trim buoyancy.

Deriving mass properties keeps a single source of truth per part and lets a loadout change — adding a battery, moving ballast, fitting a sensor — propagate on its own. What was missing is not a declaration but visibility: nothing today reports the aggregate, so the as-configured vehicle is not something you can inspect. Tooling at the assembly level closes that gap without moving the source of truth.

Displacement is different, in a way that differs again between the two vehicle types.

For a UUV, adding a sensor in the real vehicle means adding lead or foam to restore trim. In simulation we do not want to repeat that, so net buoyancy is stated for the assembly and holds across loadout changes.

For a USV, nothing is trimmed — the vessel finds its own waterline. What matters is that the displacing shape is the hull, and only the hull. If displacement were summed from whatever the parts carry, then fitting a sensor or a bracket would change the draft of the boat by however much collision geometry that part happened to be modeled with, which is an artifact of the model rather than a property of the vessel. Declaring the hull's displacement geometry at the assembly keeps the waterline a consequence of the vessel and its load, not of modeling detail in the catalog.

## What changed in review

The earlier draft proposed that AUR mass, inertia and center of mass be declared directly on the assembly, with rigidly-attached parts carrying no inertia of their own.

That is not the direction. Deriving from parts is retained, and assembly-level tooling is what makes the aggregate visible.

Introducing a displacement shape distinct from the collision mechanism was considered in the same review and rejected as too much change for now. The buoyancy plugin's only input is `<collision>` geometry, so displacement continues to be communicated that way. That is a separate question from *which* collision geometry displaces water — see [Open questions](#open-questions).

Consequently these are **not** part of the design:

- Assembly-declared mass, inertia or center of mass.
- Rigidly-attached parts carrying no inertia.
- A displacement primitive independent of the `<collision>` mechanism.

## Where each value lives

Every part is delivered with a xacro macro that instantiates its link — visual, inertia, and optionally collision. The macro is the source of truth for that part's **mass, inertia tensor and center-of-gravity pose**, taken from physical reality rather than from primitive geometry.

Collision is optional per part. The starting point for a part that has one is a translation of the collision geometry already described in its `model.sdf`.

Assemblies are composed from a parts-level YAML, generalizing the `accessories:` list that `bluerov2_description/config/bluerov2.yaml` uses today. The YAML selects which parts make up a configuration and generates the models from them. The chassis is not always included, so membership is a choice the file expresses rather than an assumption baked into the assembly.

The delivery contract for a part is in [bluerobotics_parts/README.md](bluerobotics_parts/README.md).

## The two cases are not symmetric

This is the central point of the design, and the thing most likely to be got wrong by treating both vehicles the same way.

### UUV — submerged, flotation is a free parameter

UUVs such as the BlueROV2 operate fully submerged. Displacement is fixed by hull geometry, and the operator sets net buoyancy deliberately by adding foam or lead until the vehicle behaves as wanted. Net buoyancy is a design choice, so the simulation must let us state it.

Typical intents:

- **Neutral** — hangs in the column, neither rising nor sinking.
- **Slightly positive (negative)**  — drifts up slowly when unpowered, so a control failure surfaces the vehicle rather than losing it.


Changing payload changes mass. In the real vehicle the operator re-trims to restore the target buoyancy. The simulation should express those two independently: **mass is what it is, and net buoyancy is what we trimmed it to.**

Magnitude is only half of it. Where the two forces act matters as much as how large they are, so the user needs the **center of mass relative to the chassis origin** as well as the total, and needs to place the **center of buoyancy** against it.

The separation between center of gravity and center of buoyancy is a key design choice. It sets the righting moment: a CB above the CG rights the vehicle when it is disturbed, and the size of the offset sets how stiffly. Get it wrong and the vehicle either refuses to hold attitude or snaps back unrealistically hard. Both quantities therefore have to be expressible as poses, not just as scalars.

### USV — floating, flotation is an outcome

USVs such as BlueBoat float. The vessel settles where displacement equals weight, so net buoyancy at rest is zero by definition.

What varies instead, and what matters:

- **Draft** — how deep it sits, set by total mass.
- **Trim** — fore-and-aft attitude, set by longitudinal center of mass.
- **List** — port-and-starboard attitude, set by lateral center of mass.

So for a surface vessel the waterline is an outcome the water works out, from mass properties that are themselves derived. Adding payload makes the boat sit deeper; putting it on one side makes the boat lean.

The behaviors worth exercising: correct resting waterline, recovery from a disturbance, and sensible response to asymmetric loading. This is still all actively being tested with the general purpose buoyancy plugin, and moving away from the previous surface plugin for this.


## The UUV parameters as implemented

`config/bluerov2.yaml` accepts an optional `buoyancy:` block with two keys:

```yaml
buoyancy:
  net_buoyancy: 0.002        # kg, positive floats up
  cob_offset: "0 0 0.046"    # m, center of buoyancy relative to the center of mass
```

Both are optional, and the defaults preserve the previous behavior: a two gram fail safe rise, with the center of buoyancy about 46 mm above the center of mass. The USV does not use them.

`net_buoyancy` is a displaced mass in kilograms rather than a fraction. That is the quantity an operator actually handles, since foam and lead are bought in grams, and it does not scale silently when the vehicle gets heavier. The earlier `buoyancy_margin` fraction, and the hundredfold trap that came with it, are gone.

`cob_offset` is the BG vector: where the buoyant force acts relative to where weight acts. It sets the righting stiffness directly, because the righting moment of a submerged vehicle is (m + b) g BG sin(theta). It is declared relative to the center of mass rather than in the chassis frame on purpose: mass is what it is, and handling is what we tuned it to, so a loadout change preserves both. Keep the z component positive, since a center of buoyancy at or below the center of mass is unstable.

The generation composes the total mass and center of mass from the same data that builds the links, then solves the height and the full 3D center of the `base_link` collision box so that both declarations hold for the configured loadout. The earlier `buoyancy_cob_z` positioned the box in z only, pinning x and y to zero; the new solve places all three axes. A declaration that cannot be met, because it would need a non positive box volume, fails the build loudly.

## Out of scope

- Power, energy, state of charge, endurance, electrical faults. None of it is simulated, and no part of this feature implies it.
- Identified hydrodynamic coefficients. Drag remains placeholder values; nothing here changes that.
- Enabling added mass.
- Dynamic mass change during a run — shedding ballast, releasing a payload. Composition is at build time.
- A displacement primitive independent of the `<collision>` mechanism.
- **Where the parts-level YAML lives** and how it relates to the existing per-vehicle config. Handled separately.

## Known constraints for the implementation

Recorded so the design of *how* starts from the right place, without deciding it here.

- **URDF cannot express `<fluid_added_mass>`.** It lives in an SDF `<inertial>`, so the ROS and Gazebo paths will see different things unless handled deliberately.
- **`bluerov2_gazebo/model.sdf.xacro:254` records added mass as intentionally zero** because of the summation approach. Since summation is retained, that constraint stands and is not resolved by this design.
- **Graded buoyancy (floating vessels) accepts only box and sphere collisions**, and the buoyancy geometry doubles as contact geometry.
- **Sensors need their own links** for TF frames.
- **The parts library is empty today.** `bluerobotics_parts/models/` holds placeholder directories and `parts.csv`; no meshes, no `model.sdf`, no xacros have been delivered. Nothing here is blocked by existing content, which is why the delivery contract is worth settling now.

## Open questions

1. **Resolved: the hull box makes up the difference, but the correction is derived, not maintained.** The concern with keeping part collisions was hand maintained corrections that silently go wrong. In the implementation nothing is maintained by hand: the same accessory tables that generate the collision geometry feed the solve, so the box height and center re derive on every build and the combined centroid of every collision in the model lands on the declared center of buoyancy. Each accessory's collision is taken as displacing at its mount pose, an approximation worth well under a millimeter of CoB for the current catalog.

   Ignoring part collisions entirely through the buoyancy plugin's per link `<enable>` was considered and set aside: the enable list lives in the world file, which stays vehicle agnostic, and scoped link names would couple it to the internals of one model. If worlds become generated artifacts this is worth revisiting.

2. **Does the design need to distinguish "collision for contact" from "collision for displacement" at the part level** to make the above work, given that introducing a separate displacement primitive is out of scope?  Yes, that is too drastic a change.
