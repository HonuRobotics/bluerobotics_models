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
"""
Catalog self test: every part stands on its own.

The vehicle suites sweep only their own parts; the guarantee that EVERY
catalog part is well formed lives here, next to the parts. Each part runs
through the part_probe harness (four mounts: standalone, twin instances,
collision off, part on part), the result must satisfy urdfdom, and every
mesh it references must ship.
"""

from pathlib import Path
import re
import subprocess
import tempfile

from ament_index_python.packages import get_package_share_directory
import pytest

SHARE = Path(get_package_share_directory('bluerobotics_parts'))
PARTS_XACRO = SHARE / 'urdf' / 'parts.xacro'
PROBE = SHARE / 'urdf' / 'part_probe.urdf.xacro'


def catalog():
    """Part types the library offers: the include list of parts.xacro."""
    names = re.findall(r'/urdf/([a-z0-9_]+)\.urdf\.xacro', PARTS_XACRO.read_text())
    return sorted(set(names) - {'part_probe'})


@pytest.mark.parametrize('part', catalog())
def test_part_probe(part):
    """The part instantiates four ways, parses, and its meshes ship."""
    out = subprocess.run(
        ['xacro', str(PROBE), f'part:={part}'],
        capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, (
        f'{part} failed the probe:\n{out.stderr[-800:]}')
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(out.stdout)
        path = f.name
    check = subprocess.run(['check_urdf', path], capture_output=True,
                           text=True, timeout=60)
    assert check.returncode == 0, (
        f'check_urdf rejected {part}:\n{check.stderr}')
    for uri in set(re.findall(r'package://bluerobotics_parts/(\S+?)"', out.stdout)):
        assert (SHARE / uri).is_file(), f'{part}: missing mesh {uri}'


def test_catalog_includes_every_part_file():
    """Every part file in urdf/ is included by parts.xacro (no orphans)."""
    files = {p.stem.replace('.urdf', '') for p in (SHARE / 'urdf').glob('*.urdf.xacro')}
    files -= {'part_probe'}
    assert files == set(catalog()), (
        f'catalog drift: not included {files - set(catalog())}, '
        f'missing files {set(catalog()) - files}')


def test_glb_textured_materials_have_a_base_color_texture():
    """
    A material with only a normal (or similar) map aborts RViz.

    rviz_rendering up to at least 15.2.2 assumes every material texture is
    a diffuse map; the failed lookup resolves to the mesh's directory and
    the resource retriever exception terminates RViz. Such deliveries are
    fixed by injecting a visually neutral base color texture (a 1x1 white
    pixel: the spec multiplies baseColorFactor by it, so nothing changes).
    """
    import json
    import struct
    bad = []
    for glb in sorted((SHARE / 'models').rglob('*.glb')):
        data = glb.read_bytes()
        json_len = struct.unpack('<I', data[12:16])[0]
        gltf = json.loads(data[20:20 + json_len])
        for material in gltf.get('materials', []):
            pbr = material.get('pbrMetallicRoughness', {})
            textured = ('metallicRoughnessTexture' in pbr or any(
                k in material for k in
                ('normalTexture', 'occlusionTexture', 'emissiveTexture')))
            if textured and 'baseColorTexture' not in pbr:
                bad.append(f'{glb.name}: {material.get("name", "unnamed")}')
    assert not bad, ('materials without a base color texture crash RViz; '
                     f'bake a neutral base color texture into: {bad}')
