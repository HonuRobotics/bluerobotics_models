---
orphan: true
---

# SITL spec

Experimenting with spec-driven development.

This spec defines our current SITL integration plan  and is stated so it can be verified.  There is deeper background and context in  [SITL_SPEC_CONTEXT.md](SITL_SPEC_CONTEXT.md)

## How this spec is used

The spec and the source are both editable and a commit may modify either or both.  

Types of PRs: 

* **Spec only.** The plan moves ahead of the source — a request to review the intent before anything is built. 
* **Source only.** If the change is only to source, the spec is still valid and the PR is implementation consistent with the spec.  Makes it easier for humans and agents to review the source if they know the spec.
* **Spec and source together.** The plan and its implementation change at once. This is for what the plan did not anticipate, an unexpected issue or a technical detail too small to be worth a standalone spec revision and review, but significant enough that leaving the spec alone would make it false.

The unit of work and of review is a phase: one phase, one pull request.

Status values: **done** (merged), **in review**, **next**, **later**.

## Phases

| Phase | Deliverable | Repository | Status |
|---|---|---|---|
| 0 | Toolchain and a setup document | `bluerobotics_models`, `drydock` | done — [#43](https://github.com/HonuRobotics/bluerobotics_models/pull/43) |
| 1 | BlueBoat under ArduRover, newtons interface | `bluerobotics_models` | done — [#44](https://github.com/HonuRobotics/bluerobotics_models/pull/44) |
| 2 | Normalized command mode on the thruster | `gz-maritime`, `bluerobotics_models` | done — [gz-maritime#18](https://github.com/HonuRobotics/gz-maritime/pull/18), [#53](https://github.com/HonuRobotics/bluerobotics_models/pull/53) |
| 2.999 | Pin the ArduPilot versions | `bluerobotics_models` | next |
| 3 | BlueROV2 under ArduSub | `bluerobotics_models` | later |
| 4 | Stabilization layer, boat | `bluerobotics_models` | later |
| 5 | Stabilization layer, ROV | `bluerobotics_models` | later |
| 6 | Waypoint mission, boat only | `bluerobotics_models` | later |
| 7 | Waves, boat only | `bluerobotics_models` | later |
| 8 | Documentation and CI | `bluerobotics_models` | later |
| 9 | Upstream the thruster mode | `gz-maritime`, then `gz-sim` | later |

Each phase states an objective and how it is verified met. The objective is the clarification of intent — what this phase is for and what it deliberately leaves to a later one — and the verification is the checks actually run to decide it is done, automated where they can be and by hand where they cannot.

From phase 4 on, each phase states its verification in two parts. **Automated** is what CI and an agent can run unattended: which existing tests become load-bearing for the change, and which new ones the phase writes. **Human** is the instruction to a PR reviewer, and it is usually "follow this page and confirm what it says will happen" — which only works if the page states the development environment, the exact run steps and what a correct result looks like. A phase whose human verification cannot be written as a walkthrough has a documentation gap to close before it is done.

Both vehicles are in scope up to and including phase 5. Phases 0 to 2 were BlueBoat-first because the BlueBoat is the simpler platform and had the published parameter sets to be faithful to; phase 3 brings the BlueROV2 up to the same line, then phase 4 does the stabilization layer for the boat and phase 5 repeats it for the ROV. Phases 6 and 7 are the boat alone, for reasons each states. Where a phase claims both vehicles, a walkthrough that covers only one is an incomplete phase.

### Prerequisites, assumptions and contraints

* Developed and verified inside the drydock container.
* End-to-end walkthroughs are written against running in the drydock environment
* ArduPilot and `ardupilot_gazebo` are built from source into `thirdparty/`, not installed from apt and not resolved by rosdep — neither has a rosdep key.
* Extending CI to install and exercise an autopilot is out of scope, and so are rosdep keys, buildfarm and packaging. These aspects of the project are not ready for packaging and that work contains its own decisions.  

### Phase 0 — Toolchain and a setup document

**Objective:** have `ardupilot_gazebo` and the ArduPilot firmware building and running inside drydock, and a setup document written alongside the work rather than after it. Nothing of ours is involved — this establishes the toolchain and proves the loop closes on a vehicle somebody else wrote.

*Verified by* the procedure in [ArduPilot SITL setup](../getting-started/ardupilot_setup.md)


### Phase 1 — BlueBoat under ArduRover, newtons interface

**Objective:** have the BlueBoat moving under ArduRover, on the newtons interface exactly as it stood, so the plumbing and the channel mapping are proven without waiting on phase 2. `MANUAL` only, so that no low-level stabilization has to be configured to get a result. Includes a documentation walkthrough complete enough that a PR reviewer can exercise the whole path end to end.

*Verified by* the walkthrough in [Verify the SITL connection](../how-to/verify-sitl.md), by hand. `mode manual`, `arm throttle`, then `rc` overrides at the MAVProxy prompt, each with a stated expectation and a stated meaning if it fails:

### Phase 2 — Normalized command mode on the thruster

**Objective:** have one thruster interface that an autopilot and a custom controller reach the same way — a third input mode taking a normalized command in [-1, 1], scaled by the limits the plugin already carries. It lives in `gz-maritime` because a normalized thruster command is vehicle-agnostic capability, not something a vehicle repository should own.

The thruster plugin is forked into a package we own and patched in place: it is a system plugin, so it builds as a standalone shared library against the installed gz-sim headers and is loaded by filename — no Gazebo source build. The schema stays additive, so a model that does not ask for the new mode behaves exactly as before, and the existing `<deadband>` is reused. The topic suffix changes from `/thrust` to `/cmd`, since the units change.

Documentation: both vehicles' actuator pages move to the new topic and units, and the phase 1 walkthrough is re-run and corrected against the new interface rather than left to drift.

*Verified by* a mix, since this phase has something automated to check:

1. `colcon test` on `gz_thruster` — six cases over the scaling: the ends and center, half command on each side of an asymmetric range, out-of-range clamping, NaN, propeller direction, and force mode unchanged.
2. `colcon test` on `blueboat_gazebo`, `bluerov2_gazebo` and `bluerobotics_teleop` — the generated model names the forked plugin, the bridge and mixers speak `/cmd` with a unity envelope, and the launch tests spawn a vehicle, command it and assert it moves.
3. The phase 1 walkthrough re-run by hand, reproducing the same `rc` results on the new mode.
4. `gz topic -e -t /blueboat/motor_port/cmd` while moving the sticks, confirming the `<control>` block emits [-1, 1] and carries no vehicle physics.

### Phase 2.999 — Pin the ArduPilot versions

**Objective:** make the versions we depend on reproducible. Current setup document doesnt name versions of ArduPilot and `ardupilot_gazebo`Raised in review of this spec. A small PR, done before phase 3.

The simplest thing that work: the setup document names the versions and the clone steps check them out. Nothing mechanized, nothing new to maintain for now.

*Verified by* following the setup document from a clean `thirdparty/` and then do both walkthroughs.

### Phase 3 — BlueROV2 under ArduSub

**Objective:** have the BlueROV2 moving under ArduSub, bringing it up to the line the BlueBoat reached in phase 1. It shares the thruster interface from phase 2 and nothing else today — no `ArduPilotPlugin` block, no IMU frame, no parameter set, no SITL world — so this is phase 1 done again for a different vehicle: prove the plumbing and the channel mapping in the simplest mode, and leave fidelity to phase 5.

- ArduSub rather than ArduRover, built the same way and pinned the same way: a release tag paired with the matching published BlueROV2 parameter directory. Our derived file lands at `bluerov2_gazebo/params/bluerov2_sitl.params`, alongside the BlueBoat's.  To be documented alongside blueboat.
- An `ArduPilotPlugin` block on the BlueROV2 model, behind the same `ardupilot` xacro flag, with one `<control>` per thruster — six on the standard vehicle, eight on the heavy.
- An IMU frame on the BlueROV2 chassis, declared the way the BlueBoat's is: a `frames` entry in the part, not a Gazebo-only link.
- A SITL world for the ROV, and the servo-to-thruster mapping stated in the  config rather than assumed.
- `MANUAL` only. ArduSub's stabilized modes close loops around attitude and depth, and those need the actuator work in phase 5 before proceeding. 

Use the ArduSub configuration from BlueRobotics so that Ardu config matches the ROV.  This is also a good check that the way we've modelled the ROV is consistent with the Ardu config - which it should be.  

*To be verified by* a walkthrough written alongside the work, in the shape of [Verify the SITL connection](../how-to/verify-sitl.md) but per axis: in `MANUAL`, arm, then command surge, sway, heave and yaw one at a time and confirm each produces that motion and no other. A cross-coupled response means the allocation is wrong; a reversed one means a thruster or a channel is. Magnitudes are not trusted yet, exactly as in phase 1.



### Phase 4 — Stabilization layer, boat

**Objective:** demonstrate the BlueBoat's inner loops (yaw rate and surge ) behaving under Blue Robotics' published gains the way the hardware boat does, by engineering judgement.  Requires the vehicle configuration to match the hardware and the hydrodynamics to be identified, which is most of the work.

The boat is first b/c it is simpler

Mode: ArduRover's `ACRO`, where the throttle stick commands a speed and the steering stick commands a turn rate, so both inner loops are exercised directly. No waypoints, no navigation.

`STEERING` mode is out of scope.  It is not needed at this point to be able to move onto waypoint guidance.   This is not on the critical path, so trying to keep scope from ballooning.  

Use Blue Robotics  performance data to set the  `max_thrust_cmd`, `min_thrust_cmd` and `<deadband>` parameters at the boat's battery voltage.  
- the BlueBoat runs M200 motors with the 112 mm weedless propeller, 
- the BlueROV2 runs T200s with a 76 mm propeller, 
both on a 14.8 V nominal pack.

Note: Our part library does not yet reflect that: the M200 propeller parts carry T200 endpoints as placeholders and say so in their own headers. Correcting them is part of this phase. The general lesson is the one the provenance page exists for — a number present in the model is not evidence of anything until something records where it came from.

**The parameter provenance.** Three descriptions of a configured BlueBoat exist and they disagree: 

1. Blue Robotics' dump off the hardware, 
2. their own SITL parameter set, and
3. the block contributed to `SITL_Models`. 

The differences specify which channel carries which throttle, whether a thruster is reversed, the servo range, the neutral trim, the cruise speed, etc. . This phase audits our derived file against the published ones line by line, decides which source is authoritative for what, and justifies every remaining delta in the file itself rather than silently.

Divergences found in the audit are recorded here rather than raised with Blue Robotics or ArduPilot; this plan is about being faithful to what they ship, not about changing it.

Then the cross-checks, which are where an autopilot parameter is allowed to speak: the forward/reverse ratio against `MOT_THST_ASYM`, which the shipped BlueBoat parameters set to 1.6; `MOT_SLEWRATE` 200 %/s either represented or shown to be dominated by the thruster's own dynamics; `SERVO_RATE` 50 Hz against `SIM_RATE_HZ`. A persistent disagreement on `MOT_THST_ASYM` is a finding about the vehicle's calibration, not a reason to move the thrust numbers.

**The stabilization loops.** ArduRover's `ATC_STR_RAT_*` steering-rate PID and `ATC_SPEED_*` speed PID, with `CRUISE_SPEED` and `CRUISE_THROTTLE` as the feedforward. Blue Robotics publish gains for all of them, and the target is that those gains work unmodified.

`ATC_STR_ANG_P`, the outer heading controller, is deliberately not exercised here: `ACRO` does not reach it. It wraps the same rate loop and is validated in phase 6, where the boat actually uses it.

This inverts the usual direction for parameter selection. Normally the controller is tuned to the plant. Here the controller is the artifact we are trying to be faithful to, so its gains are held at the published values and the vehicle dynamics are what moves — the hydrodynamic damping and added-mass coefficients, which today are placeholders with no measurement behind them.

That inversion runs close to the hazard this whole document is written against, and the line has to be drawn explicitly. Thruster limits and deadband come from measurement, so they are fixed and unavailable for fitting. The hydrodynamic coefficients have never been measured, so choosing them to reproduce observed vehicle behavior is identification rather than tuning-to-succeed. It stops being identification the moment a measured value is moved to make a loop behave.

The reason this needs a procedure rather than good intentions is the "colinearity of the regressors" (a phrase I love ;). Closed-loop response under a fixed controller is a weak observation: many combinations of added mass, linear damping, quadratic damping, thrust limits and gains produce nearly the same response, so the parameters are not separately identifiable from closed-loop runs. The procedure that follows from that:

1. Fix everything measurable elsewhere — mass and inertia from the model, thrust and deadband from the data above. These are not free.
2. Identify the remaining hydrodynamic coefficients from **open-loop** trials, with the controller out of the loop: acceleration from rest at a fixed command, coast-down from steady speed, steady-state speed against command, turning circle at fixed differential. Each excites damping directly rather than through a controller.
3. Use the closed-loop stabilization runs as validation only, never as the fit.
4. Report what was fit, from which trial, and what stayed unexplained.

Choosing the coefficients is a judgement call. An automated fit against a colinear set will find numbers that satisfy the trial and are physically odd, so the tooling runs the trials and reports the numbers while a developer picks the values.

Acceptance here is engineering judgement rather than a threshold, and the judgement should be made against named quantities — time to speed, overshoot, settling time, steady-state error, achieved turn rate — rather than against an impression of the response.  As we get into this and I see what examples are out there, I'll try to write these into automated tests that we can run.

Note that this will also indiretly test that we have the boat's sensors provisioned correctly and consistent with the hardware because in order for the feedback to work, the sensing feedback will need to be correct.  

Documentation: a page recording where the parameter file came from, which values are the shipped ones, and which are deltas with the reason for each — enough that a reviewer can confirm we are running Blue Robotics' configuration rather than one tuned until the boat behaved. The file already carries this in its header and its `DELTA` comments; this phase makes it a reviewable document.

The same page carries a mode table: per mode, what the rc commands, what the vehicle is observed to do, and which feedback the loop needs to close. ArduPilot's own documentation for boats and submarines is thin and in places misleading, so the table is filled in from what the implementation actually establishes and then used for verification. To keep the spec somewhat lightweight, leave this TBD for the docs and to be verfied during review. 

#### Automated verification

Existing tests that become pertinent: `test_gz_launch.py` already derives its commands from `MAX_THRUST` / `MIN_THRUST` module constants, so changing the limits changes what it commands. Its distance and speed thresholds are tuned to today's numbers and will need re-tuning — treat that re-tuning as the signal it is, not as a chore. `test_model_generation.py` asserts the limits reach the generated SDF.

New tests this phase writes:

- The parameter file's `SERVOn_FUNCTION` values agree with the composition's channel order. These live in different files with different provenance and nothing checks them today; when they drift the vehicle still runs, it just steers the wrong way.
- Every value in a `*_sitl.params` file either matches the published source or carries a `DELTA` comment. This is the audit made executable, so it cannot rot.  Pin this to released params where possible. 
- The open-loop identification trials as headless runs — acceleration, coast-down, steady-state speed, turning circle — each producing a number and asserting it against the identified coefficients. These are the regression guard for the hydrodynamics: they fail if someone later moves a coefficient without redoing the identification.  We'll need to use engineering judgement to set up these ranges.

Whether the closed-loop checks below can be automated at all is decided during the phase. It needs a MAVLink client the workspace does not declare today and a tolerance nobody can yet defend, so the criteria are written down first and automated only if that turns out to be cheap.

#### Human verification

The reviewer runs the step responses from the walkthrough: command a speed, let it settle, and compare steady state against the command, then command a turn rate and check the same. The check is that the shipped gains — `ATC_STR_RAT_*` and `ATC_SPEED_*` — work unmodified. If the boat needs retuning, the actuator model or the hydrodynamics is wrong, not the gains.

The judgement call is whether the responses look like the real vessel: time to speed, overshoot, settling, steady-state error. The page has to put the expected figures in front of the reviewer rather than leaving it to memory.  I'll try to write as many automatable test conditiosn here as we can, but that may be harder than the engineering judgement - and not worth the extra effort.  

The page must state that this runs in drydock, give the shell-by-shell commands, and say what the observation looks like when it is right. The tolerance is an open question below, so will need to develop description of what should be expected and what indicates a problem.

### Phase 5 — Stabilization layer, ROV

**Objective:** the same exercise as phase 4, for the BlueROV2 under ArduSub, carrying whatever the boat taught. Held separate because the vehicle has more degrees of freedom, a different autopilot and a different set of loops, and because doing the simpler one first is how the pattern gets settled.

Modes: ArduSub's `STABILIZE` and `ALT_HOLD`. What they close is attitude and depth — forward and lateral remain direct motor demands, so the ROV's objective is heading and depth holding rather than a commanded speed. There is no surge-speed loop to exercise.

The work follows phase 4's shape: thrust limits from Blue Robotics' T200 data at the vehicle's own voltage, an audit of the derived parameter file against the published chain, hydrodynamic identification by the same open-loop-then-validate procedure, and a provenance page. Two things differ and are worth stating in advance.

First, the ROV's published bollard figures are a cross-check the boat has no equivalent of: Blue Robotics quote thrust for the assembled vehicle as well as for the thruster on a bench, and the two do not have to agree. Which one the model should carry is a decision for this phase rather than an assumption.

Second, the standard six-thruster vehicle has less authority than the mode names suggest. The `Vectored` frame mixes no pitch at all, and Blue Robotics ship a roll gain of zero, so `STABILIZE` on that vehicle meaningfully closes yaw. The phase should say what it is actually holding rather than what the mode is called.

#### Automated verification

The parameter audit and the identification trials from phase 4, pointed at the ROV. The launch tests in `bluerov2_gazebo` become pertinent for the same reason the boat's do: they derive their commands from the thrust constants.

#### Human verification

The reviewer holds depth and heading in a stabilized mode and confirms the shipped ArduSub gains work unmodified, judged against the same kind of named quantities as the boat's — settling, overshoot, steady-state error. Same rule: if it needs retuning, the actuator model or the hydrodynamics is wrong, not the gains.

### Phase 6 — Waypoint mission, boat only

**Objective:** demonstrate one standard waypoint mission on the BlueBoat, flown unattended in `AUTO` with the failsafes in the loop. This is the autopilot layer above the phase 4 stabilization layer.  It is also the broader test of the transfer claim, because the parameters governing it were tuned on the water.

The inner loops are inherited unchanged: the waypoint controller produces a turn rate and a speed, and those go to the same `ATC_STR_RAT_*` and `ATC_SPEED_*` controllers phase 4 validated. One loop is new — `ATC_STR_ANG_P`, the heading controller, which a boat reaches on arriving at a waypoint and on pivot turns between legs. That is the only control gain this phase puts under test for the first time, and it is worth naming so it does not arrive as a surprise.

- One mission, held in the repository rather than typed in per run: a lawnmower survey pattern, in `blueboat_gazebo/missions/` and installed with the package, in the QGC WPL format both MAVProxy's `wp load` and QGroundControl read.
- `WP_SPEED`, `WP_RADIUS` and `TURN_RADIUS` from the factory parameters.

One mission, not a family of them. It is a fixed artifact so that the automated run, the walkthrough and any later regression all exercise the same waypoints — a mission that changes between runs is not a regression test. Anything beyond it is more mission rather than more evidence.

**The BlueROV2 is not in this phase.** Geodetic waypoint navigation asks for something the vehicle does not have: underwater there is no GNSS, so a position fix has to come from DVL dead reckoning or an acoustic system, and the BlueROV2 as configured is not set up for that. It is not where ArduSub is strongest either, and it is not what the VRX application needs. The ROV's closed-loop behavior is fully exercised one layer down, in phase 5.

If a guidance result disappoints, the first question is whether phase 4 is actually finished. Splitting the phases exists to make that question answerable: with the inner loops validated and the hydrodynamics identified separately, a bad track points at the navigation parameters rather than at everything at once.

Other closed-loop behaviors are out of scope, as listed below — `GUIDED`, `LOITER`, `HOLD` and station keeping, follow and line- or path-following modes. They are more capability on the same loops rather than a different thing to prove.

#### Automated verification

New: a headless run of the repository's mission file — upload it over MAVLink, fly it, and assert each waypoint is reached within a radius and the mission completes. Failsafes scripted the same way: trigger GCS loss, low battery and a failing arming check, and assert the response rather than the parameter.

The test loads the same file the walkthrough tells a reviewer to load. This is the one place where the automated check and the human one are the same procedure, only unattended — which is the argument for the mission being a versioned artifact rather than a set of instructions.

#### Human verification

The reviewer loads the mission file from the installed package, then watches it run on the MAVProxy map or in QGroundControl, touching nothing. Checked against `CRUISE_SPEED` 1 m/s and `TURN_RADIUS` 0.1 m. Cross-track error and achieved turn radius are the quantities to judge against, and the page states the expected figures beforehand.

Then each failsafe triggered deliberately, with the expected response stated in the page before the reviewer triggers it.

### Phase 7 — Waves, boat only

**Objective:** This is a regression test and demonstration for marketing and raising awareness.   We'll repeat the tests of phases 4 and 6 within an active wavefield. Previous tests did not exercise the added wave enfironment effects.   In theory this should work out of the box, but important to test end-to-end to identify regressions.  This is only pertinent to the Boat.  Testing the ROV in near surface waves is out of scope.

Since this is a regression check rather than new capability, the work is mostly in the world and the run rather than in the vehicle: a wave world for the BlueBoat, and the phase 4 and 6 checks pointed at it. If something has to change in the boat to survive a sea state, then we fix.

#### Automated verification

Existing: `gz_waves` carries its own suite in `gz-maritime`, and `blueboat_gazebo`'s launch tests must keep passing once a wave world is an option rather than always flat water.

New: phase 6's headless mission run, repeated in a wave world, asserting the same waypoints are reached and the mission completes — with widened bounds, stated and justified, rather than the flat-water ones. Plus a station-hold run asserting the pose stays bounded and the EKF's innovations stay inside a threshold, which is the check worth most here: the failure mode is slow divergence that a human watching for two minutes will not see.

#### Human verification

The reviewer runs both wave providers, Gerstner and FFT, and watches the boat in the viewport — the buoyancy lag between the two is a visual finding before it is a numerical one, and it is the known issue this phase is most likely to surface.

Then phase 4's step responses and phase 6's survey mission re-run in a stated sea state, confirming the boat still completes them and degrades gracefully rather than diverging. The sea state and the widened bounds are numbers to pick before the run and write into the page, so the reviewer is checking a claim rather than forming an impression.

This phase also produces the material worth showing: a wave-field run is the demonstration, so capturing video or stills while the reviewer is there costs nothing extra.

### Phase 8 — Documentation and Announce

**Objective:** The user-facing documention should be in the form of walkthroughs that simultaneously serve two purposes: 

1. to demonstrate to a user the capability 
2. to support development as end-to-end testing of the new feature while the feature is being developed and as a regression test for later. 

This documentation will have been built incrementally in the previous phases.  This phase is simply to clean that up that documenation for consistency and make a public announcement about the features of this spec. 


Packaging and binary distribution are deliberately not here. Everything in this plan is source-built in the drydock container, and ArduPilot in particular is cloned into `thirdparty/` rather than installed, because it has no rosdep key and is pinned by hand. Deciding where these packages are meant to land is its own effort with its own owner, and putting it on this plan's critical path would couple a simulation milestone to a distribution decision. The one thing this plan owes that effort is a flag: `thruster.repos` pins an unreleased sibling package, which is exactly the kind of thing packaging trips over, and it goes away when the thruster mode reaches gz-sim upstream in phase 9.

CI is left out of the plan and discussion on CI in Issue #66 so we are tracking.



#### Automated verification

Existing: the `docs / docs` job already builds the site with warnings as errors, so a broken cross-reference fails the PR. The full `colcon test` across the workspace is the other half.

New: a link check over the documentation, and whatever headless subset of the SITL path the phase concludes is worth running in CI — that conclusion is itself a deliverable, including "none of it, and here is why".

#### Human verification

The reviewer starts from a clean workspace and follows the documentation end to end, reaching both a driving boat and a diving ROV without asking anyone a question. Every place they have to guess, ask, or read source is a defect to file against this phase.

### Phase 9 — Upstream the thruster mode

**Objective:** have the normalized mode in Gazebo itself and the fork gone. It is a liability while it lasts — a divergence from a `Thruster` that is not frozen, plus a `.repos` pin and a plugin name that exist only because the mode is not upstream yet. The delta is kept tiny so the eventual pull request stays readable.

Timing matters: prepare it for `gz-sim` only once the mode has stopped changing. Then, once it is released in Gazebo, delete the local implementation along with the `.repos` pin that fetches it and the models' reference to the forked plugin name.

#### Automated verification

The `gz_thruster` tests go upstream with the plugin. Locally, the whole workspace suite must pass with `gz_thruster` deleted and the models naming `gz-sim-thruster-system` — that is the check that the fork left nothing behind.

#### Human verification

The reviewer re-runs the phase 2 walkthrough on the stock plugin and gets the same results, and confirms nothing in the workspace still pins a branch or names the forked library.

## What the phases are protecting

Phases 4 to 6 are the real test of the sim2real transfer claim — first that the inner loops track under the published gains, boat then ROV, then that waypoint guidance flies a mission on top of them on the boat — and the hazard they guard against is a simulation that cannot fail. Every number here can be adjusted until the boat behaves, and a model tuned to agree with the autopilot it is meant to test proves nothing. Any moment where an autopilot parameter is used to justify a physics value is that failure happening.

"Close, with these caveats" is an acceptable and publishable answer, provided it is stated as a result rather than discovered as a disappointment.

## Out of scope

Stated so they are not quietly re-entered: PWM as the plugin's interface; thrust curves, rotor dynamics or advance-ratio work; arbitration between competing commanders; hardware in the loop; forking the firmware; pull requests to `SITL_Models`; building Gazebo from source; any change to `gz_waves` or `ehukai`.

Closed-loop behaviors beyond the phases above are out of scope: `GUIDED`, `LOITER`, `HOLD` and station keeping, follow modes, and line- or path-following. Each is more capability riding on the same stabilization and guidance loops rather than a different thing to prove, so exercising them adds review burden without adding evidence. They become interesting once the transfer claim is settled.

Waypoint missions for the BlueROV2 are out of scope, for the reason phase 6 gives: geodetic navigation underwater needs a position source the vehicle is not configured for, and the ROV's closed-loop behavior is fully exercised one layer down in phase 5.

The BlueROV2 in waves is out of scope. Near-surface wave interaction for a submerged vehicle is its own modeling problem, and phase 7 is a regression check on the boat rather than new capability for either vehicle.

The Holybro X500 and any other UAV is out of scope for this plan. It is a different vehicle class with a different autopilot binding, it lives in `holybro_models` rather than here, and nothing in these phases is blocked on it. Rebinding it from PX4 is its own effort with its own plan.

PX4 is community supported and deliberately not designed out. The normalized command is what a PX4 actuator output produces too, so the interface fits; we keep the design open to it and do not test it.

Packaging: this set of features all too new and too unstable to dedicated cycles to packaging (and debugging packaging) at this point. Also, It is not overt in our SOW that we have to do anything specific. Since we are over budget and behind schedule, it seems like being conservative with scope is the way.

## Open questions

- What we compare the closed-loop behavior in phases 4 to 6 *against*. "Similar to the hardware vessel" needs a source: logs from a real BlueBoat or BlueROV2, or published performance figures. Without one, the judgement has nothing to be a judgement about, and this is the dependency most likely to block that phase.

Leaving that open is the point rather than a gap. A waterfall spec would pick a source and a tolerance now, on no evidence, and the phase would then be measured against a guess. Flagging it here says we know the issue is there; the decision gets made from what the implementation turns up, recorded in the source and its documentation, and folded back into this spec only if it changes the intent.
