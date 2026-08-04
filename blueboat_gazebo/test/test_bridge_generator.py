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

from ament_index_python.packages import get_package_prefix  # noqa: I100

_SCRIPT = (Path(get_package_prefix('blueboat_gazebo'))
           / 'lib' / 'blueboat_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)


def entries_for(cfg):
    """Run the generator and index the entries by ros topic."""
    entries = bridge_gen.bridge_entries(cfg)
    return {e['ros_topic_name']: e for e in entries}


def accessory(type_name, name, **extra):
    """Build a minimal accessory config entry."""
    return {'type': type_name, 'name': name,
            'xyz': '0 0 0', 'rpy': '0 0 0', **extra}


def test_thrusters_always_bridged():
    """#9: drivetrain thrust commands exist even with no accessories."""
    entries = entries_for({'accessories': []})
    assert set(entries) == {'/clock', '/blueboat/thrusters/port/thrust',
                            '/blueboat/thrusters/stbd/thrust'}
    port = entries['/blueboat/thrusters/port/thrust']
    assert port['direction'] == 'ROS_TO_GZ'
    assert port['gz_topic_name'] == \
        '/model/blueboat/joint/motor_port_joint/cmd_thrust'


def test_ping_sonar_topics():
    """#9: the echosounder produces its LaserScan entry, lazily."""
    entries = entries_for({'accessories': [accessory('ping_sonar', 'ping')]})
    ping = entries['/blueboat/ping/range']
    assert ping['ros_type_name'] == 'sensor_msgs/msg/LaserScan'
    assert ping['lazy'] is True


def test_non_sensor_accessories_produce_nothing():
    """#9: geometry-only accessories add no bridge entries."""
    cfg = {'accessories': [accessory('flag', 'flag'),
                           accessory('antenna_mast', 'mast'),
                           accessory('omniscan_450', 'sidescan'),
                           accessory('surveyor_multibeam', 'multibeam')]}
    assert set(entries_for(cfg)) == {'/clock',
                                     '/blueboat/thrusters/port/thrust',
                                     '/blueboat/thrusters/stbd/thrust'}


def test_topic_override_precedence():
    """#9: gz_topic/ros_topic > topic > /<namespace>/<name>."""
    cfg = {'topic_namespace': 'boat_a', 'accessories': [
        accessory('ping_sonar', 'ping',
                  gz_topic='boat_a/ping_raw', ros_topic='/sensors/ping'),
    ]}
    entries = entries_for(cfg)
    ping = entries['/sensors/ping/range']
    assert ping['gz_topic_name'] == '/boat_a/ping_raw/range'
    assert '/boat_a/thrusters/port/thrust' in entries


def test_extra_bridge_topics_verbatim():
    """#9: extra_bridge_topics entries are appended untouched."""
    extra = {'ros_topic_name': '/odom',
             'gz_topic_name': '/model/blueboat/odom',
             'ros_type_name': 'nav_msgs/msg/Odometry',
             'gz_type_name': 'gz.msgs.Odometry', 'direction': 'GZ_TO_ROS'}
    cfg = {'accessories': [], 'extra_bridge_topics': [dict(extra)]}
    assert entries_for(cfg)['/odom'] == extra
