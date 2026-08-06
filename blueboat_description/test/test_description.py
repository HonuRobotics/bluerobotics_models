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
"""Generation-pipeline tests: config yaml -> URDF (validity, pontoons, catalog)."""

from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory

SHARE = Path(get_package_share_directory('blueboat_description'))
TOP_XACRO = SHARE / 'urdf' / 'blueboat.urdf.xacro'
ACCESSORIES_XACRO = SHARE / 'urdf' / 'accessories.xacro'

WATER_DENSITY = 1025.0

# Full accessory catalog: type -> demo pose.
CATALOG = {
    'flag': '-0.3 0 -0.08',
    'antenna_mast': '-0.35 0 0.45',
    'basestation_antenna': '-0.35 0 0.78',
    'ping_sonar': '0 0 -0.05',
    'ping_mount': '0 -0.12 -0.02',
    'payload_bracket': '0.1 0 0.15',
    'omniscan_450': '0.2 0.22 -0.03',
    'surveyor_multibeam': '0.35 0 -0.08',
}


def make_config(accessories=()):
    """Return vehicle-config yaml text for the given loadout."""
    lines = ['accessories:']
    if not accessories:
        lines = ['accessories: []']
    for type_name, name, xyz in accessories:
        lines.append(
            f'  - {{type: {type_name}, name: {name}, '
            f'xyz: "{xyz}", rpy: "0 0 0"}}')
    return '\n'.join(lines) + '\n'


def full_catalog_accessories():
    """Return one accessory entry per catalog type."""
    return [(t, f'acc_{t}', pose) for t, pose in CATALOG.items()]


def xacro_output(config_text):
    """Run xacro on the top-level file with the given config; return the URDF."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        ['xacro', str(TOP_XACRO), f'config_file:={config_path}'],
        capture_output=True, text=True, timeout=60)
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
    """Return [(name, x, y, z, lx, ly, lz)] for the pontoon collisions."""
    base = next(li for li in root.findall('link')
                if li.get('name') == 'base_link')
    boxes = []
    for coll in base.findall('collision'):
        name = coll.get('name') or ''
        if not name.startswith('pontoon_'):
            continue
        x, y, z = (float(v) for v in
                   coll.find('origin').get('xyz').split())
        lx, ly, lz = (float(v) for v in
                      coll.find('./geometry/box').get('size').split())
        boxes.append((name, x, y, z, lx, ly, lz))
    return boxes


def test_default_config_ping_only():
    """The shipped default config builds two motors and the echosounder."""
    default = (SHARE / 'config' / 'blueboat.yaml').read_text()
    links = link_names(generate_urdf(default))
    assert {'base_link', 'motor_port_link', 'motor_stbd_link', 'ping'} <= links
    accessory_links = links - {'base_link', 'motor_port_link',
                               'motor_stbd_link'}
    assert accessory_links == {'ping'}


def test_pontoon_buoyancy_invariant():
    """Segmented pontoons tile fully and give positive reserve buoyancy."""
    root = generate_urdf(make_config(full_catalog_accessories()))
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


def test_catalog_completeness_and_toggle():
    """Every accessory type generates its link, and only when configured."""
    empty_links = link_names(generate_urdf(make_config()))
    for type_name, pose in CATALOG.items():
        name = f'acc_{type_name}'
        root = generate_urdf(make_config([(type_name, name, pose)]))
        assert name in link_names(root), f'{type_name} missing link'
        assert name not in empty_links
    # The dispatcher invokes the config type directly as a macro, so every
    # catalog type must have a same-named macro.
    macros = set(re.findall(r'<xacro:macro name="([a-z]\w*)"',
                            ACCESSORIES_XACRO.read_text()))
    assert set(CATALOG) <= macros, f'missing macros: {set(CATALOG) - macros}'


def test_no_mesh_assets():
    """Licensing guard: the package ships no meshes, visuals are primitive."""
    root = generate_urdf(make_config(full_catalog_accessories()))
    assert not root.findall('.//mesh'), 'unexpected mesh reference in URDF'
    assert not (SHARE / 'meshes').exists(), 'unexpected meshes directory'


def test_check_urdf_accepts_generated():
    """The urdfdom validator accepts the generated URDF."""
    text = xacro_output(make_config(full_catalog_accessories()))
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(text)
        urdf_path = f.name
    out = subprocess.run(['check_urdf', urdf_path], capture_output=True,
                         text=True, timeout=30)
    assert out.returncode == 0, (
        f'check_urdf rejected the URDF ({out.returncode})\n'
        f'--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}')
