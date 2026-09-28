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
Regenerate the worked example in docs/reference/GLB_INVENTORY.md.

Writes the smallest file that still exercises every term in that
document's glossary: one scene holding one node, which places one mesh,
which groups one primitive, which reads four accessors through four
buffer views of one buffer and names one material, which reads one
texture, which pairs one sampler with one image.

    docs/_tools/make_minimal_gltf.py

Two outputs, the same asset in both of glTF's containers:

  docs/reference/minimal.gltf  JSON with the buffer as a base64 data URI,
                               which is the form meant to be read
  docs/reference/minimal.glb   the binary container, which is the form the
                               delivered parts use and the only one
                               glb_inventory.py reads

The geometry is a one metre square in the XY plane facing +Z, authored
Y up like the deliveries. It is a teaching artifact, not a part: nothing
installs it and no world references it.
"""

import base64
import io
import json
import pathlib
import struct

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "reference"

# Four corners, counter-clockwise seen from +Z, so the winding faces the
# viewer. glTF puts the UV origin at the top left with v running down, so
# the v coordinates are the mirror of the y ones.
POSITIONS = np.array(
    [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float32
)
NORMALS = np.array([[0, 0, 1]] * 4, dtype=np.float32)
TEXCOORDS = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float32)
INDICES = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint16)

# 2x2 base colour, one texel per corner, so a viewer shows which way is up.
SWATCH = [(0, 90, 156), (0, 130, 200), (200, 200, 200), (120, 120, 120)]


def base_color_png():
    image = Image.new("RGB", (2, 2))
    image.putdata(SWATCH)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def pad4(data, fill=b"\x00"):
    return data + fill * (-len(data) % 4)


def build():
    """Return (gltf dict without a buffer uri, buffer bytes)."""
    png = base_color_png()
    blocks = [
        (POSITIONS.tobytes(), 34962),  # ARRAY_BUFFER
        (NORMALS.tobytes(), 34962),
        (TEXCOORDS.tobytes(), 34962),
        (INDICES.tobytes(), 34963),  # ELEMENT_ARRAY_BUFFER
        (png, None),
    ]

    buffer, views = bytearray(), []
    for payload, target in blocks:
        views.append(
            {
                "buffer": 0,
                "byteOffset": len(buffer),
                "byteLength": len(payload),
                **({"target": target} if target else {}),
            }
        )
        buffer += pad4(payload)

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "Honu Robotics docs/_tools/make_minimal_gltf.py",
        },
        "scene": 0,
        "scenes": [{"name": "minimal", "nodes": [0]}],
        "nodes": [{"name": "quad", "mesh": 0}],
        "meshes": [
            {
                "name": "quad",
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 0,
                            "NORMAL": 1,
                            "TEXCOORD_0": 2,
                        },
                        "indices": 3,
                        "material": 0,
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "Quad",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.8,
                },
            }
        ],
        "textures": [{"sampler": 0, "source": 0}],
        # LINEAR magnification, trilinear minification, repeat on both axes.
        "samplers": [
            {"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}
        ],
        "images": [
            {"name": "Albedo-Quad", "mimeType": "image/png", "bufferView": 4}
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": len(POSITIONS),
                "type": "VEC3",
                # Required on POSITION, which is why a reader can get the
                # bounding box without touching the binary.
                "min": POSITIONS.min(axis=0).tolist(),
                "max": POSITIONS.max(axis=0).tolist(),
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": len(NORMALS),
                "type": "VEC3",
            },
            {
                "bufferView": 2,
                "componentType": 5126,
                "count": len(TEXCOORDS),
                "type": "VEC2",
            },
            {
                "bufferView": 3,
                "componentType": 5123,
                "count": len(INDICES),
                "type": "SCALAR",
            },
        ],
        "bufferViews": views,
        "buffers": [{"byteLength": len(buffer)}],
    }
    return gltf, bytes(buffer)


def write_gltf(gltf, buffer, path):
    """The JSON container: one file, buffer inlined as a data URI."""
    doc = json.loads(json.dumps(gltf))
    doc["buffers"][0]["uri"] = (
        "data:application/octet-stream;base64,"
        + base64.b64encode(buffer).decode("ascii")
    )
    path.write_text(json.dumps(doc, indent=2) + "\n")


def write_glb(gltf, buffer, path):
    """The binary container: header, JSON chunk, BIN chunk."""
    js = pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_ = pad4(buffer)
    length = 12 + 8 + len(js) + 8 + len(bin_)
    with path.open("wb") as out:
        out.write(struct.pack("<4sII", b"glTF", 2, length))
        out.write(struct.pack("<II", len(js), 0x4E4F534A))
        out.write(js)
        out.write(struct.pack("<II", len(bin_), 0x004E4942))
        out.write(bin_)


def main():
    gltf, buffer = build()
    write_gltf(gltf, buffer, OUT / "minimal.gltf")
    write_glb(gltf, buffer, OUT / "minimal.glb")
    for name in ("minimal.gltf", "minimal.glb"):
        print(f"{OUT / name}  {(OUT / name).stat().st_size} bytes")


if __name__ == "__main__":
    main()
