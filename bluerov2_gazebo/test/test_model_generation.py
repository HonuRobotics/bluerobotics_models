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
import yaml

GZ_SHARE = Path(get_package_share_directory('bluerov2_gazebo'))
DESC_SHARE = Path(get_package_share_directory('bluerov2_description'))
MODEL_XACRO = GZ_SHARE / 'model.sdf.xacro'
URDF_XACRO = DESC_SHARE / 'urdf' / 'bluerov2.urdf.xacro'

_SCRIPT = (Path(get_package_prefix('bluerov2_gazebo'))
           / 'lib' / 'bluerov2_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)

FULL_CONFIG = """\
variant: heavy
accessories:
  - {type: explorehd_camera, name: camera,  xyz: "0.22 0 0.05",   rpy: "0 0 0"}
  - {type: marinesitu_c3,    name: stereo,  xyz: "-0.16 0 0.16",  rpy: "0 0 0"}
  - {type: ping360,          name: ping360, xyz: "0.16 0 0.13",   rpy: "0 0 0"}
  - {type: dvl_a50,          name: dvl,     xyz: "-0.12 0 -0.14", rpy: "0 0 0"}
  - {type: newton_gripper,   name: gripper, xyz: "0.28 0 -0.08",  rpy: "0 0 0"}
  - {type: roof_rack,        name: rack,    xyz: "0 0 0.17",      rpy: "0 0 0"}
"""

RGBD_SUFFIXES = ('image', 'depth_image', 'points', 'camera_info')


def xacro(top_file, config_text):
    """Run xacro with a temp config; return the parsed XML root."""
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
    assert len(plugins(root, 'gz-sim-thruster-system')) == 8  # heavy
    assert len(plugins(root, 'gz-sim-hydrodynamics-system')) == 1
    assert len(plugins(root, 'gz-sim-joint-position-controller-system')) == 2
    sensors = list(root.iter('sensor'))
    by_type = {s.get('type') for s in sensors}
    assert by_type == {'camera', 'rgbd_camera', 'gpu_lidar', 'custom'}
    assert len(sensors) == 4  # roof_rack emits nothing
    std_root, _ = xacro(MODEL_XACRO, 'variant: standard\naccessories: []\n')
    assert len(plugins(std_root, 'gz-sim-thruster-system')) == 6
    assert not list(std_root.iter('sensor'))


def test_plugin_references_survive_lumping():
    """
    #8: plugin joint/link refs exist in the POST-lumping converted model.

    gz's URDF conversion lumps fixed joints away (their child links merge into
    the parent), so validating against the raw URDF is not enough: a plugin
    referencing a fixed joint would pass there yet fail at runtime. Convert the
    URDF the way gz does (gz sdf -p) and check against the survivors.
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
        return  # raw-URDF check only where the gz CLI is unavailable
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
    """Collect the gz-side topics the model advertises/subscribes."""
    topics = set()
    for sensor in root.iter('sensor'):
        base = sensor.find('topic').text
        if sensor.get('type') == 'rgbd_camera':
            topics |= {f'{base}/{s}' for s in RGBD_SUFFIXES}
        else:
            topics.add(base)
    for info in root.iter('camera_info_topic'):
        topics.add(info.text)
    for plugin in plugins(root, 'gz-sim-joint-position-controller-system'):
        topics.add(plugin.find('topic').text)
    return {t if t.startswith('/') else '/' + t for t in topics}


def test_sensor_and_bridge_topics_agree():
    """#10: model gz topics == generated bridge gz topics, by construction."""
    configs = [
        FULL_CONFIG,
        (DESC_SHARE / 'config' / 'bluerov2.yaml').read_text(),
        FULL_CONFIG.replace('variant: heavy',
                            'variant: standard\ntopic_namespace: rov_a'),
    ]
    for config in configs:
        root, _ = xacro(MODEL_XACRO, config)
        entries = bridge_gen.bridge_entries(yaml.safe_load(config))
        bridge_topics = {e['gz_topic_name'] for e in entries} - {'/clock'}
        assert sdf_gz_topics(root) == bridge_topics
