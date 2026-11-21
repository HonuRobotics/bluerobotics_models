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
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import (get_package_prefix,
                                         get_package_share_directory)
from bluerobotics_parts import assembly
from conftest import kit_config, kit_config_text
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

# A config with every simulated part type fitted.
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
  - {type: sonoptix_echo_multibeam, name: sonar_forward, xyz: "0.25 0 0.12", rpy: "0 0.2618 0",
     sonar: {range_max: 15, labels: true}}
  - {type: surveyor_multibeam, name: profiler, xyz: "0 0 -0.14", rpy: "0 0 0"}
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


def gen_model(config_text, ardupilot=False):
    """Generate model.sdf via generate_model.py; return (root, text)."""
    _, _, urdf, config = urdf_for(config_text)
    with tempfile.NamedTemporaryFile('w', suffix='.sdf', delete=False) as f:
        out_path = f.name
    run = subprocess.run(
        [sys.executable, str(GZ_LIB / 'generate_model.py')]
        + (['--ardupilot'] if ardupilot else [])
        + [config, urdf, str(MODEL_XACRO), out_path],
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
    thrusters = plugins(root, 'gz-maritime-thruster-system')
    assert len(thrusters) == 8  # heavy
    # one controller per claw joint: gripper jaws + sampler cups
    assert len(plugins(root, 'gz-sim-joint-position-controller-system')) == 4
    # gz-maritime's Hydrodynamics, which damps against the ocean current.
    assert len(plugins(root, 'gz-maritime-hydrodynamics-system')) == 1
    assert not plugins(root, 'gz-sim-hydrodynamics-system')
    by_type = {s.get('type') for s in root.iter('sensor')}
    assert by_type == {'camera', 'rgbd_camera', 'gpu_lidar', 'custom'}
    root, _ = gen_model(kit_config_text())
    assert len(plugins(root, 'gz-maritime-thruster-system')) == 6
    assert {s.get('type') for s in root.iter('sensor')} == {'camera'}


def test_thrusters_follow_the_propeller_parts():
    """One Thruster per propeller, on its joint, with balanced coefficients."""
    root, _ = gen_model(kit_config_text())
    thrusters = plugins(root, 'gz-maritime-thruster-system')
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
    root, _ = gen_model(kit_config_text())
    assert not plugins(root, 'gz-sim-dvl-system')
    root, _ = gen_model(FULL_CONFIG)
    assert len(plugins(root, 'gz-sim-dvl-system')) == 1
    for world in ('bluerov2_water.sdf', 'bluerov2_pool.sdf',
                  'bluerov2_playground.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        assert '<plugin filename="gz-sim-dvl-system"' not in text, world


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


@pytest.mark.parametrize('base', ['bluerov2_chassis', 'bluerov2_heavy_chassis'])
def test_drag_and_mass_lie_on_the_horizontal_thrust_lines(base):
    """
    Surge and sway thrust pass through the drag point and the center of mass.

    Thrust and drag on different lines make a couple: off the thrust plane it
    pitches or rolls the vehicle, and off the sway line it turns it, which
    shows as a forward creep in a sideways drive. A thruster moved without
    the chassis's center of pressure, or the reverse, fails here by more
    than a millimeter.
    """
    cfg = kit_config()
    cfg['base'] = {'type': base, 'name': 'base_link'}
    if base == 'bluerov2_heavy_chassis':
        cfg['buoyancy']['footprint'] = '0.457 0.575'
    config = yaml.safe_dump(cfg, sort_keys=False)
    urdf_root, _, _, _ = urdf_for(config)
    poses = assembly.link_poses(urdf_root)
    thrusters = []
    for joint in urdf_root.findall('joint'):
        if not re.fullmatch(r'thruster_\d+_joint', joint.get('name')):
            continue
        rot, pos = poses[joint.find('child').get('link')]
        axis = [float(v) for v in joint.find('axis').get('xyz').split()]
        direction = tuple(sum(rot[i][k] * axis[k] for k in range(3)) for i in range(3))
        if abs(direction[2]) < 0.1:          # the horizontals
            thrusters.append((pos, direction))
    assert len(thrusters) == 4

    root, _ = gen_model(config)
    hydro = plugins(root, 'gz-maritime-hydrodynamics-system')[0]
    drag = [float(v) for v in hydro.find('center_of_pressure').text.split()]
    _, com = assembly.mass_properties(urdf_root)

    for name, body_axis in (('surge', 0), ('sway', 1)):
        # Each thruster pushes the way that adds to the commanded axis.
        pushes = [(pos, tuple(math.copysign(1.0, d[body_axis]) * c for c in d))
                  for pos, d in thrusters]
        force = [sum(f[i] for _, f in pushes) for i in range(3)]
        strength = math.sqrt(sum(c * c for c in force))
        assert strength > 2.0 and abs(force[body_axis]) == pytest.approx(strength), (
            f'{name}: the horizontals do not add to a pure {name} force: {force}')
        for what, point in (('center of pressure', drag), ('center of mass', com)):
            moment = [0.0, 0.0, 0.0]
            for pos, f in pushes:
                arm = [pos[i] - point[i] for i in range(3)]
                moment = [m + c for m, c in zip(moment, _cross(arm, f))]
            offset = math.sqrt(sum(c * c for c in moment)) / strength
            assert offset < 1e-3, (
                f'{name} thrust passes {offset * 1000:.1f} mm from the {what} {point}')


def test_buoyancy_displacement_realizes_the_declaration():
    """The displacement box solves density * volume = mass + net at the CoB."""
    cfg = kit_config()
    declared = cfg['buoyancy']
    urdf_root, _, _, _ = urdf_for(kit_config_text())
    total, com = assembly.mass_properties(urdf_root)
    root, _ = gen_model(kit_config_text())
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
    # The box is the model's only marked collision, so a world whose buoyancy
    # reads marks (gz-maritime's) floats exactly it, under any spawn name.
    marked = [c for c in root.iter('collision')
              if c.get('{http://gazebosim.org/schema}buoyancy') == 'true']
    assert [c.get('name') for c in marked] == ['displacement']
    # It displaces only: a zero collide_bitmask keeps it out of contact,
    # which stays with the parts' collisions it overlaps.
    bitmask = link.find('.//collision/surface/contact/collide_bitmask')
    assert bitmask is not None and int(bitmask.text, 16) == 0
    # The worlds enable buoyancy on exactly this link.
    for world in ('bluerov2_water.sdf', 'bluerov2_pool.sdf',
                  'bluerov2_playground.sdf', 'bluerov2_sitl.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        assert '<enable>bluerov2::buoyancy_displacement</enable>' in text, world


@pytest.mark.parametrize('ardupilot', [False, True])
def test_plugin_references_survive_lumping(ardupilot):
    """Plugin joint/link refs exist in the POST lumping converted model."""
    sdf_root, _ = gen_model(FULL_CONFIG, ardupilot=ardupilot)
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
    """Every sensor's <frame_id> names a frame TF carries for the instance."""
    config = FULL_CONFIG.replace('topic_namespace: bluerov2', 'topic_namespace: rov_a')
    sdf_root, _ = gen_model(config)
    urdf_root, _, _, _ = urdf_for(config)
    urdf_links = {li.get('name') for li in urdf_root.findall('link')}
    sensors = list(sdf_root.iter('sensor'))
    assert sensors
    for sensor in sensors:
        frame = sensor.find('frame_id')
        assert frame is not None, f'{sensor.get("name")} sets no <frame_id>'
        prefix, _, link = frame.text.partition('/')
        assert prefix == 'rov_a' and link in urdf_links, (
            f'sensor {sensor.get("name")} publishes frame_id {frame.text!r}, '
            f'which robot_state_publisher never puts in TF for instance rov_a')
    # The sonars reach ROS through kai_sonar_bridge, stamped with the frames
    # it is given, not the sensors' <frame_id>.
    params = bridge_gen.sonar_entries(yaml.safe_load(config), urdf_instances(config))[
        'sonar_bridge']['ros__parameters']
    assert params['frame_ids']
    for frame in params['frame_ids']:
        prefix, _, link = frame.partition('/')
        assert prefix == 'rov_a' and link in urdf_links, (
            f'kai_sonar_bridge stamps {frame!r}, which TF does not carry')


def test_sonar_settings_reach_the_sensor():
    """A part's `sonar:` dict becomes its <gz:sonar> elements, booleans as sdformat spells them."""
    root, _ = gen_model(FULL_CONFIG)
    sensor = next(s for s in root.iter('sensor') if s.get('name') == 'sonar_forward')
    block = sensor.find('{http://gazebosim.org/schema}sonar')
    if block is None:
        block = sensor.find('gz:sonar')
    assert {c.tag.split('}')[-1]: c.text for c in block} == {
        'range_max': '15', 'labels': 'true'}


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
    for plugin in plugins(root, 'gz-maritime-thruster-system'):
        topics.add(plugin.find('topic').text)
    for plugin in plugins(root, 'gz-sim-joint-state-publisher-system'):
        topics.add(plugin.find('topic').text)
    return {t if t.startswith('/') else '/' + t for t in topics}


def test_sensor_and_bridge_topics_agree():
    """Model gz topics equal generated bridge gz topics, by construction."""
    for config in (kit_config_text(), FULL_CONFIG):
        root, _ = gen_model(config)
        sdf_topics = sdf_gz_topics(root)
        cfg = yaml.safe_load(config)
        entries = bridge_gen.bridge_entries(cfg, urdf_instances(config))
        bridge_topics = {e['gz_topic_name'] for e in entries} - {'/clock'}
        # Sonars go through kai_sonar_bridge, not ros_gz_bridge.
        sonar = bridge_gen.sonar_entries(cfg, urdf_instances(config))
        bridge_topics |= set(sonar['sonar_bridge']['ros__parameters'].get('gz_topics', []))
        assert sdf_topics == bridge_topics


@pytest.mark.parametrize('config', sorted(
    p.name for p in (DESC_SHARE / 'config').glob('bluerov2*.yaml')))
def test_every_shipped_config_generates(config):
    """
    Each shipped config generates a model whose topics the bridges cover.

    A variant (bluerov2_sonar.yaml, say) differs from the default only in
    its parts; anything else drifting would make it a different vehicle.
    """
    text = (DESC_SHARE / 'config' / config).read_text()
    cfg, default = yaml.safe_load(text), yaml.safe_load(default_config())
    for key in set(cfg) | set(default):
        if key not in ('parts', 'base', 'slot_defaults'):
            assert cfg.get(key) == default.get(key), f'{config}: {key} differs from bluerov2.yaml'
    root, _ = gen_model(text)
    entries = bridge_gen.bridge_entries(cfg, urdf_instances(text))
    bridge_topics = {e['gz_topic_name'] for e in entries} - {'/clock'}
    sonar = bridge_gen.sonar_entries(cfg, urdf_instances(text))
    bridge_topics |= set(sonar['sonar_bridge']['ros__parameters'].get('gz_topics', []))
    assert sdf_gz_topics(root) == bridge_topics


def test_installed_artifacts_match_shipped_config():
    """The generated files that ship agree with the config they came from."""
    cfg = yaml.safe_load(default_config())
    installed_urdf = ET.parse(DESC_SHARE / 'urdf' / 'bluerov2.urdf').getroot()
    instances = [(t, n) for t, n, _ in assembly.instances(installed_urdf)]
    bridge_yaml = GZ_SHARE / 'config' / 'ros_gz_bridge.yaml'
    assert yaml.safe_load(bridge_yaml.read_text()) == \
        bridge_gen.bridge_entries(cfg, instances)
    installed_sdf = (GZ_SHARE / 'models' / 'bluerov2' / 'model.sdf').read_text()
    assert 'model specs' in installed_sdf, 'installed model.sdf is not stamped'


def test_world_fluid_density_matches_the_description():
    """The worlds' buoyancy density equals the config's declaration."""
    declared = kit_config()['buoyancy']
    for world in ('bluerov2_water.sdf', 'bluerov2_pool.sdf',
                  'bluerov2_playground.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        density = float(text.split('<default_density>')[1].split('<')[0])
        assert density == pytest.approx(float(declared['fluid_density'])), world


def test_model_name_follows_the_topic_namespace():
    """The composed model is named after the config's topic_namespace."""
    root, _ = gen_model(FULL_CONFIG.replace(
        'topic_namespace: bluerov2', 'topic_namespace: rov_a'))
    assert root.find('model').get('name') == 'rov_a'


def test_ardupilot_variant_is_additive():
    """ardupilot:=false generates exactly what it always did."""
    plain, plain_text = gen_model(kit_config_text())
    assert not plugins(plain, 'ArduPilotPlugin')
    assert 'imu_sensor' not in plain_text


def test_ardupilot_controls_follow_the_thrusters():
    """One <control> per propeller, on the channel ArduSub expects."""
    root, _ = gen_model(kit_config_text(), ardupilot=True)
    ap = plugins(root, 'ArduPilotPlugin')
    assert len(ap) == 1, 'expected exactly one ArduPilotPlugin'
    controls = ap[0].findall('control')

    thruster_topics = {
        p.find('joint_name').text: p.find('topic').text
        for p in plugins(root, 'gz-maritime-thruster-system')}
    assert thruster_topics, 'no thrusters to compare the controls against'
    assert len(controls) == len(thruster_topics), (
        f'{len(controls)} controls for {len(thruster_topics)} thrusters')

    # Channels are contiguous from zero: ArduSub assigns Motor1..MotorN to
    # SERVO1..SERVON from FRAME_CONFIG, and channel= is zero based.
    assert sorted(int(c.get('channel')) for c in controls) == \
        list(range(len(controls)))

    for control in controls:
        joint = control.find('jointName').text
        channel = int(control.get('channel'))
        assert joint == f'thruster_{channel + 1}_joint', (
            f'channel {channel} drives {joint}; ArduSub mixes that channel '
            f'as Motor {channel + 1}')
        # The command topic must be the one the thruster listens on: both
        # come from the same topic_base, and this is what proves it.
        assert control.find('cmd_topic').text == '/' + thruster_topics[joint]


def test_ardupilot_imu_is_the_declared_frame():
    """The imuName resolves to the sensor on the chassis's imu frame."""
    root, _ = gen_model(kit_config_text(), ardupilot=True)
    ap = plugins(root, 'ArduPilotPlugin')[0]
    link, sensor = ap.find('imuName').text.split('::')
    links = {ln.get('name'): ln for ln in root.iter('link')}
    assert link in links, f'imuName names a link that does not exist: {link}'
    assert any(s.get('name') == sensor and s.get('type') == 'imu'
               for s in links[link].iter('sensor')), (
        f'{link} carries no imu sensor named {sensor}')
