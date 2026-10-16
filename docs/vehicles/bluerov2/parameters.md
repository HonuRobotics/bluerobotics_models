# BlueROV2 Parameters

Where the BlueROV2's autopilot parameters and vehicle dynamics come from, so a reviewer can confirm we run the manufacturer's configuration where one exists and ArduSub's own where it does not.

```{note}
The autopilot parameters below are settled: every value is either Blue Robotics' published figure or an ArduSub compiled default written out, and the table says which. The thrust endpoints and deadband are settled from published data. The hydrodynamic coefficients have a coarse first estimate but are not settled — they are still being identified, and their section says so.
```

## What is fixed and what is free

| | Source | May it move to make a loop behave? |
|---|---|---|
| Frame, motor outputs, `ATC_ANG_RLL_P`, `ATC_ANGLE_MAX`, `ATC_INPUT_TC`, `EK3_SRC1_POSXY` | Blue Robotics' published chain | No — they are what we are being faithful to |
| `ATC_ANG_YAW_P`, `ATC_RAT_YAW_*`, `PSC_D_*` | ArduSub firmware defaults | No — see the note below on why these are the reference |
| Thrust limits and deadband | T200 bench data, scaled to Blue Robotics' published bollard pull for the assembled vehicle — see [Thrust](#thrust) | No — measured |
| Mass | Blue Robotics' published weight in air — see [Mass](#mass) | No |
| Inertia | the model, scaled to the mass | No |
| Hydrodynamic damping in surge, sway, heave and yaw | never measured; a coarse estimate from published thrust and top speeds, then identified here | Yes, by identification from open-loop trials |

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

## Mass

Blue Robotics publish the BlueROV2's weight in air, with the default ballast and their lithium-ion battery, as 11–12 kg ([BlueROV2 specifications](https://bluerobotics.com/store/rov/bluerov2/)). The model targets the middle of that range, **11.5 kg**, for the assembled vehicle.

The mass is not set in one place: the model adds up every part. The six T200 thruster bodies, six propellers and the camera are parts with their own masses, together 2.144 kg, so the chassis (`base_link` in `bluerobotics_parts/urdf/bluerov2_chassis.urdf.xacro`) carries the rest: 11.5 − 2.144 = **9.36 kg**. Changing a part's mass, or adding parts in the vehicle config, changes the total; buoyancy follows it automatically, so the vehicle stays at its configured trim.

The chassis inertia tensor was scaled to an earlier 9.4 kg; at 9.36 kg the difference is under 0.5% and it is left as is. [Practice]

## Thrust

Blue Robotics publish two different things, and they do not agree:

| Figure | Value | Measured on | Source |
|---|---|---|---|
| T200 bench thrust at 14 V / 16 V | 4.524 / 5.245 kgf ahead, 3.517 / 4.069 kgf astern | the thruster alone | [T200 performance data](https://cad.bluerobotics.com/T200-Public-Performance-Data-10-20V-September-2019.xlsx) |
| BlueROV2 bollard pull | 9 kgf forward (45°), 9 kgf lateral (45°), 7 kgf vertical | the assembled vehicle | [BlueROV2 specifications](https://bluerobotics.com/store/rov/bluerov2/) |

The model carries the vehicle's figure, because the vehicle's own measurement is the better evidence for how the vehicle behaves. It is applied in two layers, so each number lives where it belongs:

1. **The part carries the thruster on a bench**, at the vehicle's 14.8 V pack, interpolated between the 14 V and 16 V sheets: **4.812 kgf = 47.2 N ahead, 3.738 kgf = 36.7 N astern**. That is a fact about the T200 and is in `bluerobotics_parts/urdf/t200_prop_ccw.urdf.xacro` and `t200_prop_cw.urdf.xacro`.
2. **The vehicle applies an installation factor**, `thrust_install_factor` in `bluerov2_gazebo/model.sdf.xacro`, for what the frame costs the thrusters: ducting, interference, flow through a crowded frame. That is a fact about this vehicle.

### The installation factor

ArduSub's `Vectored` mixing (`AP_Motors6DOF.cpp`, `Sub-4.7.1`) sets which way each thruster runs in a bollard pull:

- **Forward:** thrusters 1 and 2 astern, 3 and 4 ahead. Lateral is the same split. Each horizontal is at 45°, so it contributes cos 45° of its thrust.
- **Vertical:** both verticals run the same way.

Setting the factor *k* so the bench figures reproduce the published pull:

| Axis | Equation | *k* |
|---|---|---|
| forward / lateral | 0.707 × 2 × *k* × (4.812 + 3.738) = 9 kgf | 0.744 |
| vertical | 2 × *k* × 4.812 = 7 kgf | 0.727 |

The vertical row assumes the published 7 kgf is the ahead direction, the stronger one. Against the astern figure it would be 0.936, which is out of line with the horizontals; the agreement between 0.744 and 0.727 is the reason to read it this way. [Practice]

**The model uses *k* = 0.74**, one factor for all six thrusters, giving **34.9 N ahead and 27.2 N astern** per installed thruster. With it the model reproduces 8.94 kgf forward and lateral and 7.12 kgf vertical.

The Heavy has no published bollard figures and takes the same factor. That is an assumption, not a measurement. [Open]

```{note}
An earlier draft of this page put the factor at 60–65%. That compared the 16 V bench figures against the pull with all four horizontals running ahead; with the pack voltage and the astern pair accounted for, it is 0.74. [Corrected]
```

### Deadband

The T200's ESC gives zero thrust within ±32 µs of neutral at 14 V and ±28 µs at 16 V, out of a ±400 µs range: about 0.075 of the command, from the same performance data.

The plugin's `<deadband>` is a threshold on thrust in newtons, not on the command. Under the plugin's linear map from command to thrust, 0.075 of the bench endpoint is **3.5 N**, which the part declares; the vehicle scales it by *k* with the endpoints, so the installed deadband is **2.6 N** and the dead zone stays the same fraction of the command.

The cost: just outside that band the real thruster delivers about 0.4 N, not 2.6 N, because its thrust curve is not linear near zero. Thrust curves are out of scope, so the model reproduces where the dead zone is rather than the force at its edge. [Practice]

## Hydrodynamics

### Coarse identification

A first estimate, from published figures and stated guesses, made before any trial. Quadratic drag only: the linear terms are zero. At top speed the full thrust is balanced by drag alone, so each coefficient is the full thrust over the top speed squared, *c* = *F* / *v*².

| Coefficient | Value | Full thrust *F* | Top speed *v* | Confidence |
|---|---|---|---|---|
| `xUabsU` (surge) | −39.2 N·s²/m² | 9 kgf = 88.3 N, published forward bollard | 1.5 m/s, published maximum forward speed | [Practice] |
| `yVabsV` (sway) | −157.0 N·s²/m² | 9 kgf = 88.3 N, published lateral bollard | 0.75 m/s, estimated at half the surge speed | [Open] |
| `zWabsW` (heave) | −122.1 N·s²/m² | 7 kgf = 68.7 N, published vertical bollard | 0.75 m/s, estimated at half the surge speed | [Open] |
| `nRabsR` (yaw) | −2.11 N·m·s²/rad² | 20.8 N·m, derived below | π rad/s (180 °/s), estimated | [Open] |
| `kPabsP` (roll), `mQabsQ` (pitch) | −3.992 N·m·s²/rad² | — | — | unchanged; neither axis is closed on this vehicle |

Blue Robotics publish no yaw figure, so the yaw torque comes from the thrusters and the frame. A full yaw command drives all four horizontals at full, two ahead and two astern, so the torque is (34.9 + 27.2) N × (0.164 + 0.171) m = 20.8 N·m. The thrust figures are the installed endpoints from [Thrust](#thrust); the moment arms are each thruster's perpendicular distance from the center, from the slot positions and 45° mounting in `bluerov2_chassis.urdf.xacro`. Nothing in it depends on the damping being identified.

The sway, heave and yaw top speeds are guesses, to be revised as we learn more; the coefficients follow from them directly, so revising a speed means recomputing its row.

### Verifying the coarse identification

This differs from the boat. There, because we had estimates on the maximum surge and yaw rate from the Ardu configuration, we could tune with the objective of matching the specified closed-loop response.  Here we do something similar in that we first set open loop from estimated top speeds, and the check is mostly automated: a test commands each axis and reports what the vehicle did, and a person reads the report and spot-checks it in the viewport.

**1. Run the autmated, headless motion tests.** In drydock:

This test runs automated open-loop command tests, providing fixed command efforts in each controllable degree of freedom (surge, sway, heave an yaw).  The commands are giving in both +/- directions.  They pass through teleop mixer thrust allocation (not the ArduSub vectored thrust allocaion)

(Warning: This test takes order of minutes to complete!)

```bash
source ~/maritime_ws/install/setup.bash
cd ~/maritime_ws/src/bluerobotics_models/bluerov2_gazebo
python3 -m pytest -s test/test_gz_launch.py -k axis
```
(BTW, the same test can be run with 
`colcon test --packages-select bluerov2_gazebo` which the same output to `log/latest_test/bluerov2_gazebo/stdout.log`.


The test commands (currently 0.5, or 50% effort) on each of surge, sway, heave and yaw, in both directions, through the teleop mixer's allocation (not through ArduSub's vectored thrust).  The test  passes a case when the motion lies within a fized angle (currently 25 degrees) of the commanded axis and its speed is within a factor of ten of an expected figure. The acceptance criteria are set in [src/bluerobotics_models/bluerov2_gazebo/test/test_gz_launch.py] as parameters of the test. The acceptable values and acceptance ranges come from the vehicle's published performance and engineering judgment.

The test ends with one row per case: the expected speed, the limits, the measured speed, their ratio, the angle off the commanded axis, and the velocity in the body frame. Read it for more than pass or fail:

- **Measured speed.** Under quadratic drag, a 0.5 command should give about 0.71 (√0.5) of the axis's top speed in the coarse identification table above. A measured speed far from that points at the coefficient for that axis, or at the thrust.
- **Ratio.** Measured over expected, the figure the factor-of-ten limit is applied to.
- **Off axis.** A few degrees is coupling. An angle near 180° is a reversed thruster or a wrong mixer sign.
- **Body rate.** The off-axis components say which way the vehicle drifts. A drift with the same sign in both directions of an axis is coupling, not polarity.

Expect to see output similar to this (the numbers will likely be different)
```
================================== Axis command results ===================================
case     expected     speed limits  measured     ratio  off axis (<= 25)  body rate x, y, z       result
-------  -----------  ------------  -----------  -----  ----------------  ----------------------  ------
surge +  0.750 m/s    0.075 - 7.5   1.059 m/s    1.41   1.2 deg           +1.058, -0.010, +0.020  pass
surge -  0.750 m/s    0.075 - 7.5   1.058 m/s    1.41   1.3 deg           -1.058, -0.015, +0.018  pass
sway +   0.500 m/s    0.05 - 5      0.568 m/s    1.14   22.5 deg          -0.217, +0.524, +0.013  pass
sway -   0.500 m/s    0.05 - 5      0.558 m/s    1.12   19.7 deg          -0.188, -0.525, +0.010  pass
heave +  0.500 m/s    0.05 - 5      0.472 m/s    0.94   1.4 deg           +0.002, -0.012, +0.472  pass
heave -  0.500 m/s    0.05 - 5      0.536 m/s    1.07   3.2 deg           +0.030, -0.002, -0.535  pass
yaw +    3.142 rad/s  0.314 - 31.4  2.221 rad/s  0.71   0.1 deg           -0.002, +0.004, +2.221  pass
yaw -    3.142 rad/s  0.314 - 31.4  2.221 rad/s  0.71   0.2 deg           +0.004, -0.005, -2.221  pass
======================= 8 passed, 5 deselected in 103.66s (0:01:43) =======================
```
**2. Spot-check in the viewport (manual and with GUI).** The table can be right about numbers and still miss something a person sees at once, such as the vehicle tumbling or rolling. Start the playground with the GUI:

```bash
source ~/maritime_ws/install/setup.bash
gz sim -r $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_playground.sdf
```

Then, in a second shell, command one axis with  the small utility `axis_command`, which sends each thruster what the teleop mixer would for that axis (the same allocation as the test). E.g., Surge ahead at 0.5:

```bash
source ~/maritime_ws/install/setup.bash
ros2 run bluerobotics_teleop axis_command x 0.5 --timeout -1
```

It prints the per-thruster commands and holds them until Ctrl+C (`--timeout -1`; the default is one second), then stops every thruster. Repeat for `y`, `z` and `yaw`, and with `-0.5` for the reverse direction.

(In the future, this utility script may be replace by a future keyboard teleop configuration - see issue #77)

This manual validation is less algorithmic and engineering judgement.  It helps to have piloted one of these ROV's in the past.  They are snappy and responsive, so the user should verify it "feels" similar.  Also, because we will be mainly using this under the control of ArduSub, we can afford to have the open-loop ROV tuned to be more controllable and then regulate the max rates using ArduSub settings.

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

- **Sway drifts off axis in the axis test.** With the coarse coefficients, a sway command drifts backward as well as sideways, about 22–24° off axis, sometimes in only one direction. That rules out polarity; the suspected cause, not yet confirmed, is a small yaw torque from the thruster layout turning the vehicle while it slides, which the open-loop teleop mix does nothing to hold. The direction bound was widened from 20° to 25° to accept it, and the behavior is assessed by hand in the spot check.
