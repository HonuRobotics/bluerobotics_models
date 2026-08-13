# All-up-round mass and buoyancy

Status: draft design, for review. **Functional scope only** — what the feature does and why. Implementation is deliberately deferred.

---

## Proposal

The key concept is that both the inertia and displacement parameters of the vessel assembly be specified directly at the assembly level instead of indirectly by specifying the parameters of each part within the assembly.   The properties of the vessel assembly are termed the all-up-round (AUR) properites.  "All-up-round" is the assembled vehicle as it goes in the water: hull, thrusters, accessories, batteries, ballast, cabling and everything else, in the configuration being simulated.  

## Why
For vehicles that float at the surface or subsea, the correct level of abstraction for defining mass and displacement (buoyancy) is at the AUR level, not at the individual part level.  This is the point of contact between sim and real and the natural point of connection to allow users to mimic hardware behavior through selecting the overall mass and dislaced volume of the entire robot/vehicle.   

This also allows for configuring internal changes (e.g., additional battery mass) in a general purpose and reusable way.   For the battery use case (one of many), the user configures the inertial properties, in the standard URDF way, to mimic the effect of adding, subtracting or moving batteries internal to the hull - while leaving the overall vessel displacement unchanged.   The resulting change in simulated behavior mirrors the changes in vessel loadout. 

This also allows us to add sensors, payload, actuators, etc. without having to change the assembly.   For underwater vehicles, everytime you add a sensor you have to add ballast (lead) or buoyancy (foam) to mantain trim.  We dont need to do that same process in the sim and we can just add and subtract parts without affecting the neutral buoyancy ballance.  

## Current design 

**Nothing owns the aggregate.** Mass is summed upward from parts, there is not one source of truth for the as configured vehicle.  We want the expose this as a user-defined parameter because this is the point of connection between sim and real - measuring the mass of the real vessel.

**Displacement and mass are handled by opposite philosophies.** In the same file, displacement (and hence buoyancy) is *declared* — state a target, back-solve the hull box, subtract accessory volume to hit it — while mass is *summed*. The declared approach is the one that works and we can reuse the same concept for mass as well.

**Added mass is blocked on it.** `bluerov2_gazebo/model.sdf.xacro:254` records that added mass is intentionally zero because of a limitation of the summation approach.   Setting the mass of the entire assembly would allow us to set the added mass o fthe assembly at the AUR level as ell.  


This also completes a rule the repo already adopted. `README.md` states that *the assembly owns displacement and parts own contact geometry*. Mass and inertia are the properties that rule did not yet cover.

## What the feature provides

The assembly declares, and the model is built to match:

| Declaration | Meaning |
|---|---|
| **AUR dry mass** | Mass of the assembled vehicle in air, as configured |
| **AUR inertia** | Rotational inertia of that assembled vehicle |
| **Centre of mass** | Where that mass acts, in the vehicle frame |
| **Flotation intent** | How the vehicle should behave in water — see the two cases below |

These values are **set directly on the assembly**, not reconciled against anything. There is no nominal-versus-declared comparison and nothing to back-solve: the declaration simply is the vehicle body's inertial specification, written the ordinary URDF/SDF way.

A full inertia tensor is declared where it is known and derived from geometry and the declared mass where it is not — precision where we have it, a reasonable default everywhere else. There is deliberately no check against what the parts would have summed to: the sum is not a source of truth and is ignored from the start.

Rigidly-attached parts therefore contribute no inertia of their own — they are already inside the declared total, and giving them mass as well would double-count. Parts that articulate are the exception: a propeller spinning on a joint needs its own rotational inertia for the joint dynamics to mean anything, so it keeps it.

## The two cases are not symmetric

This is the central point of the design, and the thing most likely to be got wrong by treating both vehicles the same way.

### UUV — submerged, flotation is a free parameter

UUVs such as the BlueROV2 operate fully submerged. Its displacement is fixed by hull geometry, and the operator sets net buoyancy deliberately by adding foam or lead until the vehicle behaves as wanted. Net buoyancy is a design choice, so the simulation must let us state it.

Typical intents:

- **Neutral** — hangs in the column, neither rising nor sinking.
- **Slightly positive** (the normal case) — drifts up slowly when unpowered, so a control failure surfaces the vehicle rather than losing it.
- **A specific offset** — float or sink by a stated amount, for testing recovery or descent.

The behaviour we want to exercise is the slightly-positive case: the ROV rises gently with thrusters idle, and depth-holding control has something real to work against. That is the single most valuable behaviour this feature delivers.

Changing payload changes mass. In the real vehicle the operator re-trims to restore the target buoyancy. The simulation should express those two independently: **mass is what it is, and net buoyancy is what we trimmed it to.**

How the user states all of this is covered in [User interface intent](#user-interface-intent) below.

### USV — floating, flotation is an outcome

USVs such as BlueBoat float. It settles where displacement equals weight, so net buoyancy at rest is zero **by definition** 

What varies instead, and what matters:

- **Draft** — how deep it sits, set by total mass.
- **Trim** — fore-and-aft attitude, set by longitudinal centre of mass.
- **List** — port-and-starboard attitude, set by lateral centre of mass.

So for a surface vessel the declaration is **mass and centre of mass**, and the waterline is an outcome the water works out. Adding payload makes the boat sit deeper; putting it on one side makes the boat lean.

The behaviours worth exercising: correct resting waterline, recovery from a disturbance, and sensible response to asymmetric loading.

### Stated as one rule

> The assembly declares its mass properties. For a submerged vehicle it also declares net buoyancy, because that is something the operator sets. For a floating vehicle it does not, because the water decides.

## User interface intent

**Discussion point — the intent is settled, the mechanism is not.**

The four quantities a user should be able to state for the assembled vehicle:

| Quantity | Sets |
|---|---|
| **Mass** | How much vehicle there is |
| **Moment of inertia** | How it resists rotation |
| **Centre of mass** | Where the weight acts |
| **Total displacement** | The buoyant force |
| **Centre of buoyancy** | Where that force acts |

The first three are already stated directly and in a form users know — the ordinary URDF/SDF `<inertial>` block. That is the model to follow.

Displacement is not. Today it is *implied* by collision geometry: the buoyancy plugin sums collision volumes and derives a centre of volume from them, so the only way to say "this vehicle displaces 11.5 litres, centred here" is to construct a box that happens to work out that way. That is why the ROV back-solves a hull box height, and why fitted accessories have to be subtracted from it. The number the user cares about is never written down; a proxy for it is.

**The intent is symmetry**: displacement and centre of buoyancy stated as plainly as mass and centre of mass, with the geometry following from the declaration rather than the other way round.

Whether that is achievable is an implementation question, but it is not obviously blocked. The Buoyancy plugin exposes no SDF element for volume or centre of volume — its only inputs are `uniform_fluid_density`, `graded_buoyancy` and `enable`. However, it derives those quantities into `components::Volume` and `components::CenterOfVolume` and **skips the derivation entirely for any link that already has them**. So a declared value is something the plugin would honour if it were populated ahead of it.

Two things to settle before designing this:

1. Whether displacement is declared per vehicle or per buoyancy link, given that a USV wants distributed displacement for pitch response and a UUV wants a single body.
2. Whether the collision geometry still has to exist for contact purposes once it is no longer carrying displacement duty — and if so, whether the two can finally be separate shapes rather than one box doing both jobs.

## What this replaces

- The hardcoded near-neutral buoyancy margin in the ROV, which becomes an explicit declaration.
- The hand-maintained accessory volume table used to compensate displacement for fitted accessories.
- Any need for a battery loadout feature. Everything a battery does to the engineering reaches the simulation through mass and net buoyancy, both covered here. A battery would only warrant being a part if it needed a *visible* model, which is a mesh question for the parts library rather than a physics one.

## Out of scope

- Power, energy, state of charge, endurance, electrical faults. None of it is simulated, and no part of this feature implies it.
- Identified hydrodynamic coefficients. Drag remains placeholder values; nothing here changes that.
- Enabling added mass. This feature makes it *expressible*; turning it on is separate work.
- Dynamic mass change during a run — shedding ballast, releasing a payload. Declaration is at build time.

## Known constraints for the implementation

Recorded so the design of *how* starts from the right place, without deciding it here.

- **URDF cannot express `<fluid_added_mass>`.** It lives in an SDF `<inertial>`, so the ROS and Gazebo paths will see different things unless handled deliberately.
- **The engine composes link inertias — but that is avoidable.** It only forces a back-solve if rigidly-attached parts carry inertia of their own. If they carry none, there is no sum to reconcile and the declaration is simply the body's `<inertial>`. Articulated parts keep their own inertia and compose on top, which is physically correct rather than a workaround.
- **Graded buoyancy (floating vessels) accepts only box and sphere collisions**, and the buoyancy geometry doubles as contact geometry.
- **Sensors need their own links** for TF frames, so not every part can be folded into the parent body.

## Open questions

1. **Does the USV need a net-buoyancy override for non-equilibrium cases** such as swamping or a flooded hull, or is mass and centre of mass sufficient?
2. **Where does the declaration live** — vehicle config, assembly, or both, and what happens when a configuration changes the loadout?
