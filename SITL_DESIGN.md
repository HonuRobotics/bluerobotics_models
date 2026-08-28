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

One thruster model, several commanders, identical units and topics. The thrust limits, the deadband and the forward/reverse asymmetry live inside the thruster plugin, where the physical ESC and propeller keep them. The ArduPilot `<control>` block reduces to arithmetic — `servo_min` 1100, `servo_max` 1900, `offset` -0.5, `multiplier` 2 lands exactly on [-1, 1] — carrying no vehicle-specific quantity at all.

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

Each phase is one pull request. Two of them land in other repositories

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

Lands in `gz-maritime`, which is intended as a sandbox for features headed to Gazebo. A normalized thruster command is vehicle-agnostic — it is the ordinary interface across UUV and USV work — so it does not belong in a vehicle repository.

- Fork `gz-sim-thruster-system` into a package we own. It is a system plugin, so it builds as a standalone shared library against the installed gz-sim development headers and is loaded by filename: no Gazebo source build, no change to the installed Gazebo.
- Add the mode alongside the existing two.
- Reuse `<deadband>` as it stands rather than reinventing it.
- Keep the SDF schema additive, so a model that does not ask for the new mode behaves exactly as before.
- Rename the topic: `${topic_base}/thrust` becomes `${topic_base}/cmd`, since the units change and the old name would be a lie. The generated `ros_gz_bridge.yaml` follows from `configure_vehicle.py`, so this is one edit rather than a migration.

Exit criterion: the BlueBoat runs end to end on the new mode, with the ArduPilot `<control>` block reduced to a pure PWM-to-normalized mapping carrying no vehicle physics, and phase 1 behavior reproduced.

### Phase 3 — Actuator fidelity

Make the thrust the firmware asks for equal the thrust the water sees.

- Check `max_thrust_cmd` 51.5 and `min_thrust_cmd` -40.2 against Blue Robotics' published T200 data at the boat's actual battery voltage. These are the numbers ±1 lands on, so they are now the whole actuator calibration.
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

## Layout

Following `bluerov2_gz`, and the `_with_ardupilot` wrapper convention from `ardupilot_gazebo` rather than the inline style `SITL_Models` used for the BlueBoat itself:

```
blueboat_gazebo/
  model.sdf.xacro              # thrust limits and deadband; still autopilot-agnostic
  models/
    blueboat_with_ardupilot/   # thin wrapper: merge-include + ArduPilotPlugin block
  params/
    blueboat.params            # derived from BlueBoat120.params, with provenance
  launch/
    blueboat_sitl.launch.py
  worlds/                      # existing
```

The wrapper uses `<include merge='true'>` rather than a plain include, so joint names stay unscoped and `<control><jointName>` does not need `blueboat::` prefixes.

The ArduPilot binding is additive: the ROS-2-only path keeps working, and after phase 2 it gains a better interface rather than losing the one it has.

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
7. Arbitration between competing commanders is out of scope. A mux is the right answer eventually, and there are many options, but not here.
8. We pin ArduRover 4.7, matching the newest published BlueBoat parameters, accepting that it is tagged BETA.
9. `gz-maritime` is the right home for the thruster plugin change; its contents are currently all waves, but it is intended as a sandbox for capability headed to Gazebo.
10. The new `thirdparty/` directory needs no agreement beyond this PR.

## What this PR is asking for

The decisions above are settled unless someone argues otherwise here — that is the main thing this document is for.

Two things are genuinely open.

The phase sequence spans three repositories. Phase 2 lands in `gz-maritime` and phase 0 touches `drydock`, while everything else lands here. That is the honest split of the work, but it means "one phase, one PR" is not one review queue, and the plan is only as good as whoever is watching all three. Say if it should be organized differently.

The three-way parameter assessment is planned for phase 1. It could reasonably come earlier, as its own piece of work before any code — the argument for doing it inside phase 1 is that the files are being loaded there anyway, and the argument against is that its conclusions could change what phase 1 builds.

## Risks

The Jetty build of `ardupilot_gazebo` is unproven and gates everything. Mitigated by doing it first and timeboxing it.

Carrying a modified Gazebo system plugin means a divergence from gz-sim's `Thruster`, which is not frozen. The delta is deliberately tiny — a scaling step and an SDF flag — so the rebase should stay cheap and the eventual pull request readable. Resist growing it.

The most dangerous failure is a simulation that cannot fail. Every parameter here can be adjusted until the boat behaves, and a model tuned to agree with the autopilot it is meant to test proves nothing. The defense is that the thrust limits are derived from thruster measurements alone, and that the exit criteria are stated in advance and allowed to fail. Any moment where an autopilot parameter is used to justify a physics value is that failure happening.

The transfer claim may not hold at the tolerance we would like. A field parameter set encodes hull, fouling, loading and battery state as much as it encodes the controller. Phases 3 and 5 are where that gets found out, and "close, with these caveats" is an acceptable and publishable answer — but it should be stated as a result rather than discovered as a disappointment.

Phase 4 assumes the wave stack and an EKF interact benignly. The buoyancy lag already observed could produce heave the EKF reads as real, and that is a research problem rather than an integration problem if it goes badly.
