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
import tempfile

from ament_index_python.packages import get_package_prefix  # noqa: I100

_SCRIPT = (Path(get_package_prefix('blueboat_gazebo'))
           / 'lib' / 'blueboat_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)

DRIVETRAIN = {'/clock', '/joint_states',
              '/blueboat/thrusters/port/thrust', '/blueboat/thrusters/stbd/thrust'}


def entries_for(cfg, instances):
    """Run the generator and index the entries by ros topic."""
    entries = bridge_gen.bridge_entries(cfg, instances)
    return {e['ros_topic_name']: e for e in entries}


def test_thrusters_always_bridged():
    """Drivetrain thrust commands exist even with no parts."""
    entries = entries_for({}, [])
    assert set(entries) == DRIVETRAIN
    port = entries['/blueboat/thrusters/port/thrust']
    assert port['direction'] == 'ROS_TO_GZ'
    assert port['gz_topic_name'] == \
        '/model/blueboat/joint/motor_port_joint/cmd_thrust'


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
    assert set(entries_for({}, instances)) == DRIVETRAIN


def test_topic_override_precedence():
    """Gz_topic/ros_topic > topic > /<namespace>/<name>, matched by instance."""
    cfg = {'topic_namespace': 'boat_a', 'parts': [
        {'slot': 'ping', 'on': 'ping_mount', 'type': 'ping_singlebeam',
         'gz_topic': 'boat_a/ping_raw', 'ros_topic': '/sensors/ping'}]}
    entries = entries_for(cfg, [('ping_singlebeam', 'ping')])
    ping = entries['/sensors/ping/range']
    assert ping['gz_topic_name'] == '/boat_a/ping_raw/range'
    assert '/boat_a/thrusters/port/thrust' in entries
    # A renamed occupant is matched by its name, not the slot.
    cfg = {'parts': [{'slot': 'ping', 'on': 'ping_mount', 'type': 'ping_singlebeam',
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


def test_instances_from_urdf_manifest():
    """The manifest elements of an assembled URDF become (type, name) pairs."""
    urdf = ('<robot name="x"><assembly_part type="blueboat_chassis" name="base_link" parent=""/>'
            '<assembly_part type="ping_singlebeam" name="ping" parent="ping_mount_ping"/>'
            '<link name="base_link"/></robot>')
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(urdf)
        path = f.name
    assert bridge_gen.instances_from_urdf(path) == [
        ('blueboat_chassis', 'base_link'), ('ping_singlebeam', 'ping')]
