# BlueBoat Parameters

This documents the sources and methods used to define the default Blueboat vehicle dynamic and autopilot parameters.  


```{note}
OUTLINE. The tables below are headings and empty rows; each is filled in as
phase 4 of the [SITL spec](../../specs/SITL_SPEC.md) produces it. Nothing
here is measured yet.
```

## Approach

Our approach in defining the BlueBoat parameter is as follows:

1. Use the easily measureable parameters, e.g., mass
1. Use what is provided as autopilot stabilization layer parameters 
1. Derive what we can from first principles and approximation, e.g., inertia tensor
1. Select via testing and qualitative comparison, the hydrodynamic parameters that can not be easily measured or estimated.  These are the free parameters to tune the response to match (qualitatively) the known closed-loop performance. 


## Set via reference 

See [../parameter_refs.ods] for calculations weher a

| | Source | Value | Destination|
|---|---|---|---|
Mass | [BlueBoat spec sheets](https://bluerobotics.com/store/boat/blueboat/blueboat/) Boat chassis + 2 batteries | see [../parameter_refs.ods]  | blueboat_chassis.urdf.xacro |
Inertia tensor | Estimated based on uniform box and L, W, H dimensions BR specs. Consistent with original values. | see [../parameter_refs.ods] |  blueboat_chassis.urdf.xacro |
| Thrust limits | Deduced from [thruster performance](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/m200-motor/?attribute_cable-variant=BlueBoat+-+0.71+meter+cable+length+%2B+M14+WLP) at 16 V and max forward total thrust value from [blueboat specs](https://bluerobotics.com/store/boat/blueboat/blueboat/) | see [../parameter_refs.ods] | bluerobotics_parts/urdf/m200_weedless_prop_ccw.urdf.xacro and bluerobotics_parts/urdf/m200_weedless_prop_cw.urdf.xacro (known issue that they are repeated)
| Deadband | Approximated from the graph for the [m200](https://bluerobotics.com/store/thrusters/t100-t200-thrusters/m200-motor/?attribute_cable-variant=BlueBoat+-+0.71+meter+cable+length+%2B+M14+WLP) and engineering judgement. Small deadband.  Can be tuned out with PWM settings per vessel. | | bluerobotics_parts/urdf/m200_weedless_prop_ccw.urdf.xacro


### Drag estimates - open loop

Derive estimates of the linear and quadradic drag based on plublished maximum velocity specs.

#### Surge

##### Estimate
From blueboat specs, max speed is 3 m/s and the max static thrust is 8.2 kgf.   The Fossen drag implementation has both a linear and quadratic terms.  We neglect the linear term and estimate the quadradic coefficient - see [../parameter_refs.ods] 

##### Verify

Run a test to command full forward thrust and measure the steady state speed.  Compare the the 3 m/s target.

Run the scenario for the open-loop (`MANUAL`) test - [../../how-to/verify-sitl-boat.md]

The verify the speed of the USV two ways (do both to make sure the simulated model state is shared by the sensed state in the autopilot.  

1. In Gazebo use UI to view the World Linear Velocity of the blueboat/base_link.  (USV travels in x, so no need to resolve to body-frame.)
2. In MAVProxy...

```
module load graph
graph VFR_HUD.groundspeed
```

Then command full speed
```
rc 3 1900
```

The results do not meet expectations, we expected 3.0 m/s, but observe a steady-state speed 2.65 m/s.   
./images/surge_drag_tune_init.png

##### Adapt

* Based on evidence

* Reduce by drag that there is a margin on necessary control authority to achieve closed loop speed of 3 m/s.



Do open loop trials at max thrust and do first level of tunning.

* Mass: 


| | Source | May it move to make a loop behave? |
|---|---|---|
| `ATC_*`, `MOT_*`, speeds | Blue Robotics' published parameter sets | No — they are what we are being faithful to |
| Thrust limits, deadband | Blue Robotics' published performance data | No — measured |
| Mass, inertia | the model | No |
| Hydrodynamic damping | never measured; identified here | Yes, by identification from open-loop trials |

Identification stops being identification the moment a measured value is moved to make a loop behave. If the loops cannot be made to work without moving one, that is a finding to write down here, not a number to adjust.

## The parameter file

`blueboat_gazebo/params/blueboat_sitl.params`. TBD — one paragraph: what it is derived from, and that it is loaded last so it wins over the frame defaults `sim_vehicle.py` supplies.

### Provenance

Three published descriptions of a configured BlueBoat exist and they disagree. TBD — name each with its source and date:

| Source | What it is | Authoritative for |
|---|---|---|
| `BlueBoat120.params` | dump off the hardware | TBD |
| Blue Robotics' SITL set | their own simulation parameters | TBD |
| `SITL_Models` block | the ArduPilot-side model | TBD |

### Line by line

TBD — every parameter in our file: which source it came from, whether the three agree, and the reason for each `DELTA`. The file already carries this in its header comments; this table is the reviewable form.

| Parameter | Ours | Hardware | BR SITL | SITL_Models | Note |
|---|---|---|---|---|---|
| | | | | | |

### Cross-checks

TBD — where an autopilot parameter is allowed to speak about the model:

- `MOT_THST_ASYM` against the thruster's forward/reverse ratio. The shipped value is 1.6; our limits imply a different ratio, and a persistent disagreement is a finding about the vehicle's calibration rather than a reason to move the thrust numbers.
- `MOT_SLEWRATE` either represented, or shown to be dominated by the thruster's own dynamics.
- `SERVO_RATE` against the simulation rate.

## Thrust

TBD — the M200 with the 112 mm weedless propeller, at the boat's battery voltage, with each number's source named and each placeholder marked as one.

| Quantity | Value | Source |
|---|---|---|
| Forward thrust, per thruster | | published static thrust |
| Reverse thrust, per thruster | | performance chart — PLACEHOLDER until read |
| Deadband | | performance chart — PLACEHOLDER until read |
| Propeller diameter | | product page |

## Hydrodynamics

TBD — the identified coefficients, each with the trial it came from, and what stayed unexplained. Added mass is held at zero; the reason goes here.

| Coefficient | Value | Identified from | Notes |
|---|---|---|---|
| `xU`, `xUabsU` | | | |
| `nR`, `nRabsR` | | | |

The trials are open-loop, with the controller out of the loop, because closed-loop response under a fixed controller cannot separate these from thrust and gains. TBD — the four trials and what each constrains.

## Modes

TBD — per mode: what the RC input commands, what the vehicle is observed to do, and which feedback the loop needs to close. Filled in from what the implementation establishes rather than from ArduPilot's documentation, which is thin for boats.

| Mode | Stick commands | Observed | Feedback required |
|---|---|---|---|
| `MANUAL` | | | |
| `ACRO` | | | |

## Open questions

TBD — anything that could not be resolved from published data: the question, why it matters, and what was assumed in the meantime.
