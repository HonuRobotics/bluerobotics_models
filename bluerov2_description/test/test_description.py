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
"""Generation-pipeline tests: config yaml -> URDF (validity, variants, buoyancy)."""

import math
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest

SHARE = Path(get_package_share_directory('bluerov2_description'))
TOP_XACRO = SHARE / 'urdf' / 'bluerov2.urdf.xacro'
ACCESSORIES_XACRO = SHARE / 'urdf' / 'accessories.xacro'

WATER_DENSITY = 1025.0
NET_BUOYANCY_DEFAULT = 0.002   # kg, per the default buoyancy declaration
COB_OFFSET_DEFAULT = (0.0, 0.0, 0.046)  # m, CoB relative to CoM

# Full accessory catalog: type -> (demo pose, links the macro must generate).
CATALOG = {
    'ping360': ('0.16 0 0.13', ['{n}']),
    'roof_rack': ('0 0 0.17', ['{n}']),
    'payload_skid': ('0 0 -0.17', ['{n}']),
    'dvl_a50': ('-0.12 0 -0.14', ['{n}']),
    'explorehd_camera': ('0.22 0 0.05', ['{n}']),
    'sonoptix_echo': ('0.14 0.16 -0.05', ['{n}']),
    'omniscan_450_fs': ('0.14 -0.16 -0.05', ['{n}']),
    'marinesitu_c3': ('-0.16 0 0.16', ['{n}']),
    'newton_gripper': ('0.28 0 -0.08',
                       ['{n}_body', '{n}_jaw_left', '{n}_jaw_right']),
    'sediment_sampler': ('-0.26 0 -0.06',
                         ['{n}_body', '{n}_cup_left', '{n}_cup_right']),
}


def make_config(variant='standard', accessories=(), buoyancy=None):
    """Return vehicle-config yaml text for the given loadout."""
    lines = [f'variant: {variant}']
    if buoyancy:
        lines.append('buoyancy:')
        lines.extend(f'  {k}: {v}' for k, v in buoyancy.items())
    lines.append('accessories:' if accessories else 'accessories: []')
    for type_name, name, xyz in accessories:
        lines.append(
            f'  - {{type: {type_name}, name: {name}, '
            f'xyz: "{xyz}", rpy: "0 0 0"}}')
    return '\n'.join(lines) + '\n'


def full_catalog_accessories():
    """Return one accessory entry per catalog type."""
    return [(t, f'acc_{t}', pose) for t, (pose, _) in CATALOG.items()]


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


def joint_names(root):
    """Return the set of joint names in a URDF tree."""
    return {joint.get('name') for joint in root.findall('joint')}


def total_mass(root):
    """Sum every link mass in a URDF tree."""
    return sum(float(m.get('value'))
               for m in root.findall('.//inertial/mass'))


def collision_volume(root):
    """Sum every collision volume in the URDF, as the gz Buoyancy system does."""
    total = 0.0
    for geo in root.findall('.//collision/geometry'):
        box = geo.find('box')
        cyl = geo.find('cylinder')
        sph = geo.find('sphere')
        if box is not None:
            x, y, z = (float(v) for v in box.get('size').split())
            total += x * y * z
        elif cyl is not None:
            total += (math.pi * float(cyl.get('radius')) ** 2
                      * float(cyl.get('length')))
        elif sph is not None:
            total += 4 / 3 * math.pi * float(sph.get('radius')) ** 3
        else:
            raise AssertionError(
                f'unhandled collision geometry: {[c.tag for c in geo]}')
    return total


def link_origins(root):
    """
    Map each link to its translation in the base frame.

    Mount rpy are zero in every config these tests generate, so translations
    compose without rotation.
    """
    origins = {'base_link': (0.0, 0.0, 0.0)}
    pending = root.findall('joint')
    while pending:
        rest = []
        for joint in pending:
            parent = joint.find('parent').get('link')
            if parent not in origins:
                rest.append(joint)
                continue
            origin = joint.find('origin')
            xyz = [float(v) for v in origin.get('xyz').split()] \
                if origin is not None else [0.0, 0.0, 0.0]
            base = origins[parent]
            origins[joint.find('child').get('link')] = tuple(
                base[k] + xyz[k] for k in range(3))
        assert len(rest) < len(pending), 'joint graph has an orphan'
        pending = rest
    return origins


def element_offset(parent):
    """Return the xyz of an element's <origin>, or zero."""
    origin = parent.find('origin')
    if origin is None:
        return [0.0, 0.0, 0.0]
    return [float(v) for v in origin.get('xyz').split()]


def center_of_mass(root):
    """Mass-weighted centroid of every inertial, in the base frame."""
    origins = link_origins(root)
    mass, moment = 0.0, [0.0, 0.0, 0.0]
    for link in root.findall('link'):
        inertial = link.find('inertial')
        if inertial is None:
            continue
        m = float(inertial.find('mass').get('value'))
        off = element_offset(inertial)
        base = origins[link.get('name')]
        mass += m
        for k in range(3):
            moment[k] += m * (base[k] + off[k])
    return tuple(mo / mass for mo in moment)


def center_of_buoyancy(root):
    """Volume-weighted centroid of every collision, in the base frame."""
    origins = link_origins(root)
    volume, moment = 0.0, [0.0, 0.0, 0.0]
    for link in root.findall('link'):
        base = origins[link.get('name')]
        for col in link.findall('collision'):
            box = col.find('geometry/box')
            d = [float(v) for v in box.get('size').split()]
            vol = d[0] * d[1] * d[2]
            off = element_offset(col)
            volume += vol
            for k in range(3):
                moment[k] += vol * (base[k] + off[k])
    return tuple(mo / volume for mo in moment)


def net_buoyancy(root):
    """Return water_density * total collision volume - total mass, in kg."""
    return WATER_DENSITY * collision_volume(root) - total_mass(root)


def test_default_config_camera_only():
    """The shipped default config builds a standard model with camera only."""
    default = (SHARE / 'config' / 'bluerov2.yaml').read_text()
    root = generate_urdf(default)
    links = link_names(root)
    thrusters = {li for li in links if re.fullmatch(r'thruster\d', li)}
    assert len(thrusters) == 6
    assert 'camera' in links
    accessory_links = links - thrusters - {'base_link'}
    assert accessory_links == {'camera'}


def test_buoyancy_invariant_across_loadouts():
    """
    Both declared quantities hold for any loadout.

    rho*V - m stays at the declared net buoyancy, and the CoB sits at the
    declared offset from the CoM. Tolerance on the offset covers the
    mount-pose approximation for claw collision volumes.
    """
    configs = [
        make_config(),
        (SHARE / 'config' / 'bluerov2.yaml').read_text(),
        make_config('heavy', full_catalog_accessories()),
        make_config('standard', full_catalog_accessories()),
    ]
    for config in configs:
        root = generate_urdf(config)
        assert abs(net_buoyancy(root) - NET_BUOYANCY_DEFAULT) < 1e-6
        com, cob = center_of_mass(root), center_of_buoyancy(root)
        for k in range(3):
            assert abs(cob[k] - com[k] - COB_OFFSET_DEFAULT[k]) < 2e-3


def test_buoyancy_declaration_honored():
    """An explicit buoyancy block drives both declared quantities."""
    root = generate_urdf(make_config(
        'heavy', full_catalog_accessories(),
        buoyancy={'net_buoyancy': 0.05, 'cob_offset': '"0.01 0.005 0.03"'}))
    assert abs(net_buoyancy(root) - 0.05) < 1e-6
    com, cob = center_of_mass(root), center_of_buoyancy(root)
    for k, want in enumerate((0.01, 0.005, 0.03)):
        assert abs(cob[k] - com[k] - want) < 2e-3


def test_unbuildable_declaration_fails_loudly():
    """A net buoyancy the hull box cannot realize fails the build by name."""
    config = make_config(buoyancy={'net_buoyancy': -100.0})
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config)
        config_path = f.name
    out = subprocess.run(
        ['xacro', str(TOP_XACRO), f'config_file:={config_path}'],
        capture_output=True, text=True, timeout=60)
    assert out.returncode != 0
    assert 'net_buoyancy' in out.stderr


def test_variant_selects_thrusters_and_mesh():
    """The heavy variant gets 8 thrusters + heavy mesh; standard 6 + standard."""
    std = generate_urdf(make_config('standard'))
    heavy = generate_urdf(make_config('heavy'))
    count = {r: len([li for li in link_names(r)
                     if re.fullmatch(r'thruster\d', li)])
             for r in (std, heavy)}
    assert count[std] == 6 and count[heavy] == 8
    std_meshes = ET.tostring(std, encoding='unicode')
    heavy_meshes = ET.tostring(heavy, encoding='unicode')
    assert 'bluerov2_heavy.dae' not in std_meshes
    assert 'bluerov2_heavy.dae' in heavy_meshes


def test_catalog_completeness_and_toggle():
    """Every accessory type generates its links, and only when configured."""
    empty_links = link_names(generate_urdf(make_config()))
    for type_name, (pose, links_tpl) in CATALOG.items():
        name = f'acc_{type_name}'
        root = generate_urdf(make_config('standard', [(type_name, name, pose)]))
        expected = {tpl.format(n=name) for tpl in links_tpl}
        assert expected <= link_names(root), f'{type_name} missing links'
        assert not expected & empty_links, f'{type_name} present when absent'


@pytest.mark.parametrize('variant', ('standard', 'heavy'))
def test_mesh_references_resolve(variant):
    """Every package:// mesh URI in the generated URDF exists on disk."""
    root = generate_urdf(make_config(variant, full_catalog_accessories()))
    uris = {m.get('filename') for m in root.findall('.//mesh')}
    assert uris
    for uri in uris:
        package, _, rel = uri.removeprefix('package://').partition('/')
        path = Path(get_package_share_directory(package)) / rel
        assert path.is_file(), f'missing mesh {uri}'


@pytest.mark.parametrize('variant', ('standard', 'heavy'))
def test_check_urdf_accepts_generated(variant):
    """The urdfdom validator accepts the generated URDF."""
    text = xacro_output(make_config(variant, full_catalog_accessories()))
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(text)
        urdf_path = f.name
    out = subprocess.run(['check_urdf', urdf_path], capture_output=True,
                         text=True, timeout=30)
    assert out.returncode == 0, (
        f'check_urdf rejected the URDF ({out.returncode})\n'
        f'--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}')


def test_mass_table_matches_macros():
    """
    Accessory mass keys match the catalog, and each names a macro.

    The dispatcher invokes the config type directly as a macro, so a key
    without a same-named macro would fail only at build time.
    """
    text = ACCESSORIES_XACRO.read_text()
    dict_src = re.search(r'\$\{dict\(([^)]*)\)\}', text).group(1)
    mass_keys = set(re.findall(r'(\w+)=', dict_src))
    macros = set(re.findall(r'<xacro:macro name="(\w+)"', text))
    assert mass_keys <= macros, f'mass keys without a macro: {mass_keys - macros}'
    assert mass_keys == set(CATALOG)
