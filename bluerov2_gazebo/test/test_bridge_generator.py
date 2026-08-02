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

_SCRIPT = (Path(get_package_prefix('bluerov2_gazebo'))
           / 'lib' / 'bluerov2_gazebo' / 'generate_bridge_config.py')
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


def test_default_camera_only():
    """#9: camera-only config yields exactly clock + image + camera_info."""
    cfg = {'accessories': [accessory('explorehd_camera', 'camera')]}
    entries = entries_for(cfg)
    assert set(entries) == {'/clock', '/bluerov2/camera/image',
                            '/bluerov2/camera/camera_info'}


def test_per_type_topic_sets():
    """#9: each accessory type produces its documented topics and types."""
    cfg = {'accessories': [
        accessory('marinesitu_c3', 'stereo'),
        accessory('dvl_a50', 'dvl'),
        accessory('ping360', 'ping360'),
        accessory('newton_gripper', 'gripper'),
    ]}
    entries = entries_for(cfg)
    for suffix in ('image', 'depth_image', 'points', 'camera_info'):
        assert f'/bluerov2/stereo/{suffix}' in entries
    dvl = entries['/bluerov2/dvl/velocity']
    assert dvl['ros_type_name'] == 'marine_acoustic_msgs/msg/Dvl'
    assert dvl['gz_type_name'] == 'gz.msgs.DVLVelocityTracking'
    assert entries['/bluerov2/ping360/scan']['ros_type_name'] == \
        'sensor_msgs/msg/LaserScan'
    claw = entries['/bluerov2/gripper/cmd_pos']
    assert claw['direction'] == 'ROS_TO_GZ'


def test_non_sensor_accessories_produce_nothing():
    """#9: geometry-only accessories add no bridge entries."""
    cfg = {'accessories': [accessory('roof_rack', 'rack'),
                           accessory('payload_skid', 'skid'),
                           accessory('sonoptix_echo', 'sonoptix'),
                           accessory('omniscan_450_fs', 'omniscan')]}
    assert set(entries_for(cfg)) == {'/clock'}


def test_topic_override_precedence():
    """#9: gz_topic/ros_topic > topic > /<namespace>/<name>."""
    cfg = {'topic_namespace': 'rov_a', 'accessories': [
        accessory('explorehd_camera', 'camera'),
        accessory('ping360', 'ping360', topic='/sonar/front'),
        accessory('dvl_a50', 'dvl',
                  gz_topic='rov_a/dvl_raw', ros_topic='/sensors/dvl'),
    ]}
    entries = entries_for(cfg)
    assert '/rov_a/camera/image' in entries
    front = entries['/sonar/front/scan']
    assert front['gz_topic_name'] == '/sonar/front/scan'
    dvl = entries['/sensors/dvl/velocity']
    assert dvl['gz_topic_name'] == '/rov_a/dvl_raw/velocity'


def test_lazy_default_and_bridge_override():
    """#9: GZ_TO_ROS entries default lazy, clock is eager, bridge: overrides."""
    cfg = {'accessories': [
        accessory('explorehd_camera', 'camera'),
        accessory('ping360', 'ping360',
                  bridge={'lazy': False, 'publisher_queue': 5}),
        accessory('newton_gripper', 'gripper'),
    ]}
    entries = entries_for(cfg)
    assert 'lazy' not in entries['/clock']
    assert entries['/bluerov2/camera/image']['lazy'] is True
    ping = entries['/bluerov2/ping360/scan']
    assert ping['lazy'] is False and ping['publisher_queue'] == 5
    assert 'lazy' not in entries['/bluerov2/gripper/cmd_pos']


def test_extra_bridge_topics_verbatim():
    """#9: extra_bridge_topics entries are appended untouched."""
    extra = {'ros_topic_name': '/thrust1',
             'gz_topic_name': '/model/bluerov2/joint/thruster1_joint/cmd_thrust',
             'ros_type_name': 'std_msgs/msg/Float64',
             'gz_type_name': 'gz.msgs.Double',
             'direction': 'ROS_TO_GZ'}
    cfg = {'accessories': [], 'extra_bridge_topics': [dict(extra)]}
    assert entries_for(cfg)['/thrust1'] == extra
