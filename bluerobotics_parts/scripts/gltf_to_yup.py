#!/usr/bin/env python3
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
Convert a Z-up .glb (as some exporters write it) to the glTF standard Y-up.

glTF is Y-up by specification. RViz and other ROS tools rotate glTF meshes
from Y-up to ROS Z-up on load; a file whose vertex data is already Z-up
therefore shows up rolled 90 degrees in RViz (Gazebo applies no conversion
and shows the data as is, which hides the problem). This tool bakes the
rotation (x, y, z) -> (x, z, -y) into every POSITION, NORMAL and TANGENT
accessor of the binary glTF, in place, so the file conforms to the spec.

Run once on a delivery that was exported Z-up; running it on a compliant
file would rotate it the wrong way, so check in a viewer first (or compare
with the collision SDF: the mesh extent that is "up" in the SDF must be
along y in the glb).

    gltf_to_yup.py models/<part>/<part>.visual.glb [more.glb ...]
"""

import json
import pathlib
import struct
import sys

import numpy as np

COMPONENT_DTYPES = {5126: np.float32}
ROTATED = ('POSITION', 'NORMAL', 'TANGENT')


def convert(path):
    data = bytearray(path.read_bytes())
    magic, version, _ = struct.unpack_from('<III', data, 0)
    if magic != 0x46546C67 or version != 2:
        sys.exit(f'{path}: not a binary glTF 2.0 file')
    json_len, json_type = struct.unpack_from('<I4s', data, 12)
    if json_type != b'JSON':
        sys.exit(f'{path}: first chunk is not JSON')
    doc = json.loads(bytes(data[20:20 + json_len]))
    bin_len, bin_type = struct.unpack_from('<I4s', data, 20 + json_len)
    if bin_type != b'BIN\x00':
        sys.exit(f'{path}: second chunk is not BIN')
    bin_off = 28 + json_len

    done = set()
    for mesh in doc.get('meshes', []):
        for prim in mesh.get('primitives', []):
            for attr, idx in prim.get('attributes', {}).items():
                if attr not in ROTATED or idx in done:
                    continue
                done.add(idx)
                acc = doc['accessors'][idx]
                view = doc['bufferViews'][acc['bufferView']]
                if acc['componentType'] not in COMPONENT_DTYPES:
                    sys.exit(f'{path}: {attr} accessor is not float32')
                width = {'VEC3': 3, 'VEC4': 4}[acc['type']]
                stride = view.get('byteStride') or 4 * width
                off = bin_off + view.get('byteOffset', 0) + acc.get('byteOffset', 0)
                for i in range(acc['count']):
                    at = off + i * stride
                    x, y, z = struct.unpack_from('<fff', data, at)
                    struct.pack_into('<fff', data, at, x, z, -y)
                if attr == 'POSITION':
                    lo, hi = acc['min'], acc['max']
                    acc['min'] = [lo[0], lo[2], -hi[1]]
                    acc['max'] = [hi[0], hi[2], -lo[1]]

    # Node transforms live in the same space as the vertex data: rotate
    # translations the same way; rotation nodes would need conjugating and
    # matrices decomposing, which no delivery has used, so refuse loudly.
    for node in doc.get('nodes', []):
        if 'rotation' in node or 'matrix' in node:
            sys.exit(f'{path}: node with a rotation/matrix transform; convert this one by hand')
        if 'translation' in node:
            x, y, z = node['translation']
            node['translation'] = [x, z, -y]

    payload = json.dumps(doc, separators=(',', ':')).encode()
    payload += b' ' * ((4 - len(payload) % 4) % 4)
    out = bytearray()
    out += struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(payload) + 8 + bin_len)
    out += struct.pack('<I4s', len(payload), b'JSON') + payload
    out += struct.pack('<I4s', bin_len, b'BIN\x00') + bytes(data[bin_off:bin_off + bin_len])
    path.write_bytes(out)
    return len(done)


def main(argv=None):
    args = (argv if argv is not None else sys.argv[1:])
    if not args or args[0] in ('-h', '--help'):
        sys.exit(__doc__)
    for name in args:
        path = pathlib.Path(name)
        n = convert(path)
        print(f'{path}: rotated {n} accessors to Y-up')


if __name__ == '__main__':
    main()
