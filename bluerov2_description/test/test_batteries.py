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
"""Battery and buoyancy trim tests for the BlueROV2."""

from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix
from ament_index_python.packages import get_package_share_directory
import pytest

SHARE = Path(get_package_share_directory('bluerov2_description'))
TOP_XACRO = SHARE / 'urdf' / 'bluerov2.urdf.xacro'
CATALOG = SHARE / 'config' / 'batteries.yaml'
VALIDATOR = (Path(get_package_prefix('bluerov2_description'))
             / 'lib' / 'bluerov2_description' / 'validate_battery_config.py')

WATER_DENSITY = 1025.0
PACK_18AH_MASS = 1.400
PACK_10AH_MASS = 0.750
BASE_MASS = 8.0
THRUSTERS_MASS = 6 * 0.344


def make_config(batteries=None, extra=''):
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
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
        f.write(config_text)
        config_path = f.name
    out = subprocess.run(
        [sys.executable, str(VALIDATOR), '--vehicle', 'bluerov2',
         '--config', config_path, '--catalog', str(CATALOG)],
        capture_output=True, text=True, timeout=30)
    return out.returncode, out.stderr


def total_mass(root):
    return sum(float(m.get('value'))
               for m in root.findall('.//inertial/mass'))


def displacement(root):
    """Displaced mass (kg) of base_link's buoyancy box at full submersion."""
    base = next(li for li in root.findall('link')
                if li.get('name') == 'base_link')
    box = base.find('./collision/geometry/box')
    lx, ly, lz = (float(v) for v in box.get('size').split())
    return WATER_DENSITY * lx * ly * lz


def test_default_battery_in_the_tube():
    """Omitting `batteries:` mounts one 18Ah pack centred in the tube."""
    root = generate_urdf(make_config())
    link = next(li for li in root.findall('link')
                if li.get('name') == 'battery_tube')
    assert float(link.find('./inertial/mass').get('value')) == \
        pytest.approx(PACK_18AH_MASS)
    assert link.find('collision') is None
    assert link.find('visual') is None
    joint = next(j for j in root.findall('joint')
                 if j.get('name') == 'battery_tube_joint')
    assert [float(v) for v in joint.find('origin').get('xyz').split()] == \
        pytest.approx([0.0, 0.0, -0.08])


def test_default_total_mass_preserved():
    """De-baking kept the standard all-up mass at ~11.5 kg with the pack."""
    total = total_mass(generate_urdf(make_config()))
    assert total == pytest.approx(BASE_MASS + THRUSTERS_MASS
                                  + PACK_18AH_MASS)


def test_neutral_trim_balances_displacement_and_mass():
    """Neutral trim balances displacement and all-up mass exactly."""
    root = generate_urdf(make_config(extra='buoyancy_trim: neutral\n'))
    assert displacement(root) == pytest.approx(total_mass(root), rel=1e-6)


def test_neutral_plus_is_slightly_positive():
    root = generate_urdf(make_config())
    assert displacement(root) > total_mass(root)
    assert displacement(root) == pytest.approx(total_mass(root), rel=1e-3)


def test_numeric_trim_shifts_net_buoyancy():
    """A signed trim in kg moves displacement by exactly that much."""
    root = generate_urdf(make_config(extra='buoyancy_trim: -0.5\n'))
    assert displacement(root) == pytest.approx(total_mass(root) - 0.5,
                                               rel=1e-6)


def test_lighter_pack_shrinks_the_buoyancy_box():
    """Swapping to the LiPo travel pack reduces mass AND sizing follows."""
    heavy = generate_urdf(make_config(extra='buoyancy_trim: neutral\n'))
    light = generate_urdf(make_config(
        ['{pack: br_lipo_10ah, slot: tube}'],
        extra='buoyancy_trim: neutral\n'))
    delta_mass = total_mass(heavy) - total_mass(light)
    assert delta_mass == pytest.approx(PACK_18AH_MASS - PACK_10AH_MASS)
    assert displacement(heavy) - displacement(light) == \
        pytest.approx(delta_mass, rel=1e-6)


def test_custom_pack_resizes_the_buoyancy_box():
    """A third party pack's mass lands on the link AND the box sizing."""
    base = generate_urdf(make_config(extra='buoyancy_trim: neutral\n'))
    custom = generate_urdf(make_config(
        ['{custom_pack: {mass: 2.0, size: [0.14, 0.07, 0.06]}, slot: tube}'],
        extra='buoyancy_trim: neutral\n'))
    link = next(li for li in custom.findall('link')
                if li.get('name') == 'battery_tube')
    assert float(link.find('./inertial/mass').get('value')) == \
        pytest.approx(2.0)
    delta = total_mass(custom) - total_mass(base)
    assert delta == pytest.approx(2.0 - PACK_18AH_MASS)
    assert displacement(custom) - displacement(base) == \
        pytest.approx(delta, rel=1e-6)


def test_in_tube_offset_trims_pitch():
    root = generate_urdf(make_config(
        ['{pack: br_liion_18ah, slot: tube, offset: {x: 0.05}}']))
    joint = next(j for j in root.findall('joint')
                 if j.get('name') == 'battery_tube_joint')
    assert [float(v) for v in joint.find('origin').get('xyz').split()] == \
        pytest.approx([0.05, 0.0, -0.08])


@pytest.mark.parametrize('config,fragment', [
    (make_config(['{pack: br_liion_18ah, slot: tube}',
                  '{pack: br_lipo_10ah, slot: tube}']), 'at most 1'),
    (make_config(['{pack: br_liion_18ah, slot: hull}']), 'unknown slot'),
    (make_config(extra='buoyancy_trim: 2.5\n'), 'sanity limit'),
    (make_config(extra='buoyancy_trim: floaty\n'), 'must be'),
    (make_config(['{pack: br_liion_18ah, custom_pack: {mass: 1.0, '
                  'size: [0.1, 0.05, 0.05]}, slot: tube}']), 'exactly one'),
    (make_config(['{slot: tube}']), 'exactly one'),
    (make_config(['{pack: br_liion_18ah, slot: tube, ofset: {x: 0.01}}']),
     'unknown keys'),
    (make_config(['{custom_pack: {size: [0.1, 0.05, 0.05]}, slot: tube}']),
     'positive `mass`'),
    (make_config(['{custom_pack: {mass: 1.0, size: [0.1, 0.05]}, '
                  'slot: tube}']), 'needs `size:'),
])
def test_validator_rejects(config, fragment):
    code, stderr = run_validator(config)
    assert code != 0
    assert fragment in stderr, stderr


def test_validator_warns_on_discontinued_pack():
    """The retired 15.6Ah pack still generates, but warns at validation."""
    code, stderr = run_validator(make_config(
        ['{pack: br_liion_15_6ah, slot: tube}']))
    assert code == 0
    assert 'discontinued' in stderr, stderr


def test_validator_accepts_default():
    assert run_validator(make_config())[0] == 0
