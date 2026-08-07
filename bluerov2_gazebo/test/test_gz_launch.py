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

import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid

from ament_index_python.packages import get_package_share_directory
import pytest

WORLD = (Path(get_package_share_directory('bluerov2_gazebo'))
         / 'worlds' / 'bluerov2_playground.sdf')
WORLD_NAME = 'bluerov2_playground'

_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
POSE_TRIPLE = re.compile(rf'({_NUM}) ({_NUM}) ({_NUM})')


def gz(env, *args, timeout=10):
    """Run a gz CLI command; return (returncode, stdout, stderr)."""
    try:
        out = subprocess.run(['gz', *args], env=env, capture_output=True,
                             text=True, timeout=timeout)
        return out.returncode, out.stdout, out.stderr
    except subprocess.TimeoutExpired:
        return -1, '', f'gz {args[0]}: timed out after {timeout}s'


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
    sec = re.search(r'sec:\s*(\d+)', block.group(1))
    nsec = re.search(r'nsec:\s*(\d+)', block.group(1))
    return (int(sec.group(1)) if sec else 0) + \
        (int(nsec.group(1)) if nsec else 0) / 1e9


def wait_sim_seconds(env, seconds, timeout=120):
    """Block until the sim clock advances `seconds`, whatever the RTF."""
    start = sim_seconds(env)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if sim_seconds(env) - start >= seconds:
            return
        time.sleep(0.5)
    pytest.fail(f'sim advanced less than {seconds}s in {timeout}s of wall time')


def teleport(env, x, y, z):
    """Move the vehicle to a pose with identity orientation."""
    req = (f'name: "bluerov2", position: {{x: {x}, y: {y}, z: {z}}}, '
           'orientation: {w: 1}')
    code, out, err = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/set_pose',
                        '--reqtype', 'gz.msgs.Pose',
                        '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '5000', '--req', req, timeout=15)
    assert code == 0 and 'true' in out, f'set_pose failed:\n{out}\n{err}'


def command_thrusters(env, mapping, repeats=6):
    """
    Latch thrust commands (N), publishing every topic in parallel each round.

    Parallel publication matters: commands latch, so staggered one-at-a-time
    onset applies an unbalanced wrench and yaws the vehicle off its heading.
    Rounds repeat because one-shot publications can lose the discovery race.
    """
    for _ in range(repeats):
        procs = [(n, subprocess.Popen(
            ['gz', 'topic', '-t',
             f'/model/bluerov2/joint/thruster{n}_joint/cmd_thrust',
             '-m', 'gz.msgs.Double', '-p', f'data: {value}'],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True)) for n, value in mapping.items()]
        for n, proc in procs:
            _, err = proc.communicate(timeout=20)
            assert proc.returncode == 0, (
                f'thruster {n} command failed ({proc.returncode}): {err}')


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on an isolated partition; yield its env."""
    if shutil.which('gz') is None:
        pytest.fail('gz CLI not available: the simulation suite cannot run')
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    log = tempfile.NamedTemporaryFile('w+', suffix='.log', delete=False,
                                      prefix='gz_launch_')
    # -v 3 so warnings and messages (not just errors) reach the audited log.
    proc = subprocess.Popen(['gz', 'sim', '-s', '-r', '-v', '3', str(WORLD)],
                            env=env, stdout=log, stderr=subprocess.STDOUT)

    def fail(message):
        log.flush()
        tail = ''.join(open(log.name).readlines()[-40:])
        pytest.fail(f'{message}\nlast gz output ({log.name}):\n{tail}')

    def teardown():
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        # Always surface the server output: warnings matter even when every
        # assertion passed, and exit codes underreport partial failures.
        log.flush()
        tail = ''.join(open(log.name).readlines()[-60:])
        print(f'\n--- gz sim output tail ({log.name}) ---\n{tail}')

    request.addfinalizer(teardown)
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            fail('gz server exited during startup')
        _, out, _ = gz(env, 'model', '--list')
        if 'bluerov2' in out:
            return env
        time.sleep(2)
    fail('model never appeared in the world')


def test_model_loaded(sim):
    """The composed model is in the world."""
    _, out, _ = gz(sim, 'model', '--list')
    assert 'bluerov2' in out


def test_interfaces_advertised(sim):
    """Thruster commands and sensor topics are advertised."""
    deadline = time.time() + 30
    needed = ('/model/bluerov2/joint/thruster1_joint/cmd_thrust',
              '/model/bluerov2/joint/thruster6_joint/cmd_thrust',
              f'/world/{WORLD_NAME}/clock')
    while time.time() < deadline:
        _, out, _ = gz(sim, 'topic', '-l')
        if all(topic in out for topic in needed):
            return
        time.sleep(2)
    pytest.fail(f'missing topics; last listing:\n{out}')


def test_physics_steps(sim):
    """Simulation iterations advance (systems survive stepping)."""
    deadline = time.time() + 30
    while time.time() < deadline:
        code, out, _ = gz(sim, 'topic', '-e', '-t',
                          f'/world/{WORLD_NAME}/stats', '-n', '1', timeout=15)
        if code == 0 and 'iterations' in out:
            iterations = int(out.split('iterations:')[1].split()[0])
            if iterations > 0:
                return
        time.sleep(2)
    pytest.fail('sim iterations did not advance')


def test_camera_renders(sim):
    """The default loadout's camera streams frames at its configured size."""
    code, out, err = gz(sim, 'topic', '-e', '-t', '/bluerov2/camera/image',
                        '-n', '1', timeout=30)
    assert code == 0 and 'data' in out, (
        f'no camera image: broken sensor config or no usable render path\n{err}')
    assert 'width: 1920' in out


def test_vehicle_slightly_positively_buoyant(sim):
    """Submerged, the near-neutral trim rises slowly: the sizing holds in sim."""
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)           # let the relocation transient damp out
    t0, z0 = sim_seconds(sim), model_pose(sim)[2]
    wait_sim_seconds(sim, 8)
    t1, z1 = sim_seconds(sim), model_pose(sim)[2]
    rate = (z1 - z0) / (t1 - t0)
    assert 0.001 < rate < 0.10, (
        f'rise rate {rate:.4f} m/s outside the near-neutral band '
        f'(z {z0:.3f} -> {z1:.3f} over {t1 - t0:.1f} sim s)')


def test_vertical_thrusters_heave(sim):
    """
    The vertical pair heaves: commanded up, the climb dwarfs the passive rise.

    Positive commands push down (both vertical axes point -z), so up is
    negative. The heavy variant's extra pair (7, 8) is not in the playground's
    standard model and is exercised by the same macro at generation time.
    """
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)
    t0, z0 = sim_seconds(sim), model_pose(sim)[2]
    command_thrusters(sim, {5: -20.0, 6: -20.0})
    wait_sim_seconds(sim, 6)
    t1, z1 = sim_seconds(sim), model_pose(sim)[2]
    command_thrusters(sim, {5: 0.0, 6: 0.0}, repeats=3)
    rate = (z1 - z0) / (t1 - t0)
    assert rate > 0.10, (
        f'no heave authority: climbed {rate:.3f} m/s '
        f'(z {z0:.2f} -> {z1:.2f} over {t1 - t0:.1f} sim s)')


def test_forward_thrust_mix_surges(sim):
    """
    The vectored surge mix drives the vehicle along its nose, without crab.

    Command onset can rotate the heading (see command_thrusters), so the
    assertion is on the steady state, which is what the model owns: velocity
    aligned with the body x axis and no residual yaw, wherever the nose ended
    up pointing.
    """
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)
    command_thrusters(sim, {1: -10.0, 2: -10.0, 3: 10.0, 4: 10.0})
    wait_sim_seconds(sim, 8)          # onset transient: spin damps, speed builds
    t1 = sim_seconds(sim)
    x1, y1, _, _, _, yaw1 = model_pose(sim)
    wait_sim_seconds(sim, 8)
    t2 = sim_seconds(sim)
    x2, y2, _, _, _, yaw2 = model_pose(sim)
    dx, dy = x2 - x1, y2 - y1
    speed = math.hypot(dx, dy) / (t2 - t1)
    assert speed > 0.05, (
        f'no surge: {speed:.3f} m/s over {t2 - t1:.1f} sim s')
    crab = math.degrees(math.atan2(dy, dx) - yaw2)
    crab = (crab + 180) % 360 - 180
    assert abs(crab) < 20, (
        f'not moving along the nose: crab {crab:+.1f} deg, '
        f'travel ({dx:+.2f},{dy:+.2f}) m at yaw {math.degrees(yaw2):+.1f} deg')
    residual_yaw = math.degrees(yaw2 - yaw1)
    assert abs(residual_yaw) < 20, (
        f'still yawing in steady state: {residual_yaw:+.1f} deg over the window')
