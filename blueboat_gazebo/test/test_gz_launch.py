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

Everything here is a hard requirement, including the echosounder render test:
a missing gz CLI or render path fails the suite rather than skipping it, so
a broken environment cannot report green. CI runners render headless via EGL.
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

WORLD = (Path(get_package_share_directory('blueboat_gazebo'))
         / 'worlds' / 'blueboat_playground.sdf')
WORLD_NAME = 'blueboat_playground'

_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
POSE_TRIPLE = re.compile(rf'({_NUM}) ({_NUM}) ({_NUM})')


def gz(env, *args, timeout=10):
    """Run a gz CLI command; return (returncode, stdout)."""
    try:
        out = subprocess.run(['gz', *args], env=env, capture_output=True,
                             text=True, timeout=timeout)
        return out.returncode, out.stdout
    except subprocess.TimeoutExpired:
        return -1, ''


def model_pose(env):
    """Vehicle world pose from `gz model -p`: (x, y, z, roll, pitch, yaw)."""
    code, out = gz(env, 'model', '-m', 'blueboat', '-p', timeout=15)
    triples = POSE_TRIPLE.findall(out)
    assert code == 0 and len(triples) >= 2, f'cannot read model pose:\n{out}'
    return tuple(float(v) for triple in triples[:2] for v in triple)


def teleport(env, x, y, z):
    """Move the vehicle to a pose with identity orientation."""
    req = (f'name: "blueboat", position: {{x: {x}, y: {y}, z: {z}}}, '
           'orientation: {w: 1}')
    code, out = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/set_pose',
                   '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean',
                   '--timeout', '5000', '--req', req, timeout=15)
    assert code == 0 and 'true' in out, f'set_pose failed:\n{out}'


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
        _, out = gz(env, 'model', '--list')
        if 'blueboat' in out:
            return env
        time.sleep(2)
    fail('model never appeared in the world')


def test_model_loaded(sim):
    """The composed model is in the world."""
    _, out = gz(sim, 'model', '--list')
    assert 'blueboat' in out


def test_interfaces_advertised(sim):
    """Thruster commands and the world clock are advertised."""
    deadline = time.time() + 30
    needed = ('/model/blueboat/joint/motor_port_joint/cmd_thrust',
              '/model/blueboat/joint/motor_stbd_joint/cmd_thrust',
              f'/world/{WORLD_NAME}/clock')
    while time.time() < deadline:
        _, out = gz(sim, 'topic', '-l')
        if all(topic in out for topic in needed):
            return
        time.sleep(2)
    pytest.fail(f'missing topics; last listing:\n{out}')


def test_physics_steps(sim):
    """Simulation iterations advance (systems survive stepping)."""
    deadline = time.time() + 30
    while time.time() < deadline:
        code, out = gz(sim, 'topic', '-e', '-t',
                       f'/world/{WORLD_NAME}/stats', '-n', '1', timeout=15)
        if code == 0 and 'iterations' in out:
            iterations = int(out.split('iterations:')[1].split()[0])
            if iterations > 0:
                return
        time.sleep(2)
    pytest.fail('sim iterations did not advance')


def test_echosounder_ranges(sim):
    """The ping sensor streams ranges (gpu_lidar render path required)."""
    code, out = gz(sim, 'topic', '-e', '-t', '/blueboat/ping/range',
                   '-n', '1', timeout=30)
    assert code == 0 and 'ranges' in out, (
        'no ranges: broken sensor config or no usable render path')
    assert 'frame' in out


def test_boat_recovers_from_submersion(sim):
    """Pushed under, the pontoons drive the boat straight back to the surface."""
    teleport(sim, 0, 0, -1.0)
    z0 = model_pose(sim)[2]
    time.sleep(4)
    z1 = model_pose(sim)[2]
    assert z1 > z0 + 0.3 and z1 > -0.3, (
        f'no reserve-buoyancy recovery: z {z0:.2f} -> {z1:.2f}')


def test_forward_thrust_surges(sim):
    """
    Equal thrust on both motors drives the boat along its nose, without crab.

    Thrust commands latch and each one-shot publication lands separately, so
    the pair is momentarily unbalanced during onset and may rotate the heading
    (worse on slow CI runners). The assertion is therefore on the steady
    state, which is what the model owns: velocity aligned with the body x axis
    and no residual yaw, wherever the nose ended up pointing.
    """
    teleport(sim, 0, 0, 0.0)
    time.sleep(3)
    for _ in range(6):    # repeats: one-shot pubs can lose the discovery race
        procs = [subprocess.Popen(
            ['gz', 'topic', '-t',
             f'/model/blueboat/joint/motor_{side}_joint/cmd_thrust',
             '-m', 'gz.msgs.Double', '-p', 'data: 10.0'],
            env=sim, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for side in ('port', 'stbd')]
        for proc in procs:
            proc.wait(timeout=20)
    time.sleep(8)                     # onset transient: spin damps, speed builds
    x1, y1, _, _, _, yaw1 = model_pose(sim)
    time.sleep(8)
    x2, y2, _, _, _, yaw2 = model_pose(sim)
    dx, dy = x2 - x1, y2 - y1
    distance = math.hypot(dx, dy)
    assert distance > 0.5, f'no surge: moved {distance:.2f} m in the window'
    crab = math.degrees(math.atan2(dy, dx) - yaw2)
    crab = (crab + 180) % 360 - 180
    assert abs(crab) < 20, (
        f'not moving along the nose: crab {crab:+.1f} deg, '
        f'travel ({dx:+.2f},{dy:+.2f}) m at yaw {math.degrees(yaw2):+.1f} deg')
    residual_yaw = math.degrees(yaw2 - yaw1)
    assert abs(residual_yaw) < 20, (
        f'still yawing in steady state: {residual_yaw:+.1f} deg over the window')
