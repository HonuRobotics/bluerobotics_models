# BlueROV2 Parameters

Where the BlueROV2's autopilot parameters and vehicle dynamics come from, so a reviewer can confirm we run the manufacturer's configuration where one exists and ArduSub's own where it does not.

```{note}
The autopilot parameters below are settled: every value is either Blue Robotics' published figure or an ArduSub compiled default written out, and the table says which. The thrust endpoints and the hydrodynamic coefficients are not settled — they are still being identified, and their sections say so.
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

What we do instead: treat ArduSub's compiled firmware defaults as the reference and write them into our file explicitly, so they are visible and cannot be changed by something we did not audit. Each value and the firmware constant it comes from is in the line-by-line table below, and the file repeats the constant in a comment beside every line.

The one that makes this necessary: ArduPilot's own SITL test file, `sub.parm`, is loaded by the `gazebo-bluerov2` frame and retunes the depth loop. It sets `PSC_D_ACC_P 0.2`, `PSC_D_ACC_I 0.4` and `PSC_D_ACC_FF 0.075` where the ArduSub defaults are 0.05, 0.01 and no feedforward, and `PSC_D_JERK 8` where the default is 5. Without writing the defaults out, depth behavior in simulation is set by an ArduPilot autotest value rather than by anything anyone chose for this vehicle.

The audit found the split is clean. `sub.parm` sets no `ATC_` parameter at all, so the yaw loops this phase tests were already running ArduSub's own gains; it is only the depth chain that was being retuned underneath us. It also sets the horizontal position gains `PSC_NE_*`, which do not apply here — with `EK3_SRC1_POSXY 0` there is no horizontal position estimate for them to act on, so our file leaves them alone rather than writing out a loop that cannot run.

### Line by line

Every parameter in the file, where it came from, and whether it agrees with stock ArduSub. Published values are from the three files above; defaults are from the pinned checkout, which is tagged both `Rover-4.7.1` and `Sub-4.7.1`, so they are the constants this SITL build compiles in.

| Parameter | Ours | Published | ArduSub default | Note |
|---|---|---|---|---|
| `FRAME_CONFIG` | 1 | 1, `standard.params` | 1, `SUB_FRAME_VECTORED` | Shipped, and already the stock value |
| `SERVO1..6_FUNCTION` | 33–38 | 33–38, `base.params` | derived from `FRAME_CONFIG` | Shipped. Redundant, since ArduSub assigns these itself; kept so our file reads against theirs |
| `ATC_ANG_RLL_P` | 0.0 | 0.0, `standard.params` | 6.0 | Shipped, and a real departure — two verticals give the standard vehicle little roll authority |
| `ATC_ANGLE_MAX` | 45 | 45, `base.params` | 30 | Shipped |
| `ATC_INPUT_TC` | 0.1 | 0.1, `base.params` | 0.10 | Shipped, and already the stock value |
| `EK3_SRC1_POSXY` | 0 | 0, `base.params` | 3, GPS | Shipped. No horizontal position source underwater |
| `ATC_ANG_YAW_P` | 6.0 | — | 6.0 | Default written out. The outer heading loop |
| `ATC_RAT_YAW_P` / `_I` / `_D` | 0.180 / 0.018 / 0.0 | — | same | Default written out. The loop this phase puts under test |
| `ATC_RAT_YAW_FF` | 0.0 | — | 0.0 | Default written out. No feedforward, which is why the boat's method of inferring the plant from a published FF does not transfer |
| `ATC_RAT_YAW_IMAX` | 0.222 | — | same | Default written out |
| `ATC_RAT_YAW_FLTT` / `_FLTD` | 5.0 / 5.0 | — | same | Default written out |
| `ATC_ACCEL_Y_MAX` | 1100 | — | same | Default written out, deg/s² |
| `PSC_D_POS_P` | 3.0 | — | 3.0 | Default written out. `sub.parm` agrees |
| `PSC_D_VEL_P` | 8.0 | — | 8.0 | Default written out. `sub.parm` agrees |
| `PSC_D_ACC_P` | 0.05 | — | 0.05 | Default written out, overriding `sub.parm`'s 0.2 |
| `PSC_D_ACC_I` | 0.01 | — | 0.01 | Default written out, overriding `sub.parm`'s 0.4 |
| `PSC_D_ACC_D` | 0.0 | — | 0.0 | Default written out |
| `PSC_D_ACC_FF` | 0.0 | — | 0.0 | Default written out, overriding `sub.parm`'s 0.075 |
| `PSC_D_ACC_IMAX` | 0.1 | — | 0.1 | Default written out |
| `PSC_D_JERK` | 5.0 | — | 5.0 | Default written out, overriding `sub.parm`'s 8 |

There is no `DELTA` row, and that is the result rather than an omission: every value is either what Blue Robotics publish or what the firmware compiles in. Simulation needed no concession from this vehicle, unlike the boat, whose trim and reversal had to be undone.

Blue Robotics' published configuration departs from stock ArduSub in only three values — the roll gain, the lean-angle limit and the horizontal position source. The roll gain is the one that changes what a mode does, and it is why `STABILIZE` on this vehicle meaningfully closes yaw and not roll.

The roll and pitch rate gains are deliberately not written out. `sub.parm` does not touch them, so nothing is moving underneath us, and neither loop is under test here: pitch because the `Vectored` frame mixes none, roll because its angle gain is zero.

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
