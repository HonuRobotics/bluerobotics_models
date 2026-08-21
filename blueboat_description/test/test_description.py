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
"""Generation pipeline tests: config yaml + part slots -> URDF."""

from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest
import yaml

SHARE = Path(get_package_share_directory('blueboat_description'))
PARTS_SHARE = Path(get_package_share_directory('bluerobotics_parts'))
TOP_XACRO = SHARE / 'urdf' / 'blueboat.urdf.xacro'
PARTS_XACRO = PARTS_SHARE / 'urdf' / 'parts.xacro'
DEFAULT_CONFIG = (SHARE / 'config' / 'blueboat.yaml').read_text()

WATER_DENSITY = 1025.0
HULL = yaml.safe_load(DEFAULT_CONFIG)['hull_displacement']
# What the chassis slots fill with when the config is silent.
DEFAULT_LOADOUT = {'base_link': 'blueboat_chassis',
                   'motor_port': 'm200_weedless_prop_ccw',
                   'motor_stbd': 'm200_weedless_prop_cw',
                   'flag': 'blueboat_flag',
                   'ping_mount': 'blueboat_ping_singlebeam_mount',
                   'ping': 'ping_singlebeam'}
# The Ping2 transducer face sits this far below the part origin (delivered mesh).
PING_FACE_BELOW_ORIGIN = 0.044


def catalog():
    """Part types the library offers: the include list of parts.xacro."""
    names = re.findall(r'/urdf/([a-z0-9_]+)\.urdf\.xacro', PARTS_XACRO.read_text())
    return sorted(set(names) - {'part_probe'})


def make_config(parts=(), slots=(), hull=True):
    """Vehicle config yaml: chassis base, overrides/additions, hull displacement."""
    cfg = {'base': {'type': 'blueboat_chassis', 'name': 'base_link',
                    'collision': False},
           'parts': [dict(p) for p in parts]}
    if slots:
        cfg['slots'] = [dict(s) for s in slots]
    if hull:
        cfg['hull_displacement'] = dict(HULL)
    return yaml.safe_dump(cfg, sort_keys=False)


def xacro_run(config_text):
    """Run xacro on the top-level file with the given config."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    return subprocess.run(
        ['xacro', str(TOP_XACRO), f'config_file:={config_path}'],
        capture_output=True, text=True, timeout=120)


def xacro_output(config_text):
    """Expand; fail the test with xacro's stderr on error."""
    out = xacro_run(config_text)
    assert out.returncode == 0, (
        f'xacro failed ({out.returncode})\n--- stderr ---\n{out.stderr}')
    return out.stdout


def generate_urdf(config_text):
    """Generate the URDF for a config and return the parsed XML root."""
    return ET.fromstring(xacro_output(config_text))


def expect_failure(config_text, fragment):
    """Assert the expansion fails and names the problem."""
    out = xacro_run(config_text)
    assert out.returncode != 0, 'xacro accepted a config it should reject'
    assert fragment in out.stderr, (
        f'expected {fragment!r} in the error, got:\n{out.stderr[-800:]}')


def link_names(root):
    """Return the set of link names in a URDF tree."""
    return {link.get('name') for link in root.findall('link')}


def manifest(root):
    """Map instance name -> part type from the <assembly_part> elements."""
    return {e.get('name'): e.get('type') for e in root.findall('assembly_part')}


def total_mass(root):
    """Sum every link mass in a URDF tree."""
    return sum(float(m.get('value'))
               for m in root.findall('.//inertial/mass'))


def pontoon_boxes(root):
    """Return [(name, x, y, z, lx, ly, lz)] for the hull displacement boxes."""
    boxes = []
    for link in root.findall('link'):
        for coll in link.findall('collision'):
            name = coll.get('name') or ''
            if not name.startswith('pontoon_'):
                continue
            x, y, z = (float(v) for v in coll.find('origin').get('xyz').split())
            lx, ly, lz = (float(v) for v in
                          coll.find('./geometry/box').get('size').split())
            boxes.append((name, x, y, z, lx, ly, lz))
    return boxes


def joints_by_child(root):
    """Map child link -> (parent link, origin xyz) over every joint."""
    table = {}
    for joint in root.findall('joint'):
        origin = joint.find('origin')
        xyz = [float(v) for v in (origin.get('xyz') if origin is not None
                                  else '0 0 0').split()]
        table[joint.find('child').get('link')] = (joint.find('parent').get('link'), xyz)
    return table


def position_in_base(root, link):
    """
    Return the position of a link origin in base_link.

    Follows the joint origins up the tree; every joint in it has zero
    rotation, so translations simply add.
    """
    table = joints_by_child(root)
    pos = [0.0, 0.0, 0.0]
    while link in table:
        link, xyz = table[link]
        pos = [pos[i] + xyz[i] for i in range(3)]
    return pos


def test_default_config_is_the_default_loadout():
    """With no parts configured, the slots fill with their defaults."""
    root = generate_urdf(DEFAULT_CONFIG)
    assert manifest(root) == DEFAULT_LOADOUT
    assert set(DEFAULT_LOADOUT) <= link_names(root)
    motors = {j.get('name'): j for j in root.findall('joint')
              if j.get('name') in ('motor_port_joint', 'motor_stbd_joint')}
    assert set(motors) == {'motor_port_joint', 'motor_stbd_joint'}
    for joint in motors.values():
        assert joint.get('type') == 'continuous'
        assert joint.find('axis') is not None


def test_manifest_names_are_links():
    """Every manifest instance exists as a link (and vice versa for parts)."""
    root = generate_urdf(DEFAULT_CONFIG)
    links = link_names(root)
    for name in manifest(root):
        assert name in links


def test_slot_chains_through_the_parent_part():
    """Slot occupants hang off the slot frame of the instance carrying it."""
    table = joints_by_child(generate_urdf(DEFAULT_CONFIG))
    assert table['ping'][0] == 'ping_mount_ping'
    assert table['ping_mount_ping'][0] == 'ping_mount'
    assert table['ping_mount'][0] == 'base_link_ping_mount'
    assert table['base_link_ping_mount'][0] == 'base_link'
    assert table['motor_port'][0] == 'base_link_motor_port'
    assert table['ping_beam'][0] == 'ping', 'the Ping declares its beam frame'


def test_slot_override_picks_another_option():
    """A slot entry swaps the occupant for another accepted type."""
    root = generate_urdf(make_config([{'slot': 'motor_port', 'type': 't200_prop_ccw'}]))
    assert manifest(root)['motor_port'] == 't200_prop_ccw'
    assert manifest(root)['motor_stbd'] == 'm200_weedless_prop_cw'


def test_slot_none_leaves_it_empty():
    """type: none empties a slot, recursively (the bracket's Ping goes too)."""
    root = generate_urdf(make_config([{'slot': 'ping_mount', 'type': 'none'}]))
    assert 'ping_mount' not in manifest(root)
    assert 'ping' not in manifest(root)
    assert 'base_link_ping_mount' in link_names(root), 'the slot frame stays'


def test_slot_without_default_fills_on_request():
    """Slots with default none fill when the config names a part."""
    root = generate_urdf(make_config([{'slot': 'mast', 'type': 'blueboat_antenna_mast'},
                                      {'slot': 'payload', 'type': 'blueboat_payload_bracket'}]))
    assert manifest(root)['mast'] == 'blueboat_antenna_mast'
    assert manifest(root)['payload'] == 'blueboat_payload_bracket'


def test_slot_entry_on_another_part():
    """An entry can address a slot of a non base instance with on:."""
    root = generate_urdf(make_config(
        [{'slot': 'ping', 'on': 'ping_mount', 'type': 'ping_singlebeam', 'name': 'sonar'}]))
    assert manifest(root)['sonar'] == 'ping_singlebeam'
    assert 'ping' not in manifest(root)


def test_slot_rejects_parts_that_do_not_fit():
    """A type outside the slot's accepts list fails the expansion."""
    expect_failure(make_config([{'slot': 'motor_port', 'type': 'blueboat_flag'}]),
                   'does not fit')


def test_unknown_slot_on_base_fails():
    """A typo in the slot name fails the expansion naming it."""
    expect_failure(make_config([{'slot': 'nope', 'type': 'blueboat_flag'}]),
                   "unknown slot 'nope'")


def test_slot_configured_twice_fails():
    """Two entries for one slot fail the expansion."""
    expect_failure(make_config([{'slot': 'mast', 'type': 'blueboat_antenna_mast'},
                                {'slot': 'mast', 'type': 'none'}]),
                   'configured 2 times')


def test_unknown_part_type_fails_loudly():
    """A typo in type: fails the expansion naming the type."""
    expect_failure(make_config([{'type': 'no_such_part', 'name': 'x', 'xyz': '0 0 0'}]),
                   'no_such_part')


def test_ad_hoc_slot_from_config():
    """The config can declare a slot on an instance and fill it."""
    root = generate_urdf(make_config(
        parts=[{'slot': 'camera', 'type': 'surveyor_multibeam', 'name': 'mb'}],
        slots=[{'on': 'base_link', 'name': 'camera', 'xyz': '0.45 0 0.2',
                'accepts': ['surveyor_multibeam']}]))
    assert 'base_link_camera' in link_names(root)
    assert joints_by_child(root)['mb'][0] == 'base_link_camera'
    assert position_in_base(root, 'mb') == pytest.approx([0.45, 0.0, 0.2])


def test_free_placement_pose_propagates():
    """A free placed part lands at its xyz relative to the parent."""
    root = generate_urdf(make_config(
        [{'type': 'ping_singlebeam', 'name': 'extra', 'xyz': '0.11 -0.22 0.33'}]))
    assert position_in_base(root, 'extra') == pytest.approx([0.11, -0.22, 0.33])
    assert joints_by_child(root)['extra'][0] == 'base_link'


def test_catalog_completeness():
    """Every part type can be fitted (free placement) and appears by name."""
    for type_name in catalog():
        if type_name == 'blueboat_chassis':
            continue
        root = generate_urdf(make_config(
            [{'type': type_name, 'name': f'acc_{type_name}', 'xyz': '0 0 0.5'}]))
        assert manifest(root)[f'acc_{type_name}'] == type_name


def test_hull_displacement_invariant():
    """Segmented pontoons tile fully and give positive reserve buoyancy."""
    root = generate_urdf(DEFAULT_CONFIG)
    boxes = pontoon_boxes(root)
    sides = {'port': [], 'stbd': []}
    for name, x, _, _, lx, _, lz in boxes:
        sides[name.split('_')[1]].append((x, lx, lz))
    volume = 0.0
    for side, segments in sides.items():
        assert len(segments) >= 2, f'{side}: pontoon not segmented'
        segments.sort()
        for (x0, l0, _), (x1, _, _) in zip(segments, segments[1:]):
            assert abs((x0 + l0 / 2) - (x1 - l0 / 2)) < 1e-6, \
                f'{side}: segments do not tile'
    for _, x, y, z, lx, ly, lz in boxes:
        volume += lx * ly * lz
    mass = total_mass(root)
    displacement = WATER_DENSITY * volume
    assert displacement > mass, 'boat would sink fully loaded'
    height = boxes[0][6]
    draft = mass / (WATER_DENSITY * volume / height)
    assert draft < height, 'waterline above the pontoon tops'


def test_pontoons_are_a_symmetric_catamaran():
    """Both pontoons mirror across y and their segments tile without gaps."""
    boxes = pontoon_boxes(generate_urdf(DEFAULT_CONFIG))
    assert len(boxes) == 2 * HULL['segments']
    sides = {}
    for name, x, y, z, lx, ly, lz in boxes:
        sides.setdefault(name.split('_')[1], []).append((x, y, z, lx, ly, lz))
    assert set(sides) == {'port', 'stbd'}
    seg_len = HULL['length'] / HULL['segments']
    for side, sign in (('port', +1), ('stbd', -1)):
        segments = sorted(sides[side])
        assert len(segments) == HULL['segments']
        for x, y, z, lx, ly, lz in segments:
            assert y == pytest.approx(sign * HULL['y'])
            assert z == pytest.approx(HULL['z'])
            assert (lx, ly, lz) == pytest.approx(
                (seg_len, HULL['width'], HULL['height']))
        for (x0, *_), (x1, *_) in zip(segments, segments[1:]):
            assert x1 - x0 == pytest.approx(seg_len), f'{side}: gap or overlap'


def test_mesh_assets_resolve():
    """Every mesh the URDF references ships in bluerobotics_parts."""
    root = generate_urdf(DEFAULT_CONFIG)
    meshes = list(root.iter('mesh'))
    assert meshes, 'the parts based model must reference the delivered meshes'
    prefix = 'package://bluerobotics_parts/'
    for mesh in meshes:
        uri = mesh.get('filename')
        assert uri.startswith(prefix), f'mesh outside the parts package: {uri}'
        assert (PARTS_SHARE / uri[len(prefix):]).is_file(), f'missing asset {uri}'


def test_check_urdf_accepts_generated():
    """The urdfdom validator accepts the generated URDF, manifest included."""
    text = xacro_output(make_config([{'slot': 'mast', 'type': 'blueboat_antenna_mast'}]))
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(text)
        urdf_path = f.name
    out = subprocess.run(['check_urdf', urdf_path], capture_output=True,
                         text=True, timeout=30)
    assert out.returncode == 0, (
        f'check_urdf rejected the URDF ({out.returncode})\n'
        f'--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}')


def test_echosounder_mounted_below_waterline():
    """
    The default Ping transducer is submerged at rest.

    The gpu_lidar returns seabed ranges from anywhere, so a transducer in the
    air fails silently; lock its face below the static waterline computed from
    mass and waterplane area.
    """
    root = generate_urdf(DEFAULT_CONFIG)
    face_z = position_in_base(root, 'ping')[2] - PING_FACE_BELOW_ORIGIN
    assert position_in_base(root, 'ping_beam')[2] == pytest.approx(face_z, abs=1e-6)
    area = 2 * HULL['length'] * HULL['width']
    draft = total_mass(root) / (WATER_DENSITY * area)
    waterline_z = HULL['z'] - HULL['height'] / 2 + draft
    assert face_z < waterline_z - 0.02, (
        f'ping transducer face at z {face_z:.3f} is not below the static '
        f'waterline {waterline_z:.3f}')
