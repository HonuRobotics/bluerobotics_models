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
"""The installed URDF carries a specs stamp consistent with the declaration."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest
import yaml

SHARE = Path(get_package_share_directory('bluerov2_description'))
URDF = SHARE / 'urdf' / 'bluerov2.urdf'


def spec(text, label):
    """Value string of a labelled row inside the specs comment."""
    match = re.search(rf'^  {label}: +(.+)$', text, re.M)
    assert match, f'specs comment misses the {label!r} row'
    return match.group(1)


def test_specs_stamp_matches_model_and_declaration():
    """Stamped mass sums the parts; displacement realizes the declaration."""
    text = URDF.read_text()
    assert 'model specs' in text, 'installed URDF is not stamped'
    root = ET.fromstring(text)  # the comment must not break parsing
    total = sum(float(m.get('value'))
                for m in root.findall('.//inertial/mass'))
    stamped_mass = float(spec(text, 'total mass').split()[0])
    assert stamped_mass == pytest.approx(total, abs=5e-4)
    # Displacement is declared (realized on the Gazebo side), so the stamp
    # must solve fluid_density * volume = mass + net_buoyancy exactly.
    cfg = yaml.safe_load((SHARE / 'config' / 'bluerov2.yaml').read_text())
    declared = cfg.get('buoyancy') or {}
    density = float(declared.get('fluid_density', 1025.0))
    net_declared = float(declared.get('net_buoyancy', 0.002))
    stamped_volume = float(spec(text, 'displaced volume').split()[0])
    assert stamped_volume * density == pytest.approx(total + net_declared,
                                                     abs=2e-3)
    net = float(spec(text, 'net buoyancy').split()[0])
    assert net == pytest.approx(net_declared, abs=1e-3)
    # CoB offset row equals the declared BG vector.
    cob_declared = [float(v) for v in
                    str(declared.get('cob_offset', '0 0 0.046')).split()]
    offset = [float(v) for v in
              re.findall(r'-?\d+\.\d+', spec(text, 'cob offset'))[:3]]
    for k in range(3):
        assert offset[k] == pytest.approx(cob_declared[k], abs=1e-3)


def test_specs_stamp_reports_the_loadout():
    """The parts row reflects the resolved default loadout, defaults included."""
    text = URDF.read_text()
    parts = spec(text, 'parts')
    for expected in ('bluerov2_chassis', 't200_prop_ccw', 'explorehd_camera'):
        assert expected in parts
