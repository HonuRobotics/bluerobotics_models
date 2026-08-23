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
Bootstrap a part macro (urdf/<part>.urdf.xacro) from a modeler's SDF delivery.

The URDF xacro is the part. This tool only writes its first version, from
models/<part>/model.sdf: the visual mesh reference, the collision primitives
translated to URDF, and an inertia estimated by SDF auto inertia from those
primitives (or integrated from a collision mesh) at a uniform density, scaled
to --mass when one is known. Slots (mount points with the part types that
fit and a default occupant), reference frames, the attach offset and the
spin axis can be seeded from the command line. After that the file is
maintained by hand like any other source; rerunning refuses to overwrite
unless --force.

A part can equally be written by hand without ever having an SDF.

The visual .glb must be Y-up as the glTF specification requires (see
gltf_to_yup.py for deliveries exported Z-up); part_visual in parts.xacro
handles the Gazebo side.

    sdf_to_part.py models/t200_thruster --mass 0.344 --axis "1 0 0"
    sdf_to_part.py models/blueboat_chassis --mass 12
        --slot "motor_port=-0.52,0.301,-0.117;accepts=m200_weedless_prop_ccw;
                default=m200_weedless_prop_ccw;joint=continuous"
    sdf_to_part.py models/ping_singlebeam --frame beam=0,0,-0.044
    sdf_to_part.py --all models            # first version of every delivered part
"""

import argparse
import datetime
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

PACKAGE = 'bluerobotics_parts'
DEFAULT_DENSITY = 1000.0  # kg/m^3, fresh water: a neutral default for parts

URDF_SHAPES = ('box', 'cylinder', 'sphere', 'mesh')


class ConversionError(Exception):
    pass


# --------------------------------------------------------------------------
# model.sdf
# --------------------------------------------------------------------------

def parse_pose(text):
    vals = [float(v) for v in (text or '0 0 0 0 0 0').split()]
    if len(vals) != 6:
        raise ConversionError(f'bad pose: {text!r}')
    return vals


def read_delivery(part_dir):
    """
    Return (visuals, collisions) read from model.sdf.

    collisions: list of dicts {name, pose, shape, params} with params in
    URDF terms (size / radius+length / radius / filename+scale).
    """
    sdf_path = part_dir / 'model.sdf'
    if not sdf_path.exists():
        raise ConversionError(f'{sdf_path} missing')
    model = ET.parse(sdf_path).getroot().find('model')
    links = model.findall('link')
    if len(links) != 1:
        raise ConversionError(f'{sdf_path}: expected one link, found {len(links)}')
    link = links[0]

    visuals = []
    for vis in link.findall('visual'):
        uri = vis.findtext('geometry/mesh/uri')
        if uri is None:
            raise ConversionError(f'{sdf_path}: visual without a mesh uri')
        if not (part_dir / uri).exists():
            raise ConversionError(f'{sdf_path}: visual mesh {uri} not delivered')
        visuals.append({'uri': uri, 'pose': parse_pose(vis.findtext('pose'))})

    collisions = []
    for col in link.findall('collision'):
        geom = col.find('geometry')
        shape_el = next(iter(geom)) if geom is not None and len(geom) else None
        if shape_el is None or shape_el.tag not in URDF_SHAPES:
            raise ConversionError(
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
                raise ConversionError(f'{sdf_path}: collision mesh {uri} not delivered')
            entry['filename'] = uri
            entry['scale'] = [float(v) for v in (shape_el.findtext('scale') or '1 1 1').split()]
        collisions.append(entry)
    return visuals, collisions


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
        raise ConversionError(f'gz sdf auto inertia failed for {part_dir.name}:\n{out.stderr}')
    expanded = ET.fromstring(out.stdout[out.stdout.index('<sdf'):])
    inert = expanded.find('model/link/inertial')
    mass = float(inert.findtext('mass'))
    pose = parse_pose(inert.findtext('pose'))
    tensor = {k: float(inert.findtext(f'inertia/{k}')) for k in
              ('ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz')}
    return mass, pose[:3], tensor


def read_stl(path):
    """Return the triangles of a binary or ASCII STL as lists of 3 vertices."""
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
        raise ConversionError(f'{path.name}: mesh volume {vol:.3g}, not a closed outward mesh')
    com = [c / vol for c in com]
    mass = density * vol
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
    """Combine (mass, com, tensor about own com) bodies into one."""
    mass = sum(b[0] for b in bodies)
    com = [sum(b[0] * b[1][i] for b in bodies) / mass for i in range(3)]
    tot = dict.fromkeys(('ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz'), 0.0)
    for m, c, t in bodies:
        dx, dy, dz = (c[i] - com[i] for i in range(3))
        tot['ixx'] += t['ixx'] + m * (dy * dy + dz * dz)
        tot['iyy'] += t['iyy'] + m * (dx * dx + dz * dz)
        tot['izz'] += t['izz'] + m * (dx * dx + dy * dy)
        tot['ixy'] += t['ixy'] - m * dx * dy
        tot['iyz'] += t['iyz'] - m * dy * dz
        tot['ixz'] += t['ixz'] - m * dx * dz
    return mass, com, tot


def estimate_inertia(part_dir, collisions, density, mass_override):
    bodies = []
    prim = auto_inertia_primitives(part_dir, density)
    if prim:
        bodies.append(prim)
    for col in collisions:
        if col['shape'] == 'mesh':
            m, c, t = mesh_inertia(part_dir / col['filename'], col['scale'], density)
            c = [c[i] + col['pose'][i] for i in range(3)]
            bodies.append((m, c, t))
    if not bodies:
        raise ConversionError('no collision geometry to estimate inertia from; '
                              'write the part by hand')
    mass, com, tensor = combine(bodies)
    source = (f'estimated from the delivered collision geometry at {density:g} kg/m^3 '
              f'(SDF auto inertia); replace with measured values')
    if mass_override is not None:
        k = mass_override / mass
        tensor = {key: v * k for key, v in tensor.items()}
        source = (f'tensor shape estimated from the collision geometry, scaled from '
                  f'{mass:.3f} kg at {density:g} kg/m^3 to the stated {mass_override:g} kg')
        mass = mass_override
    return (mass, com, tensor), source


# --------------------------------------------------------------------------
# xacro emission
# --------------------------------------------------------------------------

def fmt(v):
    return f'{v:.6g}'


def fmt_xyz(vals):
    return ' '.join(fmt(v) for v in vals)


def py_str(value):
    return repr(str(value))


def emit_info(part, attach, slots, frames):
    """Emit the <part>_info macro: metadata exported as the property part_info."""
    lines = [f'  <xacro:macro name="{part}_info">',
             '    <xacro:property name="part_info" scope="parent" value="${dict(',
             f'        attach={py_str(attach)},',
             '        slots=dict(']
    for name, slot in slots.items():
        fields = [f'xyz={py_str(slot["xyz"])}', f'rpy={py_str(slot["rpy"])}']
        if 'accepts' in slot:
            fields.append(f'accepts={slot["accepts"]!r}')
        fields.append(f'default={py_str(slot.get("default", "none"))}')
        if 'joint' in slot:
            fields.append(f'joint={py_str(slot["joint"])}')
        lines.append(f'            {name}=dict({", ".join(fields)}),')
    lines.append('        ),')
    lines.append('        frames=dict(')
    for name, frame in frames.items():
        lines.append(f'            {name}=dict(xyz={py_str(frame["xyz"])}, '
                     f'rpy={py_str(frame["rpy"])}),')
    lines.append('        ))}"/>')
    lines.append('  </xacro:macro>')
    return lines


def emit_macro(part, visuals, collisions, inertia, source, axis, attach, slots, frames):
    mass, com, t = inertia
    today = datetime.date.today().isoformat()
    lines = []
    w = lines.append
    w('<?xml version="1.0"?>')
    w('<!--')
    w(f'  {part} part macro.')
    w('')
    w(f'  Bootstrapped from models/{part}/model.sdf by scripts/sdf_to_part.py on')
    w(f'  {today}. This file is the part: maintain it by hand from here on.')
    w('')
    w(f'  Inertia: {source}.')
    w('')
    w('  Contract (see parts.xacro): <part>_info exports the metadata (attach,')
    w('  slots, frames, drive); <part> instantiates the link, its mounting joint')
    w('  and its slot / frame links.')
    if slots:
        w('  Slots other parts fit into, as frames <name>_<slot>:')
        for name, slot in slots.items():
            fits = ', '.join(slot.get('accepts', ['any part']))
            w(f'    {name}: {fits}; default {slot.get("default", "none")}')
    if frames:
        w('  Reference frames, as <name>_<frame>: ' + ', '.join(frames))
    w('-->')
    w('<robot xmlns:xacro="http://ros.org/wiki/xacro">')
    w('')
    lines.extend(emit_info(part, attach, slots, frames))
    w('')
    w(f'  <xacro:macro name="{part}"')
    w(f'               params="name parent xyz:=\'0 0 0\' rpy:=\'0 0 0\' collision:=true '
      f'joint:=fixed axis:=\'{axis}\'">')
    w(f'    <xacro:{part}_info/>')
    w('')
    w('    <link name="${name}">')
    w('      <inertial>')
    w(f'        <origin xyz="{fmt_xyz(com)}" rpy="0 0 0"/>')
    w(f'        <mass value="{fmt(mass)}"/>')
    w(f'        <inertia ixx="{fmt(t["ixx"])}" ixy="{fmt(t["ixy"])}" ixz="{fmt(t["ixz"])}"')
    w(f'                 iyy="{fmt(t["iyy"])}" iyz="{fmt(t["iyz"])}"')
    w(f'                 izz="{fmt(t["izz"])}"/>')
    w('      </inertial>')
    for vis in visuals:
        if any(abs(v) > 1e-9 for v in vis['pose'][3:]):
            raise ConversionError(f'{part}: visual pose with a rotation is not supported; '
                                  'deliver the mesh in the part frame')
        xyz = (f' xyz="{fmt_xyz(vis["pose"][:3])}"'
               if any(abs(v) > 1e-9 for v in vis['pose'][:3]) else '')
        w(f'      <xacro:part_visual mesh="package://{PACKAGE}/models/{part}/{vis["uri"]}"'
          f'{xyz}/>')
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
    w('    <xacro:part_joint name="${name}" parent="${parent}" xyz="${xyz}" rpy="${rpy}"')
    w('                      joint="${joint}" axis="${axis}" attach="${part_info[\'attach\']}"/>')
    w('    <xacro:part_slots name="${name}" items="${list(part_info[\'slots\'].items())}"/>')
    w('    <xacro:part_frames name="${name}" items="${list(part_info[\'frames\'].items())}"/>')
    w('')
    w('  </xacro:macro>')
    w('')
    w('</robot>')
    return '\n'.join(lines) + '\n'


def parse_pose_spec(spec, what):
    """name=x,y,z[,r,p,y] -> (name, {'xyz': ..., 'rpy': ...}, remaining options)."""
    head, *opts = spec.split(';')
    name, _, nums = head.partition('=')
    try:
        vals = [float(v) for v in nums.split(',')]
    except ValueError:
        vals = []
    if not name or len(vals) not in (3, 6):
        raise ConversionError(f'bad {what} {spec!r}; expected name=x,y,z[,r,p,y]')
    vals += [0.0] * (6 - len(vals))
    return name, {'xyz': fmt_xyz(vals[:3]), 'rpy': fmt_xyz(vals[3:])}, opts


def parse_slot(spec):
    """name=x,y,z[,r,p,y][;accepts=a,b][;default=type|none][;joint=continuous]."""
    name, slot, opts = parse_pose_spec(spec, '--slot')
    for opt in opts:
        key, _, val = opt.partition('=')
        if key == 'accepts':
            slot['accepts'] = [v for v in val.split(',') if v]
        elif key == 'default':
            slot['default'] = val
        elif key == 'joint':
            slot['joint'] = val
        else:
            raise ConversionError(f'bad --slot option {opt!r} in {spec!r}')
    if 'accepts' in slot and slot.get('default', 'none') not in slot['accepts'] + ['none']:
        raise ConversionError(f'--slot {name}: default {slot["default"]!r} is not in accepts')
    return name, slot


def convert(part_dir, out_dir, args):
    part = part_dir.name
    out = out_dir / f'{part}.urdf.xacro'
    if out.exists() and not args.force:
        raise ConversionError(f'{out} exists; it is the part now. Use --force to overwrite')
    visuals, collisions = read_delivery(part_dir)
    inertia, source = estimate_inertia(part_dir, collisions, args.density, args.mass)
    slots = dict(parse_slot(spec) for spec in args.slot or [])
    frames = {}
    for spec in args.frame or []:
        name, frame, opts = parse_pose_spec(spec, '--frame')
        if opts:
            raise ConversionError(f'--frame takes no options: {spec!r}')
        frames[name] = frame
    out.write_text(emit_macro(part, visuals, collisions, inertia, source,
                              args.axis, args.attach, slots, frames))
    return out, inertia[0], len(collisions)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('paths', nargs='+', help='part directory, or the models/ dir with --all')
    ap.add_argument('--all', action='store_true',
                    help='bootstrap every delivered part under the given dir')
    ap.add_argument('--out-dir', help='where the macros go (default: ../urdf next to models/)')
    ap.add_argument('--mass', type=float, help='known mass in kg; the estimate is scaled to it')
    ap.add_argument('--density', type=float, default=DEFAULT_DENSITY,
                    help='density for the estimate, kg/m^3 (default %(default)s)')
    ap.add_argument('--axis', default='1 0 0',
                    help='spin axis in the part frame, the axis default of the macro')
    ap.add_argument('--attach', default='0 0 0',
                    help='attach point in the part frame, "x y z"')
    ap.add_argument('--slot', action='append',
                    metavar='NAME=x,y,z[,r,p,y][;accepts=a,b][;default=t][;joint=continuous]',
                    help='mount slot to declare (repeatable)')
    ap.add_argument('--frame', action='append', metavar='NAME=x,y,z[,r,p,y]',
                    help='reference frame to declare (repeatable)')
    ap.add_argument('--force', action='store_true', help='overwrite an existing macro')
    args = ap.parse_args(argv)

    if args.all:
        root = pathlib.Path(args.paths[0])
        parts = sorted(p for p in root.iterdir() if (p / 'model.sdf').exists())
    else:
        parts = [pathlib.Path(p) for p in args.paths]
    if not parts:
        sys.exit('no delivered parts found')
    out_dir = pathlib.Path(args.out_dir) if args.out_dir else parts[0].parent.parent / 'urdf'
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for part_dir in parts:
        try:
            out, mass, ncol = convert(part_dir, out_dir, args)
            print(f'{part_dir.name:34s} mass={mass:8.3f} kg  collisions={ncol}  -> {out}')
        except ConversionError as exc:
            failures += 1
            print(f'{part_dir.name:34s} FAILED: {exc}', file=sys.stderr)
    if not failures:
        print('next: add the include line to urdf/parts.xacro and review the file')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
