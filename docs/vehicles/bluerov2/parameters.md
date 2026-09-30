# BlueROV2 Parameters

Where the BlueROV2's autopilot parameters and vehicle dynamics come from, so a reviewer can confirm we run the manufacturer's configuration where one exists and ArduSub's own where it does not.

```{note}
OUTLINE. The tables below are headings and empty rows; each is filled in as
phase 5 of the [SITL spec](../../specs/SITL_SPEC.md) produces it. Nothing
here is measured yet.
```

## What is fixed and what is free

| | Source | May it move to make a loop behave? |
|---|---|---|
| Frame, motor outputs, `ATC_ANG_RLL_P`, `ATC_ANGLE_MAX`, `ATC_INPUT_TC`, `EK3_SRC1_POSXY` | Blue Robotics' published chain | No — they are what we are being faithful to |
| `ATC_ANG_YAW_P`, `ATC_RAT_YAW_*`, `PSC_D_*` | ArduSub firmware defaults | No — see the note below on why these are the reference |
| Thrust limits | Blue Robotics' published bollard pull for the assembled vehicle | No — measured |
| Mass, inertia | the model | No |
| Hydrodynamic damping in yaw and heave | never measured; identified here | Yes, by identification from open-loop trials |

Identification stops being identification the moment a measured value is moved to make a loop behave. If the loops cannot work without moving one, that is a finding to write down here.

## The autopilot parameter file

`bluerov2_gazebo/params/bluerov2_sitl.params`, loaded last so it wins over the frame defaults `sim_vehicle.py` supplies.

### Blue Robotics publish very little, and that changes the claim

Their published chain for this vehicle is three files, and between them they set only:

| Source | What it sets |
|---|---|
| `ArduSub/4.7/base.params` | `SERVO1..6_FUNCTION` 33–38, `ATC_ANGLE_MAX`, `ATC_INPUT_TC`, `EK3_SRC1_POSXY` |
| `ArduSub/4.7/standard.params` | `FRAME_CONFIG 1`, `ATC_ANG_RLL_P 0.0` |
| `navigator/Standard BlueROV2.params` | the `%include` lines and auxiliary output assignments |

Our file already carries all of it. **There are no shipped gains for the loops this phase tests** — no yaw rate or angle gains, no depth gains. So "do the shipped gains work unmodified", the question phase 4 asked of the boat, cannot be asked the same way here.

What we do instead: treat ArduSub's compiled firmware defaults as the reference and write them into our file explicitly, so they are visible and cannot be changed by something we did not audit. TBD — the table of those values with the firmware constant each comes from.

The one that makes this necessary: ArduPilot's own SITL test file, `sub.parm`, sets `PSC_D_ACC_P 0.2`, `PSC_D_ACC_I 0.4` and `PSC_D_ACC_FF 0.075` where the firmware defaults are 0.05, 0.01 and no feedforward. Without writing the defaults out, depth behavior in simulation is set by an ArduPilot autotest value rather than by anything anyone chose for this vehicle.

### Line by line

TBD — every parameter in our file: which source it came from, whether it is published or a firmware default written out, and the reason for each `DELTA`.

| Parameter | Ours | Published | Firmware default | Note |
|---|---|---|---|---|
| | | | | |

## Thrust

Blue Robotics publish two different things, and they do not agree:

| Figure | Value | Measured on |
|---|---|---|
| T200 bench thrust at 16 V | 51.5 N ahead / 40.2 N astern | the thruster alone |
| BlueROV2 bollard pull | ~9 kgf forward, ~9 kgf lateral, ~7 kgf vertical | the assembled vehicle |

Four horizontals at 45° at the bench figure would give about 146 N forward where the vehicle measures about 88 N; two verticals would give 103 N against about 69 N. So in situ each thruster delivers roughly 60–65% of its bench figure — ducting, interference, flow through a crowded frame.

**The model carries the derated figures**, because the vehicle's own measurement is the better evidence for how the vehicle behaves, and the bench number would let the simulated ROV out-thrust the real one by half. TBD — the per-thruster endpoints, the arithmetic, and the resulting factor.

`deadband` is not set. Blue Robotics give no figure for the T200 beyond charts, and the boat's value is not transferable.

## Hydrodynamics

TBD — the identified coefficients, each with the trial it came from, and what stayed unexplained.

| Coefficient | Value | Identified from | Notes |
|---|---|---|---|
| `nRabsR` (yaw) | | | |
| `zWabsW` (heave) | | | |

Added mass is zero and stays zero: the model declares no added-mass terms, and the hydrodynamics plugin's explicit-acceleration path diverges when added mass exceeds rigid-body mass.

Why the trials are open loop, and why this differs from the boat: ArduSub's yaw loops are P+I with no feedforward, and the depth loop has an integrator too. An integrator drives steady-state error to zero whether or not the plant is right, so unlike the boat there is no standing bias to infer the plant gain from — and no published feedforward to invert. The open-loop trials are the only evidence, and the closed-loop runs are validation of the transient.

## Modes

TBD — per mode: what the RC input commands, what the vehicle is observed to do, and which feedback the loop needs to close.

| Mode | Stick commands | Observed | Feedback required |
|---|---|---|---|
| `MANUAL` | | | |
| `STABILIZE` | | | |
| `ALT_HOLD` | | | |

What the modes do *not* close is worth stating in the same table: roll, because `ATC_ANG_RLL_P` is 0 on the standard vehicle; pitch, because the `Vectored` frame mixes none; and horizontal position, because `EK3_SRC1_POSXY` is 0 and the vehicle carries no DVL or acoustic positioning.

## Open questions

TBD — anything that could not be resolved from published data: the question, why it matters, and what was assumed in the meantime.
