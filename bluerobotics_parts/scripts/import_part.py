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
Generate a part's URDF xacro macro from the modeler's delivery.

PROTOTYPE. Reads models/<part>/model.sdf (collision primitives and the
visual mesh reference as delivered) and writes urdf/<part>.urdf.xacro: one
macro emitting a link with inertia, visual and optional collision, plus the
joint that mounts it. Nothing here is hand edited afterwards; the inputs
that are not in the delivery (a measured mass, mount sockets, a spin axis)
live in models/<part>/<part>.yaml and are folded in on every run.

Inertia comes from SDF auto inertia: the delivered collision primitives are
run through `gz sdf --expand-auto-inertials` at a uniform density, giving a
mass, a center of mass and a full tensor. When <part>.yaml states a mass
the tensor is scaled to it (inertia is linear in density, so the shape of
the tensor and the center of mass are unchanged). Mesh collisions are
integrated directly (the gz CLI has no mesh calculator).

    import_part.py models/t200_thruster            # one part
    import_part.py --all models                    # every delivered part
"""

import argparse
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import yaml

PACKAGE = 'bluerobotics_parts'
DEFAULT_DENSITY = 1000.0  # kg/m^3, fresh water: a neutral default for parts

URDF_SHAPES = ('box', 'cylinder', 'sphere', 'mesh')


class ImportError_(Exception):
    pass


# --------------------------------------------------------------------------
# model.sdf
# --------------------------------------------------------------------------

def parse_pose(text):
    vals = [float(v) for v in (text or '0 0 0 0 0 0').split()]
    if len(vals) != 6:
        raise ImportError_(f'bad pose: {text!r}')
    return vals


def read_delivery(part_dir):
    """
    Return (link_name, visuals, collisions, frames) read from model.sdf.

    collisions: list of dicts {name, pose, shape, params} with params in
    URDF terms (size / radius+length / radius / filename+scale).
    """
    sdf_path = part_dir / 'model.sdf'
    if not sdf_path.exists():
        raise ImportError_(f'{sdf_path} missing')
    model = ET.parse(sdf_path).getroot().find('model')
    links = model.findall('link')
    if len(links) != 1:
        raise ImportError_(f'{sdf_path}: expected one link, found {len(links)}')
    link = links[0]

    visuals = []
    for vis in link.findall('visual'):
        uri = vis.findtext('geometry/mesh/uri')
        if uri is None:
            raise ImportError_(f'{sdf_path}: visual without a mesh uri')
        if not (part_dir / uri).exists():
            raise ImportError_(f'{sdf_path}: visual mesh {uri} not delivered')
        visuals.append({'uri': uri, 'pose': parse_pose(vis.findtext('pose'))})

    collisions = []
    for col in link.findall('collision'):
        geom = col.find('geometry')
        shape_el = next(iter(geom)) if geom is not None and len(geom) else None
        if shape_el is None or shape_el.tag not in URDF_SHAPES:
            raise ImportError_(
                f'{sdf_path}: collision {col.get("name")!r} uses '
                f'{shape_el.tag if shape_el is not None else "no"} geometry; '
                f'URDF expresses only {", ".join(URDF_SHAPES)}')
        entry = {'name': col.get('name', ''), 'pose': parse_pose(col.findtext('pose')),
                 'shape': shape_el.tag}
        if shape_el.tag == 'box':
            entry['size'] = [float(v) for v in shape_el.findtext('size').split()]
        elif shape_el.tag == 'cylinder':
            entry['radius'] = float(shape_el.findtext('radius'))
            entry['length'] = float(shape_el.findtext('length'))
        elif shape_el.tag == 'sphere':
            entry['radius'] = float(shape_el.findtext('radius'))
        else:
            uri = shape_el.findtext('uri')
            if not (part_dir / uri).exists():
                raise ImportError_(f'{sdf_path}: collision mesh {uri} not delivered')
            entry['filename'] = uri
            entry['scale'] = [float(v) for v in (shape_el.findtext('scale') or '1 1 1').split()]
        collisions.append(entry)

    # Frames are the preferred channel for attachment data: a frame named
    # `attach` is where this part bolts onto its parent, frames named
    # `mount_<socket>` are where other parts bolt onto this one. Nothing in
    # the deliveries carries them yet; <part>.yaml supplies the same data.
    frames = {}
    for fr in model.findall('frame') + link.findall('frame'):
        frames[fr.get('name')] = parse_pose(fr.findtext('pose'))

    return link.get('name'), visuals, collisions, frames


def load_spec(part_dir, frames):
    """
    Load the per part data that is not in the delivery, or overrides it.

    Keys: mass, density, com, axis, attach, mounts. Delivered frames seed
    attach and mounts; the yaml wins on conflict.
    """
    part = part_dir.name
    spec_path = part_dir / f'{part}.yaml'
    spec = (yaml.safe_load(spec_path.read_text()) or {}) if spec_path.exists() else {}
    mounts = {name[len('mount_'):]: pose for name, pose in frames.items()
              if name.startswith('mount_')}
    mounts.update(spec.get('mounts', {}))
    if mounts:
        spec['mounts'] = mounts
    if 'attach' in frames and 'attach' not in spec:
        spec['attach'] = frames['attach']
    return spec


# --------------------------------------------------------------------------
# inertia
# --------------------------------------------------------------------------

def auto_inertia_primitives(part_dir, density):
    """
    Run the delivered model.sdf through gz sdf auto inertia.

    Collisions of mesh type are removed first (the CLI cannot integrate
    them). Returns (mass, com_xyz, tensor dict), or None when the part has
    no primitive collisions.
    """
    tree = ET.parse(part_dir / 'model.sdf')
    link = tree.getroot().find('model/link')
    kept = 0
    for col in list(link.findall('collision')):
        if col.find('geometry/mesh') is not None:
            link.remove(col)
        else:
            kept += 1
    if kept == 0:
        return None
    inertial = ET.Element('inertial', {'auto': 'true'})
    ET.SubElement(inertial, 'density').text = str(density)
    link.insert(0, inertial)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for f in part_dir.iterdir():
            if f.suffix in ('.glb', '.stl', '.dae', '.obj'):
                shutil.copy(f, tmp / f.name)
        tree.write(tmp / 'model.sdf')
        out = subprocess.run(['gz', 'sdf', '-p', '--expand-auto-inertials', 'model.sdf'],
                             cwd=tmp, capture_output=True, text=True)
    if out.returncode != 0 or '<inertial' not in out.stdout:
        raise ImportError_(f'gz sdf auto inertia failed for {part_dir.name}:\n{out.stderr}')
    expanded = ET.fromstring(out.stdout[out.stdout.index('<sdf'):])
    inert = expanded.find('model/link/inertial')
    mass = float(inert.findtext('mass'))
    pose = parse_pose(inert.findtext('pose'))
    tensor = {k: float(inert.findtext(f'inertia/{k}')) for k in
              ('ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz')}
    return mass, pose[:3], tensor


def read_stl(path):
    """Triangles of a binary or ASCII STL as a list of 3 vertex tuples."""
    data = path.read_bytes()
    if data[:5] == b'solid' and b'facet' in data[:400]:
        nums = [float(v) for v in re.findall(rb'vertex\s+(\S+)\s+(\S+)\s+(\S+)', data)
                for v in v]
        verts = [tuple(nums[i:i + 3]) for i in range(0, len(nums), 3)]
    else:
        count = struct.unpack_from('<I', data, 80)[0]
        verts = []
        for i in range(count):
            off = 84 + i * 50 + 12
            for j in range(3):
                verts.append(struct.unpack_from('<fff', data, off + j * 12))
    return [verts[i:i + 3] for i in range(0, len(verts), 3)]


def mesh_inertia(path, scale, density):
    """
    Integrate a closed triangle mesh at uniform density.

    Returns mass, center of mass and the inertia tensor about it, by
    summing signed tetrahedra against the origin.
    """
    tris = read_stl(path)
    vol = 0.0
    com = [0.0, 0.0, 0.0]
    # second moments accumulated about the origin
    xx = yy = zz = xy = yz = xz = 0.0
    for tri in tris:
        a, b, c = [[v[i] * scale[i] for i in range(3)] for v in tri]
        det = (a[0] * (b[1] * c[2] - b[2] * c[1])
               - a[1] * (b[0] * c[2] - b[2] * c[0])
               + a[2] * (b[0] * c[1] - b[1] * c[0]))
        v = det / 6.0
        vol += v
        for i in range(3):
            com[i] += v * (a[i] + b[i] + c[i]) / 4.0

        def f2(i):
            return (a[i] * a[i] + b[i] * b[i] + c[i] * c[i]
                    + a[i] * b[i] + b[i] * c[i] + c[i] * a[i]) * det / 60.0

        def f11(i, j):
            return (2 * a[i] * a[j] + 2 * b[i] * b[j] + 2 * c[i] * c[j]
                    + a[i] * b[j] + a[j] * b[i] + b[i] * c[j] + b[j] * c[i]
                    + c[i] * a[j] + c[j] * a[i]) * det / 120.0
        xx += f2(0)
        yy += f2(1)
        zz += f2(2)
        xy += f11(0, 1)
        yz += f11(1, 2)
        xz += f11(0, 2)
    if vol <= 0:
        raise ImportError_(f'{path.name}: mesh volume {vol:.3g}, not a closed outward mesh')
    com = [c / vol for c in com]
    mass = density * vol
    # tensor about origin, then shift to the center of mass
    ixx = density * (yy + zz)
    iyy = density * (xx + zz)
    izz = density * (xx + yy)
    ixy = -density * xy
    iyz = -density * yz
    ixz = -density * xz
    cx, cy, cz = com
    ixx -= mass * (cy * cy + cz * cz)
    iyy -= mass * (cx * cx + cz * cz)
    izz -= mass * (cx * cx + cy * cy)
    ixy += mass * cx * cy
    iyz += mass * cy * cz
    ixz += mass * cx * cz
    return mass, com, {'ixx': ixx, 'ixy': ixy, 'ixz': ixz, 'iyy': iyy, 'iyz': iyz, 'izz': izz}


def combine(bodies):
    """Combine (mass, com, tensor-about-own-com) bodies into one."""
    mass = sum(b[0] for b in bodies)
    com = [sum(b[0] * b[1][i] for b in bodies) / mass for i in range(3)]
    tot = {k: 0.0 for k in ('ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz')}
    for m, c, t in bodies:
        dx, dy, dz = (c[i] - com[i] for i in range(3))
        tot['ixx'] += t['ixx'] + m * (dy * dy + dz * dz)
        tot['iyy'] += t['iyy'] + m * (dx * dx + dz * dz)
        tot['izz'] += t['izz'] + m * (dx * dx + dy * dy)
        tot['ixy'] += t['ixy'] - m * dx * dy
        tot['iyz'] += t['iyz'] - m * dy * dz
        tot['ixz'] += t['ixz'] - m * dx * dz
    return mass, com, tot


def compute_inertia(part_dir, collisions, spec):
    density = float(spec.get('density', DEFAULT_DENSITY))
    bodies = []
    prim = auto_inertia_primitives(part_dir, density)
    if prim:
        bodies.append(prim)
    for col in collisions:
        if col['shape'] == 'mesh':
            m, c, t = mesh_inertia(part_dir / col['filename'], col['scale'], density)
            # the collision pose places the mesh in the link frame; rotation
            # of mesh collisions is not handled by this prototype
            c = [c[i] + col['pose'][i] for i in range(3)]
            bodies.append((m, c, t))
    if not bodies:
        return None, 'no collision geometry: inertia must be stated in the yaml'
    mass, com, tensor = combine(bodies)
    source = f'auto inertia from the delivered collision geometry at {density:g} kg/m^3'
    if 'mass' in spec:
        target = float(spec['mass'])
        k = target / mass
        tensor = {key: v * k for key, v in tensor.items()}
        source = (f'auto inertia shape from the collision geometry, scaled from '
                  f'{mass:.3f} kg (at {density:g} kg/m^3) to the stated mass {target:g} kg')
        mass = target
    if 'com' in spec:
        com = [float(v) for v in spec['com']]
        source += '; center of mass overridden by the yaml'
    return (mass, com, tensor), source


# --------------------------------------------------------------------------
# xacro emission
# --------------------------------------------------------------------------

def fmt(v):
    return f'{v:.6g}'


def fmt_xyz(vals):
    return ' '.join(fmt(v) for v in vals)


def emit_macro(part, visuals, collisions, inertia, source, spec):
    mounts = spec.get('mounts', {})
    default_axis = spec.get('axis', '0 0 1')
    lines = []
    w = lines.append
    w('<?xml version="1.0"?>')
    w('<!--')
    w(f'  {part} part macro. GENERATED FILE, DO NOT EDIT.')
    w('')
    w(f'  Written by scripts/import_part.py from models/{part}/model.sdf (the')
    w(f'  modeler delivery) and models/{part}/{part}.yaml (measured values and')
    w('  mounts); rerun the import to change anything here.')
    w('')
    w(f'  Inertia: {source}.')
    w('')
    w('  Macro contract: name parent xyz rpy collision, plus joint (fixed by')
    w('  default) and axis for parts that spin. parent="" emits the link alone,')
    w('  for the part that serves as the assembly root.')
    w('-->')
    w('<robot xmlns:xacro="http://ros.org/wiki/xacro">')
    w('')
    if mounts:
        w('  <!-- Mount sockets: named poses on this part where other parts attach,')
        w('       [x, y, z, roll, pitch, yaw] in the part frame. -->')
        w(f'  <xacro:property name="{part}_mounts" value="${{dict(')
        for i, (key, pose) in enumerate(mounts.items()):
            sep = ',' if i < len(mounts) - 1 else ''
            w(f'      {key}=[{", ".join(fmt(float(v)) for v in pose)}]{sep}')
        w('  )}"/>')
        w('')
    w(f'  <xacro:macro name="{part}"')
    w(f'               params="name parent xyz:=\'0 0 0\' rpy:=\'0 0 0\' collision:=true '
      f'joint:=fixed axis:=\'{default_axis}\'">')
    w('')
    w('    <link name="${name}">')
    if inertia:
        mass, com, t = inertia
        w('      <inertial>')
        w(f'        <origin xyz="{fmt_xyz(com)}" rpy="0 0 0"/>')
        w(f'        <mass value="{fmt(mass)}"/>')
        w(f'        <inertia ixx="{fmt(t["ixx"])}" ixy="{fmt(t["ixy"])}" ixz="{fmt(t["ixz"])}"')
        w(f'                 iyy="{fmt(t["iyy"])}" iyz="{fmt(t["iyz"])}"')
        w(f'                 izz="{fmt(t["izz"])}"/>')
        w('      </inertial>')
    for vis in visuals:
        w('      <visual>')
        w(f'        <origin xyz="{fmt_xyz(vis["pose"][:3])}" rpy="{fmt_xyz(vis["pose"][3:])}"/>')
        w('        <geometry>')
        w(f'          <mesh filename="package://{PACKAGE}/models/{part}/{vis["uri"]}"/>')
        w('        </geometry>')
        w('      </visual>')
    if collisions:
        w('      <xacro:if value="${collision}">')
        for col in collisions:
            w('        <collision>')
            w(f'          <origin xyz="{fmt_xyz(col["pose"][:3])}"'
              f' rpy="{fmt_xyz(col["pose"][3:])}"/>')
            w('          <geometry>')
            if col['shape'] == 'box':
                w(f'            <box size="{fmt_xyz(col["size"])}"/>')
            elif col['shape'] == 'cylinder':
                w(f'            <cylinder radius="{fmt(col["radius"])}"'
                  f' length="{fmt(col["length"])}"/>')
            elif col['shape'] == 'sphere':
                w(f'            <sphere radius="{fmt(col["radius"])}"/>')
            else:
                w(f'            <mesh filename="package://{PACKAGE}/models/{part}/'
                  f'{col["filename"]}" scale="{fmt_xyz(col["scale"])}"/>')
            w('          </geometry>')
            w('        </collision>')
        w('      </xacro:if>')
    w('    </link>')
    w('')
    w('    <xacro:if value="${parent != \'\'}">')
    w('      <joint name="${name}_joint" type="${joint}">')
    w('        <parent link="${parent}"/>')
    w('        <child link="${name}"/>')
    w('        <origin xyz="${xyz}" rpy="${rpy}"/>')
    w('        <xacro:if value="${joint != \'fixed\'}">')
    w('          <axis xyz="${axis}"/>')
    w('        </xacro:if>')
    w('      </joint>')
    w('    </xacro:if>')
    w('')
    w('  </xacro:macro>')
    w('')
    w('</robot>')
    return '\n'.join(lines) + '\n'


def import_part(part_dir, urdf_dir):
    part = part_dir.name
    link_name, visuals, collisions, frames = read_delivery(part_dir)
    spec = load_spec(part_dir, frames)
    inertia, source = compute_inertia(part_dir, collisions, spec)
    if inertia is None and 'mass' not in spec:
        raise ImportError_(f'{part}: {source}')
    out = urdf_dir / f'{part}.urdf.xacro'
    out.write_text(emit_macro(part, visuals, collisions, inertia, source, spec))
    mass = inertia[0] if inertia else float(spec['mass'])
    mount_data = {'attach': [float(v) for v in spec.get('attach', [0, 0, 0, 0, 0, 0])],
                  'axis': str(spec.get('axis', '0 0 1')),
                  'mounts': {k: [float(v) for v in pose]
                             for k, pose in spec.get('mounts', {}).items()}}
    return out, mass, len(collisions), mount_data


PARTS_XACRO_HEADER = """\
<?xml version="1.0"?>
<!--
  bluerobotics_parts: the parts level macro library. GENERATED include list,
  written by scripts/import_part.py; rerun the import after adding a part.

  Include this once and every part is available as a macro:

      <xacro:include filename="$(find bluerobotics_parts)/urdf/parts.xacro"/>
      <xacro:t200_thruster name="thruster_port" parent="base_link" xyz="-0.5 0.3 -0.1"/>

  Macro contract, identical for every part:

      name       link name for this instance; the joint is <name>_joint
      parent     link to attach to; "" emits the link alone (assembly root)
      xyz / rpy  mount pose relative to parent (meters / radians)
      collision  false to instantiate the part without contact geometry
      joint      fixed (default) or continuous / revolute for parts that spin
      axis       joint axis in the part frame, used when joint is not fixed

  Mount sockets and attach frames are in mounts.yaml, consumed by the
  dispatcher in assembly.xacro.
-->
<robot xmlns:xacro="http://ros.org/wiki/xacro">

"""


def write_library(urdf_dir, imported):
    lines = [PARTS_XACRO_HEADER]
    for part in sorted(imported):
        lines.append(f'  <xacro:include filename="$(find {PACKAGE})/urdf/{part}.urdf.xacro"/>\n')
    lines.append('\n</robot>\n')
    (urdf_dir / 'parts.xacro').write_text(''.join(lines))
    mounts = {part: imported[part] for part in sorted(imported)}
    header = ('# GENERATED by scripts/import_part.py: attach frame and mount sockets\n'
              '# per part, [x, y, z, roll, pitch, yaw] in the part frame. Edit the\n'
              '# per part <part>.yaml (or deliver SDF frames) and rerun the import.\n')
    (urdf_dir / 'mounts.yaml').write_text(
        header + yaml.safe_dump(mounts, sort_keys=False, default_flow_style=None, width=120))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('paths', nargs='+', help='part directories, or the models/ dir with --all')
    ap.add_argument('--all', action='store_true',
                    help='import every delivered part under the given dir')
    ap.add_argument('--urdf-dir', help='output directory (default: ../urdf next to models/)')
    args = ap.parse_args(argv)

    if args.all:
        roots = [pathlib.Path(args.paths[0])]
        parts = sorted(p for p in roots[0].iterdir() if (p / 'model.sdf').exists())
    else:
        parts = [pathlib.Path(p) for p in args.paths]
    if not parts:
        sys.exit('no delivered parts found')
    urdf_dir = pathlib.Path(args.urdf_dir) if args.urdf_dir else parts[0].parent.parent / 'urdf'
    urdf_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    imported = {}
    for part_dir in parts:
        try:
            out, mass, ncol, mount_data = import_part(part_dir, urdf_dir)
            imported[part_dir.name] = mount_data
            print(f'{part_dir.name:34s} mass={mass:8.3f} kg  collisions={ncol}  -> {out.name}')
        except ImportError_ as exc:
            failures += 1
            print(f'{part_dir.name:34s} FAILED: {exc}', file=sys.stderr)
    if args.all:
        write_library(urdf_dir, imported)
        print(f'library: {urdf_dir / "parts.xacro"}, {urdf_dir / "mounts.yaml"}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
