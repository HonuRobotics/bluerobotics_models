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
Stamp a generated model file with a specs comment.

Reads the generated URDF and the vehicle config, computes the headline
numbers of the model (total mass, center of mass, displaced volume and
center of buoyancy from the collision geometry, net buoyancy) and writes
the target file back with a summary comment in the XML prolog. Run at
build time on the generated URDF itself and on the composed model.sdf,
so the installed artifacts document the vehicle they describe:

    stamp_model_specs.py --vehicle bluerov2 --urdf gen/bluerov2.urdf \
        --config config/bluerov2.yaml \
        --stamp gen/bluerov2.urdf --out stamped/bluerov2.urdf

The comment is informational only; every consumer parses the XML and
ignores it. Restamping replaces a previous comment, never duplicates it.
"""

import argparse
import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import yaml

WATER_DENSITY = 1025.0

STAMP_RE = re.compile(r'<!-- =+ model specs =+.*?=+ -->\n?', re.S)


def rpy_matrix(r, p, y):
    """Rotation matrix (row tuples) for URDF fixed axis rpy angles."""
    cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p),
                              math.sin(p), math.cos(y), math.sin(y))
    return ((cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
            (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
            (-sp, cp * sr, cp * cr))


def compose(a, b):
    """Compose two (rotation, translation) transforms: a then b."""
    ra, ta = a
    rb, tb = b
    rot = tuple(tuple(sum(ra[i][k] * rb[k][j] for k in range(3))
                      for j in range(3)) for i in range(3))
    trans = tuple(ta[i] + sum(ra[i][k] * tb[k] for k in range(3))
                  for i in range(3))
    return rot, trans


def apply(tf, v):
    """Apply a (rotation, translation) transform to a point."""
    rot, trans = tf
    return tuple(trans[i] + sum(rot[i][k] * v[k] for k in range(3))
                 for i in range(3))


def origin_tf(element):
    """Transform of an <origin> child (identity when absent)."""
    origin = element.find('origin') if element is not None else None
    if origin is None:
        return rpy_matrix(0, 0, 0), (0.0, 0.0, 0.0)
    xyz = [float(v) for v in origin.get('xyz', '0 0 0').split()]
    rpy = [float(v) for v in origin.get('rpy', '0 0 0').split()]
    return rpy_matrix(*rpy), tuple(xyz)


def link_poses(root):
    """Pose of every link in the root link frame, via the joint tree."""
    parent_joint = {j.find('child').get('link'): j
                    for j in root.findall('joint')}
    poses = {}

    def pose(name):
        if name not in poses:
            joint = parent_joint.get(name)
            if joint is None:
                poses[name] = rpy_matrix(0, 0, 0), (0.0, 0.0, 0.0)
            else:
                poses[name] = compose(pose(joint.find('parent').get('link')),
                                      origin_tf(joint))
        return poses[name]

    for link in root.findall('link'):
        pose(link.get('name'))
    return poses


def mass_properties(root):
    """Total mass and center of mass of the URDF, in the root link frame."""
    poses = link_poses(root)
    total, moment = 0.0, [0.0, 0.0, 0.0]
    for link in root.findall('link'):
        inertial = link.find('inertial')
        if inertial is None:
            continue
        mass = float(inertial.find('mass').get('value'))
        com = apply(compose(poses[link.get('name')], origin_tf(inertial)),
                    (0.0, 0.0, 0.0))
        total += mass
        for i in range(3):
            moment[i] += mass * com[i]
    return total, tuple(m / total for m in moment)


def buoyancy_properties(root):
    """Displaced volume and its centroid from the box collision geometry."""
    poses = link_poses(root)
    volume, moment = 0.0, [0.0, 0.0, 0.0]
    for link in root.findall('link'):
        for collision in link.findall('collision'):
            box = collision.find('geometry/box')
            if box is None:
                continue  # graded buoyancy also ignores non box geometry
            size = [float(v) for v in box.get('size').split()]
            vol = size[0] * size[1] * size[2]
            center = apply(compose(poses[link.get('name')],
                                   origin_tf(collision)), (0.0, 0.0, 0.0))
            volume += vol
            for i in range(3):
                moment[i] += vol * center[i]
    return volume, tuple(m / volume for m in moment)


def accessory_summary(cfg):
    """One `type (name)` item per configured accessory."""
    return [f'{a["type"]} ({a["name"]})'
            for a in cfg.get('accessories') or []]


def specs_comment(vehicle, urdf_root, cfg):
    """Build the model specs comment block for the stamped file."""
    total, com = mass_properties(urdf_root)
    volume, cob = buoyancy_properties(urdf_root)
    displaced = WATER_DENSITY * volume
    rows = []
    if 'variant' in cfg:
        rows.append(('variant', cfg['variant']))
    rows += [
        ('total mass', f'{total:.3f} kg'),
        ('center of mass',
         f'[{com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f}] m in base_link'),
        ('displaced volume',
         f'{volume:.6f} m^3 = {displaced:.3f} kg of seawater '
         f'at {WATER_DENSITY:.0f} kg/m^3'),
        ('center of buoyancy',
         f'[{cob[0]:.4f}, {cob[1]:.4f}, {cob[2]:.4f}] m in base_link'),
    ]
    if vehicle == 'bluerov2':
        rows.append(('net buoyancy', f'{displaced - total:+.4f} kg'))
    else:
        rows.append(('reserve buoyancy',
                     f'{displaced - total:+.3f} kg at full submersion'))
    accessories = accessory_summary(cfg) or ['none']
    rows.append(('accessories', '; '.join(accessories)))
    width = max(len(label) for label, _ in rows) + 2
    body = '\n'.join(f'  {label + ":":<{width}}{value}'
                     for label, value in rows)
    bar = '=' * 24
    return (f'<!-- {bar} model specs {bar}\n'
            f'  Generated at build time by stamp_model_specs.py; do not edit.\n'
            f'{body}\n'
            f'{bar}{bar}============= -->\n')


def stamp(text, comment):
    """Insert the comment into the XML prolog, replacing any old stamp."""
    text = STAMP_RE.sub('', text)
    match = re.match(r'<\?xml[^>]*\?>\n?', text)
    head = match.group(0) if match else ''
    return head + comment + text[len(head):]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vehicle', required=True,
                        choices=['blueboat', 'bluerov2'])
    parser.add_argument('--urdf', required=True,
                        help='generated URDF the numbers are computed from')
    parser.add_argument('--config', required=True)
    parser.add_argument('--stamp', required=True,
                        help='file the comment is inserted into')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f) or {}
    urdf_root = ET.parse(args.urdf).getroot()
    comment = specs_comment(args.vehicle, urdf_root, cfg)
    if '--' in comment.replace('<!--', '', 1)[:-len('-->\n')]:
        sys.exit('model specs comment would contain "--", illegal in XML')
    with open(args.stamp) as f:
        text = f.read()
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w') as f:
        f.write(stamp(text, comment))


if __name__ == '__main__':
    main()
