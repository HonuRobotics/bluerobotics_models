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

The gz CLI is a hard requirement: its absence fails the suite rather than
skipping it, so a broken environment cannot report green. The render smoke
test (camera image) is the one exception: it SKIPS when no usable render path
exists, so CPU-only CI runners stay green while still exercising rendering
where available.
"""

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
    """Run a gz CLI command; return (returncode, stdout)."""
    try:
        out = subprocess.run(['gz', *args], env=env, capture_output=True,
                             text=True, timeout=timeout)
        return out.returncode, out.stdout
    except subprocess.TimeoutExpired:
        return -1, ''


def model_pose(env):
    """Vehicle world pose from `gz model -p`: (x, y, z, roll, pitch, yaw)."""
    code, out = gz(env, 'model', '-m', 'bluerov2', '-p', timeout=15)
    triples = POSE_TRIPLE.findall(out)
    assert code == 0 and len(triples) >= 2, f'cannot read model pose:\n{out}'
    return tuple(float(v) for triple in triples[:2] for v in triple)


def teleport(env, x, y, z):
    """Move the vehicle to a pose with identity orientation."""
    req = (f'name: "bluerov2", position: {{x: {x}, y: {y}, z: {z}}}, '
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
    proc = subprocess.Popen(['gz', 'sim', '-s', '-r', str(WORLD)], env=env,
                            stdout=log, stderr=subprocess.STDOUT)

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
        if 'bluerov2' in out:
            return env
        time.sleep(2)
    fail('model never appeared in the world')


def test_model_loaded(sim):
    """#11: the composed model is in the world."""
    _, out = gz(sim, 'model', '--list')
    assert 'bluerov2' in out


def test_interfaces_advertised(sim):
    """#11: thruster commands and sensor topics are advertised."""
    deadline = time.time() + 30
    needed = ('/model/bluerov2/joint/thruster1_joint/cmd_thrust',
              '/model/bluerov2/joint/thruster6_joint/cmd_thrust',
              f'/world/{WORLD_NAME}/clock')
    while time.time() < deadline:
        _, out = gz(sim, 'topic', '-l')
        if all(topic in out for topic in needed):
            return
        time.sleep(2)
    pytest.fail(f'missing topics; last listing:\n{out}')


def test_physics_steps(sim):
    """#11: simulation iterations advance (systems survive stepping)."""
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


def test_camera_renders(sim):
    """#12: camera publishes an image if a render path exists (else skip)."""
    code, out = gz(sim, 'topic', '-e', '-t', '/bluerov2/camera/image',
                   '-n', '1', timeout=30)
    if code != 0 or 'data' not in out:
        pytest.skip('no image (no usable render engine on this host)')
    assert 'width: 1920' in out


def test_vehicle_slightly_positively_buoyant(sim):
    """Submerged, the near-neutral trim rises slowly: the sizing holds in sim."""
    teleport(sim, 0, 0, -3.0)
    time.sleep(3)                      # let the relocation transient damp out
    z0 = model_pose(sim)[2]
    time.sleep(8)
    z1 = model_pose(sim)[2]
    rate = (z1 - z0) / 8.0
    assert 0.001 < rate < 0.10, (
        f'rise rate {rate:.4f} m/s outside the near-neutral band '
        f'(z {z0:.3f} -> {z1:.3f})')


def test_forward_thrust_mix_surges(sim):
    """
    The vectored surge mix drives the vehicle forward, not sideways.

    The four commands go out in parallel: thrust commands latch, so bringing
    thrusters up one at a time applies an unbalanced wrench during onset and
    yaws the vehicle off its heading before it translates.
    """
    teleport(sim, 0, 0, -3.0)
    time.sleep(3)
    x0, y0 = model_pose(sim)[:2]
    mix = {1: -10.0, 2: -10.0, 3: 10.0, 4: 10.0}
    for _ in range(6):    # repeats: one-shot pubs can lose the discovery race
        procs = [subprocess.Popen(
            ['gz', 'topic', '-t',
             f'/model/bluerov2/joint/thruster{n}_joint/cmd_thrust',
             '-m', 'gz.msgs.Double', '-p', f'data: {value}'],
            env=sim, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for n, value in mix.items()]
        for proc in procs:
            proc.wait(timeout=20)
    time.sleep(8)
    x1, y1, _, _, _, yaw = model_pose(sim)
    dx, dy = x1 - x0, y1 - y0
    assert dx > 0.5, f'no surge: moved ({dx:+.2f}, {dy:+.2f}) m'
    assert dx > 2.5 * abs(dy), f'sideways drift: ({dx:+.2f}, {dy:+.2f}) m'
    assert abs(yaw) < 0.35, f'yawed {yaw:+.2f} rad under a torque-free mix'
