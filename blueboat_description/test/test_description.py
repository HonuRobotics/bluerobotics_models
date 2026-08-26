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
"""Generation pipeline tests: config yaml + part slots -> URDF (displacement is Gazebo side)."""

from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from bluerobotics_parts import assembly
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


# The library is shared across vehicles; these tests sweep the BlueBoat's
# sub catalog only (the BlueROV2 parts have their own suite).
ROV_PARTS = {'bluerov2_chassis', 'bluerov2_heavy_chassis', 'ping360', 'payload_skid',
             'roof_rack', 'sonoptix_echo', 'omniscan_450_fs', 'marinesitu_c3',
             'explorehd_camera', 'dvl_a50', 'newton_gripper', 'sediment_sampler'}


def catalog():
    """Part types the BlueBoat sweep covers: the include list minus the ROV's."""
    names = re.findall(r'/urdf/([a-z0-9_]+)\.urdf\.xacro', PARTS_XACRO.read_text())
    return sorted(set(names) - {'part_probe'} - ROV_PARTS)


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
    assert 'hull_displacement' not in link_names(root), 'displacement belongs to the Gazebo side'
    base = next(li for li in root.findall('link') if li.get('name') == 'base_link')
    assert base.findall('collision'), 'the chassis keeps its delivered contact geometry'
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


def test_slot_entry_of_another_part():
    """An entry can address a slot of a non base instance with of:."""
    root = generate_urdf(make_config(
        [{'slot': 'ping', 'of': 'ping_mount', 'type': 'ping_singlebeam', 'name': 'sonar'}]))
    assert manifest(root)['sonar'] == 'ping_singlebeam'
    assert 'ping' not in manifest(root)


def test_bare_on_key_is_rejected():
    """A bare on: key is the YAML boolean true; the expansion says so."""
    # Flow style as a user types it: PyYAML reads the key as True.
    text = make_config() + '\nparts:\n  - {slot: ping, on: ping_mount, type: none}\n'
    text = text.replace('parts: []\n', '', 1)
    expect_failure(text, "bare 'on:' key")


def test_manifest_records_every_slot_visited():
    """<assembly_slot of name/> covers the parts' own slots and the ad hoc ones."""
    root = generate_urdf(make_config(
        slots=[{'of': 'ping_mount', 'name': 'side', 'xyz': '0 0.05 0'}]))
    visited = assembly.slots(root)
    assert {('base_link', 'motor_port'), ('base_link', 'ping_mount'),
            ('ping_mount', 'ping'), ('ping_mount', 'side')} <= visited


def test_check_catches_what_the_expansion_cannot():
    """Entries matching nothing deeper down, and duplicate names, fail the check."""
    # A typo in a slot of a non base instance, and a non existent instance:
    # the expansion cannot see them (it only validates the base's slots).
    cfg = yaml.safe_load(make_config(
        [{'slot': 'pingg', 'of': 'ping_mount', 'type': 'none'},
         {'slot': 'ping', 'of': 'ping_mountt', 'type': 'none'}],
        slots=[{'of': 'nowhere', 'name': 'x', 'xyz': '0 0 0'}]))
    root = generate_urdf(yaml.safe_dump(cfg))
    found = assembly.problems(cfg, root)
    assert any("'pingg' of 'ping_mount'" in f and "['ping']" in f for f in found), found
    assert any("'ping' of 'ping_mountt'" in f and 'no instance' in f for f in found), found
    assert any("ad hoc slot 'x' of 'nowhere'" in f for f in found), found
    # The same part fitted twice without a name: the bracket's slot fills
    # with `ping` on both, which the URDF cannot hold.
    cfg = yaml.safe_load(make_config(
        [{'type': 'blueboat_ping_singlebeam_mount', 'name': 'mount2', 'xyz': '0 0.26 0.01'}]))
    found = assembly.problems(cfg, generate_urdf(yaml.safe_dump(cfg)))
    assert any("['ping']" in f and 'more than once' in f for f in found), found
    # Unknown keys are typos.
    cfg = yaml.safe_load(make_config([{'slot': 'flag', 'type': 'none', 'bogus': 1}]))
    found = assembly.problems(cfg, generate_urdf(yaml.safe_dump(cfg)))
    assert any("['bogus']" in f for f in found), found
    # And a clean config has nothing to report.
    cfg = yaml.safe_load(make_config(
        [{'slot': 'ping', 'of': 'ping_mount', 'type': 'ping_singlebeam', 'name': 'sonar',
          'topic': 'sonar'}]))
    assert assembly.problems(cfg, generate_urdf(yaml.safe_dump(cfg))) == []


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
        slots=[{'of': 'base_link', 'name': 'camera', 'xyz': '0.45 0 0.2',
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
