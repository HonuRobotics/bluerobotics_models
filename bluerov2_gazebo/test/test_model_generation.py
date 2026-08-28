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
"""Generation tests for the composed model: plugins, buoyancy solve, accord."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import (get_package_prefix,
                                         get_package_share_directory)
from bluerobotics_parts import assembly
import pytest
import yaml

GZ_SHARE = Path(get_package_share_directory('bluerov2_gazebo'))
DESC_SHARE = Path(get_package_share_directory('bluerov2_description'))
GZ_LIB = Path(get_package_prefix('bluerov2_gazebo')) / 'lib' / 'bluerov2_gazebo'
MODEL_XACRO = GZ_SHARE / 'model.sdf.xacro'
URDF_XACRO = DESC_SHARE / 'urdf' / 'bluerov2.urdf.xacro'

_spec = importlib.util.spec_from_file_location(
    'bridge_gen', GZ_LIB / 'generate_bridge_config.py')
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)

# A loadout with every simulated part type fitted.
FULL_CONFIG = """\
topic_namespace: bluerov2
base: {type: bluerov2_heavy_chassis, name: base_link}
parts:
  - {slot: camera, type: marinesitu_c3, name: stereo}
  - {slot: sonar, type: ping360, name: sonar}
  - {slot: dvl, type: dvl_a50, name: dvl}
  - {slot: gripper, type: newton_gripper, name: gripper}
  - {slot: payload, type: payload_skid, name: skid}
  - {type: explorehd_camera, name: camera, xyz: "0.22 0 0.05", rpy: "0 0 0"}
  - {type: sediment_sampler, name: sampler, xyz: "-0.26 0 -0.06", rpy: "0 0 0"}
buoyancy: {net_buoyancy: 0.002, cob_offset: "0 0 0.046", cob_frame: com,
           fluid_density: 1025.0, footprint: "0.457 0.575"}
"""


def default_config():
    """Return the shipped default vehicle config text."""
    return (DESC_SHARE / 'config' / 'bluerov2.yaml').read_text()


def urdf_for(config_text):
    """Generate the URDF for a config; return (root, text, urdf path)."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config = f.name
    out = subprocess.run(
        ['xacro', str(URDF_XACRO), f'config_file:={config}'],
        check=True, capture_output=True, text=True, timeout=120)
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(out.stdout)
    return ET.fromstring(out.stdout), out.stdout, f.name, config


def gen_model(config_text):
    """Generate model.sdf via generate_model.py; return (root, text)."""
    _, _, urdf, config = urdf_for(config_text)
    with tempfile.NamedTemporaryFile('w', suffix='.sdf', delete=False) as f:
        out_path = f.name
    run = subprocess.run(
        [sys.executable, str(GZ_LIB / 'generate_model.py'), config, urdf,
         str(MODEL_XACRO), out_path],
        capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, f'generate_model failed:\n{run.stderr}'
    text = Path(out_path).read_text()
    return ET.fromstring(text), text


def plugins(root, filename):
    """Return the plugin elements with the given filename attribute."""
    return [p for p in root.iter('plugin') if p.get('filename') == filename]


def urdf_instances(config_text):
    """(type, name) pairs of the assembled URDF for a config."""
    root, _, _, _ = urdf_for(config_text)
    return [(t, n) for t, n, _ in assembly.instances(root)]


def test_model_generation_follows_config():
    """Plugin and sensor counts track the config; no residue."""
    root, text = gen_model(FULL_CONFIG)
    assert 'xacro:' not in text and 'xmlns:xacro' not in text
    assert 'assembly_part' not in text and 'assembly_slot' not in text
    thrusters = plugins(root, 'gz-sim-thruster-system')
    assert len(thrusters) == 8  # heavy
    # one controller per claw joint: gripper jaws + sampler cups
    assert len(plugins(root, 'gz-sim-joint-position-controller-system')) == 4
    by_type = {s.get('type') for s in root.iter('sensor')}
    assert by_type == {'camera', 'rgbd_camera', 'gpu_lidar', 'custom'}
    root, _ = gen_model(default_config())
    assert len(plugins(root, 'gz-sim-thruster-system')) == 6
    assert {s.get('type') for s in root.iter('sensor')} == {'camera'}


def test_thrusters_follow_the_propeller_parts():
    """One Thruster per propeller, on its joint, with balanced coefficients."""
    root, _ = gen_model(default_config())
    thrusters = plugins(root, 'gz-sim-thruster-system')
    coeffs = {t.find('joint_name').text: float(t.find('thrust_coefficient').text)
              for t in thrusters}
    assert set(coeffs) == {f'thruster_{n}_joint' for n in range(1, 7)}
    assert sum(1 for c in coeffs.values() if c > 0) == 3  # ccw props
    one = thrusters[0]
    assert one.find('topic') is not None
    assert one.find('max_thrust_cmd') is not None


def test_dvl_backend_loads_only_with_a_dvl():
    """
    Load gz-sim-dvl-system with the model iff a DVL is configured.

    Loaded unconditionally (e.g. from the world), the idle
    DopplerVelocityLogSystem joins every render iteration once any rendering
    sensor exists and costs half or more of the real time factor.
    """
    root, _ = gen_model(default_config())
    assert not plugins(root, 'gz-sim-dvl-system')
    root, _ = gen_model(FULL_CONFIG)
    assert len(plugins(root, 'gz-sim-dvl-system')) == 1
    for world in ('bluerov2_water.sdf', 'bluerov2_pool.sdf',
                  'bluerov2_playground.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        assert '<plugin filename="gz-sim-dvl-system"' not in text, world


def test_buoyancy_displacement_realizes_the_declaration():
    """The displacement box solves density * volume = mass + net at the CoB."""
    cfg = yaml.safe_load(default_config())
    declared = cfg['buoyancy']
    urdf_root, _, _, _ = urdf_for(default_config())
    total, com = assembly.mass_properties(urdf_root)
    root, _ = gen_model(default_config())
    link = root.find('.//link[@name="buoyancy_displacement"]')
    assert link is not None
    size = [float(v) for v in link.find('.//box/size').text.split()]
    volume = size[0] * size[1] * size[2]
    density = float(declared['fluid_density'])
    net = float(declared['net_buoyancy'])
    assert density * volume == pytest.approx(total + net, abs=2e-3)
    fx, fy = (float(v) for v in str(declared['footprint']).split())
    assert size[0] == pytest.approx(fx) and size[1] == pytest.approx(fy)
    centroid = [float(v) for v in link.find('.//collision/pose').text.split()[:3]]
    offset = [float(v) for v in str(declared['cob_offset']).split()]
    for i in range(3):
        assert centroid[i] == pytest.approx(com[i] + offset[i], abs=1e-4)
    # The worlds enable buoyancy on exactly this link.
    for world in ('bluerov2_water.sdf', 'bluerov2_pool.sdf',
                  'bluerov2_playground.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        assert '<enable>bluerov2::buoyancy_displacement</enable>' in text, world


def test_plugin_references_survive_lumping():
    """Plugin joint/link refs exist in the POST lumping converted model."""
    sdf_root, _ = gen_model(FULL_CONFIG)
    _, urdf_text, urdf_path, _ = urdf_for(FULL_CONFIG)
    joint_refs = {ref.text for ref in sdf_root.iter('joint_name')}
    joint_refs |= {ref.text for ref in sdf_root.iter('jointName')}
    assert joint_refs
    out = subprocess.run(['gz', 'sdf', '-p', urdf_path], check=True,
                         capture_output=True, text=True, timeout=60)
    converted = ET.fromstring(out.stdout)
    surviving = {j.get('name') for j in converted.iter('joint')}
    assert joint_refs <= surviving, (
        f'plugin joints lumped away: {joint_refs - surviving}')


def test_sensor_frame_ids_resolve_in_tf():
    """Every sensor's <frame_id> names a frame TF actually carries."""
    sdf_root, _ = gen_model(FULL_CONFIG)
    urdf_root, _, _, _ = urdf_for(FULL_CONFIG)
    urdf_links = {li.get('name') for li in urdf_root.findall('link')}
    sensors = list(sdf_root.iter('sensor'))
    assert sensors
    for sensor in sensors:
        frame = sensor.find('frame_id')
        assert frame is not None, f'{sensor.get("name")} sets no <frame_id>'
        assert frame.text in urdf_links, (
            f'sensor {sensor.get("name")} publishes frame_id {frame.text!r}, '
            f'which robot_state_publisher never puts in TF')


RGBD_SUFFIXES = ('image', 'depth_image', 'points', 'camera_info')


def sdf_gz_topics(root):
    """Collect the gz side topics the model advertises/subscribes."""
    topics = set()
    for sensor in root.iter('sensor'):
        base = sensor.find('topic').text
        if sensor.get('type') == 'rgbd_camera':
            # gz derives the four streams from the rgbd base topic.
            topics |= {f'{base}/{suffix}' for suffix in RGBD_SUFFIXES}
        else:
            topics.add(base)
    for info in root.iter('camera_info_topic'):
        topics.add(info.text)
    for plugin in plugins(root, 'gz-sim-joint-position-controller-system'):
        topics.add(plugin.find('topic').text)
    for plugin in plugins(root, 'gz-sim-thruster-system'):
        topics.add(plugin.find('topic').text)
    for plugin in plugins(root, 'gz-sim-joint-state-publisher-system'):
        topics.add(plugin.find('topic').text)
    return {t if t.startswith('/') else '/' + t for t in topics}


def test_sensor_and_bridge_topics_agree():
    """Model gz topics equal generated bridge gz topics, by construction."""
    for config in (default_config(), FULL_CONFIG):
        root, _ = gen_model(config)
        sdf_topics = sdf_gz_topics(root)
        cfg = yaml.safe_load(config)
        entries = bridge_gen.bridge_entries(cfg, urdf_instances(config))
        bridge_topics = {e['gz_topic_name'] for e in entries} - {'/clock'}
        assert sdf_topics == bridge_topics


def test_installed_artifacts_match_shipped_config():
    """The generated files that ship agree with the config they came from."""
    cfg = yaml.safe_load(default_config())
    installed_urdf = ET.parse(DESC_SHARE / 'urdf' / 'bluerov2.urdf').getroot()
    instances = [(t, n) for t, n, _ in assembly.instances(installed_urdf)]
    bridge_yaml = GZ_SHARE / 'config' / 'ros_gz_bridge.yaml'
    assert yaml.safe_load(bridge_yaml.read_text()) == \
        bridge_gen.bridge_entries(cfg, instances)
    names = {n for _, n in instances}
    assert {'thruster_1', 'thruster_6', 'camera'} <= names
    installed_sdf = (GZ_SHARE / 'models' / 'bluerov2' / 'model.sdf').read_text()
    assert 'model specs' in installed_sdf, 'installed model.sdf is not stamped'


def test_world_fluid_density_matches_the_description():
    """The worlds' buoyancy density equals the config's declaration."""
    declared = yaml.safe_load(default_config())['buoyancy']
    for world in ('bluerov2_water.sdf', 'bluerov2_pool.sdf',
                  'bluerov2_playground.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        density = float(text.split('<default_density>')[1].split('<')[0])
        assert density == pytest.approx(float(declared['fluid_density'])), world
