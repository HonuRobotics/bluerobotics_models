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

_SCRIPT = (Path(get_package_prefix('bluerov2_gazebo'))
           / 'lib' / 'bluerov2_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)

ALWAYS = {'/clock', '/joint_states'}
PROPS = [('t200_prop_ccw', 'thruster_1'), ('t200_prop_cw', 'thruster_3')]


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
    assert set(entries) == ALWAYS | {'/bluerov2/thruster_1/thrust', '/bluerov2/thruster_3/thrust'}
    one = entries['/bluerov2/thruster_1/thrust']
    assert one['direction'] == 'ROS_TO_GZ'
    assert one['ros_type_name'] == 'std_msgs/msg/Float64'
    # Same name on the gz side: model.sdf.xacro gives the Thruster this <topic>.
    assert one['gz_topic_name'] == '/bluerov2/thruster_1/thrust'


def test_sensor_and_claw_parts_bridge_their_topics():
    """Camera, DVL and claw instances produce their entries, named after them."""
    instances = [('explorehd_camera', 'camera'), ('dvl_a50', 'dvl'),
                 ('newton_gripper', 'gripper'), ('marinesitu_c3', 'stereo'),
                 ('ping360', 'sonar')]
    entries = entries_for({}, instances)
    assert entries['/bluerov2/camera/image']['lazy'] is True
    assert '/bluerov2/camera/camera_info' in entries
    dvl = entries['/bluerov2/dvl/velocity']
    assert dvl['ros_type_name'] == 'marine_acoustic_msgs/msg/Dvl'
    grip = entries['/bluerov2/gripper/cmd_pos']
    assert grip['direction'] == 'ROS_TO_GZ' and 'lazy' not in grip
    assert '/bluerov2/stereo/points' in entries
    assert '/bluerov2/sonar/scan' in entries


def test_geometry_only_parts_produce_nothing():
    """Parts without a sensor model add no bridge entries."""
    instances = [('bluerov2_flag', 'flag'), ('bluerov2_antenna_mast', 'mast'),
                 ('omniscan_450_sidescan', 'sidescan'), ('surveyor_multibeam', 'multibeam')]
    assert set(entries_for({}, instances)) == ALWAYS


def test_topic_override_precedence():
    """Gz_topic/ros_topic > topic > /<namespace>/<name>, matched by instance."""
    cfg = {'topic_namespace': 'rov_a', 'parts': [
        {'slot': 'camera', 'type': 'explorehd_camera',
         'gz_topic': 'rov_a/cam_raw', 'ros_topic': '/sensors/cam'}]}
    entries = entries_for(cfg, [('explorehd_camera', 'camera')] + PROPS)
    cam = entries['/sensors/cam/image']
    assert cam['gz_topic_name'] == '/rov_a/cam_raw/image'
    assert '/rov_a/thruster_1/thrust' in entries
    # A renamed occupant is matched by its name, not the slot.
    cfg = {'parts': [{'slot': 'camera', 'type': 'explorehd_camera',
                      'name': 'cam', 'topic': 'eye'}]}
    assert '/eye/image' in entries_for(cfg, [('explorehd_camera', 'cam')])


def test_extra_bridge_topics_verbatim():
    """Extra_bridge_topics entries are appended untouched."""
    extra = {'ros_topic_name': '/odom',
             'gz_topic_name': '/model/bluerov2/odom',
             'ros_type_name': 'nav_msgs/msg/Odometry',
             'gz_type_name': 'gz.msgs.Odometry', 'direction': 'GZ_TO_ROS'}
    cfg = {'parts': [], 'extra_bridge_topics': [dict(extra)]}
    assert entries_for(cfg, [])['/odom'] == extra


def test_cli_rejects_a_config_that_matches_nothing(tmp_path):
    """The generator runs the assembly check: a stray entry fails with the reason."""
    urdf = ('<robot name="x"><assembly_part type="bluerov2_chassis" name="base_link" parent=""/>'
            '<assembly_slot of="base_link" name="dvl"/><link name="base_link"/></robot>')
    (tmp_path / 'v.urdf').write_text(urdf)
    (tmp_path / 'bad.yaml').write_text('parts:\n  - {slot: dvll, type: none}\n')
    out = subprocess.run([sys.executable, str(_SCRIPT), str(tmp_path / 'bad.yaml'),
                          str(tmp_path / 'v.urdf'), str(tmp_path / 'out.yaml')],
                         capture_output=True, text=True)
    assert out.returncode != 0 and "'dvll' of 'base_link'" in out.stderr, out.stderr
    assert not (tmp_path / 'out.yaml').exists()
