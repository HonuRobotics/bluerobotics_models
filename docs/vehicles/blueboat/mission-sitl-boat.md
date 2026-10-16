# Waypoint mission for BlueBoat

This walkthrough flies one waypoint mission on the simulated BlueBoat in ArduRover's `AUTO` mode, unattended, and states beforehand what a correct run looks like.

`AUTO` is the layer above the stabilization layer exercised in [Tuning of closed-loop response](tune-sitl-boat.md). The waypoint navigator produces a speed and a turn rate, and those go to the same `ATC_SPEED_*` and `ATC_STR_RAT_*` loops. Two things are new here. One is the heading controller `ATC_STR_ANG_P`, which the boat reaches when it pivots at a waypoint. The other is the waypoint navigation parameters (`WP_*`, `WP_PIVOT_*`, `PSC_*`), all at Blue Robotics' shipped values.

## Prerequisites

* Setup and run the drydock + source development environment: [installation_drydock.md](../../getting-started/installation_drydock.md)
* [ArduPilot SITL setup](../../getting-started/ardupilot_setup.md); (the rest of this page assumes the Iris smoke test passed.)
* [Verify the SITL connection (Boat)](verify-sitl-boat.md) and [Tuning of closed-loop response](tune-sitl-boat.md) pass. If a mission result disappoints, check those first: a bad track on top of an unvalidated inner loop says nothing about navigation.

## The mission

The mission is a fixed file installed with the package, `blueboat_gazebo/missions/lawnmower.waypoints`, in the QGC WPL format that both MAVProxy and QGroundControl read. It is a small lawnmower: 10 m legs east and west, 5 m steps north between them, then a diagonal back to the start.

| Item | North [m] | East [m] | Leg into it |
|---|---|---|---|
| 0 (home) | 0 | 0 | |
| 1 | 0 | 10 | 10 m east, the direction the boat spawns facing |
| 2 | 5 | 10 | 5 m north, after a 90° pivot |
| 3 | 5 | 0 | 10 m west, after a 90° pivot |
| 4 | 10 | 0 | 5 m north, after a 90° pivot |
| 5 | 10 | 10 | 10 m east, after a 90° pivot |
| 6 | 0 | 0 | 14 m diagonal home, after a 135° pivot |

The waypoints are geodetic, so they only land where intended against a fixed home. The walkthrough pins it with `--custom-location` to ArduPilot's default SITL location, written out so that a change upstream cannot move the mission. Gazebo's +X is east here (`gazeboXYZToNED` in the model), and the boat spawns with its bow along +X, so the first leg starts dead ahead.

Every turn in this mission is sharper than `WP_PIVOT_ANGLE` (45°), so at each waypoint the boat stops and pivots at up to `WP_PIVOT_RATE` (15 deg/s) before setting off down the next leg.

## Walkthrough

All commands are issued within the drydock dev container. Two shells, as in the verification walkthrough.

First, the simulation:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v3 -r $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_sitl.sdf
```

Then the autopilot, with the map and the pinned home:

```bash
source ~/maritime_ws/install/setup.bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
AP=$HOME/maritime_ws/thirdparty/ardupilot/Tools/autotest
sim_vehicle.py -v Rover -f rover-skid --model JSON --console --map -w \
  --custom-location=-35.363261,149.165230,584,90 \
  --add-param-file=$AP/default_params/rover.parm \
  --add-param-file=$(ros2 pkg prefix --share blueboat_gazebo)/params/blueboat_sitl.params
```

Wait until the console reports `EKF3 IMU0 is using GPS`, about 40 s after start. A mission sent earlier is refused (`Only 0 items are supported`), and `AUTO` needs a position estimate.

### Load the mission

At the MAVProxy prompt:

```
wp load /home/<you>/maritime_ws/install/share/blueboat_gazebo/missions/lawnmower.waypoints
wp list
```

MAVProxy does not expand `$(...)`, so give it the path. `ros2 pkg prefix --share blueboat_gazebo` in a shell prints it. Expect `Loaded 7 waypoints`, then `Flight plan received` in the console, and the six legs drawn on the map.

### Graph the navigation

```
module load graph
graph NAV_CONTROLLER_OUTPUT.xtrack_error
graph VFR_HUD.groundspeed
```

### Fly it

```
arm throttle
mode auto
```

Then touch nothing. The console reports `Mission: 1 WP`, then `Reached waypoint #1` through `#6`, then `Mission Complete`. The boat then loiters at home (`MIS_DONE_BEHAVE 1`). To stop, `mode manual` and `disarm`.

## What a correct run looks like

SITL steps in lockstep with Gazebo, so the run is deterministic. Repeated runs here agreed to 0.01 m and 0.1 s, and a reviewer should see the same figures, not just similar ones. Times are from `mode auto`.

| Leg | Reached at [s] | Leg time [s] | Peak \|xtrack\| [m] | \|xtrack\| at arrival [m] |
|---|---|---|---|---|
| home → WP1 | 13.9 | 13.9 | 0.01 | 0.00 |
| WP1 → WP2 | 28.8 | 14.9 | 1.2 | 0.25 |
| WP2 → WP3 | 47.3 | 18.5 | 1.6 | 0.09 |
| WP3 → WP4 | 63.2 | 15.9 | 1.5 | 0.26 |
| WP4 → WP5 | 81.5 | 18.3 | 1.7 | 0.10 |
| WP5 → WP6 | 108.0 | 26.5 | 2.3 | 0.06 |

* **Speed.** 1.0 m/s on the first leg (`WP_SPEED`), dropping to about 0 at each waypoint for the pivot, then 0.8–0.95 m/s on the later legs before slowing for the next waypoint.
* **Mission time.** 108 s, all six waypoints reached, `Mission Complete`.
* **End.** The boat holds within 0.4 m of home.

![Planned legs and flown track](images/mission_track.png)

![Cross-track error through the mission](images/mission_xtrack.png)

![Speed through the mission](images/mission_speed.png)

### The corners: a pivot that drifts

The first leg is flown dead on the line. Every leg after a pivot starts 1 to 2 m off it, because the pivot is not on the spot: the boat moves forward at 0.2–0.4 m/s while it turns, and swings a loop of 1.5–2 m outside the corner. The navigator then works the offset off over the leg, and arrives at each waypoint within 0.3 m of the line.

The cause is one layer down, not in the navigation parameters. A pivot is a steering-only command, and on this model a steering-only command does not cancel in surge. The forward-running thruster gives 40.2 N per unit output. The reverse-running one gives 20.1 N, scaled by `MOT_THST_ASYM` 1.6 to 32.2 N. The 8 N left over drives the boat forward through the turn. It shows outside `AUTO` too: in `MANUAL`, `rc 1 1700` with throttle neutral spins the boat at about 25 deg/s while it travels at about 0.6 m/s, a circle of about 1.3 m radius rather than a turn on the spot.

This is the `MOT_THST_ASYM` cross-check the [SITL spec](../../specs/SITL_SPEC.md) names for the stabilization layer. The published thrust data puts the forward/reverse ratio at 2.0, and the shipped parameter compensates for 1.6. That is a finding about the vehicle's calibration, not a reason to move the thrust numbers or the navigation gains, so it is stated here as a result. If the hardware boat pivots on the spot, the disagreement is in the thrust model or the calibration, and the place to look is [Parameters](parameters.md).

## If it goes wrong

| Observation | What it means |
|---|---|
| `Only 0 items are supported` on `wp load` | sent before ArduPilot was ready; wait for `is using GPS` and load again |
| `No Mission. Can't set AUTO.` | the mission did not load; repeat `wp load` and check `wp list` |
| the boat turns before the first leg | the boat is not spawned facing east, or `--custom-location` was dropped; check the command |
| the boat circles a waypoint and never reaches it | it cannot get inside `WP_RADIUS` (1 m); check the turn-rate loop in [Tuning](tune-sitl-boat.md) |
| the boat arcs through corners at speed instead of stopping | the `WP_PIVOT_*` lines are missing from the parameter file; the firmware default disables pivot turns |
| large, steady cross-track on a leg | the speed or heading loop; re-run [Tuning](tune-sitl-boat.md) before suspecting the navigator |
| times or errors differ from the table | something in the vehicle, the parameters or the firmware version changed; the run is deterministic, so a difference is a change, not noise |
