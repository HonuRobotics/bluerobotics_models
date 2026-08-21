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
PARTS_SHARE = Path(get_package_share_directory('bluerobotics_parts'))
MODEL_XACRO = GZ_SHARE / 'model.sdf.xacro'
URDF_XACRO = DESC_SHARE / 'urdf' / 'blueboat.urdf.xacro'
DEFAULT_CONFIG = (DESC_SHARE / 'config' / 'blueboat.yaml').read_text()

_SCRIPT = (Path(get_package_prefix('blueboat_gazebo'))
           / 'lib' / 'blueboat_gazebo' / 'generate_bridge_config.py')
_spec = importlib.util.spec_from_file_location('bridge_gen', _SCRIPT)
bridge_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_gen)


def catalog():
    """Part types the library offers: the include list of parts.xacro."""
    text = (PARTS_SHARE / 'urdf' / 'parts.xacro').read_text()
    return sorted(set(re.findall(r'/urdf/([a-z0-9_]+)\.urdf\.xacro', text))
                  - {'part_probe'})


# Types the chassis slots fit by default; everything else in the catalog is
# added explicitly below so FULL_CONFIG exercises the whole library.
DEFAULT_TYPES = {'blueboat_chassis', 'm200_weedless_prop_ccw', 'm200_weedless_prop_cw',
                 'blueboat_flag', 'blueboat_ping_singlebeam_mount', 'ping_singlebeam'}
SLOTTED_EXTRAS = {'blueboat_antenna_mast': 'mast', 'blueboat_payload_bracket': 'payload'}


def full_config_text(extra=''):
    """
    Build a config exercising every catalog type.

    Defaults fill the chassis slots; the mast and payload bracket go in their
    slots; every remaining type is free placed. test_full_config_covers_catalog
    enforces that nothing is left out.
    """
    cfg = yaml.safe_load(DEFAULT_CONFIG)
    parts = [{'slot': slot, 'type': t} for t, slot in SLOTTED_EXTRAS.items()]
    free = [t for t in catalog() if t not in DEFAULT_TYPES and t not in SLOTTED_EXTRAS]
    parts += [{'type': t, 'name': f'acc_{t}', 'xyz': f'{0.1 * i - 0.6:.2f} 0 0.5',
               'rpy': '0 0 0'} for i, t in enumerate(free)]
    cfg['parts'] = parts
    return yaml.safe_dump(cfg, sort_keys=False) + extra


FULL_CONFIG = full_config_text()
NO_SENSOR_CONFIG = yaml.safe_dump(
    yaml.safe_load(DEFAULT_CONFIG) | {'parts': [{'slot': 'ping_mount', 'type': 'none'}]},
    sort_keys=False)


def xacro(top_file, config_text):
    """Run xacro with a temp config; return the parsed XML root and text."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        ['xacro', str(top_file), f'config_file:={config_path}'],
        check=True, capture_output=True, text=True, timeout=120)
    return ET.fromstring(out.stdout), out.stdout


def urdf_instances(config_text):
    """(type, name) pairs of the assembled URDF for a config."""
    root, _ = xacro(URDF_XACRO, config_text)
    return [(e.get('type'), e.get('name')) for e in root.findall('assembly_part')]


def plugins(root, filename):
    """Return the plugin elements with the given filename attribute."""
    return [p for p in root.iter('plugin') if p.get('filename') == filename]


def test_model_generation_follows_config():
    """Plugin and sensor counts track the config; no xacro residue."""
    root, text = xacro(MODEL_XACRO, FULL_CONFIG)
    assert 'xacro:' not in text and 'xmlns:xacro' not in text
    assert 'assembly_part' not in text, 'manifest elements belong to the URDF only'
    assert len(plugins(root, 'gz-sim-thruster-system')) == 2
    assert len(plugins(root, 'gz-sim-hydrodynamics-system')) == 1
    sensors = list(root.iter('sensor'))
    assert {s.get('type') for s in sensors} == {'gpu_lidar'}
    assert len(sensors) == 1  # only the Ping2 emits a sensor
    empty_root, _ = xacro(MODEL_XACRO, NO_SENSOR_CONFIG)
    assert not list(empty_root.iter('sensor')), 'emptying the Ping slot removes the sensor'
    assert len(plugins(empty_root, 'gz-sim-thruster-system')) == 2


def test_default_config_has_the_ping_sensor():
    """The zero configuration model ships the echosounder, through the slot default."""
    root, _ = xacro(MODEL_XACRO, DEFAULT_CONFIG)
    sensors = list(root.iter('sensor'))
    assert [s.get('name') for s in sensors] == ['ping']


def test_sensors_follow_their_part_frame():
    """A sensor link is posed at the part's declared sensing frame."""
    root, _ = xacro(MODEL_XACRO, DEFAULT_CONFIG)
    sensor_links = [li for li in root.iter('link') if li.get('name') == 'ping_sensor']
    assert len(sensor_links) == 1
    assert sensor_links[0].find('pose').get('relative_to') == 'ping_beam'
    sensor = next(root.iter('sensor'))
    assert sensor.find('frame_id').text == 'ping_beam'


HULL = yaml.safe_load(DEFAULT_CONFIG)['hull_displacement']
WATER_DENSITY = 1025.0


def pontoon_boxes(model_root):
    """Return [(name, x, y, z, lx, ly, lz)] of the hull_displacement link's boxes."""
    link = next(li for li in model_root.iter('link') if li.get('name') == 'hull_displacement')
    boxes = []
    for coll in link.findall('collision'):
        x, y, z = (float(v) for v in coll.find('pose').text.split()[:3])
        lx, ly, lz = (float(v) for v in coll.find('geometry/box/size').text.split())
        boxes.append((coll.get('name'), x, y, z, lx, ly, lz))
    return boxes


def test_hull_displacement_is_its_own_enabled_link():
    """
    Displacement lives on a dedicated link the worlds enable by name.

    Fixed to base_link; the parts' collisions never displace.
    """
    root, _ = xacro(MODEL_XACRO, DEFAULT_CONFIG)
    link = next(li for li in root.iter('link') if li.get('name') == 'hull_displacement')
    assert link.find('pose').get('relative_to') == 'base_link'
    joint = next(j for j in root.iter('joint') if j.get('name') == 'hull_displacement_joint')
    assert joint.get('type') == 'fixed'
    assert joint.find('parent').text == 'base_link'
    assert joint.find('child').text == 'hull_displacement'
    for world in ('blueboat_water.sdf', 'blueboat_playground.sdf'):
        text = (GZ_SHARE / 'worlds' / world).read_text()
        assert '<enable>blueboat::hull_displacement</enable>' in text, world
        assert '<enable>blueboat</enable>' not in text, f'{world}: must not enable the whole model'


def test_pontoons_tile_and_float_the_boat():
    """Segmented pontoons mirror across y, tile, and give positive reserve buoyancy."""
    root, _ = xacro(MODEL_XACRO, DEFAULT_CONFIG)
    boxes = pontoon_boxes(root)
    assert len(boxes) == 2 * HULL['segments']
    sides = {}
    for name, x, y, z, lx, ly, lz in boxes:
        sides.setdefault(name.split('_')[1], []).append((x, y, z, lx, ly, lz))
    assert set(sides) == {'port', 'stbd'}
    seg_len = HULL['length'] / HULL['segments']
    for side, sign in (('port', +1), ('stbd', -1)):
        segments = sorted(sides[side])
        for x, y, z, lx, ly, lz in segments:
            assert y == pytest.approx(sign * HULL['y']) and z == pytest.approx(HULL['z'])
            assert (lx, ly, lz) == pytest.approx((seg_len, HULL['width'], HULL['height']))
        for (x0, *_), (x1, *_) in zip(segments, segments[1:]):
            assert x1 - x0 == pytest.approx(seg_len), f'{side}: gap or overlap'
    urdf_root = ET.parse(DESC_SHARE / 'urdf' / 'blueboat.urdf').getroot()
    mass = sum(float(m.get('value')) for m in urdf_root.findall('.//inertial/mass'))
    volume = sum(lx * ly * lz for *_, lx, ly, lz in boxes)
    assert WATER_DENSITY * volume > mass, 'boat would sink fully loaded'
    draft = mass / (WATER_DENSITY * 2 * HULL['length'] * HULL['width'])
    assert draft < HULL['height'], 'waterline above the pontoon tops'


def test_installed_model_merges_the_gazebo_flavoured_urdf():
    """
    The model merges the Gazebo flavoured URDF installed next to it.

    model://blueboat/blueboat.urdf is the gltf_up:=z expansion: glTF visuals
    pre-rotated for Gazebo, same parts as the ROS URDF.
    """
    model_dir = GZ_SHARE / 'models' / 'blueboat'
    root = ET.parse(model_dir / 'model.sdf').getroot()
    assert next(root.iter('include')).find('uri').text == 'model://blueboat/blueboat.urdf'
    gz_urdf = ET.parse(model_dir / 'blueboat.urdf').getroot()
    ros_urdf = ET.parse(DESC_SHARE / 'urdf' / 'blueboat.urdf').getroot()
    assert {li.get('name') for li in gz_urdf.findall('link')} == \
        {li.get('name') for li in ros_urdf.findall('link')}
    gz_rpys = {v.find('origin').get('rpy') for v in gz_urdf.iter('visual')
               if v.find('geometry/mesh') is not None}
    ros_rpys = {v.find('origin').get('rpy') for v in ros_urdf.iter('visual')
                if v.find('geometry/mesh') is not None}
    assert gz_rpys == {'1.5708 0 0'} and ros_rpys == {'0 0 0'}


def test_installed_model_sdf_carries_the_specs_comment():
    """The stamped model.sdf repeats the URDF specs; the masses agree."""
    text = (GZ_SHARE / 'models' / 'blueboat' / 'model.sdf').read_text()
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
    surviving_frames = {fr.get('name') for fr in converted.iter('frame')}
    assert joint_refs <= surviving_joints, (
        f'plugin joints lumped away: {joint_refs - surviving_joints}')
    assert link_refs <= surviving_links, (
        f'plugin links lumped away: {link_refs - surviving_links}')
    sensor_frames = {li.find('pose').get('relative_to')
                     for li in sdf_root.iter('link') if li.find('pose') is not None
                     and li.find('pose').get('relative_to')}
    assert sensor_frames <= surviving_frames | surviving_links, (
        f'sensor frames not in the converted model: '
        f'{sensor_frames - surviving_frames - surviving_links}')


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
    renamed = yaml.safe_dump(yaml.safe_load(DEFAULT_CONFIG) | {'parts': [
        {'slot': 'ping', 'on': 'ping_mount', 'type': 'ping_singlebeam',
         'name': 'sonar', 'topic': 'echo'}]}, sort_keys=False)
    for config in (FULL_CONFIG, DEFAULT_CONFIG, NO_SENSOR_CONFIG, renamed,
                   full_config_text('topic_namespace: boat_a\n')):
        cfg = yaml.safe_load(config)
        cfg.setdefault('extra_bridge_topics', []).append(extra)
        entries = bridge_gen.bridge_entries(cfg, urdf_instances(config))
        assert extra in entries, 'extra_bridge_topics dropped'
        ns = cfg.get('topic_namespace', 'blueboat')
        fixed = {'/clock', f'/{ns}/joint_states', extra['gz_topic_name']}
        bridge_topics = {e['gz_topic_name'] for e in entries
                         if e['gz_topic_name'] not in fixed
                         and not e['gz_topic_name'].endswith('/cmd_thrust')}
        root, _ = xacro(MODEL_XACRO, config)
        assert sdf_gz_topics(root) == bridge_topics


def test_full_config_covers_catalog():
    """FULL_CONFIG (with the defaults) fits every part type the library offers."""
    types = {t for t, _ in urdf_instances(FULL_CONFIG)}
    assert types == set(catalog()), (
        f'FULL_CONFIG drift: missing {set(catalog()) - types}, '
        f'unknown {types - set(catalog())}')


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
    cfg = yaml.safe_load(DEFAULT_CONFIG)
    installed_urdf = DESC_SHARE / 'urdf' / 'blueboat.urdf'
    bridge_yaml = GZ_SHARE / 'config' / 'ros_gz_bridge.yaml'
    assert yaml.safe_load(bridge_yaml.read_text()) == \
        bridge_gen.bridge_entries(cfg, bridge_gen.instances_from_urdf(installed_urdf))
    urdf = ET.parse(installed_urdf).getroot()
    links = {li.get('name') for li in urdf.findall('link')}
    for part in urdf.findall('assembly_part'):
        assert part.get('name') in links, f'{part.get("name")} missing from shipped URDF'
    assert any(p.get('type') == 'ping_singlebeam' for p in urdf.findall('assembly_part')), \
        'the shipped default must carry the Ping'
