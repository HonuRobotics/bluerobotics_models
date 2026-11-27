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
End-to-end test of the sonar chain: the imaging walkthrough, headless.

sim.launch.xml with bluerov2_sonar.yaml in gz_sonar's sonar_imaging world:
the generated model carries the ECHO, the world's sonar system pings it on
the Sensors system's rendering thread, and kai_sonar_bridge, started because
the vehicle has a sonar, publishes marine_acoustic_msgs/ProjectedSonarImage.
The other tests check the generated model and the bridge's parameters; this
one waits for the message itself.
"""

import functools
import os
from pathlib import Path
import signal
import uuid

from ament_index_python.packages import get_package_share_directory
from conftest import launch_sim, make_cli, stop_process_group
import pytest

TOPIC = '/bluerov2/sonar_forward/image'
WORLD = Path(get_package_share_directory('gz_sonar')) / 'worlds' / 'sonar_imaging.sdf'
CONFIG = (Path(get_package_share_directory('bluerov2_description')) / 'config'
          / 'bluerov2_sonar.yaml')
LAUNCH = ['ros2', 'launch', 'bluerov2_gazebo', 'sim.launch.xml', 'gui:=false',
          f'world:={WORLD}', f'config_file:={CONFIG}']

ros = make_cli('ros2', default_timeout=15)


@pytest.fixture(scope='module')
def sim(request):
    """Bring up the imaging walkthrough headless on isolated domains; return the env."""
    env = dict(os.environ,
               GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}',
               # Domains 34 to 66: each launch test of this repository has a band
               # of its own, so two of them running at once never share a domain.
               ROS_DOMAIN_ID=str(os.getpid() % 33 + 34))
    return launch_sim(
        request, 'ros2 launch', LAUNCH, env,
        ready=lambda e: TOPIC in ros(e, 'topic', 'list')[1],
        stop=functools.partial(stop_process_group, sig=signal.SIGINT, grace=20))


def test_sonar_image_arrives(sim):
    """A ProjectedSonarImage arrives on the ROV's topic, stamped in its acoustic frame."""
    code, out, err = ros(sim, 'topic', 'type', TOPIC)
    assert out.strip() == 'marine_acoustic_msgs/msg/ProjectedSonarImage', out + err
    code, out, err = ros(sim, 'topic', 'echo', TOPIC, '--once', '--no-arr', timeout=60)
    assert code == 0, f'no sonar image on {TOPIC}\n{err}'
    assert 'frame_id: bluerov2/sonar_forward_acoustic' in out, out
