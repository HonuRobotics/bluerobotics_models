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

import functools
import os
import signal
import uuid

from conftest import launch_sim, make_cli, poll_until, stop_process_group
import pytest

LAUNCH = ['ros2', 'launch', 'bluerov2_gazebo', 'sim.launch.xml', 'gui:=false']

ros = make_cli('ros2', default_timeout=15)


@pytest.fixture(scope='module')
def sim(request):
    """Bring up sim.launch.xml headless on isolated domains; yield the env."""
    env = dict(os.environ,
               GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}',
               ROS_DOMAIN_ID=str(os.getpid() % 100 + 1))
    # SIGINT first so ros2 launch shuts its children down in order.
    return launch_sim(
        request, 'ros2 launch', LAUNCH, env,
        ready=lambda e: '/robot_state_publisher' in ros(e, 'node', 'list')[1],
        stop=functools.partial(stop_process_group,
                               sig=signal.SIGINT, grace=20))


def test_container_and_nodes_up(sim):
    """The container and its three composed nodes are alive."""
    needed = ('/ros_gz_container', '/robot_state_publisher', '/ros_gz_bridge')
    poll_until(
        lambda: all(n in ros(sim, 'node', 'list')[1] for n in needed), 30,
        lambda: f'missing nodes; last listing:\n{ros(sim, "node", "list")[1]}')


def test_bridge_clock_flows(sim):
    """/clock arrives on the ROS side: the generated bridge config loaded."""
    code, out, err = ros(sim, 'topic', 'echo', '/clock', '--once', timeout=30)
    assert code == 0 and 'clock' in out, f'no /clock over the bridge\n{err}'


def test_robot_description_published(sim):
    """robot_state_publisher latched the xacro-expanded URDF."""
    code, out, err = ros(sim, 'topic', 'echo', '/robot_description', '--once',
                         '--full-length', '--qos-durability', 'transient_local',
                         '--qos-reliability', 'reliable', timeout=30)
    assert code == 0 and 'bluerov2' in out, f'no latched description\n{err}'


def test_camera_topic_bridged(sim):
    """The default loadout's camera topics exist on the ROS graph."""
    poll_until(
        lambda: '/bluerov2/camera/image' in ros(sim, 'topic', 'list')[1], 30,
        lambda: 'camera topic not bridged; last listing:\n'
                f'{ros(sim, "topic", "list")[1]}')
