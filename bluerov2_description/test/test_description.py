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
from bluerobotics_parts import assembly
import yaml

SHARE = Path(get_package_share_directory('bluerov2_description'))
PARTS_SHARE = Path(get_package_share_directory('bluerobotics_parts'))
TOP_XACRO = SHARE / 'urdf' / 'bluerov2.urdf.xacro'
PARTS_XACRO = PARTS_SHARE / 'urdf' / 'parts.xacro'

DEFAULT_CONFIG = (SHARE / 'config' / 'bluerov2.yaml').read_text()

# What the chassis slots fill with when the config is silent.
DEFAULT_LOADOUT = {'base_link': 'bluerov2_chassis',
                   'thruster_1': 't200_prop_ccw', 'thruster_2': 't200_prop_ccw',
                   'thruster_3': 't200_prop_cw', 'thruster_4': 't200_prop_cw',
                   'thruster_5': 't200_prop_ccw', 'thruster_6': 't200_prop_cw',
                   'camera': 'explorehd_camera'}

# The library is shared across vehicles; these tests sweep the BlueROV2's
# sub catalog only (the BlueBoat parts have their own suite). The t200
# props are shared and included here.
BOAT_PARTS = {'blueboat_chassis', 'blueboat_flag', 'blueboat_antenna_mast',
              'blueboat_payload_bracket', 'blueboat_ping_singlebeam_mount',
              'ping_singlebeam', 'basestation_antenna', 'surveyor_multibeam',
              'omniscan_450_sidescan',
              'm200_weedless_prop_ccw', 'm200_weedless_prop_cw', 't200_thruster'}


def catalog():
    """Part types the BlueROV2 sweep covers: the include list minus the boat's."""
    names = re.findall(r'/urdf/([a-z0-9_]+)\.urdf\.xacro', PARTS_XACRO.read_text())
    return sorted(set(names) - {'part_probe'} - BOAT_PARTS)


def make_config(parts=(), slots=(), base='bluerov2_chassis'):
    """Vehicle config yaml: chassis base, overrides/additions."""
    cfg = {'base': {'type': base, 'name': 'base_link'},
           'parts': [dict(p) for p in parts]}
    if slots:
        cfg['slots'] = [dict(s) for s in slots]
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


def test_default_config_is_the_default_loadout():
    """The shipped default builds 6 props + the camera from slot defaults."""
    root = generate_urdf(DEFAULT_CONFIG)
    assert manifest(root) == DEFAULT_LOADOUT
    assert set(DEFAULT_LOADOUT) <= link_names(root)


def test_vectored_spin_convention():
    """Check ArduSub chirality: ccw props on 1/2/5, cw on 3/4/6, continuous."""
    root = generate_urdf(DEFAULT_CONFIG)
    parts = manifest(root)
    for n, expected in ((1, 'ccw'), (2, 'ccw'), (3, 'cw'), (4, 'cw'),
                        (5, 'ccw'), (6, 'cw')):
        assert parts[f'thruster_{n}'] == f't200_prop_{expected}'
    joints = {j.get('name'): j.get('type') for j in root.findall('joint')}
    for n in range(1, 7):
        # Propellers declare a drive table, so they land on continuous joints.
        assert joints[f'thruster_{n}_joint'] == 'continuous'


def test_heavy_chassis_has_eight_thrusters():
    """The heavy base fits four corner verticals with balanced chirality."""
    root = generate_urdf(make_config(base='bluerov2_heavy_chassis'))
    parts = manifest(root)
    props = {n: t for n, t in parts.items() if n.startswith('thruster_')}
    assert len(props) == 8
    assert sum(t.endswith('_ccw') for t in props.values()) == 4


def test_slot_override_and_none():
    """A slot entry can empty a slot, swap it or fill one with no default."""
    root = generate_urdf(make_config([{'slot': 'camera', 'type': 'marinesitu_c3'},
                                      {'slot': 'dvl', 'type': 'dvl_a50'},
                                      {'slot': 'gripper', 'type': 'newton_gripper'}]))
    parts = manifest(root)
    assert parts['camera'] == 'marinesitu_c3'
    assert parts['dvl'] == 'dvl_a50'
    assert parts['gripper'] == 'newton_gripper'
    root = generate_urdf(make_config([{'slot': 'camera', 'type': 'none'}]))
    assert 'camera' not in manifest(root)


def test_gripper_part_carries_its_jaws():
    """The claw parts are multi body: housing plus two revolute jaws."""
    root = generate_urdf(make_config([{'slot': 'gripper', 'type': 'newton_gripper'}]))
    links = link_names(root)
    assert {'gripper', 'gripper_jaw_left', 'gripper_jaw_right'} <= links
    joints = {j.get('name'): j.get('type') for j in root.findall('joint')}
    assert joints['gripper_jaw_left_joint'] == 'revolute'


def test_slot_rejects_parts_that_do_not_fit():
    """A type outside the slot's accepts list fails the expansion."""
    expect_failure(make_config([{'slot': 'thruster_1', 'type': 't200_prop_cw'}]),
                   'does not fit')


def test_unknown_slot_on_base_fails():
    """A typo in the slot name fails the expansion naming it."""
    expect_failure(make_config([{'slot': 'nope', 'type': 'ping360'}]),
                   "unknown slot 'nope'")


def test_bare_on_key_is_rejected():
    """A bare on: key is the YAML boolean true; the expansion says so."""
    text = make_config() + 'slots:\n  - {on: base_link, name: x, xyz: "0 0 0"}\n'
    expect_failure(text, "bare 'on:' key")


def test_free_placement_and_adhoc_slot():
    """Free placements and ad hoc slots work as in the config schema."""
    root = generate_urdf(make_config(
        parts=[{'type': 'sonoptix_echo', 'name': 'sonar_l',
                'xyz': '0.14 0.16 -0.05', 'rpy': '0 0 0'},
               {'slot': 'light', 'type': 'roof_rack', 'name': 'bar'}],
        slots=[{'of': 'base_link', 'name': 'light', 'xyz': '0.2 0.1 0.1'}]))
    assert {'sonar_l', 'bar', 'base_link_light'} <= link_names(root)


def test_check_catches_what_the_expansion_cannot():
    """Entries matching nothing deeper down, unknown keys, clean configs."""
    cfg = yaml.safe_load(make_config([{'slot': 'dvl', 'of': 'nowhere', 'type': 'none'}]))
    found = assembly.problems(cfg, generate_urdf(yaml.safe_dump(cfg)))
    assert any("no instance named 'nowhere'" in f for f in found), found
    cfg = yaml.safe_load(make_config([{'slot': 'dvl', 'type': 'dvl_a50', 'bogus': 1}]))
    found = assembly.problems(cfg, generate_urdf(yaml.safe_dump(cfg)))
    assert any("['bogus']" in f for f in found), found
    cfg = yaml.safe_load(DEFAULT_CONFIG)
    assert assembly.problems(cfg, generate_urdf(DEFAULT_CONFIG)) == []


def test_catalog_covered_by_defaults_plus_overrides():
    """Every ROV catalog type is reachable via slots or free placement."""
    root = generate_urdf(make_config(
        parts=[{'slot': 'sonar', 'type': 'ping360'},
               {'slot': 'dvl', 'type': 'dvl_a50'},
               {'slot': 'gripper', 'type': 'newton_gripper'},
               {'slot': 'payload', 'type': 'payload_skid'},
               {'slot': 'rack', 'type': 'roof_rack'},
               {'type': 'sonoptix_echo', 'name': 'sonar_l', 'xyz': '0.14 0.16 -0.05'},
               {'type': 'omniscan_450_fs', 'name': 'sonar_r', 'xyz': '0.14 -0.16 -0.05'},
               {'type': 'marinesitu_c3', 'name': 'stereo', 'xyz': '-0.16 0 0.16'},
               {'type': 'sediment_sampler', 'name': 'sampler', 'xyz': '-0.26 0 -0.06'},
               {'type': 'bluerov2_heavy_chassis', 'name': 'trailer', 'xyz': '0 0 0.6'}]))
    assert set(manifest(root).values()) == set(catalog())


def test_mesh_references_resolve():
    """Every package:// mesh URI in the generated URDF exists on disk."""
    root = generate_urdf(make_config([{'slot': 'sonar', 'type': 'ping360'}],
                                     base='bluerov2_heavy_chassis'))
    uris = {m.get('filename') for m in root.findall('.//mesh')}
    assert uris
    for uri in uris:
        assert uri.startswith('package://bluerobotics_parts/'), uri
        rel = uri.replace('package://bluerobotics_parts/', '')
        assert (PARTS_SHARE / rel).is_file(), f'missing mesh {uri}'


def test_check_urdf_accepts_generated():
    """The generated URDF parses with urdfdom's check_urdf."""
    text = xacro_output(DEFAULT_CONFIG)
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(text)
        path = f.name
    out = subprocess.run(['check_urdf', path], capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, f'check_urdf rejected the URDF:\n{out.stderr}'
