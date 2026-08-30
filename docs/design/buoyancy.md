# Buoyancy: all up round mass and displacement

The all up round (AUR) properties of a vessel are those of the assembled
vehicle as it goes in the water: hull, thrusters, accessories, batteries,
ballast. Mass properties and displacement are treated differently, on
purpose:

| Property | How it is obtained |
|---|---|
| Mass, inertia, center of mass | **Derived.** Composed from the parts; each part's macro is the source for its own values. Mass is never declared at the assembly |
| Displacement and center of buoyancy | **Declared** at the assembly. A USV declares hull collision geometry; a UUV declares a net buoyant balance and a center of buoyancy offset |

Deriving mass keeps one source of truth per part: a config change (a
battery, a sensor, an empty slot) propagates on its own and is visible in
the generated model's specs comment. Displacement cannot work that way: for
a USV the displacing shape must be the hull and only the hull, so that
fitting a bracket does not change the draft by whatever collision volume the
bracket carries; for a UUV, flotation is a trim the operator sets with foam
and lead, stated directly and held across configurations.

## USV: hull displacement

`hull_displacement` in the config declares each pontoon as a row of box
segments (`length`, `width`, `height`, `x`, `y`, `z`, `segments`). The Gazebo
composition places them on a dedicated `hull_displacement` link, fixed to
`base_link`, and the worlds enable graded buoyancy **on that link only**
(`<enable>blueboat::hull_displacement</enable>`). Buoyancy is evaluated per
link, so the parts' own collisions (the hull cylinders, hatch
boxes, the prop hubs) stay what they are, contact geometry, and never
displace; the chassis keeps them on. The URDF carries no displacement
geometry at all: displacement is a simulator concern. Segmenting matters:
each short box responds to its own local depth, so a pitched or rolled
waterplane restores correctly, where a single long box keys off its center
and barely restores. The boat self settles to a draft of roughly
`mass / (water_density * 2 * length * width)`, which puts `base_link` at the
waterline for the BlueBoat.

## UUV: declared trim (BlueROV2)

`buoyancy:` in the BlueROV2 config takes `net_buoyancy` (kg, positive floats
up; a displaced mass, not a fraction, so the trim does not scale silently
with heavier parts fitted), `cob_offset` and `cob_frame` (`com`: the offset is
the BG vector and sets righting stiffness directly; `base_link`: the center
of buoyancy is pinned in the hull like the real vehicle), and
`fluid_density` (must match the world's buoyancy plugin; both default to
1025) and `footprint` (the box footprint; height is solved). The model
generation computes the assembled total mass and center of mass from the
URDF and solves an analytic box on a dedicated `buoyancy_displacement`
link, the only link the worlds enable buoyancy on, so both declarations
hold for the configured vehicle and the parts' own collisions stay pure
contact geometry. The same pattern as the BlueBoat's pontoons, with the
box solved instead of declared.

## Constraints

- URDF cannot express `<fluid_added_mass>`; added mass stays out of the
  description (the Gazebo hydrodynamics plugin is where it would go).
- Graded buoyancy accepts only box and sphere collisions; both vehicles
  therefore realize displacement as boxes on a dedicated enabled link,
  separate from the parts' contact geometry.
- Sensors need their own links for TF frames, which the parts' frames
  provide.
