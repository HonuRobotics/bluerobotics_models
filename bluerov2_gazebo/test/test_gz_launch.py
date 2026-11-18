# Copyright 2026 Honu Robotics
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Headless Gazebo integration: world loads, interfaces up, physics behaves.

Everything here is a hard requirement, including the camera render test:
a missing gz CLI or render path fails the suite rather than skipping it, so
a broken environment cannot report green. CI runners render headless via EGL.
The behavior tests measure in SIM time (world stats), so a slow runner with a
low real time factor changes only how long they wait, never what they assert.
"""

import contextlib
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

from ament_index_python.packages import (get_package_prefix,
                                         get_package_share_directory)
from conftest import (kit_config, launch_sim, make_cli, poll_until, REPORT_TABLES,
                      shipped_has_camera)
import pytest
import yaml

WORLD = (Path(get_package_share_directory('bluerov2_gazebo'))
         / 'worlds' / 'bluerov2_playground.sdf')
WORLD_NAME = 'bluerov2_playground'
CONFIGURE = (Path(get_package_prefix('bluerov2_gazebo')) / 'lib' / 'bluerov2_gazebo'
             / 'configure_vehicle.py')

_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
POSE_TRIPLE = re.compile(rf'({_NUM}) ({_NUM}) ({_NUM})')

gz = make_cli('gz')


def model_pose(env):
    """Vehicle world pose from `gz model -p`: (x, y, z, roll, pitch, yaw)."""
    code, out, err = gz(env, 'model', '-m', 'bluerov2', '-p', timeout=15)
    triples = POSE_TRIPLE.findall(out)
    assert code == 0 and len(triples) >= 2, (
        f'cannot read model pose:\n{out}\n{err}')
    return tuple(float(v) for triple in triples[:2] for v in triple)


def sim_seconds(env):
    """Return the current sim time in seconds from the world stats topic."""
    code, out, err = gz(env, 'topic', '-e', '-t',
                        f'/world/{WORLD_NAME}/stats', '-n', '1', timeout=15)
    block = re.search(r'sim_time\s*{([^}]*)}', out)
    assert code == 0 and block, f'cannot read world stats:\n{out}\n{err}'
    # \b so 'sec:' cannot match inside 'nsec:' when sec is omitted (== 0).
    sec = re.search(r'\bsec:\s*(\d+)', block.group(1))
    nsec = re.search(r'nsec:\s*(\d+)', block.group(1))
    return (int(sec.group(1)) if sec else 0) + \
        (int(nsec.group(1)) if nsec else 0) / 1e9


def wait_sim_seconds(env, seconds, timeout=120):
    """Block until the sim clock advances `seconds`, whatever the RTF."""
    start = sim_seconds(env)

    def advanced():
        now = sim_seconds(env)
        assert now > start - 1.0, (
            f'sim clock went backward ({start:.3f} -> {now:.3f} s): '
            'server restart or corrupt stats read')
        return now - start >= seconds

    poll_until(advanced, timeout,
               f'sim advanced less than {seconds}s in {timeout}s of wall time',
               interval=0.5)


def teleport(env, x, y, z):
    """Move the vehicle to a pose with identity orientation."""
    req = (f'name: "bluerov2", position: {{x: {x}, y: {y}, z: {z}}}, '
           'orientation: {w: 1}')
    code, out, err = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/set_pose',
                        '--reqtype', 'gz.msgs.Pose',
                        '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '5000', '--req', req, timeout=15)
    assert code == 0 and 'true' in out, f'set_pose failed:\n{out}\n{err}'


def set_paused(env, paused):
    """Pause or resume the simulation."""
    code, out, err = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/control',
                        '--reqtype', 'gz.msgs.WorldControl',
                        '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '5000', '--req',
                        f'pause: {"true" if paused else "false"}', timeout=15)
    assert code == 0 and 'true' in out, f'world control failed:\n{out}\n{err}'


def pose_track(env, messages=120):
    """
    Sample the vehicle's world pose from the dynamic pose stream.

    Returns [(t, (x, y, z), (qw, qx, qy, qz))] in sim time. The stream runs
    at the scene broadcaster's rate, fine enough that consecutive samples
    never alias a fast spin the way two separate pose reads would.
    """
    code, out, err = gz(env, 'topic', '-e', '-t',
                        f'/world/{WORLD_NAME}/dynamic_pose/info',
                        '-n', str(messages), timeout=60)
    assert code == 0, f'cannot read the pose stream:\n{err}'
    track = []
    for msg in out.split('header {')[1:]:
        sec = re.search(r'stamp\s*{[^}]*?\bsec:\s*(\d+)', msg)
        nsec = re.search(r'stamp\s*{[^}]*?nsec:\s*(\d+)', msg)
        body = re.search(r'name: "bluerov2".*?position\s*{([^}]*)}'
                         r'\s*orientation\s*{([^}]*)}', msg, re.S)
        if not body:
            continue

        def field(block, key, default=0.0):
            m = re.search(rf'\b{key}:\s*({_NUM})', block)
            return float(m.group(1)) if m else default

        pos, ori = body.groups()
        track.append(((int(sec.group(1)) if sec else 0)
                      + (int(nsec.group(1)) if nsec else 0) / 1e9,
                      tuple(field(pos, k) for k in 'xyz'),
                      (field(ori, 'w', 1.0),) + tuple(field(ori, k) for k in 'xyz')))
    assert len(track) >= 10, f'too few pose samples ({len(track)}):\n{out[:500]}'
    return track


def _qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def _qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def _to_body(q, v):
    """Rotate a world-frame vector into the body frame of orientation q."""
    return _qmul(_qmul(_qconj(q), (0.0,) + tuple(v)), q)[1:]


def body_rates(track):
    """
    Mean linear and angular velocity over a track, both in the body frame.

    Each consecutive pair contributes its displacement, rotated into the body
    frame at the earlier sample, and its relative rotation as an axis-angle
    rate; the means are taken over the whole span of sim time.
    """
    lin, ang = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    for (t0, p0, q0), (t1, p1, q1) in zip(track, track[1:]):
        if t1 <= t0:
            continue
        d = _to_body(q0, [b - a for a, b in zip(p0, p1)])
        rw, *rv = _qmul(_qconj(q0), q1)
        if rw < 0:
            rw, rv = -rw, [-c for c in rv]
        s = math.sqrt(sum(c * c for c in rv))
        angle = 2.0 * math.atan2(s, rw)
        axis = [c / s for c in rv] if s > 1e-12 else [0.0, 0.0, 0.0]
        for i in range(3):
            lin[i] += d[i]
            ang[i] += axis[i] * angle
    span = track[-1][0] - track[0][0]
    assert span > 0, 'pose samples carry no sim time span'
    return [c / span for c in lin], [c / span for c in ang]


def _angle_deg(v, axis):
    norm = math.sqrt(sum(c * c for c in v))
    if norm == 0:
        return 180.0
    cos = sum(a * b for a, b in zip(v, axis)) / norm
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def max_tilt_deg(track):
    """Largest |roll| and |pitch| over a pose track, in degrees."""
    roll = pitch = 0.0
    for _, _, (qw, qx, qy, qz) in track:
        r = math.atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))
        p = math.asin(max(-1.0, min(1.0, 2 * (qw * qy - qz * qx))))
        roll, pitch = max(roll, abs(r)), max(pitch, abs(p))
    return math.degrees(roll), math.degrees(pitch)


def heading_deg(q):
    """Heading (yaw, counter-clockwise from above) of an orientation, in degrees."""
    qw, qx, qy, qz = q
    return math.degrees(math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)))


def latch_thrusters(env, mapping, period=0.3):
    """
    Hold normalized thrust commands [-1, 1] by republishing them until released.

    `gz topic -p` publishes once per invocation, and a single shot can lose
    the transport discovery race under load: a total loss parks the vehicle
    and a partial latch applies an unbalanced wrench that drives it
    diagonally. Republishing in a loop for the whole command window makes
    delivery a matter of time instead of luck. Stop with release_thrusters,
    which latches zero behind the commands.
    """
    procs = []
    for n, value in mapping.items():
        topic = f'/bluerov2/thruster_{n}/cmd'
        loop = (f'while true; do gz topic -t {topic} -m gz.msgs.Double '
                f'-p "data: {value}"; sleep {period}; done')
        procs.append(subprocess.Popen(
            ['bash', '-c', loop], env=env, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    return procs


def wait_commands_landed(env, numbers):
    """
    Block until every thruster in `numbers` has had a command published.

    A message seen here was also delivered to the thruster, whose subscriber
    is older than this one. With the simulation paused this tells when all
    the commands of a latch are in, however slow the publishers start.
    """
    for n in numbers:
        code, out, err = gz(env, 'topic', '-e', '-t', f'/bluerov2/thruster_{n}/cmd',
                            '-n', '1', timeout=30)
        assert code == 0 and 'data' in out, (
            f'no command seen on thruster {n}:\n{out}\n{err}')


def _stop_publishers(procs):
    for proc in procs:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
    for proc in procs:
        proc.wait(timeout=10)


def release_thrusters(env, procs, numbers):
    """Stop the publishers and latch zero so the next test starts clean."""
    _stop_publishers(procs)
    zeros = latch_thrusters(env, dict.fromkeys(numbers, 0.0))
    time.sleep(4.0)  # several republish rounds so the zeros land
    _stop_publishers(zeros)


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on an isolated partition; yield its env."""
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    # -v 3 so warnings and messages (not just errors) reach the audited log.
    return launch_sim(
        request, 'gz sim',
        ['gz', 'sim', '-s', '-r', '-v', '3', str(WORLD)], env,
        ready=lambda e: 'bluerov2' in gz(e, 'model', '--list')[1])


def test_model_loaded(sim):
    """The composed model is in the world."""
    _, out, _ = gz(sim, 'model', '--list')
    assert 'bluerov2' in out


def test_interfaces_advertised(sim):
    """Thruster commands and sensor topics are advertised."""
    needed = ('/bluerov2/thruster_1/cmd',
              '/bluerov2/thruster_6/cmd',
              f'/world/{WORLD_NAME}/clock')
    poll_until(
        lambda: all(t in gz(sim, 'topic', '-l')[1] for t in needed), 30,
        lambda: f'missing topics; last listing:\n{gz(sim, "topic", "-l")[1]}')


def test_physics_steps(sim):
    """Simulation iterations advance (systems survive stepping)."""
    def advancing():
        code, out, _ = gz(sim, 'topic', '-e', '-t',
                          f'/world/{WORLD_NAME}/stats', '-n', '1', timeout=15)
        return (code == 0 and 'iterations' in out
                and int(out.split('iterations:')[1].split()[0]) > 0)
    poll_until(advancing, 30, 'sim iterations did not advance')


def test_camera_renders(sim):
    """
    The shipped configuration's camera streams frames at its configured size.

    Skipped when the shipped config fits no camera.
    """
    if not shipped_has_camera():
        pytest.skip('the shipped config fits no camera')
    code, out, err = gz(sim, 'topic', '-e', '-t', '/bluerov2/camera/image',
                        '-n', '1', timeout=30)
    assert code == 0 and 'data' in out, (
        f'no camera image: broken sensor config or no usable render path\n{err}')
    assert 'width: 1920' in out


def test_vehicle_neutrally_buoyant(sim):
    """Submerged, the neutral shipped trim holds depth: the sizing holds in sim."""
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)           # let the relocation transient damp out
    t0, z0 = sim_seconds(sim), model_pose(sim)[2]
    wait_sim_seconds(sim, 8)
    t1, z1 = sim_seconds(sim), model_pose(sim)[2]
    rate = (z1 - z0) / (t1 - t0)
    assert abs(rate) < 0.05, (
        f'drift rate {rate:.4f} m/s outside the neutral band '
        f'(z {z0:.3f} -> {z1:.3f} over {t1 - t0:.1f} sim s)')


# The teleop mixers' gains, read from the sibling package's source rather than
# declared as a dependency: bluerobotics_teleop already test-depends on this
# package, and the reverse would be a cycle.
MIXER_DIR = Path(__file__).resolve().parents[2] / 'bluerobotics_teleop' / 'config'
MIXER_YAML = {'standard': MIXER_DIR / 'bluerov2' / 'mixer.yaml',
              'heavy': MIXER_DIR / 'bluerov2_heavy' / 'mixer.yaml'}

# Expected speed for a 0.5 command on each axis, from the vehicle's published
# performance and engineering judgement - not from the model under test, whose
# coefficients are still being identified. A factor of ten either way catches
# a value that is unreasonable without pinning one that is being tuned.
AXIS_COMMAND = 0.5
SPEED_FACTOR = 10.0
DIRECTION_DEG = 10.0
# The speed is measured once it has built up; the level and heading checks
# below also cover these first seconds, where a thrust line that misses the
# center of mass shows.
ONSET_S = 2.0
# A command on one axis must also hold the vehicle level, from its first
# step: a body-frame velocity check alone passes a vehicle that pitches up
# and climbs, since it still moves "forward" in its own frame. Thrust and
# drag on different lines tilt it under way, and thrust off the center of
# mass tilts it as it starts; buoyancy only rights it so far.
TILT_DEG = 10.0
# A surge, sway or heave command does not turn the vehicle either. Nothing
# rights a turn in yaw, so a few millimeters between the line of the thrust
# and the point where the drag acts turn it steadily, and a vehicle that
# turns while it moves sideways creeps forward.
HEADING_DEG = 5.0
# A yaw command turns the vehicle about the spot.
YAW_DRIFT_M = 0.3
AXES = {
    # name: (twist index, mixer key, body axis, expected, unit, linear?)
    'surge': (0, 'gains_linear_x', (1, 0, 0), 0.75, 'm/s', True),
    'sway': (1, 'gains_linear_y', (0, 1, 0), 0.5, 'm/s', True),
    'heave': (2, 'gains_linear_z', (0, 0, 1), 0.5, 'm/s', True),
    'yaw': (3, 'gains_angular_z', (0, 0, 1), math.pi, 'rad/s', False),
}

# Start points that leave room to travel in the commanded direction: the
# pool walls are at +/-12.55 m, the floor at -5 m and the surface at 0.
START = {
    ('surge', 1): (-10.0, 0.0, -2.5), ('surge', -1): (10.0, 0.0, -2.5),
    ('sway', 1): (0.0, -10.0, -2.5), ('sway', -1): (0.0, 10.0, -2.5),
    ('heave', 1): (0.0, 0.0, -4.2), ('heave', -1): (0.0, 0.0, -0.8),
    ('yaw', 1): (0.0, 0.0, -2.5), ('yaw', -1): (0.0, 0.0, -2.5),
}
POOL = {'x': 12.3, 'y': 12.3, 'z_top': -0.3, 'z_bottom': -4.7}

# One row per axis case, printed as a table at the end of the run (see
# conftest.REPORT_TABLES), so a run shows every measurement beside its
# limits, not just pass or fail. In the terminal and in the colcon test log.
AXIS_TABLE = {'standard': 'Axis command results',
              'heavy': 'Axis command results, heavy variant'}
AXIS_HEAD = ('case', 'expected', 'speed limits', 'measured', 'ratio',
             f'off axis (<= {DIRECTION_DEG:g})', f'roll, pitch (<= {TILT_DEG:g})',
             f'turn (<= {HEADING_DEG:g})', f'yaw drift (<= {YAW_DRIFT_M:g})',
             'body rate x, y, z', 'result')


def mixer_commands(variant, axis, sign):
    """Per-thruster commands the teleop mixer would send for one axis."""
    params = yaml.safe_load(
        MIXER_YAML[variant].read_text())['twist_to_thrust']['ros__parameters']
    gains = params[AXES[axis][1]]
    topics = params['thruster_topics']
    return {int(re.search(r'thruster_(\d+)', t).group(1)):
            max(-1.0, min(1.0, g * sign * AXIS_COMMAND))
            for t, g in zip(topics, gains)}


def check_axis_command(sim, variant, axis, sign):
    """
    Check that a 0.5 command on one body axis moves the vehicle along it.

    Checks polarity and allocation first and magnitude only loosely: once the
    speed has built up (ONSET_S), the motion must lie within DIRECTION_DEG of
    the commanded axis (REP 103: x forward, y port, z up, yaw
    counter-clockwise from above) and its speed within a factor of
    SPEED_FACTOR of the expected figure. From the first step of the command
    the vehicle must also stay within TILT_DEG of level and, on the linear
    axes, within HEADING_DEG of its heading. On yaw it must stay within
    YAW_DRIFT_M of where it started.

    This does NOT test the autopilot's thruster allocation (ArduSub's
    Vectored frame). It is contingent on the teleop thruster allocation in
    the variant's mixer.yaml under bluerobotics_teleop/config and only
    pertains to that setup.
    """
    _, _, body_axis, expected, unit, linear = AXES[axis]
    start = START[(axis, sign)]
    teleport(sim, *start)
    wait_sim_seconds(sim, 3)           # let the relocation transient damp out
    commands = mixer_commands(variant, axis, sign)
    # Each thruster has a publisher of its own, and they do not start at the
    # same instant. Latch them with the simulation paused and resume once
    # every command is in, so all thrusters start in the same step: one that
    # leads the others turns or pushes the vehicle, and nothing rights a
    # turn in yaw. The thrusters this axis leaves at rest are already at zero.
    driven = {n: value for n, value in commands.items() if value}
    set_paused(sim, True)
    procs = latch_thrusters(sim, driven)
    try:
        wait_commands_landed(sim, driven)
        began = sim_seconds(sim)
        set_paused(sim, False)
        onset = pose_track(sim)        # onset: speed builds toward steady state
        while onset[-1][0] - began < ONSET_S:
            onset += pose_track(sim, 30)
        track = pose_track(sim)
    finally:
        # Stop them together too. A thruster that runs a moment longer than
        # the others turns the vehicle, and with no linear yaw damping that
        # turn dies slowly enough to show in the next case's heading.
        set_paused(sim, True)
        release_thrusters(sim, procs, tuple(commands))
        set_paused(sim, False)

    run = onset + track
    for _, (x, y, z), _ in run:
        assert (abs(x) < POOL['x'] and abs(y) < POOL['y']
                and POOL['z_bottom'] < z < POOL['z_top']), (
            f'{axis} {sign:+d}: ran out of pool at ({x:.2f}, {y:.2f}, {z:.2f}); '
            'the measurement window is too long for this speed')

    lin, ang = body_rates(track)
    rate = lin if linear else ang
    target = [sign * c for c in body_axis]
    speed = math.sqrt(sum(c * c for c in rate))
    off_axis = _angle_deg(rate, target)
    roll, pitch = max_tilt_deg(run)
    # Heading change since the command began, for the linear axes.
    turn = heading_deg(run[-1][2]) - heading_deg(run[0][2]) if linear else 0.0
    turn = abs((turn + 180.0) % 360.0 - 180.0)
    # Furthest the vehicle gets from its start point, for yaw.
    drift = 0.0 if linear else max(
        math.hypot(x - start[0], y - start[1]) for _, (x, y, _), _ in run)
    detail = (f'{axis} {sign:+d}: measured {speed:.3f} {unit} '
              f'({", ".join(f"{c:+.3f}" for c in rate)}), expected {expected:.3f}, '
              f'commands {commands}')
    lo, hi = expected / SPEED_FACTOR, expected * SPEED_FACTOR
    level = max(roll, pitch) <= TILT_DEG
    ok = (off_axis <= DIRECTION_DEG and lo <= speed <= hi and level
          and turn <= HEADING_DEG and drift <= YAW_DRIFT_M)
    REPORT_TABLES.setdefault(AXIS_TABLE[variant], [AXIS_HEAD]).append((
        f'{axis} {"+" if sign > 0 else "-"}', f'{expected:.3f} {unit}',
        f'{lo:.3g} - {hi:.3g}', f'{speed:.3f} {unit}', f'{speed / expected:.2f}',
        f'{off_axis:.1f} deg', f'{roll:.1f}, {pitch:.1f} deg',
        f'{turn:.1f} deg' if linear else '-',
        '-' if linear else f'{drift:.2f} m', ', '.join(f'{c:+.3f}' for c in rate),
        'pass' if ok else 'FAIL'))
    assert off_axis <= DIRECTION_DEG, (
        f'{detail}: motion is {off_axis:.1f} deg off the commanded axis')
    assert expected / SPEED_FACTOR <= speed <= expected * SPEED_FACTOR, (
        f'{detail}: speed outside a factor of {SPEED_FACTOR:g} of expected')
    assert level, (
        f'{detail}: tilted {roll:.1f} deg roll, {pitch:.1f} deg pitch '
        f'(limit {TILT_DEG:g}); thrust, drag and the center of mass are not '
        'on one line')
    assert turn <= HEADING_DEG, (
        f'{detail}: the vehicle turns {turn:.1f} deg while it moves '
        f'(limit {HEADING_DEG:g}); the sway thrust misses the center of pressure')
    assert drift <= YAW_DRIFT_M, (
        f'{detail}: the vehicle drifts {drift:.2f} m from its start as it turns')


@pytest.mark.parametrize('sign', [1, -1], ids=['pos', 'neg'])
@pytest.mark.parametrize('axis', list(AXES))
def test_axis_command_moves_the_vehicle(sim, axis, sign):
    """Each axis command moves the standard vehicle along its axis."""
    check_axis_command(sim, 'standard', axis, sign)


@pytest.fixture(scope='module')
def heavy_sim(request, tmp_path_factory):
    """Start a headless gz server with the heavy variant in the playground."""
    cfg = kit_config()
    cfg['base'] = {'type': 'bluerov2_heavy_chassis', 'name': 'base_link'}
    cfg['buoyancy']['footprint'] = '0.457 0.575'
    folder = tmp_path_factory.mktemp('heavy')
    (folder / 'heavy.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False))
    # Every artifact of the heavy vehicle, as the launch file makes them; the
    # directory is then a model the world can include in place of the default.
    model = folder / 'bluerov2'
    out = subprocess.run(
        [str(CONFIGURE), '--config', str(folder / 'heavy.yaml'), '--out-dir', str(model)],
        capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, f'configure_vehicle failed:\n{out.stderr}'
    world = WORLD.read_text()
    assert world.count('<uri>model://bluerov2</uri>') == 1
    (folder / 'world.sdf').write_text(world.replace(
        '<uri>model://bluerov2</uri>', f'<uri>{model}</uri>'))
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    return launch_sim(
        request, 'gz sim heavy',
        ['gz', 'sim', '-s', '-r', '-v', '3', str(folder / 'world.sdf')], env,
        ready=lambda e: '/bluerov2/thruster_8/cmd' in gz(e, 'topic', '-l')[1])


@pytest.mark.parametrize('sign', [1, -1], ids=['pos', 'neg'])
@pytest.mark.parametrize('axis', list(AXES))
def test_axis_command_moves_the_heavy_vehicle(heavy_sim, axis, sign):
    """Each axis command moves the heavy variant along its axis."""
    check_axis_command(heavy_sim, 'heavy', axis, sign)
