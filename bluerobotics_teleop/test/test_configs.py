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
from bluerobotics_teleop.instance import default_name, node_params, under
import pytest
import yaml

TELEOP = Path(get_package_share_directory('bluerobotics_teleop'))
AXES = ('linear_x', 'linear_y', 'linear_z', 'angular_z')


def mixer_params(vehicle):
    with open(TELEOP / 'config' / vehicle / 'mixer.yaml') as f:
        return yaml.safe_load(f)['twist_to_thrust']['ros__parameters']


@pytest.mark.parametrize('vehicle', ['bluerov2', 'bluerov2_heavy', 'blueboat'])
def test_mixer_speaks_the_normalized_interface(vehicle):
    """
    Every mixer commands a normalized value, and declares a unity envelope.

    This covers bluerov2_heavy, which has no Gazebo package of its own and so
    cannot be checked against a generated bridge config below. Its topics went
    stale precisely because nothing asserted this.

    The envelope being 1.0 is the point rather than a formality: the thrust
    limits belong to the model now, and a mixer carrying newtons again would
    mean two copies of them free to drift apart.
    """
    params = mixer_params(vehicle)
    for topic in params['thruster_topics']:
        assert topic.endswith('/cmd'), (vehicle, topic)
        assert not topic.startswith('/'), (
            vehicle, topic, 'relative: the launch namespace names the instance')
    assert params['max_thrust_forward'] == 1.0, vehicle
    assert params['max_thrust_reverse'] == -1.0, vehicle


@pytest.mark.parametrize('vehicle,gazebo_pkg', [
    ('bluerov2', 'bluerov2_gazebo'),
    ('blueboat', 'blueboat_gazebo'),
])
def test_mixer_topics_exist_in_the_bridge(vehicle, gazebo_pkg):
    """
    Every mixer output, under the default name, is a thruster topic the bridge carries.

    Both vehicles command their thrusters with a normalized value on `/cmd`,
    not a force on `/thrust`; the newtons live in the model. The installed
    bridge config is generated for the vehicle's default name, which is the
    namespace the teleop launch binds to by default.
    """
    params = mixer_params(vehicle)
    params['thruster_topics'] = [under(default_name(vehicle), topic)
                                 for topic in params['thruster_topics']]
    bridge_yaml = (Path(get_package_share_directory(gazebo_pkg))
                   / 'config' / 'ros_gz_bridge.yaml')
    with open(bridge_yaml) as f:
        entries = yaml.safe_load(f)
    bridged = {e['ros_topic_name'] for e in entries
               if e['direction'] == 'ROS_TO_GZ'
               and e['gz_topic_name'].endswith('/cmd')}
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


def pad_params(name, node):
    with open(TELEOP / 'config' / 'pad' / name) as f:
        return yaml.safe_load(f)[node]['ros__parameters']


def test_pad_mapping_is_shared_and_complete():
    """One pad mapping serves every vehicle: all axes present, sane values."""
    ttj = pad_params('joystick.config.yaml', 'teleop_twist_joy_node')
    for key in ('x', 'y', 'z'):
        assert isinstance(ttj['axis_linear'][key], int), key
        assert abs(ttj['scale_linear'][key]) == 1.0, key
    assert isinstance(ttj['axis_angular']['yaw'], int)
    assert (TELEOP / 'config' / 'pad' / 'twist_to_thrust.yaml').is_file()


def test_pad_deadman_agrees_between_the_two_files():
    """teleop_twist_joy's enable button and the mixer's deadman are one."""
    ttj = pad_params('joystick.config.yaml', 'teleop_twist_joy_node')
    ttt = pad_params('twist_to_thrust.yaml', 'twist_to_thrust')
    assert ttj['enable_button'] == ttt['btn_deadman']


def test_pad_epa_axis_is_not_a_motion_axis():
    """The EPA clicks cannot share an axis with surge, sway, heave or yaw."""
    ttj = pad_params('joystick.config.yaml', 'teleop_twist_joy_node')
    ttt = pad_params('twist_to_thrust.yaml', 'twist_to_thrust')
    motion = set(ttj['axis_linear'].values()) | {ttj['axis_angular']['yaw']}
    assert ttt['axis_epa'] not in motion


def test_no_per_vehicle_pad_configs_remain():
    """Pad truth lives only in config/pad; vehicles keep the mixer alone."""
    for vehicle in ('bluerov2', 'bluerov2_heavy', 'blueboat'):
        files = {p.name for p in (TELEOP / 'config' / vehicle).iterdir()}
        assert files == {'mixer.yaml'}, (vehicle, files)


def test_pad_resolution_prefers_the_user_mapping(tmp_path, monkeypatch):
    """$ROS_HOME mapping wins when present; shipped defaults otherwise."""
    from bluerobotics_teleop import pad_paths
    monkeypatch.setenv('ROS_HOME', str(tmp_path))
    shipped = str(TELEOP / 'config' / 'pad' / 'joystick.config.yaml')
    assert pad_paths.resolve_pad_file('joystick.config.yaml') == shipped
    user_dir = tmp_path / 'bluerobotics_teleop' / 'pad'
    user_dir.mkdir(parents=True)
    user = user_dir / 'joystick.config.yaml'
    user.write_text('teleop_twist_joy_node: {ros__parameters: {}}\n')
    assert pad_paths.resolve_pad_file('joystick.config.yaml') == str(user)
    assert pad_paths.resolve_pad_file('twist_to_thrust.yaml') == str(
        TELEOP / 'config' / 'pad' / 'twist_to_thrust.yaml')


def test_default_names_are_the_sim_launch_names():
    """Without name:=, teleop binds to the instance the vehicle's own launch spawns."""
    assert default_name('blueboat') == 'blueboat'
    assert default_name('bluerov2') == 'bluerov2'
    assert default_name('bluerov2_heavy') == 'bluerov2'
    with pytest.raises(KeyError):
        default_name('wamv')


def test_under_puts_a_relative_topic_in_the_instance():
    assert under('boat_b', 'motor_port/cmd') == '/boat_b/motor_port/cmd'
    assert under('boat_b', '/motor_port/cmd') == '/boat_b/motor_port/cmd'


def test_node_params_reads_the_bare_node_key():
    """The launch hands a file's values to the node, whatever its namespace."""
    params = node_params(TELEOP / 'config' / 'blueboat' / 'mixer.yaml', 'twist_to_thrust')
    assert params['thruster_topics'] == ['motor_port/cmd', 'motor_stbd/cmd']
    params = node_params(TELEOP / 'config' / 'pad' / 'joystick.config.yaml',
                         'teleop_twist_joy_node')
    assert params['enable_button'] == 5
