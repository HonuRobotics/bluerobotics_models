# BlueBoat batteries

The battery loadout is configured in `config/blueboat.yaml` under `batteries:`.
Packs and hull bays are defined in [config/batteries.yaml](config/batteries.yaml),
which is the single source for masses, sizes and slot poses. The loadout is
validated at build time; a bad slot, an oversized pack or an out of range
offset fails the build with a message.

## Packs

| Key | Pack | Mass | Energy |
|---|---|---|---|
| `br_liion_18ah` | Lithium-ion 14.8V 18Ah (the standard) | 1.400 kg | 266.4 Wh |
| `br_lipo_10ah` | Lithium Polymer 14.8V 10Ah (travel) | 0.750 kg | 148 Wh |
| `br_liion_15_6ah` | Lithium-ion 14.8V 15.6Ah (discontinued) | 1.163 kg | 230 Wh |

Third party packs are supported inline:
`{custom_pack: {mass: 1.2, size: [0.14, 0.07, 0.06]}, slot: port_aft, name: mypack}`.

## Slots

Four bays per hull on the hull floor (`port_fwd`, `port_mid_fwd`,
`port_mid_aft`, `port_aft` and the `stbd_` mirrors), up to eight packs total.
Packs may slide fore/aft within a bay: `offset: {x: ...}` inside the bay's
allowed range. The bay grid is symmetric about the pontoon centre, so a full
loadout is pitch neutral by construction.

## Default

Omitting `batteries:` gives the as sold configuration: one 18Ah pack per hull
in the `mid_fwd` bays, even port/stbd mass per the operator guide.

## Physics

Batteries carry inertia only, never collision geometry: a pack inside a hull
displaces no water of its own, and the buoyancy plugin sums collisions as
displacement. A heavier loadout therefore rides deeper and trims with pack
placement, exactly like the real boat. The build warns when port and starboard
battery mass differ by more than one pack.
