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
"""Generation tests for the composed model: plugins, cross-refs, bridge accord."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import (get_package_prefix,
                                         get_package_share_directory)
import pytest
import yaml

GZ_SHARE = Path(get_package_share_directory('blueboat_gazebo'))
DESC_SHARE = Path(get_package_share_directory('blueboat_description'))
MODEL_XACRO = GZ_SHARE / 'model.sdf.xacro'
URDF_XACRO = DESC_SHARE / 'urdf' / 'blueboat.urdf.xacro'

_SCRIPT = (Path(get_package_prefix('blueboat_gazebo'))
           / 'lib' / 'blueboat_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)

FULL_CONFIG = """\
accessories:
  - {type: ping_sonar,         name: ping,      xyz: "0 0 -0.05",    rpy: "0 0 0"}
  - {type: flag,               name: flag,      xyz: "-0.3 0 -0.08", rpy: "0 0 0"}
  - {type: antenna_mast,       name: mast,      xyz: "-0.35 0 0.45", rpy: "0 0 0"}
  - {type: surveyor_multibeam, name: multibeam, xyz: "0.35 0 -0.08", rpy: "0 0 0"}
"""


def xacro(top_file, config_text):
    """Run xacro with a temp config; return the parsed XML root and text."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        ['xacro', str(top_file), f'config_file:={config_path}'],
        check=True, capture_output=True, text=True, timeout=60)
    return ET.fromstring(out.stdout), out.stdout


def plugins(root, filename):
    """Return the plugin elements with the given filename attribute."""
    return [p for p in root.iter('plugin') if p.get('filename') == filename]


def test_model_generation_follows_config():
    """#7: plugin/sensor counts track the config; no xacro residue."""
    root, text = xacro(MODEL_XACRO, FULL_CONFIG)
    assert 'xacro:' not in text and 'xmlns:xacro' not in text
    assert len(plugins(root, 'gz-sim-thruster-system')) == 2
    assert len(plugins(root, 'gz-sim-hydrodynamics-system')) == 1
    sensors = list(root.iter('sensor'))
    assert {s.get('type') for s in sensors} == {'gpu_lidar'}
    assert len(sensors) == 1  # only the echosounder emits a sensor
    empty_root, _ = xacro(MODEL_XACRO, 'accessories: []\n')
    assert not list(empty_root.iter('sensor'))
    assert len(plugins(empty_root, 'gz-sim-thruster-system')) == 2


def test_plugin_references_survive_lumping():
    """
    #8: plugin joint/link refs exist in the POST-lumping converted model.

    gz's URDF conversion lumps fixed joints away, so references must be
    validated against the converted model, not the raw URDF.
    """
    sdf_root, _ = xacro(MODEL_XACRO, FULL_CONFIG)
    urdf_root, urdf_text = xacro(URDF_XACRO, FULL_CONFIG)
    joint_refs = {ref.text for ref in sdf_root.iter('joint_name')}
    link_refs = {ref.text for ref in sdf_root.iter('link_name')}
    urdf_joints = {j.get('name') for j in urdf_root.findall('joint')}
    urdf_links = {li.get('name') for li in urdf_root.findall('link')}
    assert joint_refs <= urdf_joints
    assert link_refs <= urdf_links
    if shutil.which('gz') is None:
        pytest.skip('gz CLI unavailable: post-lumping check cannot run')
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(urdf_text)
        urdf_path = f.name
    out = subprocess.run(['gz', 'sdf', '-p', urdf_path], check=True,
                         capture_output=True, text=True, timeout=60)
    converted = ET.fromstring(out.stdout)
    surviving_joints = {j.get('name') for j in converted.iter('joint')}
    surviving_links = {li.get('name') for li in converted.iter('link')}
    assert joint_refs <= surviving_joints, (
        f'plugin joints lumped away: {joint_refs - surviving_joints}')
    assert link_refs <= surviving_links, (
        f'plugin links lumped away: {link_refs - surviving_links}')


def sdf_gz_topics(root):
    """Collect the gz-side topics the model's sensors declare."""
    topics = {sensor.find('topic').text for sensor in root.iter('sensor')}
    return {t if t.startswith('/') else '/' + t for t in topics}


def test_sensor_and_bridge_topics_agree():
    """#10: model gz topics == generated bridge gz topics, by construction."""
    configs = [
        FULL_CONFIG,
        (DESC_SHARE / 'config' / 'blueboat.yaml').read_text(),
        FULL_CONFIG + 'topic_namespace: boat_a\n',
    ]
    for config in configs:
        root, _ = xacro(MODEL_XACRO, config)
        entries = bridge_gen.bridge_entries(yaml.safe_load(config))
        bridge_topics = {e['gz_topic_name'] for e in entries
                         if e['gz_topic_name'] != '/clock'
                         and not e['gz_topic_name'].endswith('/cmd_thrust')}
        assert sdf_gz_topics(root) == bridge_topics
