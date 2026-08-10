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
"""Battery loadout tests: catalog packs, slots, offsets and the validator."""

from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix
from ament_index_python.packages import get_package_share_directory
import pytest

SHARE = Path(get_package_share_directory('blueboat_description'))
TOP_XACRO = SHARE / 'urdf' / 'blueboat.urdf.xacro'
CATALOG = SHARE / 'config' / 'batteries.yaml'
VALIDATOR = (Path(get_package_prefix('blueboat_description'))
             / 'lib' / 'blueboat_description' / 'validate_battery_config.py')

PACK_18AH_MASS = 1.400
HULL_MASS = 27.2
THRUSTER_MASS = 0.344
PING_MASS = 0.2


def make_config(batteries=None, extra=''):
    """Vehicle-config yaml text with no accessories and the given loadout."""
    text = 'accessories: []\n' + extra
    if batteries is not None:
        text += 'batteries:\n' + ''.join(f'  - {b}\n' for b in batteries)
    return text


def generate_urdf(config_text):
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        ['xacro', str(TOP_XACRO), f'config_file:={config_path}',
         f'batteries_file:={CATALOG}'],
        capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, (
        f'xacro failed ({out.returncode})\n--- stderr ---\n{out.stderr}')
    return ET.fromstring(out.stdout)


def run_validator(config_text):
    """Run the validator on a config; return (returncode, stderr)."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        [sys.executable, str(VALIDATOR), '--vehicle', 'blueboat',
         '--config', config_path, '--catalog', str(CATALOG)],
        capture_output=True, text=True, timeout=30)
    return out.returncode, out.stderr


def battery_links(root):
    return {li.get('name'): li for li in root.findall('link')
            if li.get('name').startswith('battery_')}


def joint_origin(root, joint_name):
    joint = next(j for j in root.findall('joint')
                 if j.get('name') == joint_name)
    return [float(v) for v in joint.find('origin').get('xyz').split()]


def test_default_loadout_one_pack_per_hull():
    """Omitting `batteries:` yields the two as-sold 18Ah packs, mid_fwd."""
    root = generate_urdf(make_config())
    links = battery_links(root)
    assert set(links) == {'battery_port_mid_fwd', 'battery_stbd_mid_fwd'}
    for link in links.values():
        mass = float(link.find('./inertial/mass').get('value'))
        assert mass == pytest.approx(PACK_18AH_MASS)
    assert joint_origin(root, 'battery_port_mid_fwd_joint') == \
        pytest.approx([0.06, 0.30, -0.27])
    assert joint_origin(root, 'battery_stbd_mid_fwd_joint') == \
        pytest.approx([0.06, -0.30, -0.27])


def test_default_total_mass_preserved():
    """De-baking the hull mass kept the all-up default vehicle at 30 kg + motors."""
    root = generate_urdf(make_config())
    total = sum(float(m.get('value'))
                for m in root.findall('.//inertial/mass'))
    assert total == pytest.approx(HULL_MASS + 2 * PACK_18AH_MASS
                                  + 2 * THRUSTER_MASS)


def test_batteries_are_inertia_only():
    """No collision (phantom displacement) and no visual on battery links."""
    root = generate_urdf(make_config())
    for name, link in battery_links(root).items():
        assert link.find('collision') is None, f'{name} has a collision'
        assert link.find('visual') is None, f'{name} has a visual'


def test_offset_moves_the_pack():
    """An in-slot x offset lands on the fixed joint origin."""
    root = generate_urdf(make_config(
        ['{pack: br_liion_18ah, slot: port_aft, offset: {x: 0.03}}',
         '{pack: br_liion_18ah, slot: stbd_aft}']))
    assert joint_origin(root, 'battery_port_aft_joint') == \
        pytest.approx([-0.38 + 0.03, 0.30, -0.27])


def test_custom_pack_mass():
    """A third party pack defined inline carries its own mass."""
    root = generate_urdf(make_config(
        ['{custom_pack: {mass: 1.0, size: [0.14, 0.07, 0.06]}, '
         'slot: port_mid_fwd, name: mypack}',
         '{pack: br_liion_18ah, slot: stbd_mid_fwd}']))
    link = battery_links(root)['battery_mypack']
    assert float(link.find('./inertial/mass').get('value')) == \
        pytest.approx(1.0)


def test_validator_accepts_default_and_full_loadout():
    assert run_validator(make_config())[0] == 0
    full = [f'{{pack: br_liion_18ah, slot: {side}_{pos}}}'
            for side in ('port', 'stbd')
            for pos in ('fwd', 'mid_fwd', 'mid_aft', 'aft')]
    assert run_validator(make_config(full))[0] == 0


@pytest.mark.parametrize('batteries,fragment', [
    (['{pack: br_liion_18ah, slot: nowhere}'], 'unknown slot'),
    (['{pack: br_liion_18ah, slot: port_fwd}',
      '{pack: br_liion_18ah, slot: port_fwd}'], 'already holds'),
    (['{pack: no_such_pack, slot: port_fwd}'], 'unknown pack'),
    (['{pack: br_liion_18ah, slot: port_fwd, offset: {y: 0.1}}'],
     'only allows an x offset'),
    (['{pack: br_liion_18ah, slot: port_fwd, offset: {x: 0.2}}'],
     'outside the'),
    (['{custom_pack: {mass: 1.0, size: [0.5, 0.1, 0.1]}, slot: port_fwd}'],
     'does not fit'),
    ([], 'not a runnable vehicle'),
    (['{pack: br_liion_18ah, custom_pack: {mass: 1.0, '
      'size: [0.1, 0.05, 0.05]}, slot: port_fwd}'], 'exactly one'),
    (['{slot: port_fwd}'], 'exactly one'),
    (['{pack: br_liion_18ah, slot: port_fwd, ofset: {x: 0.01}}'],
     'unknown keys'),
    (['{custom_pack: not_a_mapping, slot: port_fwd}'], 'must be a mapping'),
    (['{custom_pack: {mass: -1.0, size: [0.1, 0.05, 0.05]}, slot: port_fwd}'],
     'positive `mass`'),
    (['{custom_pack: {mass: 1.0, size: [0.1, 0.05]}, slot: port_fwd}'],
     'needs `size:'),
    (['{pack: br_liion_18ah, slot: port_fwd, name: twin}',
      '{pack: br_liion_18ah, slot: stbd_fwd, name: twin}'],
     'duplicate battery name'),
])
def test_validator_rejects(batteries, fragment):
    code, stderr = run_validator(make_config(batteries))
    assert code != 0
    assert fragment in stderr, stderr


def test_validator_rejects_too_many():
    nine = ['{pack: br_liion_18ah, slot: port_fwd}'] * 9
    code, stderr = run_validator(make_config(nine))
    assert code != 0
    assert 'at most 8' in stderr, stderr


def test_validator_rejects_buoyancy_trim_on_the_boat():
    code, stderr = run_validator(make_config(extra='buoyancy_trim: 0.1\n'))
    assert code != 0
    assert 'loadout placement' in stderr, stderr


def test_validator_warns_on_imbalance_and_discontinued():
    """Heavy port list warns but passes; discontinued pack warns too."""
    code, stderr = run_validator(make_config(
        ['{pack: br_liion_18ah, slot: port_fwd}',
         '{pack: br_liion_18ah, slot: port_mid_fwd}',
         '{pack: br_liion_18ah, slot: port_aft}',
         '{pack: br_liion_18ah, slot: stbd_fwd}']))
    assert code == 0
    assert 'heel' in stderr, stderr
    code, stderr = run_validator(make_config(
        ['{pack: br_liion_15_6ah, slot: port_fwd}',
         '{pack: br_liion_15_6ah, slot: stbd_fwd}']))
    assert code == 0
    assert 'discontinued' in stderr, stderr
