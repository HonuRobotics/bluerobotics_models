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
Check that a chassis xacro's thruster slots match the Blender assembly.

The assembly scene is the source of truth for where each T200 sits; the
xacro's thruster_N / thruster_body_N slots follow it. This reads every T200
body and prop in the scene, maps it into base_link (the scene origin is the
commissioned datum, which is base_link; x = -Blender y, y = Blender x,
z = Blender z), matches it to its slot by role, and compares:

  - position, within 0.5 mm;
  - the thrust axis as a line, within 1 degree. A T200's duct axis is its
    mesh's local Y in the scene; a slot's thrust axis is its +x, or -x where
    the slot sets axis '-1 0 0'. The sign along the line is ArduSub's
    convention and is set in the xacro, so only the line is compared.

Run inside Blender, by a person (not the build):

    blender -b --python-exit-code 1 bluerobotics_parts/assemblies/bluerov2_assembly.blend \
        --python bluerobotics_parts/scripts/check_blend_slots.py -- \
        bluerobotics_parts/urdf/bluerov2_chassis.urdf.xacro

The heavy chassis is checked the same way, against its own scene:

    blender -b --python-exit-code 1 bluerobotics_parts/assemblies/bluerov2_heavy_assembly.blend \
        --python bluerobotics_parts/scripts/check_blend_slots.py -- \
        bluerobotics_parts/urdf/bluerov2_heavy_chassis.urdf.xacro

Prints one row per part and exits non-zero if any row fails.
"""

import math
import re
import sys

import bpy  # noqa: I100  (Blender's module, only inside Blender)

POS_TOL = 0.0005   # m
ANGLE_TOL = 1.0    # degrees
SLOT = re.compile(r"(thruster(?:_body)?_\d)=dict\(xyz='([^']*)', rpy='([^']*)'([^)]*)\)")


def rpy_x(r, p, y):
    """First column of R = Rz(y) Ry(p) Rx(r): the slot's +x in base_link."""
    return (math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), -math.sin(p))


def read_slots(xacro):
    slots = {}
    for name, xyz, rpy, rest in SLOT.findall(open(xacro).read()):
        axis = rpy_x(*map(float, rpy.split()))
        if "axis='-1 0 0'" in rest:
            axis = tuple(-c for c in axis)
        slots[name] = (tuple(map(float, xyz.split())), axis)
    return slots


def role(pos, axis, corners):
    """
    Slot number for a T200 at pos with duct axis line axis, in base_link.

    corners: the chassis has four corner verticals (the Heavy: 5 fore
    starboard, 6 fore port, 7 aft starboard, 8 aft port), not two.
    """
    if abs(axis[2]) > 0.7:
        if corners and pos[0] < 0:
            return 8 if pos[1] > 0 else 7
        return 6 if pos[1] > 0 else 5
    if pos[0] > 0:
        return 2 if pos[1] > 0 else 1
    return 4 if pos[1] > 0 else 3


def scene_parts(corners):
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if o.type != 'MESH' or not o.name.startswith('t200'):
            continue
        m = o.matrix_world
        t = m.translation
        ly = (m[0][1], m[1][1], m[2][1])
        n = math.sqrt(sum(c * c for c in ly))
        pos = (-t.y, t.x, t.z)
        axis = (-ly[1] / n, ly[0] / n, ly[2] / n)
        kind = 'thruster_body' if o.name.startswith('t200_thruster') else 'thruster'
        yield o.name, f'{kind}_{role(pos, axis, corners)}', pos, axis


def main():
    xacro = sys.argv[sys.argv.index('--') + 1]
    slots = read_slots(xacro)
    failed, seen = 0, set()
    print(f"{'scene object':26} {'slot':16} {'position error mm':>18} "
          f"{'axis error deg':>15}  result")
    for obj, slot, pos, axis in scene_parts('thruster_7' in slots):
        seen.add(slot)
        if slot not in slots:
            print(f'{obj:26} {slot:16} {"no such slot":>18}')
            failed += 1
            continue
        sxyz, saxis = slots[slot]
        dpos = 1000 * math.dist(pos, sxyz)
        cos = abs(sum(a * b for a, b in zip(axis, saxis)))
        dang = math.degrees(math.acos(min(1.0, cos)))
        ok = dpos <= POS_TOL * 1000 and dang <= ANGLE_TOL
        failed += not ok
        print(f'{obj:26} {slot:16} {dpos:18.2f} {dang:15.2f}  {"pass" if ok else "FAIL"}')
    for slot in sorted(set(slots) - seen):
        print(f'{"(none in scene)":26} {slot:16} {"missing":>18}')
        failed += 1
    print(f'{failed} failed of {len(slots)} slots')
    sys.exit(1 if failed else 0)


main()
