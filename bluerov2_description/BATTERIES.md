# BlueROV2 battery

The battery is configured in `config/bluerov2.yaml` under `batteries:`. Packs
and the tube slot are defined in [config/batteries.yaml](config/batteries.yaml),
which is the single source for masses, sizes and the slot pose. The loadout is
validated at build time; a bad slot, an oversized pack or an out of range
offset fails the build with a message.

## Packs

| Key | Pack | Mass | Energy |
|---|---|---|---|
| `br_liion_18ah` | Lithium-ion 14.8V 18Ah (the standard) | 1.400 kg | 266.4 Wh |
| `br_lipo_10ah` | Lithium Polymer 14.8V 10Ah (travel) | 0.750 kg | 148 Wh |
| `br_liion_15_6ah` | Lithium-ion 14.8V 15.6Ah (discontinued) | 1.163 kg | 230 Wh |

Third party packs are supported inline:
`{custom_pack: {mass: 1.2, size: [0.14, 0.07, 0.06]}, slot: tube}`.

## Slot

One slot, `tube`: the 3 inch battery enclosure at the bottom centre of the
frame. The pack is much shorter than the tube; sliding it fore/aft is the real
world pitch trim practice, expressed as `offset: {x: ...}` within the allowed
range.

## Default

Omitting `batteries:` gives the as sold configuration: one 18Ah pack centred
in the tube.

## Physics and buoyancy trim

The battery carries inertia only, never collision geometry: it displaces no
water of its own. Its mass enters the buoyancy box sizing, together with the
config's net buoyancy target:

```yaml
buoyancy_trim: neutral_plus   # the default
```

- `neutral`: displacement equals all-up mass exactly; the vehicle hangs in the
  water column.
- `neutral_plus`: the historical fail-safe margin (slightly positive, a dead
  vehicle drifts up slowly).
- a signed number in kg: float up (+) or sink (-) by that much, e.g. a heavier
  custom pack without re-ballasting is `buoyancy_trim: -0.5`.

Swapping packs keeps the configured trim: the box resizes for the new mass,
modelling an operator who re-ballasts after the swap.
