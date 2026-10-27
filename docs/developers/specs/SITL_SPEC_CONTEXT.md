# SITL integration for the BlueBoat: a roadmap

Proposed 2026-08-28, for comment before any of it is built.  

Start with BlueBoat, then move on to BlueROV and Holybro UAV

## What we are trying to do



The goal is to give the simulated vehicle the same autopilot the real one has, running in SITL.

The test of success is sim2real transfer: take a parameter set off a boat in the field, load it into the simulation unchanged, and get pretty much the same closed-loop behavior. Not the same trajectory — the same response. (Actually testing this may be beyond the scope of this project, but that is what we are working toward.)

A second requirement runs alongside. The autopilot is one way to drive the vehicle, not the only one.  The interface also supports users who wantsto write their own low-level controller — a ROS 2 node, a custome controller — must be able to command the same thrusters through the same interface.

## Background: what SITL actually is

For reviewers who have not worked with it. SITL is the real ArduPilot flight code compiled natively for x86 — the actual EKF, mode logic, PID loops, parameter system and failsafes, not a model of them. Only the bottom layer differs: where hardware reads an IMU over SPI and drives PWM on a timer, SITL reads sensor values from a socket and writes servo outputs to a socket. Everything above that layer cannot tell the difference, which is why a mission that works in SITL usually works on the water.

Running it means three processes, started together by ArduPilot's `sim_vehicle.py`:

```
  ┌──────────────┐   JSON / UDP 9002    ┌──────────────┐
  │  the backend │ ◄──────────────────► │   firmware   │
  │  (gz sim)    │   PWM out, state in  │ (ardurover)  │
  └──────────────┘                      └──────┬───────┘
                                               │ MAVLink / TCP 5760
                                        ┌──────▼───────┐
                                        │   MAVProxy   │
                                        │    (GCS)     │
                                        └──────────────┘
```

The firmware is `ardurover`. Two ground stations are worth showing, and the documentation should use both. `sim_vehicle.py` starts MAVProxy of its own accord — a command-line console and map, which is convenient for scripted work and makes for terse, copyable examples in a document. It also rebroadcasts on UDP 14550, so QGroundControl attaches alongside it exactly as it would to a real vehicle over a telemetry radio. QGC is what Blue Robotics use and what a BlueBoat operator already has in front of them, so occasional QGC examples are what connect the simulation back to the boat.

The backend is everything the firmware would otherwise sense and push against: water, hull, thrusters, GPS, gravity. Gazebo plays that part, through [ArduPilot/ardupilot_gazebo](https://github.com/ArduPilot/ardupilot_gazebo), a Gazebo system plugin that speaks ArduPilot's JSON protocol on one side and drives model joints and sensors on the other.


## The interface question

A normalized thrust command is the correct nexus at which to separate the controller (autopilot or custom) from the robot (embodied or simulated). Above that boundary sits the decision of how hard to push (manual, scripted or automated). Below it sits everything that turns a command into force: the ESC, the motor and the propeller.

Exposing this interface will require (a small) modification of the upstream Thruster plugin for gz sim.  

### Where we are

From `blueboat_gazebo/model.sdf.xacro`, one of these per propeller:

```xml
<plugin filename="gz-sim-thruster-system" name="gz::sim::systems::Thruster">
  <joint_name>${name}_joint</joint_name>
  <namespace></namespace>
  <topic>${topic_base}/thrust</topic>        <!-- /blueboat/motor_port/thrust -->
  <thrust_coefficient>±0.02</thrust_coefficient>
  <propeller_diameter>0.076</propeller_diameter>
  <velocity_control>true</velocity_control>
  <max_thrust_cmd>51.5</max_thrust_cmd>      <!-- T200 at 16 V, forward -->
  <min_thrust_cmd>-40.2</min_thrust_cmd>     <!-- T200 at 16 V, reverse -->
</plugin>
```

The command is thrust in newtons — `gz.msgs.Double` on gz transport, bridged to ROS 2 as `std_msgs/msg/Float64`. Any commander therefore has to carry an ESC and propeller model of its own, and a parameter set tuned on the water has nothing to transfer into.

Per [`Thruster.hh`](https://github.com/gazebosim/gz-sim/blob/main/src/systems/thruster/Thruster.hh), the stock plugin has exactly two input modes: force in newtons by default, or angular velocity in rad/s with `<use_angvel_cmd>`. Neither is what a flight controller, a ROS controller or a custom controller produces.

### Where we want to be

```
  ArduRover SITL ──► ArduPilotPlugin ─┐   normalized command [-1, 1]
                     (PWM µs → cmd)   │
                                      ├──► Thruster plugin ──► scale + deadband ──► force
  Custom controller ──────────────────┘
       (bridge, Float64 → Double)
```

One thruster model, several commanders, identical units and topics. The thrust limits, the deadband and the forward/reverse asymmetry live inside the thruster plugin, where the physical ESC and propeller keep them. The ArduPilot `<control>` block reduces to arithmetic — `servo_min` 1100, `servo_max` 1900, `offset` -0.5, `multiplier` 2 gives exactly [-1, 1] — carrying no vehicle-specific quantity at all.

(Why normalized and not PWM, which is what actually crosses the wire on the boat: PWM is a property of the link between an autopilot and an ESC, not a property of a thruster. A CAN or DShot thruster has no PWM, and neither does a vehicle whose low-level controller is not an RC autopilot. Microseconds in the plugin would make it unupstreamable and would oblige a custom ROS controller to know that 1500 means stop. Note that ±1 means full command in that direction, not equal thrust: +1 is 51.5 N and -1 is -40.2 N, which is the asymmetry ArduPilot's `MOT_THST_ASYM` exists to describe.)

### The change to the thruster plugin

Small, and deliberately so. A third input mode taking a command in [-1, 1], scaled by the `max_thrust_cmd` and `min_thrust_cmd` that already exist and clipped by the `<deadband>` that already exists. A positive command scales by `max_thrust_cmd`, a negative one by the magnitude of `min_thrust_cmd`. Everything downstream is untouched, the asymmetry needs no new parameter, and the existing newtons and angular-velocity modes keep working unchanged.

This is an interface, not a new physics model — the same mapping the plugin already performs, reached through a different interface. The deliberate simplification is that thrust stays linear in command within each direction, where a real ESC and propeller are not; that is exactly the fidelity we have today, so the new mode loses nothing.

Prior art supports the shape. Stonefish declares `normalized_setpoint` and VRX Classic used `maxCmd` 1.0 — two projects arriving independently at the same convention, and essentially the only two.

Most simulators do what gz-sim does. HoloOcean's native control schemes take force directly: `AUV_THRUSTERS` is an "8-vector of forces for each thruster", `SV_THRUSTERS` a "2-vector of forces for left and right thruster", both in newtons. Its propeller modeling lives in a separate optional `fossen_dynamics` layer wrapping Fossen's Python Vehicle Simulator, and that works from propeller rpm rather than from a normalized command — a Wageningen B-series `KT`/`KQ` pair varying with advance ratio plus a first-order rotor lag for the REMUS-like thruster, and a simpler forward/reverse bollard quadratic for the Otter USV. OceanSim has no actuator model at all; it is an Isaac Sim perception simulator, and its one control example applies force and torque through the PhysX API straight from the keyboard.

The Yoerger and Bessa thruster-dynamics models are real and worth knowing about, but they live in Stonefish (`<rotor_dynamics type="yoerger">`, `type="bessa"`) and in `uuv_simulator`, not in HoloOcean. They sit on the far side of a command-to-rpm stage that this proposal explicitly does not build.


## What the firmware side commits us to

The firmware is stock ArduRover from the ArduPilot project, unmodified, at the version Blue Robotics ships. We do not fork it, we do not add a simulation-only backend to it, and we do not tune the boat by editing firmware defaults.

"Stock" does not mean "latest", and this is not a promise to track ArduRover. It is pinned as a pair: a specific ArduPilot release tag, and the matching parameter directory in [bluerobotics/Blueos-Parameter-Repository](https://github.com/bluerobotics/Blueos-Parameter-Repository). Both halves are already discrete and versioned — the parameter repo is organized by ArduRover minor version, and BlueOS ships a specific firmware build rather than whatever is on master. Moving the pin is a deliberate task with its own re-validation, not something that happens by rebuilding.

Two files from that repository matter, and both are Blue Robotics' own:

- `params/ardupilot/ArduRover/4.7/Navigator/BlueBoat120.params` — the BlueBoat's configuration for the Navigator flight controller. 951 lines, headed `Vehicle: Surface Boat / Platform: navigator`. This is the real vehicle, and it is what we are trying to be faithful to.
- `params/ardupilot/ArduRover/4.6/sitl/MotorBoat.params` — Blue Robotics' own parameter set for running ArduRover SITL with no hardware attached. Interesting because it is the same delta we are about to derive: it shows which parameters they consider necessary to change when a boat becomes a simulation. How it differs from the hardware set, and from what is in `SITL_Models`, is assessed in phase 1; see below.

## PX4: community supported, and not designed out

This document is ArduPilot-shaped, and that is deliberate rather than accidental. It is worth stating the position explicitly so users know what to expect.

**ArduPilot is the supported integration.** Both vehicles ship with it — the BlueBoat runs ArduRover on a Navigator, the BlueROV2 runs ArduSub — and Blue Robotics publish working parameter sets for both. That gives us something to be faithful to and something to check against. A PX4 airframe configuration would have to be invented, with no hardware to validate it and no published reference to disagree with, and it would carry ongoing test and maintenance cost against a user base that overwhelmingly runs ArduPilot on these two vehicles.

**PX4 is community supported.** We will not write airframe configurations, ship parameter sets, run it in CI, or debug its behavior. What we will do is avoid designing it out, and the distinction is worth being concrete about because it is cheap to honor and expensive to recover.

### Why the architecture already accommodates it

The URDF-first assembly does most of the work here. The vehicle description — links, joints, inertia, sensor frames — is autopilot-agnostic and is exactly what PX4 would need. Nothing about ArduPilot reaches into it. The Gazebo composition then adds plugins on top, and an autopilot integration is a set of plugins: for ArduPilot, `ArduPilotPlugin` plus per-thruster command topics. A PX4 flavor is another composition variant over the same URDF, which is the same mechanism phase 2 introduces rather than a new one. If the `ardupilot` flag ever needs to become an `autopilot` selector, that is a rename and a second branch, not a redesign.

### What PX4 actually expects, and why our interface fits

Worth checking rather than assuming, so: PX4's own BlueROV2 Heavy model in [PX4-gazebo-models](https://github.com/PX4/PX4-gazebo-models) drives each thruster through `GenericMotorModel` configured like this:

```xml
<motorType>force_polynomial</motorType>
<controlMethod>duty_cycle</controlMethod>
<minDutyCycle>1100</minDutyCycle>
<maxDutyCycle>1900</maxDutyCycle>
<bidirectionalMotor>1</bidirectionalMotor>
<positiveThrustPolynomial>[0.0, 2.379, 149.2, -327.4, 436.6, -194.4]</positiveThrustPolynomial>
<negativeThrustPolynomial>[0.0, 0.343, 134.4, -284.6, 351.7, -152.2]</negativeThrustPolynomial>
```

Three things follow, and all of them support the direction this document already argues for.

PX4 commands thrusters by **duty cycle over the same 1100–1900 band** the BlueBoat's shipped parameters use. It has never fed newtons to a thruster. So a normalized command is not merely compatible with PX4 — it is closer to what PX4 already does than the newtons interface we have today. The nexus argued for in the interface section is the one both autopilots meet at.

PX4 models **forward and reverse separately**, with two fitted polynomials. That is independent confirmation that the thruster asymmetry discussed above is real and that a symmetric mapping is the odd one out.

The difference that does exist is message shape rather than semantics: PX4 publishes one aggregated `gz.msgs.Actuators` on `command/motor_speed` indexed by motor number, where the ArduPilot plugin publishes one `gz.msgs.Double` per thruster topic. That is a property of the autopilot's own plugin, not of the thruster, and it is the plugin a PX4 variant would swap in.

### What this commits us to

Three things, none of them costly:

1. The URDF stays autopilot-agnostic. Nothing ArduPilot-specific goes into a part, a slot or a frame.
2. The thruster's command interface stays a normalized number, not PWM microseconds and not `SERVOn` semantics. We had already decided this for upstreaming reasons; PX4 is a second reason.
3. A PX4 composition variant contributed by someone else is welcome, and would be reviewed for whether it breaks the ArduPilot path — not for whether PX4 flies correctly, which we are not in a position to judge.

It is worth adding that the phase 2 change benefits PX4 too. A normalized command mode in gz-sim's own `Thruster` is useful to anyone driving a marine vehicle, and PX4 currently carries `GenericMotorModel` as its own plugin partly because the stock one cannot express this. That widens the upstreaming argument beyond our own convenience.

## A note on ArduPilot/SITL_Models

[ArduPilot/SITL_Models](https://github.com/ArduPilot/SITL_Models) contains a Gazebo BlueBoat, and reviewers will reasonably ask why we are not simply using it.

The meshes are the main reason. They are derived directly from Blue Robotics CAD — the visual assembly is roughly 285,000 triangles — which is heavy enough to slow real-time simulation in both physics and rendering. Our models are not only for simulation: the same geometry has to serve visualization in RViz, and it has to stay portable to simulators other than Gazebo rather than being tied to a SITL setup. That argues for artist-made low-poly visual meshes with simple primitive collision shapes, which is the approach this repository already takes, and it is not a change we could reasonably make to someone else's model.

It remains a good worked example. Its `ArduPilotPlugin` block shows the wiring — channel numbering, `type COMMAND`, `cmd_topic`, the two frame transforms — more clearly than any documentation does, and we will read it for that, alongside `orca4` and `bluerov2_gz`.

We are not proposing to vendor that repository or to send changes to it. It is ArduPilot's asset collection for demonstrating their own plugin across many vehicles, and a contribution from us would ask them to maintain a model they have no way to validate.

## Three parameter sets, and reconciling them later

There are three descriptions of how a BlueBoat should be configured, and they do not agree:

1. What Blue Robotics run on the hardware — `Navigator/BlueBoat120.params`.
2. What Blue Robotics run in SITL — `sitl/MotorBoat.params`.
3. What has been contributed to `SITL_Models` — the `ArduPilotPlugin` block in `blueboat/model.sdf`.

The differences are not cosmetic. They include which output channel carries which throttle, whether a thruster is reversed, the servo range, the neutral trim, and the cruise speed and throttle. A model built by copying any one of them without knowing about the other two will behave in ways that take a while to explain.

Working out the interplay — which is authoritative for what, whether the divergences are deliberate or drift, and whether anything should be raised with Blue Robotics or with ArduPilot — is real work and it matters. It is not work that should hold up a roadmap. This document proposes doing that assessment as a task inside phase 1, where the parameter sets are being loaded anyway, and writing up the result rather than folding it silently into our own file.

## Phases

Each phase is one pull request. Two of them belong to other repositories

| Phase | Deliverable | Repository |
|---|---|---|
| 0 | Toolchain and a setup document | `bluerobotics_models` (doc), `drydock` (packages) |
| 1 | BlueBoat under ArduRover, newtons interface | `bluerobotics_models` |
| 2 | Normalized command mode on the thruster | `gz-maritime` |
| 3 | Actuator fidelity | `bluerobotics_models` |
| 4 | Waves | `bluerobotics_models` |
| 5 | Missions | `bluerobotics_models` |
| 6 | Packaging, documentation, upstreaming | `bluerobotics_models`, then `gz-sim` |

### Phase 0 — Toolchain

Get `ardupilot_gazebo` and the ArduPilot firmware building and running inside drydock, and prove the loop closes on a vehicle we did not write.

- Clone `ardupilot` and `ardupilot_gazebo` into a new `thirdparty/` directory in the workspace.
- Build the plugin against Gazebo Jetty. This is the single largest unknown in the plan: the plugin claims Jetty support, but nobody here has compiled it.
- Add whatever the build needs to drydock's `apt-packages.txt`.
- Build `ardurover` with waf; confirm `sim_vehicle.py` runs.
- Write it up as a setup document while doing it, not afterwards.

Exit criterion: the stock Iris example arms, takes off and lands under MAVProxy, inside drydock. No boat involved.

### Phase 1 — First flotation and MANUAL

Get the BlueBoat model moving under ArduRover, using the newtons interface exactly as it exists today. No plugin work — this phase proves the plumbing and the channel mapping, and deliberately does not wait on phase 2.

- Add an ArduPilot wrapper model alongside the existing one (see Layout, below).
- Wire two `<control>` channels to the existing thruster topics: `type COMMAND` with `<cmd_topic>` set to `/blueboat/motor_port/thrust` and `/blueboat/motor_stbd/thrust`, using the factory defaults' servo functions and ranges.
- Load `BlueBoat120.params` into SITL, and read `sitl/MotorBoat.params` alongside it. Record the delta we end up needing, and how it compares to theirs.
- Assess the three parameter sets against each other and write up what differs and why, as a document rather than as a silent choice, with a recommendation on whether anything should be raised with Blue Robotics or ArduPilot.
- Flat water, no waves.

Exit criterion: `MANUAL` mode, arm, throttle forward, the boat moves forward; steer right, it turns right. Signs and channel mapping correct, magnitudes not yet trusted.

### Phase 2 — A normalized command interface on the thruster

This one belongs in `gz-maritime`, which is intended as a sandbox for features headed to Gazebo. A normalized thruster command is vehicle-agnostic — it is the ordinary interface across UUV and USV work — so it does not belong in a vehicle repository.

- Fork `gz-sim-thruster-system` into a package we own. It is a system plugin, so it builds as a standalone shared library against the installed gz-sim development headers and is loaded by filename: no Gazebo source build, no change to the installed Gazebo.
- Add the mode alongside the existing two.
- Reuse `<deadband>` as it stands rather than reinventing it.
- Keep the SDF schema additive, so a model that does not ask for the new mode behaves exactly as before.
- Rename the topic: `${topic_base}/thrust` becomes `${topic_base}/cmd`, since the units change and the old name would be a lie. The generated `ros_gz_bridge.yaml` follows from `configure_vehicle.py`, so this is one edit rather than a migration.

Exit criterion: the BlueBoat runs end to end on the new mode, with the ArduPilot `<control>` block reduced to a pure PWM-to-normalized mapping carrying no vehicle physics, and phase 1 behavior reproduced.

### Phase 3 — Actuator fidelity

Make the thrust the firmware asks for equal the thrust the water sees.

- Check `max_thrust_cmd` 51.5 and `min_thrust_cmd` -40.2 against Blue Robotics' published T200 data at the boat's actual battery voltage. These are the numbers ±1 maps to, so they are now the whole actuator calibration.
- Set the autopilot-side calibration from the factory defaults: the 1100–1900 range and `SERVO3_REVERSED`. (`SERVOn_FUNCTION` is an ArduPilot enum naming what an output channel drives; for skid steering the values are 73 ThrottleLeft and 74 ThrottleRight, and the factory defaults do not assign them in the order one might guess.)
- Do not carry the 1510 trim. Set `SERVO1_TRIM` and `SERVO3_TRIM` to 1500 in our SITL parameter set and record it as a deliberate delta. The 10 µs offset is one vehicle's calibration, not a design value, and carrying it means zero throttle arrives as +0.025 and the boat creeps.
- Set the thruster `<deadband>` from Blue Robotics' T200 performance data rather than guessing it.
- Check the resulting forward/reverse ratio against `MOT_THST_ASYM`, which the factory defaults set to 1.6. Our current limits imply 1.28, and that number was never measured — it is whatever the two clamps happen to be. The limits are derived from thruster data; `MOT_THST_ASYM` is an independent check afterwards, and persistent disagreement is a finding about the vehicle's calibration rather than a reason to move the thrust numbers.
- Represent `MOT_SLEWRATE` 200 %/s, or establish that the thruster's own dynamics already dominate it.
- Confirm `SERVO_RATE` 50 Hz against `SIM_RATE_HZ`.

Exit criterion: commanded speed in a speed-controlled mode produces the commanded speed in steady state, within a stated tolerance, without retuning the boat's PIDs. If ArduRover's shipped `ATC_SPEED_*` and `CRUISE_*` gains work unmodified, the actuator model is right.

This is the first real test of the transfer claim, and it is deliberately stated so that it can fail.

### Phase 4 — Waves

- Run against `gz_waves` with the Gerstner provider first, then FFT.
- Characterize the known FFT-versus-Gerstner buoyancy lag as it appears to the EKF.
- Decide whether the interim `Surface` plugin is sufficient or the full hydrodynamics plugin is required.
- Revisit the center-of-mass and trim issue already logged against the sandbox.

Exit criterion: the boat holds `LOITER` within a stated radius in a stated sea state, and the EKF does not diverge. Radius and sea state to be chosen — numbers we pick now and defend later.

### Phase 5 — Missions

- `AUTO` mode, a survey lawnmower pattern, waypoints, `WP_SPEED` and `TURN_RADIUS` from the factory defaults.
- Failsafes behave: GCS loss, low battery, arming checks.

Exit criterion: an unattended survey mission completes and the track is plausible against `CRUISE_SPEED` 1 m/s and `TURN_RADIUS` 0.1 m. The second and broader test of the transfer claim.

### Phase 6 — Packaging, documentation, upstreaming

Launch files, a `docs/` page in the style of the existing ones, CI, and a decision on whether any of this is testable headlessly. Then, separately and only once the thruster mode has stopped changing, prepare it for `gz-sim` upstream.

## Deferred

Two pieces are in scope for the effort as a whole but not for this sequence. Tracking issues, not phases.

Custom controller demonstration — a ROS 2 node commanding the normalized thruster interface with no autopilot running. Small, and it proves the interface is genuinely shared rather than ArduPilot-shaped, but nothing else depends on it.

ROS 2 autopilot interface via AP_DDS — `ap/pose/filtered`, `ap/cmd_vel`, `/ap/arm_motors`, parallel to rather than replacing the `ros_gz` view of the simulation. `ardupilot_gz` is documented against ROS 2 Humble and we are on Lyrical, so this needs its own spike and carries its own risk.

The BlueROV2 on ArduSub follows phase 6.

## Fitting this to the URDF-first assembly

This repository made a deliberate architectural choice that the SITL work has to respect rather than route around. URDF is the source of truth: a part is a URDF xacro macro carrying its own mass, inertia, slots and frames; a vehicle is an assembly resolved from a config and the parts' own slot tables; and everything Gazebo needs is *generated* from that assembly, by running the same resolution with Gazebo emitters. Nothing converts formats at runtime, and ROS and Gazebo see the same geometry.

ArduPilot support does not fit in one place in that pipeline, and pretending otherwise is how it would go wrong. It has four pieces and they belong to three different layers.

**The IMU is a frame.** `ArduPilotPlugin` needs an attitude source, and the honest reason the BlueBoat has one is that its Navigator flight controller contains it. Two obvious homes both turn out to be wrong. Declaring an `imu_link` straight into the Gazebo model is the tempting shortcut, and it produces a link that exists in simulation and not in the description — precisely the ROS-and-Gazebo divergence the architecture exists to prevent. Making it a whole part in `bluerobotics_parts`, with mesh and mass and a slot, is the opposite error: none of that is known or interesting, and inventing it would be worse than omitting it.

Parts already declare **frames** for where they sense, and `part_frames` emits each as a real link fixed to its parent. So the IMU is one line in the chassis's `frames` dict, giving a `base_link_imu` link in the URDF and therefore in TF and RViz, with the composition hanging `<sensor type="imu">` on it exactly as it already does for the Ping's beam frame. No mesh, no mass, no new part, and nothing that exists only in Gazebo.

Its position is a placeholder at the chassis origin. Where the Navigator actually sits inside the enclosure is a measurement nobody here has, and the lever arm only starts to matter when accelerations are compared against the real boat.

**The plugin is composition.** `ArduPilotPlugin` is simulator behavior, not hardware: nothing on the boat corresponds to it. It belongs in `model.sdf.xacro` alongside `Thruster` and `Hydrodynamics`, which is where the composition layer already puts things of that kind. This part is straightforwardly consistent.

**The channel mapping is derived, except for the one thing that cannot be.** Each `<control>` block pairs a servo channel with a thruster topic, and the thruster topics already come from the assembly — the composition emits one `Thruster` per propeller part, named and topic-keyed by the instance. The `<control>` blocks should be emitted by that same iteration, so a loadout with different propellers, or four of them, gets correct blocks without anyone editing SDF.

What is not derivable is *which* `SERVOn` drives which propeller. That is autopilot configuration, not a property of a part, and it has to be stated somewhere. The natural home is the loadout config, as a per-propeller key, so it travels with the rest of the vehicle definition and a four-thruster boat can express its own mapping.

**The parameters are neither.** `blueboat_sitl.params` is derived from Blue Robotics' published file and describes the autopilot, not the vehicle geometry. It is a separate artifact with its own provenance, and nothing in the assembly generates it.

That last split is where the risk sits. The parameter file says `SERVO1_FUNCTION 74`, meaning output 1 carries the right-hand throttle; the composition says channel 0 drives the starboard thruster's topic. Those two statements have to agree, they live in different files with different provenance, and nothing currently checks them. They are exactly the kind of pair that drifts — and when they drift the boat still runs, it just steers the wrong way. Worth a test that reads both and asserts they match.

The rule that falls out, and the one to apply to later phases: if it is on the boat it is a part; if it is simulator behavior it is composition; if it is autopilot configuration it is a parameter file. ArduPilot support touches all three, which is why it cannot be one self-contained file, and why the wrapper model this document originally proposed was the wrong shape for reasons beyond the SDF limitation that killed it.

## Layout

Following `bluerov2_gz`, and the `_with_ardupilot` wrapper convention from `ardupilot_gazebo` rather than the inline style `SITL_Models` used for the BlueBoat itself:

```
blueboat_gazebo/
  model.sdf.xacro              # gains an `ardupilot` flag, default false
  models/
    blueboat_with_ardupilot/   # GENERATED from that flag, not hand-written
  params/
    blueboat_sitl.params       # derived from BlueBoat120.params, with provenance
  worlds/
    blueboat_sitl.sdf          # flat water, the ArduPilot model already in it
```

### Amended during phase 1: the wrapper does not work

This section originally proposed a hand-written `blueboat_with_ardupilot` model that merge-included `model://blueboat` and added the `ArduPilotPlugin` block — the pattern `ardupilot_gazebo` and PX4 both use, and the one that keeps ArduPilot support in a file of its own. It was tried first and it fails.

`<include merge="true">` does not nest. The composed `model://blueboat` already merge-includes its Gazebo-flavored URDF, creating a frame named `_merged__blueboat__model__`; a wrapper merge-including `blueboat` produces that name a second time and the world will not load:

```
Warning: Non-unique name[_merged__blueboat__model__] detected 2 times in XML
         children of model with name[blueboat].
Error Code 2: frame with name[_merged__blueboat__model__] already exists.
```

A plain nested `<include>` is the textbook alternative and is worse here. Every joint reference would need a `blueboat::` prefix, and the world's graded buoyancy names its link as `blueboat::hull_displacement`, which nesting pushes to `blueboat::blueboat::hull_displacement`.

So the ArduPilot variant is generated from `model.sdf.xacro` behind a xacro flag, as a second output of the generator that already produces the plain model. One model source, no nesting, and it matches how every other artifact here is made: the URDF, the composed model and the bridge config all come from one config through the same generators.

The cost is honest and worth a reviewer's attention: ArduPilot support is no longer isolated in a file of its own, it lives in the shared model source. The flag defaults to false, so the model generated today is unchanged and the ROS-2-only path is untouched — additive in effect, if not in file layout.

This paragraph is left in rather than quietly rewritten so that the intent and the implementation can be reviewed against each other.

`ardupilot_gazebo` is not vendored and is not a colcon dependency. It is built into the drydock image, or on the host, and found via `GZ_SIM_SYSTEM_PLUGIN_PATH`, as every comparable project does.

The modified thruster plugin does not live here; it lives in `gz-maritime`.

## Decisions already taken

Recorded so reviewers can challenge them rather than rediscover them.

1. The normalized command is [-1, 1]: 0 stop, ±1 full command in that direction, not equal thrust.
2. The modified thruster plugin lives in `gz-maritime`, as vehicle-agnostic capability headed for Gazebo.
3. The `ardupilot` clone lives in a new `~/maritime_ws/thirdparty/` directory — inside the workspace, but separate from `src/` (colcon packages) and `tools/` (our own repositories), because it is neither.
4. We maintain our own derived SITL parameter file rather than tracking `BlueBoat120.params` verbatim with an overlay. Easier to read; revisit if the delta grows.
5. Phase 3's exit criterion stands as an aspiration rather than a gate. It may be hard to test in the short term; Blue Robotics have indicated they can share thruster data, which is the route to testing it properly.
6. No pull requests to `SITL_Models`.
7. ArduPilot is the supported autopilot; PX4 is community supported. We keep the design open to it and do not test it.
7. Arbitration between competing commanders is out of scope. A mux is the right answer eventually, and there are many options, but not here.
8. We pin ArduRover 4.7, matching the newest published BlueBoat parameters, accepting that it is tagged BETA.
9. `gz-maritime` is the right home for the thruster plugin change; its contents are currently all waves, but it is intended as a sandbox for capability headed to Gazebo.
10. The new `thirdparty/` directory needs no agreement beyond this PR.

## What this PR is asking for

The decisions above are settled unless someone argues otherwise here — that is the main thing this document is for.

Two things are genuinely open.

The phase sequence spans three repositories. Phase 2 belongs to `gz-maritime` and phase 0 touches `drydock`, while everything else is work in this repository. That is the honest split of the work, but it means "one phase, one PR" is not one review queue, and the plan is only as good as whoever is watching all three. Say if it should be organized differently.

The three-way parameter assessment is planned for phase 1. It could reasonably come earlier, as its own piece of work before any code — the argument for doing it inside phase 1 is that the files are being loaded there anyway, and the argument against is that its conclusions could change what phase 1 builds.

## Risks

The Jetty build of `ardupilot_gazebo` is unproven and gates everything. Mitigated by doing it first and timeboxing it.

Carrying a modified Gazebo system plugin means a divergence from gz-sim's `Thruster`, which is not frozen. The delta is deliberately tiny — a scaling step and an SDF flag — so the rebase should stay cheap and the eventual pull request readable. Resist growing it.

The most dangerous failure is a simulation that cannot fail. Every parameter here can be adjusted until the boat behaves, and a model tuned to agree with the autopilot it is meant to test proves nothing. The defense is that the thrust limits are derived from thruster measurements alone, and that the exit criteria are stated in advance and allowed to fail. Any moment where an autopilot parameter is used to justify a physics value is that failure happening.

The transfer claim may not hold at the tolerance we would like. A field parameter set encodes hull, fouling, loading and battery state as much as it encodes the controller. Phases 3 and 5 are where that gets found out, and "close, with these caveats" is an acceptable and publishable answer — but it should be stated as a result rather than discovered as a disappointment.

Phase 4 assumes the wave stack and an EKF interact benignly. The buoyancy lag already observed could produce heave the EKF reads as real, and that is a research problem rather than an integration problem if it goes badly.
