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
"""Generation pipeline tests: parts config yaml -> URDF (validity, hull, catalog)."""

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
DRIVETRAIN = {'base_link', 'motor_port', 'motor_stbd'}
# The Ping2 transducer face sits this far below the part origin (delivered mesh).
PING_FACE_BELOW_ORIGIN = 0.044


def catalog():
    """Part types the library offers: the include list of parts.xacro."""
    names = re.findall(r'/urdf/([a-z0-9_]+)\.urdf\.xacro', PARTS_XACRO.read_text())
    return sorted(set(names) - {'part_probe'})


def part(type_name, name, **extra):
    """Build a parts config entry."""
    return {'type': type_name, 'name': name, **extra}


def make_config(parts=(), hull=True):
    """Vehicle config yaml: chassis base, the given parts, hull displacement."""
    cfg = {'base': {'type': 'blueboat_chassis', 'name': 'base_link',
                    'collision': False},
           'parts': [dict(p) for p in parts]}
    if hull:
        cfg['hull_displacement'] = dict(HULL)
    return yaml.safe_dump(cfg, sort_keys=False)


def full_catalog_parts():
    """One instance of every catalog type but the chassis, on explicit poses."""
    types = [t for t in catalog() if t != 'blueboat_chassis']
    return [part(t, f'acc_{t}', xyz=f'{0.1 * i - 0.6:.2f} 0 0.5', rpy='0 0 0')
            for i, t in enumerate(types)]


def xacro_output(config_text):
    """Run xacro on the top-level file with the given config; return the URDF."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        ['xacro', str(TOP_XACRO), f'config_file:={config_path}'],
        capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, (
        f'xacro failed ({out.returncode})\n--- stderr ---\n{out.stderr}')
    return out.stdout


def generate_urdf(config_text):
    """Generate the URDF for a config and return the parsed XML root."""
    return ET.fromstring(xacro_output(config_text))


def link_names(root):
    """Return the set of link names in a URDF tree."""
    return {link.get('name') for link in root.findall('link')}


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


def test_default_config_builds_the_standard_loadout():
    """The shipped config yields the chassis, two motors, flag and Ping kit."""
    root = generate_urdf(DEFAULT_CONFIG)
    assert DRIVETRAIN | {'flag', 'ping_mount', 'ping'} <= link_names(root)
    motors = {j.get('name'): j for j in root.findall('joint')
              if j.get('name') in ('motor_port_joint', 'motor_stbd_joint')}
    assert set(motors) == {'motor_port_joint', 'motor_stbd_joint'}
    for joint in motors.values():
        assert joint.get('type') == 'continuous'
        assert joint.find('axis') is not None


def test_hull_displacement_invariant():
    """Segmented pontoons tile fully and give positive reserve buoyancy."""
    root = generate_urdf(make_config(full_catalog_parts()))
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


def test_catalog_completeness_and_toggle():
    """Every part type generates its link, and only when configured."""
    empty_links = link_names(generate_urdf(make_config()))
    assert 'base_link' in empty_links
    for type_name in catalog():
        if type_name == 'blueboat_chassis':
            continue
        name = f'acc_{type_name}'
        root = generate_urdf(make_config([part(type_name, name, xyz='0 0 0.5')]))
        assert name in link_names(root), f'{type_name} missing link'
        assert name not in empty_links


def test_unknown_part_type_fails_loudly():
    """A typo in type: fails the build naming the type, never mounts nothing."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(make_config([part('no_such_part', 'x', xyz='0 0 0')]))
        config_path = f.name
    out = subprocess.run(['xacro', str(TOP_XACRO), f'config_file:={config_path}'],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode != 0
    assert 'no_such_part' in out.stderr


def test_mesh_assets_resolve():
    """Every mesh the URDF references ships in bluerobotics_parts."""
    root = generate_urdf(make_config(full_catalog_parts()))
    meshes = list(root.iter('mesh'))
    assert meshes, 'the parts based model must reference the delivered meshes'
    prefix = 'package://bluerobotics_parts/'
    for mesh in meshes:
        uri = mesh.get('filename')
        assert uri.startswith(prefix), f'mesh outside the parts package: {uri}'
        assert (PARTS_SHARE / uri[len(prefix):]).is_file(), f'missing asset {uri}'


def test_check_urdf_accepts_generated():
    """The urdfdom validator accepts the generated URDF."""
    text = xacro_output(make_config(full_catalog_parts()))
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(text)
        urdf_path = f.name
    out = subprocess.run(['check_urdf', urdf_path], capture_output=True,
                         text=True, timeout=30)
    assert out.returncode == 0, (
        f'check_urdf rejected the URDF ({out.returncode})\n'
        f'--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}')


def test_explicit_pose_propagates():
    """An explicit mount pose lands on the part's joint (zero attach part)."""
    root = generate_urdf(make_config(
        [part('ping_singlebeam', 'acc_ping', xyz='0.11 -0.22 0.33', rpy='0 0 0')]))
    joint = next(j for j in root.findall('joint') if j.get('name') == 'acc_ping_joint')
    xyz = [float(v) for v in joint.find('origin').get('xyz').split()]
    assert xyz == pytest.approx([0.11, -0.22, 0.33])
    assert joint.find('parent').get('link') == 'base_link'


def test_socket_mounting_chains_through_the_parent_part():
    """mount: on a part resolves to that part's socket frame, not base_link."""
    table = joints_by_child(generate_urdf(DEFAULT_CONFIG))
    assert table['ping'][0] == 'ping_mount_sensor'
    assert table['ping_mount_sensor'][0] == 'ping_mount'
    assert table['ping_mount'][0] == 'base_link_ping_mount'
    assert table['base_link_ping_mount'][0] == 'base_link'
    assert table['motor_port'][0] == 'base_link_motor_port'


def test_echosounder_mounted_below_waterline():
    """
    The default Ping transducer is submerged at rest.

    The gpu_lidar returns seabed ranges from anywhere, so a transducer in the
    air fails silently; lock its face below the static waterline computed from
    mass and waterplane area.
    """
    root = generate_urdf(DEFAULT_CONFIG)
    face_z = position_in_base(root, 'ping')[2] - PING_FACE_BELOW_ORIGIN
    area = 2 * HULL['length'] * HULL['width']
    draft = total_mass(root) / (WATER_DENSITY * area)
    waterline_z = HULL['z'] - HULL['height'] / 2 + draft
    assert face_z < waterline_z - 0.02, (
        f'ping transducer face at z {face_z:.3f} is not below the static '
        f'waterline {waterline_z:.3f}')
