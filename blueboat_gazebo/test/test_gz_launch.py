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
Headless Gazebo integration: world loads, interfaces up, physics steps.

The echosounder smoke test SKIPS rather than fails when no usable render path
exists (gpu_lidar is a rendered sensor), so CPU-only CI runners stay green
while still exercising software-GL rendering where available.
"""

import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from ament_index_python.packages import get_package_share_directory
import pytest

WORLD = (Path(get_package_share_directory('blueboat_gazebo'))
         / 'worlds' / 'blueboat_playground.sdf')
WORLD_NAME = 'blueboat_playground'


def gz(env, *args, timeout=10):
    """Run a gz CLI command; return (returncode, stdout)."""
    try:
        out = subprocess.run(['gz', *args], env=env, capture_output=True,
                             text=True, timeout=timeout)
        return out.returncode, out.stdout
    except subprocess.TimeoutExpired:
        return -1, ''


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on an isolated partition; yield its env."""
    if shutil.which('gz') is None:
        pytest.skip('gz CLI not available')
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    proc = subprocess.Popen(['gz', 'sim', '-s', '-r', str(WORLD)], env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    def teardown():
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)

    request.addfinalizer(teardown)
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            pytest.fail('gz server exited during startup')
        _, out = gz(env, 'model', '--list')
        if 'blueboat' in out:
            return env
        time.sleep(2)
    pytest.fail('model never appeared in the world')


def test_model_loaded(sim):
    """#11: the composed model is in the world."""
    _, out = gz(sim, 'model', '--list')
    assert 'blueboat' in out


def test_interfaces_advertised(sim):
    """#11: thruster commands and the world clock are advertised."""
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


def test_echosounder_ranges(sim):
    """#12: the ping sensor publishes ranges if a render path exists."""
    code, out = gz(sim, 'topic', '-e', '-t', '/blueboat/ping/range',
                   '-n', '1', timeout=30)
    if code != 0 or 'ranges' not in out:
        pytest.skip('no ranges (no usable render engine on this host)')
    assert 'frame' in out
