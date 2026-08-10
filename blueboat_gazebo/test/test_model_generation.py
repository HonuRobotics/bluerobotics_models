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

# One entry per catalog type; test_full_config_covers_catalog enforces sync.
FULL_CONFIG = """\
accessories:
  - {type: ping_sonar,          name: ping,      xyz: "0 0 -0.05",     rpy: "0 0 0"}
  - {type: ping_mount,          name: mount,     xyz: "0 0 -0.02",     rpy: "0 0 0"}
  - {type: flag,                name: flag,      xyz: "-0.3 0 -0.08",  rpy: "0 0 0"}
  - {type: antenna_mast,        name: mast,      xyz: "-0.35 0 0.45",  rpy: "0 0 0"}
  - {type: basestation_antenna, name: radio,     xyz: "-0.30 0 0.10",  rpy: "0 0 0"}
  - {type: payload_bracket,     name: bracket,   xyz: "0.10 0 0.05",   rpy: "0 0 0"}
  - {type: omniscan_450,        name: omniscan,  xyz: "0.30 0 -0.10",  rpy: "0 0 0"}
  - {type: surveyor_multibeam,  name: multibeam, xyz: "0.35 0 -0.08",  rpy: "0 0 0"}
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
    """Plugin and sensor counts track the config; no xacro residue."""
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


def test_installed_model_sdf_carries_the_specs_comment():
    """The stamped model.sdf repeats the URDF specs; the masses agree."""
    text = (GZ_SHARE / 'model.sdf').read_text()
    assert 'model specs' in text, 'installed model.sdf is not stamped'
    match = re.search(r'^  total mass: +([\d.]+) kg', text, re.M)
    assert match, 'specs comment misses the total mass row'
    urdf_root = ET.parse(DESC_SHARE / 'urdf' / 'blueboat.urdf').getroot()
    total = sum(float(m.get('value'))
                for m in urdf_root.findall('.//inertial/mass'))
    assert float(match.group(1)) == pytest.approx(total, abs=5e-4)


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
    """
    Model gz topics equal generated bridge gz topics, by construction.

    Fixed entries (clock, joint states, thrusters) and extra_bridge_topics
    pass through untouched; everything else must match a model sensor topic.
    """
    extra = {
        'ros_topic_name': '/diagnostics', 'gz_topic_name': '/diagnostics',
        'ros_type_name': 'std_msgs/msg/Empty', 'gz_type_name': 'gz.msgs.Empty',
        'direction': 'GZ_TO_ROS'}
    configs = [
        FULL_CONFIG,
        (DESC_SHARE / 'config' / 'blueboat.yaml').read_text(),
        FULL_CONFIG + 'topic_namespace: boat_a\n',
    ]
    for config in configs:
        cfg = yaml.safe_load(config)
        cfg.setdefault('extra_bridge_topics', []).append(extra)
        entries = bridge_gen.bridge_entries(cfg)
        assert extra in entries, 'extra_bridge_topics dropped'
        ns = cfg.get('topic_namespace', 'blueboat')
        fixed = {'/clock', f'/{ns}/joint_states', extra['gz_topic_name']}
        bridge_topics = {e['gz_topic_name'] for e in entries
                         if e['gz_topic_name'] not in fixed
                         and not e['gz_topic_name'].endswith('/cmd_thrust')}
        root, _ = xacro(MODEL_XACRO, config)
        assert sdf_gz_topics(root) == bridge_topics


def test_full_config_covers_catalog():
    """FULL_CONFIG exercises every accessory type the description offers."""
    xacro_text = (DESC_SHARE / 'urdf' / 'accessories.xacro').read_text()
    catalog = set(re.findall(r'<xacro:macro name="([a-z]\w*)"', xacro_text))
    catalog -= {'mount_accessories'}
    config_types = {a['type']
                    for a in yaml.safe_load(FULL_CONFIG)['accessories']}
    assert config_types == catalog, (
        f'FULL_CONFIG drift: missing {catalog - config_types}, '
        f'unknown {config_types - catalog}')


def test_sensor_frame_ids_resolve_in_tf():
    """
    Every sensor's <frame_id> names a frame TF actually carries.

    TF comes from the URDF via robot_state_publisher; gz's derived SDF scoped
    ids and the ${name}_sensor wrapper links are in neither, so an unset
    frame_id yields messages no lookup_transform can resolve.
    """
    sdf_root, _ = xacro(MODEL_XACRO, FULL_CONFIG)
    urdf_root, _ = xacro(URDF_XACRO, FULL_CONFIG)
    urdf_links = {li.get('name') for li in urdf_root.findall('link')}
    sensors = list(sdf_root.iter('sensor'))
    assert sensors
    for sensor in sensors:
        frame = sensor.find('frame_id')
        assert frame is not None, (
            f'sensor {sensor.get("name")} sets no <frame_id>')
        assert frame.text in urdf_links, (
            f'sensor {sensor.get("name")} publishes frame_id {frame.text!r}, '
            f'which robot_state_publisher never puts in TF')


def test_installed_artifacts_match_shipped_config():
    """The generated files that ship agree with the config they came from."""
    cfg = yaml.safe_load((DESC_SHARE / 'config' / 'blueboat.yaml').read_text())
    bridge_yaml = GZ_SHARE / 'config' / 'ros_gz_bridge.yaml'
    assert yaml.safe_load(bridge_yaml.read_text()) == \
        bridge_gen.bridge_entries(cfg)
    urdf = ET.fromstring((DESC_SHARE / 'urdf' / 'blueboat.urdf').read_text())
    links = {li.get('name') for li in urdf.findall('link')}
    for acc in cfg['accessories']:
        assert acc['name'] in links, f'{acc["name"]} missing from shipped URDF'
