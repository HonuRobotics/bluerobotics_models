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
import re
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

# One entry per catalog type; test_full_config_covers_catalog enforces sync.
FULL_CONFIG = """\
variant: heavy
accessories:
  - {type: explorehd_camera, name: camera,  xyz: "0.22 0 0.05",   rpy: "0 0 0"}
  - {type: marinesitu_c3,    name: stereo,  xyz: "-0.16 0 0.16",  rpy: "0 0 0"}
  - {type: ping360,          name: ping360, xyz: "0.16 0 0.13",   rpy: "0 0 0"}
  - {type: dvl_a50,          name: dvl,     xyz: "-0.12 0 -0.14", rpy: "0 0 0"}
  - {type: sonoptix_echo,    name: sonar_l, xyz: "0.14 0.16 -0.05",  rpy: "0 0 0"}
  - {type: omniscan_450_fs,  name: sonar_r, xyz: "0.14 -0.16 -0.05", rpy: "0 0 0"}
  - {type: newton_gripper,   name: gripper, xyz: "0.28 0 -0.08",  rpy: "0 0 0"}
  - {type: sediment_sampler, name: sampler, xyz: "-0.26 0 -0.06", rpy: "0 0 0"}
  - {type: roof_rack,        name: rack,    xyz: "0 0 0.17",      rpy: "0 0 0"}
  - {type: payload_skid,     name: skid,    xyz: "0 0 -0.17",     rpy: "0 0 0"}
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
    """Plugin and sensor counts track the config; no xacro residue."""
    root, text = xacro(MODEL_XACRO, FULL_CONFIG)
    assert 'xacro:' not in text and 'xmlns:xacro' not in text
    assert len(plugins(root, 'gz-sim-thruster-system')) == 8  # heavy
    assert len(plugins(root, 'gz-sim-hydrodynamics-system')) == 1
    # one controller per claw joint: gripper jaws + sampler cups
    assert len(plugins(root, 'gz-sim-joint-position-controller-system')) == 4
    sensors = list(root.iter('sensor'))
    by_type = {s.get('type') for s in sensors}
    assert by_type == {'camera', 'rgbd_camera', 'gpu_lidar', 'custom'}
    assert len(sensors) == 4  # geometry-only accessories emit nothing
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


def test_sensor_frame_ids_resolve_in_tf():
    """
    #34: every sensor's <frame_id> names a frame TF actually carries.

    header.frame_id is only useful if a consumer can look the frame up. TF comes
    from the URDF via robot_state_publisher, but neither sensor-side name is in
    it: gz's conversion lumps the description's fixed-joint accessory links away,
    and the SDF's own <name>_sensor wrapper links were never in the URDF at all.
    Unset, gz derives the id from the SDF ('bluerov2/camera_sensor/camera'),
    which no lookup_transform can resolve. Pin it to a URDF link name.
    """
    sdf_root, _ = xacro(MODEL_XACRO, FULL_CONFIG)
    urdf_root, _ = xacro(URDF_XACRO, FULL_CONFIG)
    urdf_links = {li.get('name') for li in urdf_root.findall('link')}
    sensors = list(sdf_root.iter('sensor'))
    assert sensors
    for sensor in sensors:
        frame = sensor.find('frame_id')
        assert frame is not None, (
            f'sensor {sensor.get("name")} sets no <frame_id>: gz will derive an '
            f'SDF-scoped id that is absent from TF')
        assert frame.text in urdf_links, (
            f'sensor {sensor.get("name")} publishes frame_id '
            f'{frame.text!r}, which robot_state_publisher never puts in TF')


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
    """Model gz topics equal generated bridge gz topics, by construction."""
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


def test_full_config_covers_catalog():
    """FULL_CONFIG exercises every accessory type the description offers."""
    xacro_text = (DESC_SHARE / 'urdf' / 'accessories.xacro').read_text()
    dict_src = re.search(r'\$\{dict\(([^)]*)\)\}', xacro_text).group(1)
    catalog = set(re.findall(r'(\w+)=', dict_src))
    config_types = {a['type']
                    for a in yaml.safe_load(FULL_CONFIG)['accessories']}
    assert config_types == catalog, (
        f'FULL_CONFIG drift: missing {catalog - config_types}, '
        f'unknown {config_types - catalog}')
