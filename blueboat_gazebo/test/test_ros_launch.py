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
"""

import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

import pytest

LAUNCH = ['ros2', 'launch', 'blueboat_gazebo', 'sim.launch.xml', 'gui:=false']


def ros(env, *args, timeout=15):
    """Run a ros2 CLI command; return (returncode, stdout)."""
    try:
        out = subprocess.run(['ros2', *args], env=env, capture_output=True,
                             text=True, timeout=timeout)
        return out.returncode, out.stdout
    except subprocess.TimeoutExpired:
        return -1, ''


@pytest.fixture(scope='module')
def sim(request):
    """Bring up sim.launch.xml headless on isolated domains; yield the env."""
    if shutil.which('ros2') is None:
        pytest.fail('ros2 CLI not available: the launch suite cannot run')
    env = dict(os.environ,
               GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}',
               ROS_DOMAIN_ID=str(os.getpid() % 100 + 1))
    log = tempfile.NamedTemporaryFile('w+', suffix='.log', delete=False,
                                      prefix='ros_launch_')
    proc = subprocess.Popen(LAUNCH, env=env, start_new_session=True,
                            stdout=log, stderr=subprocess.STDOUT)

    def fail(message):
        log.flush()
        tail = ''.join(open(log.name).readlines()[-40:])
        pytest.fail(f'{message}\nlast launch output ({log.name}):\n{tail}')

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
        # Always surface the launch output: warnings matter even when every
        # assertion passed, and exit codes underreport partial failures.
        log.flush()
        tail = ''.join(open(log.name).readlines()[-60:])
        print(f'\n--- ros2 launch output tail ({log.name}) ---\n{tail}')

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
    """The container and its composed nodes are alive."""
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
    assert code == 0 and 'blueboat' in out


def test_thruster_and_ping_topics_bridged(sim):
    """Thrust commands and the echosounder exist on the ROS graph."""
    deadline = time.time() + 30
    needed = ('/blueboat/thrusters/port/thrust',
              '/blueboat/thrusters/stbd/thrust',
              '/blueboat/ping/range')
    while time.time() < deadline:
        _, out = ros(sim, 'topic', 'list')
        if all(topic in out for topic in needed):
            return
        time.sleep(2)
    pytest.fail(f'missing bridged topics; last listing:\n{out}')
