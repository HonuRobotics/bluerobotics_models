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
End-to-end test of sim.launch.xml: the ROS side of the bring-up.

Complements test_gz_launch.py (which pins the model/world contract by running
gz directly): this one exercises the launch machinery itself, i.e. the
composable-node container with gz_server, the generated ros_gz bridge config
and robot_state_publisher, all headless (gui:=false).

Launch runs with -a (every subprocess' output, not just the ones the launch
file marks as screen-visible) and inherits this process' stdout/stderr, so the
whole bring-up log is in the test terminal on pass and fail alike
(CMakeLists.txt runs this file with NOCAPTURE so pytest does not swallow it).
"""

import os
import shutil
import signal
import subprocess
import time
import uuid

import pytest

LAUNCH = ['ros2', 'launch', '--show-all-subprocesses-output',
          'bluerov2_gazebo', 'sim.launch.xml', 'gui:=false']


def banner(message):
    """Mark a boundary in the interleaved launch/test output."""
    # flush: launch writes to the same fds directly, unbuffered.
    print(f'\n===== {message} =====', flush=True)


def ros(env, *args, timeout=15):
    """Run a ros2 CLI command; echo it to the terminal, return (rc, stdout)."""
    command = f'$ ros2 {" ".join(args)}'
    try:
        out = subprocess.run(['ros2', *args], env=env, capture_output=True,
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
    """Bring up sim.launch.xml headless on isolated domains; yield the env."""
    if shutil.which('ros2') is None:
        pytest.skip('ros2 CLI not available')
    env = dict(os.environ,
               GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}',
               ROS_DOMAIN_ID=str(os.getpid() % 100 + 1),
               # Line up the launch/node logs with the test's own output
               # instead of having them arrive in block-buffered chunks.
               PYTHONUNBUFFERED='1',
               RCUTILS_LOGGING_BUFFERED_STREAM='0')
    banner(f'launch starting: {" ".join(LAUNCH)}')
    # Passing no stdout/stderr leaves launch on this process' streams, i.e.
    # writing straight to the terminal.
    proc = subprocess.Popen(LAUNCH, env=env, start_new_session=True)

    def fail(message):
        pytest.fail(f'{message} (launch output is above)')

    def teardown():
        # SIGINT the whole group so ros2 launch shuts its children down.
        try:
            os.killpg(proc.pid, signal.SIGINT)
            proc.wait(timeout=20)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=10)
        banner(f'launch stopped (exit {proc.returncode})')

    request.addfinalizer(teardown)
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            fail('ros2 launch exited during startup')
        _, out = ros(env, 'node', 'list')
        if '/robot_state_publisher' in out:
            return env
        time.sleep(3)
    fail('launch never brought the nodes up')


def test_container_and_nodes_up(sim):
    """The container and its three composed nodes are alive."""
    deadline = time.time() + 30
    needed = ('/ros_gz_container', '/robot_state_publisher', '/ros_gz_bridge')
    while time.time() < deadline:
        _, out = ros(sim, 'node', 'list')
        if all(node in out for node in needed):
            return
        time.sleep(2)
    pytest.fail(f'missing nodes; last listing:\n{out}')


def test_bridge_clock_flows(sim):
    """/clock arrives on the ROS side: the generated bridge config loaded."""
    code, out = ros(sim, 'topic', 'echo', '/clock', '--once', timeout=30)
    assert code == 0 and 'clock' in out, 'no /clock over the bridge'


def test_robot_description_published(sim):
    """robot_state_publisher latched the xacro-expanded URDF."""
    code, out = ros(sim, 'topic', 'echo', '/robot_description', '--once',
                    '--full-length', '--qos-durability', 'transient_local',
                    '--qos-reliability', 'reliable', timeout=30)
    assert code == 0 and 'bluerov2' in out


def test_camera_topic_bridged(sim):
    """The default loadout's camera topics exist on the ROS graph."""
    deadline = time.time() + 30
    while time.time() < deadline:
        _, out = ros(sim, 'topic', 'list')
        if '/bluerov2/camera/image' in out:
            return
        time.sleep(2)
    pytest.fail(f'camera topic not bridged; last listing:\n{out}')
