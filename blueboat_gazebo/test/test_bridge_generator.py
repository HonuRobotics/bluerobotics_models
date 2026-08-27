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
"""Unit tests for the ros_gz bridge config generator (pure Python, no xacro)."""

import importlib.util
from pathlib import Path
import subprocess
import sys

from ament_index_python.packages import get_package_prefix  # noqa: I100

_SCRIPT = (Path(get_package_prefix('blueboat_gazebo'))
           / 'lib' / 'blueboat_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)

ALWAYS = {'/clock', '/joint_states'}
PROPS = [('m200_weedless_prop_ccw', 'motor_port'), ('m200_weedless_prop_cw', 'motor_stbd')]


def entries_for(cfg, instances):
    """Run the generator and index the entries by ros topic."""
    entries = bridge_gen.bridge_entries(cfg, instances)
    return {e['ros_topic_name']: e for e in entries}


def test_only_clock_and_joint_states_without_parts():
    """Nothing is hardcoded: with no parts only /clock and /joint_states remain."""
    assert set(entries_for({}, [])) == ALWAYS


def test_propellers_bridge_their_thrust_command():
    """Each propeller instance gets a ROS_TO_GZ thrust topic named after it."""
    entries = entries_for({}, PROPS)
    assert set(entries) == ALWAYS | {'/blueboat/motor_port/thrust', '/blueboat/motor_stbd/thrust'}
    port = entries['/blueboat/motor_port/thrust']
    assert port['direction'] == 'ROS_TO_GZ'
    assert port['ros_type_name'] == 'std_msgs/msg/Float64'
    # Same name on the gz side: model.sdf.xacro gives the Thruster this <topic>.
    assert port['gz_topic_name'] == '/blueboat/motor_port/thrust'
    # A renamed or swapped propeller follows its instance name.
    entries = entries_for({}, [('t200_prop_ccw', 'left')])
    assert '/blueboat/left/thrust' in entries


def test_ping_topics_from_the_manifest():
    """A Ping instance (defaults included) produces its LaserScan entry, lazily."""
    entries = entries_for({}, [('blueboat_chassis', 'base_link'), ('ping_singlebeam', 'ping')])
    ping = entries['/blueboat/ping/range']
    assert ping['ros_type_name'] == 'sensor_msgs/msg/LaserScan'
    assert ping['lazy'] is True


def test_geometry_only_parts_produce_nothing():
    """Parts without a sensor model add no bridge entries."""
    instances = [('blueboat_flag', 'flag'), ('blueboat_antenna_mast', 'mast'),
                 ('omniscan_450_sidescan', 'sidescan'), ('surveyor_multibeam', 'multibeam')]
    assert set(entries_for({}, instances)) == ALWAYS


def test_topic_override_precedence():
    """Gz_topic/ros_topic > topic > /<namespace>/<name>, matched by instance."""
    cfg = {'topic_namespace': 'boat_a', 'parts': [
        {'slot': 'ping', 'of': 'ping_mount', 'type': 'ping_singlebeam',
         'gz_topic': 'boat_a/ping_raw', 'ros_topic': '/sensors/ping'}]}
    entries = entries_for(cfg, [('ping_singlebeam', 'ping')] + PROPS)
    ping = entries['/sensors/ping/range']
    assert ping['gz_topic_name'] == '/boat_a/ping_raw/range'
    assert '/boat_a/motor_port/thrust' in entries
    # A renamed occupant is matched by its name, not the slot.
    cfg = {'parts': [{'slot': 'ping', 'of': 'ping_mount', 'type': 'ping_singlebeam',
                      'name': 'sonar', 'topic': 'echo'}]}
    assert '/echo/range' in entries_for(cfg, [('ping_singlebeam', 'sonar')])


def test_extra_bridge_topics_verbatim():
    """Extra_bridge_topics entries are appended untouched."""
    extra = {'ros_topic_name': '/odom',
             'gz_topic_name': '/model/blueboat/odom',
             'ros_type_name': 'nav_msgs/msg/Odometry',
             'gz_type_name': 'gz.msgs.Odometry', 'direction': 'GZ_TO_ROS'}
    cfg = {'parts': [], 'extra_bridge_topics': [dict(extra)]}
    assert entries_for(cfg, [])['/odom'] == extra


def test_cli_rejects_a_config_that_matches_nothing(tmp_path):
    """The generator runs the assembly check: a stray entry fails with the reason."""
    urdf = ('<robot name="x"><assembly_part type="blueboat_chassis" name="base_link" parent=""/>'
            '<assembly_slot of="base_link" name="mast"/><link name="base_link"/></robot>')
    (tmp_path / 'v.urdf').write_text(urdf)
    (tmp_path / 'bad.yaml').write_text('parts:\n  - {slot: mastt, type: none}\n')
    out = subprocess.run([sys.executable, str(_SCRIPT), str(tmp_path / 'bad.yaml'),
                          str(tmp_path / 'v.urdf'), str(tmp_path / 'out.yaml')],
                         capture_output=True, text=True)
    assert out.returncode != 0 and "'mastt' of 'base_link'" in out.stderr, out.stderr
    assert not (tmp_path / 'out.yaml').exists()
