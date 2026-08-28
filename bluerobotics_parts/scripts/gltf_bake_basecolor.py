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
Give every textured glTF material a base color texture.

A GLB material whose only texture is a normal (or roughness, occlusion,
emissive) map is valid glTF, but rviz_rendering up to at least 15.2.2
assumes any material texture is a diffuse map: the failed diffuse lookup
leaves an empty texture name whose resolved path is the mesh's directory,
and the resource retriever exception aborts RViz (ros2/rviz, unfixed as of
2026-08). Injecting a 1x1 white base color texture into such materials is
visually a no-op (the spec multiplies baseColorFactor by the texture) and
keeps the delivered maps working everywhere else.

Usage: gltf_bake_basecolor.py <file.glb> [more.glb ...]

Rewrites each file in place only when a material needs the injection.
"""

import json
import struct
import sys
import zlib

OTHER_TEXTURES = ('normalTexture', 'occlusionTexture', 'emissiveTexture')

# 1x1 opaque white RGBA PNG, built from primitives so there is no binary
# blob to trust in the repo.


def white_png():
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data)))
    ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)
    idat = zlib.compress(b'\x00\xff\xff\xff\xff')
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', idat) + chunk(b'IEND', b''))


def needs_basecolor(material):
    pbr = material.get('pbrMetallicRoughness', {})
    if 'baseColorTexture' in pbr:
        return False
    textured = any(k in material for k in OTHER_TEXTURES)
    return textured or 'metallicRoughnessTexture' in pbr


def bake(path):
    """Return True when the file was rewritten."""
    data = open(path, 'rb').read()
    magic, _, _ = struct.unpack('<III', data[:12])
    assert magic == 0x46546C67, f'{path} is not a GLB'
    json_len = struct.unpack('<I', data[12:16])[0]
    gltf = json.loads(data[20:20 + json_len])
    bin_start = 20 + json_len
    binary = b''
    if bin_start < len(data):
        bin_len = struct.unpack('<I', data[bin_start:bin_start + 4])[0]
        binary = data[bin_start + 8:bin_start + 8 + bin_len]

    fixable = [m for m in gltf.get('materials', []) if needs_basecolor(m)]
    if not fixable:
        return False

    binary += b'\x00' * (-len(binary) % 4)
    png = white_png()
    gltf.setdefault('bufferViews', []).append(
        {'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(png)})
    binary += png
    gltf.setdefault('images', []).append(
        {'bufferView': len(gltf['bufferViews']) - 1, 'mimeType': 'image/png',
         'name': 'baked_white_basecolor'})
    gltf.setdefault('textures', []).append({'source': len(gltf['images']) - 1})
    texture_index = len(gltf['textures']) - 1
    for material in fixable:
        other = next((material[k] for k in OTHER_TEXTURES if k in material),
                     material.get('pbrMetallicRoughness', {}).get(
                         'metallicRoughnessTexture', {}))
        material.setdefault('pbrMetallicRoughness', {})['baseColorTexture'] = \
            {'index': texture_index, 'texCoord': other.get('texCoord', 0)}
    gltf['buffers'][0]['byteLength'] = len(binary)

    payload = json.dumps(gltf, separators=(',', ':')).encode()
    payload += b' ' * (-len(payload) % 4)
    out = struct.pack('<III', 0x46546C67, 2,
                      12 + 8 + len(payload) + 8 + len(binary))
    out += struct.pack('<I', len(payload)) + b'JSON' + payload
    out += struct.pack('<I', len(binary)) + b'BIN\x00' + binary
    open(path, 'wb').write(out)
    return True


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for path in sys.argv[1:]:
        print(f'{path}: {"baked" if bake(path) else "already fine"}')


if __name__ == '__main__':
    main()
