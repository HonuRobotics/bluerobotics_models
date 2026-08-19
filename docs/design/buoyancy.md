# Buoyancy

The Gazebo Buoyancy plugin sums every collision in a model, which would make
displacement depend on which accessories are fitted. Instead, **the assembly
owns displacement and parts own contact geometry**.

`<enable>` is evaluated per *link*, not per model: a link that is not enabled is
never given `Volume` or `CenterOfVolume` components and contributes no
displacement. So the assembly carries a dedicated buoyancy link, and the world
enables buoyancy on that link alone:

```xml
<enable>blueboat::buoyancy_link</enable>
```

No part needs to know whether the vehicle floats, and nothing has to be
subtracted to compensate for an accessory.

Displacement geometry is generated from the all-up-round (AUR) vehicle
configuration rather than summed from components — modelling the overall
buoyancy of the assembled vehicle is the normal approach for buoyant bodies:

* **USV pontoons** — several boxes per side rather than one long box, so under
  graded buoyancy each short segment responds to its own local depth and pitch
  restores properly.
* **UUV hull** — a single box whose height is solved so that
  `density × volume = mass × (1 + margin)`, giving near-neutral buoyancy.

Shape matters here. Graded buoyancy accepts **`<box>` and `<sphere>` only**;
anything else displaces nothing and warns once per process, which is easy to
miss. Uniform buoyancy also accepts cylinder and mesh. That restriction applies
to the buoyancy link, not to parts, so it never reaches the modeller.

One consequence to design around: displacement must live entirely on the enabled
link. A genuinely buoyant part — a float, a syntactic block — cannot express
that through its own collision.
