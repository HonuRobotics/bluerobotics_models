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
"""The shipped per vehicle configs agree with the vehicles they drive."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
import pytest
import yaml

TELEOP = Path(get_package_share_directory('bluerobotics_teleop'))
AXES = ('linear_x', 'linear_y', 'linear_z', 'angular_z')


def mixer_params(vehicle):
    with open(TELEOP / 'config' / vehicle / 'mixer.yaml') as f:
        return yaml.safe_load(f)['twist_to_thrust']['ros__parameters']


@pytest.mark.parametrize('vehicle,gazebo_pkg', [
    ('bluerov2', 'bluerov2_gazebo'),
    ('blueboat', 'blueboat_gazebo'),
])
def test_mixer_topics_exist_in_the_bridge(vehicle, gazebo_pkg):
    """Every mixer output is a ROS_TO_GZ thruster topic the bridge carries.

    The two vehicles name it differently on purpose: the BlueBoat's thruster
    takes a normalized command on `/cmd`, the BlueROV2 still takes newtons on
    the stock plugin's `/cmd_thrust`.
    """
    params = mixer_params(vehicle)
    bridge_yaml = (Path(get_package_share_directory(gazebo_pkg))
                   / 'config' / 'ros_gz_bridge.yaml')
    with open(bridge_yaml) as f:
        entries = yaml.safe_load(f)
    bridged = {e['ros_topic_name'] for e in entries
               if e['direction'] == 'ROS_TO_GZ'
               and (e['gz_topic_name'].endswith('/thrust')
                    or e['gz_topic_name'].endswith('/cmd'))}
    assert set(params['thruster_topics']) == bridged


@pytest.mark.parametrize('vehicle', ['bluerov2', 'bluerov2_heavy', 'blueboat'])
def test_mixer_matrix_is_well_formed(vehicle):
    """Every gains column matches the topic list length."""
    params = mixer_params(vehicle)
    n = len(params['thruster_topics'])
    assert n > 0
    for axis in AXES:
        assert len(params[f'gains_{axis}']) == n, axis


def test_rov_surge_and_heave_match_the_verified_sign_sets():
    """The columns reproduce the sign sets the integration tests verified."""
    params = mixer_params('bluerov2')
    assert params['gains_linear_x'][:4] == [-1.0, -1.0, 1.0, 1.0]
    assert params['gains_linear_z'][4:] == [-1.0, -1.0]


def test_boat_mix_is_pure_differential():
    params = mixer_params('blueboat')
    assert params['gains_linear_x'] == [1.0, 1.0]
    assert params['gains_angular_z'] == [-1.0, 1.0]
    assert params['gains_linear_y'] == [0.0, 0.0]
    assert params['gains_linear_z'] == [0.0, 0.0]
