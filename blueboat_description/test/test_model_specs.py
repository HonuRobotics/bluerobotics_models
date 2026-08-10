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
"""The installed URDF carries a model specs comment that matches the model."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest
import yaml

SHARE = Path(get_package_share_directory('blueboat_description'))
URDF = SHARE / 'urdf' / 'blueboat.urdf'
WATER_DENSITY = 1025.0


def spec(text, label):
    """Value string of a labelled row inside the specs comment."""
    match = re.search(rf'^  {label}: +(.+)$', text, re.M)
    assert match, f'specs comment misses the {label!r} row'
    return match.group(1)


def test_specs_comment_matches_the_model():
    """Stamped mass, displacement and net buoyancy agree with the XML."""
    text = URDF.read_text()
    assert 'model specs' in text, 'installed URDF is not stamped'
    root = ET.fromstring(text)  # the comment must not break parsing
    total = sum(float(m.get('value'))
                for m in root.findall('.//inertial/mass'))
    stamped_mass = float(spec(text, 'total mass').split()[0])
    assert stamped_mass == pytest.approx(total, abs=5e-4)
    volume = 0.0
    for box in root.findall('.//collision/geometry/box'):
        lx, ly, lz = (float(v) for v in box.get('size').split())
        volume += lx * ly * lz
    stamped_volume = float(spec(text, 'displaced volume').split()[0])
    assert stamped_volume == pytest.approx(volume, abs=5e-7)
    net = float(spec(text, 'reserve buoyancy').split()[0])
    assert net == pytest.approx(WATER_DENSITY * volume - total, abs=5e-4)


def test_specs_comment_reports_the_loadout():
    """The accessories row reflects the shipped default config."""
    text = URDF.read_text()
    cfg = yaml.safe_load((SHARE / 'config' / 'blueboat.yaml').read_text())
    accessories = spec(text, 'accessories')
    for accessory in cfg.get('accessories') or []:
        assert accessory['type'] in accessories
