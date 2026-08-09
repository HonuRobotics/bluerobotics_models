# Testing

Informal manual acceptance pass for the vehicle models. Automated tests (`colcon test`) cover generation, bridge config and launch machinery; this document covers the things that need eyes on a running simulation — geometry, flotation and thrust behaviour.

Run this when changing meshes, collisions, inertia, buoyancy or thruster configuration. It is a checklist, not a gate: note what you observed, and record deviations rather than silently passing.

## Prerequisites

A GPU. Both playground worlds load `gz-sim-sensors-system`, and the rendered sensors need it.

```bash
cd ~/maritime_ws && colcon build --merge-install && source install/setup.bash
```

Reference table for the two vehicles:

| | BlueBoat (USV) | BlueROV2 (UUV) |
|---|---|---|
| world | `blueboat_playground.sdf` | `bluerov2_playground.sdf` |
| spawn pose | `z = 0.25` | `z = 0.5` |
| buoyancy | graded — seawater below `z=0`, air above | uniform 1025 everywhere |
| thrusters | 2 (`motor_{port,stbd}_joint`) | 6 standard / 8 heavy (`thruster<N>_joint`) |
| thrust bridged to ROS | yes | no — gz transport only |

```bash
gz sim $(ros2 pkg prefix --share blueboat_gazebo)/worlds/blueboat_playground.sdf
gz sim $(ros2 pkg prefix --share bluerov2_gazebo)/worlds/bluerov2_playground.sdf
```

Both worlds start paused. Press play.

---

## 1. Visuals

Load the world, unpause, orbit the model.

- [ ] All expected geometry present, nothing detached or floating
- [ ] No z-fighting or interpenetration at joins
- [ ] Proportions plausible against the real vehicle
- [ ] Accessories appear when enabled in the vehicle config (uncomment entries in `<pkg>_description/config/*.yaml` and rebuild)
- [ ] Meshes render with materials, not flat grey

On the last point: Gazebo does not reliably pick up PBR materials from inside a `.glb`. They generally need declaring explicitly in the SDF. A flat-looking mesh is usually this, not a broken export.

## 2. Collisions and mass properties

Right-click the model in the Entity Tree → View → Collisions. Also enable View → Inertia and View → Center of Mass.

- [ ] Collisions enclose the visuals, with no large unmodelled gaps
- [ ] Collision primitives do not overlap each other (overlap double-counts displaced volume)
- [ ] CoM on the centreline, and below the centre of buoyancy
- [ ] Inertia boxes roughly hull-sized — not wildly larger or smaller

For the BlueBoat specifically, the pontoon collisions are 6 boxes per side rather than one long box. That segmentation is deliberate: under graded buoyancy each short box responds to its own local depth, so pitch restores properly. Verify the segments abut rather than overlap, and treat them as part of the flotation model rather than as pure contact geometry — changing them changes how the boat floats.

## 3. Buoyancy

The two vehicles use different buoyancy modes and need different checks.

### BlueBoat — graded, has a free surface

- [ ] Settles to a steady waterline (roughly 70 mm draft) and sits level, no persistent pitch or roll
- [ ] Stable over ~30 s — no drift, oscillation or slow sink
- [ ] Drag it well below `z=0` with the GUI translate tool and release: rises and re-settles at the same waterline
- [ ] Drag the bow down and release: returns to level rather than diverging

```bash
gz topic -e -t /world/blueboat_playground/dynamic_pose/info -n 20   # watch z converge
```

### BlueROV2 — uniform density, no free surface

`uniform_fluid_density` means water everywhere, including above `z=0`. There is no surface to float at, so surfacing behaviour is not testable in this world.

- [ ] Drifts up very slowly (~1.6 cm/s terminal), damped by hydrodynamics — this matches the documented 0.02% positive buoyancy margin
- [ ] Rise is steady, with no oscillation or runaway
- [ ] Drag down and release: resumes the same slow rise

## 4. Thrusters

Check that propellers spin, that counter-rotating pairs turn opposite ways, and that a commanded sign produces the intended body-frame motion.

### BlueBoat

```bash
# Command both together — they latch, and staggering them yaws the boat
gz topic -t /model/blueboat/joint/motor_port_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
gz topic -t /model/blueboat/joint/motor_stbd_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0' &
wait
gz topic -e -t /model/blueboat/joint/motor_port_joint/ang_vel -n 5
```

| Command (port, stbd) | Expected |
|---|---|
| `+10, +10` | surge toward `+X` (bow), straight, no yaw |
| `−10, −10` | astern, straight |
| `+10, 0` | yaws to starboard |
| `0, +10` | yaws to port |
| any | `ang_vel` opposite in sign between the two props, equal in magnitude for equal thrust |

### BlueROV2

Thrust commands are not bridged, so this is gz-side only. Thrust acts along each joint axis, and the mounting angles mean per-thruster signs are not intuitive — the combinations below are the ones to test.

```bash
gz topic -t /model/bluerov2/joint/thruster1_joint/cmd_thrust -m gz.msgs.Double -p 'data: 10.0'
```

| Motion | Command | Expected |
|---|---|---|
| Surge forward | `T1,T2 = −10`; `T3,T4 = +10` | pure `+X`, no yaw or sway |
| Sway to starboard | `T1,T3 = +10`; `T2,T4 = −10` | pure sway, no yaw |
| Yaw to starboard | `T1,T4 = +10`; `T2,T3 = −10` | pure yaw, no translation |
| Heave down | `T5,T6 = +10` | descends |
| All four horizontal equal | `T1..T4 = +10` | nothing — forces and moments cancel by design |

Per-thruster reference, useful when one is suspect:

| Thruster | Thrust axis (body) | Positive command drives |
|---|---|---|
| T1 | `(−0.707, −0.707, 0)` | aft + starboard |
| T2 | `(−0.707, +0.707, 0)` | aft + port |
| T3 | `(+0.707, −0.707, 0)` | forward + starboard |
| T4 | `(+0.707, +0.707, 0)` | forward + port |
| T5, T6 | `(0, 0, −1)` | down |

Note that positive thrust on the forward horizontal pair drives the vehicle aft, and positive on the vertical pair drives it down. Both are correct: they match ArduSub's `SUB_FRAME_VECTORED` allocation matrix, where every vertical carries `throttle_fac = −1`. A naive "all positive = ahead and up" expectation will look like a failure when it isn't.

These numbers were verified against `AP_Motors6DOF.cpp` for both `SUB_FRAME_VECTORED` (6 thrusters) and `SUB_FRAME_VECTORED_6DOF` (8), accounting for the frame difference — ArduPilot uses NED (y starboard, z down), the URDFs use ROS (y port, z up). Propeller handedness is not part of that contract; ArduSub sets thrust factors from thruster facing alone and corrects spin direction via `MOT_n_DIRECTION`.

## 5. ROS interface

BlueBoat only — the ROV's thrust topics are not bridged.

```bash
ros2 launch blueboat_gazebo sim.launch.xml
ros2 topic pub /blueboat/thrusters/port/thrust std_msgs/msg/Float64 "data: 20.0" -1
ros2 topic pub /blueboat/thrusters/stbd/thrust std_msgs/msg/Float64 "data: 20.0" -1
ros2 topic echo /joint_states --once
ros2 topic echo /blueboat/ping/range --once
```

- [ ] Same motion as the gz-side commands
- [ ] `/clock` publishing
- [ ] `/joint_states` carries the motor joints, and RViz animates the props
- [ ] Enabled sensors publish on their configured topics

A `[kdl_parser] root link ... inertia` warning from `robot_state_publisher` is expected and harmless.

## 6. Adding or replacing a mesh

This procedure assumes the **current** repo layout: meshes are visual-only assets referenced from xacro, the URDF is the source of truth for kinematics, and collisions are hand-authored primitives. An alternative layout is under discussion; if it lands, this section changes.

Four constraints that catch people out, worth reading before starting:

- **URDF syntax, not SDF.** Mesh tooling and Gazebo both speak SDF, but `<pkg>_description` is URDF. Use `<mesh filename="…"/>` not `<mesh><uri>`, `<origin xyz rpy>` not `<pose>`, `<box size="a b c"/>` not `<box><size>`.
- **`package://` URIs.** A bare filename won't resolve. Write `package://blueboat_description/meshes/blueboat/blueboat.visual.glb`. The installed resource-path hook and the ament index handle Gazebo and RViz respectively.
- **Meshes are visual-only.** Collisions stay primitives. Graded buoyancy rejects mesh collisions, so on the BlueBoat the pontoon boxes are the displacement model — a hull mesh does not and must not replace them.
- **PBR needs declaring in the SDF.** Gazebo does not reliably read PBR materials out of a `.glb`. Materials belong in `<pkg>_gazebo`, not in the description.

### Procedure

1. Place the asset under `<pkg>_description/meshes/<part>/`.
2. Reference it from the relevant macro in `urdf/accessories.xacro` (or the hull visuals in `<vehicle>.urdf.xacro`).
3. Parse before launching anything:
   ```bash
   xacro blueboat_description/urdf/blueboat.urdf.xacro > /tmp/blueboat.urdf && check_urdf /tmp/blueboat.urdf
   ```
4. Check in RViz first — pure ROS, no Gazebo, fastest loop:
   ```bash
   ros2 launch blueboat_description display.launch.xml
   ```
5. Then in Gazebo, which is the only place materials and resource-path resolution get exercised:
   ```bash
   ros2 launch blueboat_gazebo sim.launch.xml
   ```

### Per-mesh acceptance

- [ ] Scale correct against a known dimension (hull length, thruster diameter)
- [ ] Orientation correct — bow at `+X`, `z` up. A mesh authored bow-aft needs re-exporting or a fixed `rpy` at the reference
- [ ] Origin lands on the intended link, not offset in `z` or laterally
- [ ] Visual sits where the collision primitive is, without drifting apart
- [ ] Renders with materials in Gazebo, not flat grey
- [ ] Mass and inertia still correct if the part's geometry changed
- [ ] Flotation unchanged, or deliberately re-tuned — re-run section 3

### Repo hygiene

- [ ] `ASSETS.md` updated with per-file provenance and license
- [ ] `NOTICE` still accurate about whether the package ships third-party assets
- [ ] File and directory naming consistent with the existing convention
- [ ] Asset size reasonable for permanent git history; decimate visual-only meshes where possible

## Recording results

Note what you actually observed, not just pass/fail — "settles level, rebounds from submersion" is more useful six months on than a tick. Deviations that are known and accepted (deferred tuning, placeholder geometry) are worth stating explicitly so the next person doesn't re-investigate them.
