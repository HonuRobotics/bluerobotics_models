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

The render smoke test (camera image) SKIPS rather than fails when no usable
render path exists, so CPU-only CI runners stay green while still exercising
software-GL rendering where available.

The gz server runs verbose and inherits this process' stdout/stderr, so its
whole log is in the test terminal on pass and fail alike (CMakeLists.txt runs
this file with NOCAPTURE so pytest does not swallow it).
"""

import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from ament_index_python.packages import get_package_share_directory
import pytest

WORLD = (Path(get_package_share_directory('bluerov2_gazebo'))
         / 'worlds' / 'bluerov2_playground.sdf')
WORLD_NAME = 'bluerov2_playground'


def banner(message):
    """Mark a boundary in the interleaved server/test output."""
    # flush: the server writes to the same fds directly, unbuffered.
    print(f'\n===== {message} =====', flush=True)


def gz(env, *args, timeout=10):
    """Run a gz CLI command; echo it to the terminal, return (rc, stdout)."""
    command = f'$ gz {" ".join(args)}'
    try:
        out = subprocess.run(['gz', *args], env=env, capture_output=True,
                             text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f'{command} -> timed out after {timeout}s', flush=True)
        return -1, ''
    # stdout is only echoed by the callers that need it (the polling loops
    # would print the same listing dozens of times); stderr never is otherwise.
    report = f'{command} -> exit {out.returncode}'
    if out.stderr.strip():
        report += f'\n{out.stderr.strip()}'
    print(report, flush=True)
    return out.returncode, out.stdout


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on an isolated partition; yield its env."""
    if shutil.which('gz') is None:
        pytest.skip('gz CLI not available')
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    # -v 4 is gz's most verbose level; passing no stdout/stderr here leaves the
    # server on this process' streams, i.e. writing straight to the terminal.
    command = ['gz', 'sim', '-s', '-r', '-v', '4', str(WORLD)]
    banner(f'gz server starting: {" ".join(command)}')
    proc = subprocess.Popen(command, env=env)

    def fail(message):
        pytest.fail(f'{message} (gz server output is above)')

    def teardown():
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        banner(f'gz server stopped (exit {proc.returncode})')

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
