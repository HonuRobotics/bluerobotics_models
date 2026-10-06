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
Inventory the mesh and texture content of delivered .visual.glb parts.

Answers the budget question (T4 in the visual asset pipeline review): what
is actually in the files, how much of each file is geometry and how much is
texture, and what resolution each map is -- both in pixels and in texels per
millimeter of the surface it covers. Pixel size alone does not say whether a
map is over- or under-sampled; a 2048 map on a 1.2 m hull and the same map
on a 50 mm sonar are two different resolutions. UV fill is the fraction of
the map the shells actually land on, so a low fill at a high pixel count is
texture memory paid for and not used.

Reads the JSON chunk, the accessors and the embedded images. It does not
render and does not need Gazebo, so it runs on the host:

    glb_inventory.py models/*/*.visual.glb            # markdown tables
    glb_inventory.py --json models/*/*.visual.glb     # raw measurements

Decoded texture memory is the uncompressed RGBA footprint (w * h * 4). It is
what the encoded byte count in the file does not tell you and what the GPU
actually spends; base color and normal maps carry mipmaps on top of it,
roughness and metalness maps do not (gz-rendering builds none for them).
"""

import argparse
import io
import json
import math
import pathlib
import struct
import sys

import numpy as np
from PIL import Image

COMPONENT_DTYPES = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
COMPONENT_NAMES = {
    5120: "int8",
    5121: "uint8",
    5122: "int16",
    5123: "uint16",
    5125: "uint32",
    5126: "float32",
}
TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

# The five purposes glTF defines for a texture on a material, in the order a
# reviewer reads them. A texture used for one of these is that kind of map.
MAP_TYPES = ("baseColor", "normal", "metallicRoughness", "occlusion", "emissive")


def read_glb(path):
    """Return (gltf_json, bin_chunk) for a binary glTF file."""
    raw = path.read_bytes()
    magic, version, _length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF":
        raise ValueError(f"{path}: not a binary glTF")
    if version != 2:
        raise ValueError(f"{path}: glTF version {version}, expected 2")
    gltf, buf, offset = None, None, 12
    while offset < len(raw):
        chunk_len, chunk_type = struct.unpack_from("<II", raw, offset)
        data = raw[offset + 8:offset + 8 + chunk_len]
        if chunk_type == 0x4E4F534A:
            gltf = json.loads(data)
        elif chunk_type == 0x004E4942:
            buf = data
        offset += 8 + chunk_len + (-chunk_len % 4)
    if gltf is None:
        raise ValueError(f"{path}: no JSON chunk")
    return gltf, (buf or b""), len(raw)


def accessor(gltf, buf, index):
    """Read accessor `index` into an (n, components) array."""
    acc = gltf["accessors"][index]
    count, comps = acc["count"], TYPE_COUNTS[acc["type"]]
    dtype = np.dtype(COMPONENT_DTYPES[acc["componentType"]])
    if "bufferView" not in acc:
        return np.zeros((count, comps), dtype=dtype)
    view = gltf["bufferViews"][acc["bufferView"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride") or comps * dtype.itemsize
    rows = np.frombuffer(buf, dtype=np.uint8, count=count * stride, offset=start)
    rows = rows.reshape(count, stride)[:, : comps * dtype.itemsize]
    return np.ascontiguousarray(rows).view(dtype).reshape(count, comps)


def node_matrix(node):
    """Local TRS (or matrix) of a node as a 4x4."""
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    m = np.eye(4)
    if "rotation" in node:
        x, y, z, w = node["rotation"]
        m[:3, :3] = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ]
        )
    if "scale" in node:
        m[:3, :3] = m[:3, :3] @ np.diag(node["scale"])
    if "translation" in node:
        m[:3, 3] = node["translation"]
    return m


def walk(gltf, node_index, parent, out):
    """Depth-first walk collecting (node_index, world_matrix) for mesh nodes."""
    node = gltf["nodes"][node_index]
    world = parent @ node_matrix(node)
    if "mesh" in node:
        out.append((node_index, world))
    for child in node.get("children", []):
        walk(gltf, child, world, out)


def image_records(gltf, buf):
    """Decode every embedded image to (mime, width, height, encoded bytes)."""
    records = []
    for image in gltf.get("images", []):
        view = gltf["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        data = buf[start:start + view["byteLength"]]
        with Image.open(io.BytesIO(data)) as handle:
            width, height = handle.size
        records.append(
            {
                "name": image.get("name", ""),
                "mime": image.get("mimeType", "").replace("image/", "").upper(),
                "width": width,
                "height": height,
                "bytes": len(data),
            }
        )
    return records


def material_maps(gltf, material_index):
    """Map every texture property of a material to its image index."""
    material = gltf["materials"][material_index]
    pbr = material.get("pbrMetallicRoughness", {})
    slots = {
        "baseColor": pbr.get("baseColorTexture"),
        "metallicRoughness": pbr.get("metallicRoughnessTexture"),
        "normal": material.get("normalTexture"),
        "occlusion": material.get("occlusionTexture"),
        "emissive": material.get("emissiveTexture"),
    }
    out = {}
    for slot, info in slots.items():
        if info is None:
            continue
        texture = gltf["textures"][info["index"]]
        if "source" in texture:
            out[slot] = {"image": texture["source"], "uv": info.get("texCoord", 0)}
    return out


def measure(path):
    """Every measurement this tool makes about one GLB, as a dict."""
    gltf, buf, file_bytes = read_glb(path)
    images = image_records(gltf, buf)

    scene = gltf.get("scene", 0)
    roots = gltf.get("scenes", [{}])[scene].get("nodes", [])
    mesh_nodes = []
    for root in roots:
        walk(gltf, root, np.eye(4), mesh_nodes)

    part = {
        "file": path.name,
        "part": path.parent.name,
        "file_bytes": file_bytes,
        "generator": gltf.get("asset", {}).get("generator", ""),
        "scenes": len(gltf.get("scenes", [])),
        "nodes": len(gltf.get("nodes", [])),
        "meshes": len(gltf.get("meshes", [])),
        "materials": len(gltf.get("materials", [])),
        "images": images,
        "node_names": [gltf["nodes"][i].get("name", "") for i, _ in mesh_nodes],
        "primitives": [],
    }

    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for node_index, world in mesh_nodes:
        mesh = gltf["meshes"][gltf["nodes"][node_index]["mesh"]]
        for prim in mesh.get("primitives", []):
            attrs = prim["attributes"]
            pos = accessor(gltf, buf, attrs["POSITION"]).astype(np.float64)
            pos = (world[:3, :3] @ pos.T).T + world[:3, 3]
            lo = np.minimum(lo, pos.min(axis=0))
            hi = np.maximum(hi, pos.max(axis=0))

            if "indices" in prim:
                idx = accessor(gltf, buf, prim["indices"]).reshape(-1).astype(np.int64)
                index_type = COMPONENT_NAMES[
                    gltf["accessors"][prim["indices"]]["componentType"]
                ]
            else:
                idx = np.arange(len(pos))
                index_type = "none"
            tri = idx.reshape(-1, 3)

            maps = (
                material_maps(gltf, prim["material"])
                if "material" in prim
                else {}
            )
            # Surface area in mm^2, and the texel count the base color map
            # spends on it, so the two can be divided into texels per mm.
            a, b, c = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
            area_mm2 = float(
                0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()
            ) * 1e6
            # Sample against the material's largest map, not its base color:
            # the BlueROV2 frame carries a 1x1 base color bake beside a 2048
            # normal map, and the 2048 is what the surface is really sampled at.
            density, uv_fill, density_slot = None, None, None
            ref = max(
                maps.items(),
                key=lambda kv: images[kv[1]["image"]]["width"]
                * images[kv[1]["image"]]["height"],
                default=None,
            )
            if ref is not None and area_mm2 > 0:
                density_slot, refmap = ref
                uv_key = f"TEXCOORD_{refmap['uv']}"
                if uv_key in attrs:
                    uv = accessor(gltf, buf, attrs[uv_key]).astype(np.float64)
                    ua, ub, uc = uv[tri[:, 0]], uv[tri[:, 1]], uv[tri[:, 2]]
                    e1, e2 = ub - ua, uc - ua
                    uv_area = float(
                        0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum()
                    )
                    img = images[refmap["image"]]
                    uv_fill = uv_area
                    density = math.sqrt(uv_area * img["width"] * img["height"] / area_mm2)

            part["primitives"].append(
                {
                    "node": gltf["nodes"][node_index].get("name", ""),
                    "material": prim.get("material"),
                    "material_name": (
                        gltf["materials"][prim["material"]].get("name", "")
                        if "material" in prim
                        else None
                    ),
                    "vertices": int(len(pos)),
                    "triangles": int(len(tri)),
                    "index_type": index_type,
                    "attributes": sorted(attrs),
                    "area_mm2": area_mm2,
                    "texels_per_mm": density,
                    "texels_from": density_slot,
                    "uv_fill": uv_fill,
                    "maps": maps,
                }
            )

    part["extent_mm"] = [round(v, 1) for v in ((hi - lo) * 1000.0)] if mesh_nodes else []
    part["vertices"] = sum(p["vertices"] for p in part["primitives"])
    part["triangles"] = sum(p["triangles"] for p in part["primitives"])
    part["area_mm2"] = sum(p["area_mm2"] for p in part["primitives"])
    part["texture_bytes"] = sum(i["bytes"] for i in images)
    part["decoded_bytes"] = sum(i["width"] * i["height"] * 4 for i in images)

    # Which kind of map each image serves, first use wins for the label.
    roles = {}
    for prim in part["primitives"]:
        for slot, ref in prim["maps"].items():
            roles.setdefault(ref["image"], slot)
    for i, image in enumerate(images):
        image["role"] = roles.get(i, "unused")
    part["map_types"] = {
        kind: sorted(
            {
                (images[r["image"]]["width"], images[r["image"]]["height"],
                 images[r["image"]]["mime"])
                for p in part["primitives"]
                for s, r in p["maps"].items()
                if s == kind
            }
        )
        for kind in MAP_TYPES
    }
    return part


def px(entries):
    """Render a map type's (w, h, mime) tuples as '2048 PNG' or '128x256 JPEG'."""
    if not entries:
        return "--"
    out = []
    for width, height, mime in entries:
        size = str(width) if width == height else f"{width}x{height}"
        out.append(f"{size} {mime}")
    return ", ".join(out)


def kb(n):
    return f"{n / 1024:.0f}"


def markdown(parts):
    lines = []
    add = lines.append

    add("### Per part: geometry and texture content\n")
    add(
        "| Part | File KB | Prims | Verts | Tris | Index | Attributes | "
        "Mats | Imgs | Tex KB | Tex % | Geom KB |"
    )
    add("|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|")
    for p in parts:
        attrs = sorted({a for prim in p["primitives"] for a in prim["attributes"]})
        short = ", ".join(
            a.replace("TEXCOORD_", "UV").replace("POSITION", "POS")
            .replace("NORMAL", "NRM").replace("TANGENT", "TAN")
            for a in attrs
        )
        idx = ", ".join(sorted({prim["index_type"] for prim in p["primitives"]}))
        geom = p["file_bytes"] - p["texture_bytes"]
        add(
            f"| {p['part']} | {kb(p['file_bytes'])} | {len(p['primitives'])} | "
            f"{p['vertices']:,} | {p['triangles']:,} | {idx} | {short} | "
            f"{p['materials']} | {len(p['images'])} | {kb(p['texture_bytes'])} | "
            f"{100 * p['texture_bytes'] / p['file_bytes']:.0f} | {kb(geom)} |"
        )
    total_file = sum(p["file_bytes"] for p in parts)
    total_tex = sum(p["texture_bytes"] for p in parts)
    add(
        f"| **total ({len(parts)})** | **{kb(total_file)}** | "
        f"**{sum(len(p['primitives']) for p in parts)}** | "
        f"**{sum(p['vertices'] for p in parts):,}** | "
        f"**{sum(p['triangles'] for p in parts):,}** | | | "
        f"**{sum(p['materials'] for p in parts)}** | "
        f"**{sum(len(p['images']) for p in parts)}** | **{kb(total_tex)}** | "
        f"**{100 * total_tex / total_file:.0f}** | "
        f"**{kb(total_file - total_tex)}** |"
    )

    add("\n### Per part: texture resolution by map type\n")
    add(
        "| Part | Base color | Normal | Metallic-roughness | Occlusion | "
        "Emissive | Decoded MB | Texels/mm | UV fill % | Extent mm (X x Y x Z) |"
    )
    add("|---|---|---|---|---|---|---:|---:|---:|---|")
    for p in parts:
        densities = [
            prim["texels_per_mm"]
            for prim in p["primitives"]
            if prim["texels_per_mm"] is not None
        ]
        weights = [
            prim["area_mm2"]
            for prim in p["primitives"]
            if prim["texels_per_mm"] is not None
        ]
        dens = (
            f"{sum(d * w for d, w in zip(densities, weights)) / sum(weights):.1f}"
            if densities and sum(weights) > 0
            else "--"
        )
        fills = [
            prim["uv_fill"] for prim in p["primitives"] if prim["uv_fill"] is not None
        ]
        fill = f"{100 * sum(fills):.0f}" if fills else "--"
        extent = " x ".join(f"{v:.0f}" for v in p["extent_mm"])
        add(
            f"| {p['part']} | " + " | ".join(px(p["map_types"][k]) for k in MAP_TYPES)
            + f" | {p['decoded_bytes'] / 1024 / 1024:.1f} | {dens} | {fill} | {extent} |"
        )
    add(
        f"| **total** | | | | | | "
        f"**{sum(p['decoded_bytes'] for p in parts) / 1024 / 1024:.1f}** | | | |"
    )

    add("\n### Every embedded image\n")
    add("| Part | Map | Image name | Format | Pixels | KB | Decoded KB |")
    add("|---|---|---|---|---|---:|---:|")
    for p in parts:
        for image in p["images"]:
            size = (
                str(image["width"])
                if image["width"] == image["height"]
                else f"{image['width']}x{image['height']}"
            )
            add(
                f"| {p['part']} | {image['role']} | {image['name'] or '--'} | "
                f"{image['mime']} | {size} | {kb(image['bytes'])} | "
                f"{kb(image['width'] * image['height'] * 4)} |"
            )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", nargs="+", type=pathlib.Path)
    parser.add_argument("--json", action="store_true", help="raw measurements")
    args = parser.parse_args()

    parts = sorted((measure(p) for p in args.glb), key=lambda p: p["part"])
    if args.json:
        json.dump(parts, sys.stdout, indent=2, default=str)
        print()
    else:
        print(markdown(parts))


if __name__ == "__main__":
    main()
