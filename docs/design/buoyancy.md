# Buoyancy: all up round mass and displacement

The all up round (AUR) properties of a vessel are those of the assembled
vehicle as it goes in the water: hull, thrusters, accessories, batteries,
ballast. Mass properties and displacement are treated differently, on
purpose:

| Property | How it is obtained |
|---|---|
| Mass, inertia, center of mass | **Derived.** Composed from the parts; each part's macro is the source for its own values. Mass is never declared at the assembly |
| Displacement and center of buoyancy | **Declared** at the assembly. A USV declares hull collision geometry; a UUV declares a net buoyant balance and a center of buoyancy offset |

Deriving mass keeps one source of truth per part: a loadout change (a
battery, a sensor, an empty slot) propagates on its own and is visible in
the generated model's specs comment. Displacement cannot work that way: for
a USV the displacing shape must be the hull and only the hull, so that
fitting a bracket does not change the draft by whatever collision volume the
bracket carries; for a UUV, flotation is a trim the operator sets with foam
and lead, stated directly and held across loadouts.

## USV: hull displacement

`hull_displacement` in the config declares each pontoon as a row of box
segments (`length`, `width`, `height`, `x`, `y`, `z`, `segments`), placed on
a massless `hull_displacement` link fixed to the base. Graded buoyancy
accepts only boxes and spheres, so the chassis part's own collisions (the
modeler's cylinders) are switched off in the base entry (`collision:
false`) and these boxes provide both displacement and contact. Segmenting
matters: each short box responds to its own local depth, so a pitched or
rolled waterplane restores correctly, where a single long box keys off its
center and barely restores. The boat self settles to a draft of roughly
`mass / (water_density * 2 * length * width)`, which puts `base_link` at the
waterline for the BlueBoat.

## UUV: declared trim (BlueROV2)

`buoyancy:` in the BlueROV2 config takes `net_buoyancy` (kg, positive floats
up; a displaced mass, not a fraction, so the trim does not scale silently
with a heavier loadout), `cob_offset` and `cob_frame` (`com`: the offset is
the BG vector and sets righting stiffness directly; `base_link`: the center
of buoyancy is pinned in the hull like the real vehicle), and
`fluid_density` (must match the world's buoyancy plugin; both default to
1025). The generation composes the total mass and center of mass and solves
the base collision box so both declarations hold for the configured
loadout; a declaration that cannot be met fails the build.

## Constraints

- URDF cannot express `<fluid_added_mass>`; added mass stays out of the
  description (the Gazebo hydrodynamics plugin is where it would go).
- Graded buoyancy accepts only box and sphere collisions; the buoyancy
  geometry doubles as contact geometry.
- Sensors need their own links for TF frames, which the parts' frames
  provide.
