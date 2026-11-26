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

import math
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


def _rpy(r, p, y):
    """Return the URDF rotation for roll, pitch, yaw: Rz(y) Ry(p) Rx(r)."""
    cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p), math.sin(p),
                              math.cos(y), math.sin(y))
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _frames(part):
    """Return a part's declared frames as {name: rotation matrix}."""
    text = (SHARE / 'urdf' / f'{part}.urdf.xacro').read_text()
    found = re.findall(r"(\w+)=dict\(xyz='[^']*', rpy='([^']*)'\)", text)
    return {name: _rpy(*map(float, rpy.split())) for name, rpy in found}


def _close(a, b):
    return all(abs(a[i][j] - b[i][j]) < 1e-6 for i in range(3) for j in range(3))


# x' = z, y' = -y, z' = x: an `_acoustic` frame's Z is its sensor's look
# direction (x) and its X is up, as marine_acoustic_msgs expects.
TO_ACOUSTIC = [[0, 0, 1], [0, -1, 0], [1, 0, 0]]


@pytest.mark.parametrize('part,acoustic,sensor', [
    ('sonoptix_echo_multibeam', 'acoustic', None),
    ('omniscan_450_sidescan', 'port_acoustic', 'port'),
    ('omniscan_450_sidescan', 'stbd_acoustic', 'stbd'),
    ('surveyor_multibeam', 'beam_acoustic', 'beam'),
])
def test_acoustic_frames_follow_their_sensor(part, acoustic, sensor):
    """Each `_acoustic` frame is its sensor's frame turned Z along the beam."""
    frames = _frames(part)
    base = frames[sensor] if sensor else _rpy(0, 0, 0)
    assert _close(frames[acoustic], _mul(base, TO_ACOUSTIC))


def test_sidescan_sides_look_out_and_down():
    """The port beam looks to port and down, the starboard beam mirrors it."""
    frames = _frames('omniscan_450_sidescan')
    port = [row[0] for row in frames['port']]
    stbd = [row[0] for row in frames['stbd']]
    assert port[1] > 0.9 and port[2] < -0.2, port
    # 20 degrees down, Cerulean's recommended mounting.
    assert abs(math.degrees(math.asin(-port[2])) - 20.0) < 1e-6, port
    assert abs(port[0]) < 1e-6
    assert all(abs(a - b) < 1e-6 for a, b in zip(stbd, (port[0], -port[1], port[2])))


def test_profiler_beam_looks_straight_down():
    """The Surveyor's beam frame looks down, its fan across the track."""
    beam = _frames('surveyor_multibeam')['beam']
    assert [round(row[0], 6) for row in beam] == [0, 0, -1]
    assert [round(row[1], 6) for row in beam] == [0, 1, 0]


def test_sonar_settings_are_checked():
    """`sonar:` belongs only on a sonar part, and holds plain values."""
    from bluerobotics_parts.sonar import entry_problems
    assert entry_problems({'type': 'surveyor_multibeam', 'sonar': {'range_max': 30}}, 'e') == []
    assert entry_problems({'type': 'ping360', 'sonar': {'range_max': 30}}, 'e')
    assert entry_problems({'type': 'surveyor_multibeam',
                           'sonar': {'range': {'min': 1, 'max': 30}}}, 'e')
    assert entry_problems({'type': 'surveyor_multibeam', 'sonar': 30}, 'e')
    assert entry_problems({'type': 'ping360'}, 'e') == []


def test_sonar_entries():
    """Each sonar sensor gets a kai_sonar_bridge entry with its kind and frame."""
    from bluerobotics_parts.sonar import sonar_entries
    instances = [('sonoptix_echo_multibeam', 'sonar_forward'),
                 ('omniscan_450_sidescan', 'sidescan'), ('surveyor_multibeam', 'profiler'),
                 ('ping_singlebeam', 'ping')]
    params = sonar_entries({'topic_namespace': 'boat'}, instances, 'x')['/**']['ros__parameters']
    assert params['gz_topics'] == ['/boat/sonar_forward/image', '/boat/sidescan/port/image',
                                   '/boat/sidescan/stbd/image', '/boat/profiler/detections']
    assert params['ros_topics'] == params['gz_topics']
    assert params['frame_ids'] == ['boat/sonar_forward_acoustic',
                                   'boat/sidescan_port_acoustic',
                                   'boat/sidescan_stbd_acoustic',
                                   'boat/profiler_beam_acoustic']
    assert params['kinds'] == ['image', 'image', 'image', 'detections']
    # With no topic_namespace in the config, the vehicle's default names it.
    params = sonar_entries({}, instances[:1], 'rov')['/**']['ros__parameters']
    assert params['gz_topics'] == ['/rov/sonar_forward/image']


def test_no_sonar_no_lists_and_no_bridge(tmp_path):
    """Without a sonar the parameters have no lists, and the launch starts no bridge."""
    from bluerobotics_parts.sonar import params_have_sonars, sonar_entries, write_bridge_params
    assert 'gz_topics' not in sonar_entries({}, [], 'rov')['/**']['ros__parameters']
    none, one = tmp_path / 'none.yaml', tmp_path / 'one.yaml'
    write_bridge_params(none, {}, [('ping360', 'sonar')], 'rov', 'test')
    write_bridge_params(one, {}, [('sonoptix_echo_multibeam', 'sonar')], 'rov', 'test')
    assert not params_have_sonars(none)
    assert params_have_sonars(one)
    assert one.read_text().startswith('# GENERATED by test')


def test_sonar_setting_keys_are_checked():
    """A misspelled `sonar:` key is refused when the model is generated, with a hint."""
    from bluerobotics_parts.sonar import entry_problems
    found = entry_problems({'type': 'sonoptix_echo_multibeam', 'sonar': {'range_mx': 15}}, 'e')
    assert len(found) == 1 and "'range_max'" in found[0]
    assert entry_problems({'type': 'sonoptix_echo_multibeam',
                           'sonar': {'range_max': 15, 'rate': 5, 'gain': 'auto'}}, 'e') == []
    for rate in (0, -1, 'fast', True, float('nan'), float('inf')):
        assert entry_problems({'type': 'sonoptix_echo_multibeam', 'sonar': {'rate': rate}}, 'e')
