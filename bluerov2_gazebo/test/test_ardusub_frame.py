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
The ROV's thruster geometry agrees with the ArduSub frame it is driven by.

ArduSub does not take a servo-to-thruster map from parameters: it assigns
Motor1..Motor6 to SERVO1..SERVO6 itself from FRAME_CONFIG, and mixes them
with the factors baked into AP_Motors6DOF. So the model's channel numbering
is not a choice, it is a claim - that our thruster_N sits where ArduSub
expects Motor N - and this asserts it.

Get it wrong and nothing errors: the vehicle arms, swims, and answers the
wrong stick.
"""

import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest

DESC_SHARE = Path(get_package_share_directory('bluerov2_description'))
URDF_XACRO = DESC_SHARE / 'urdf' / 'bluerov2.urdf.xacro'

# ArduSub SUB_FRAME_VECTORED, from AP_Motors6DOF.cpp setup_motors():
#
#   add_motor_raw_6dof(MOT_1, 0, 0,  1.0f, 0, -1.0f,  1.0f, 1)
#   ...                       roll pitch yaw throttle forward lateral
#
# Only the NON-ZERO factors are asserted. A zero factor means the mixer
# ignores that axis for that motor, not that the thruster produces no
# moment about it: the standard vehicle's verticals sit 15 mm forward of
# the origin, so they pitch slightly, and ArduSub does not model it.
VECTORED = {
    'thruster_1': {'yaw': +1, 'forward': -1, 'lateral': +1},
    'thruster_2': {'yaw': -1, 'forward': -1, 'lateral': -1},
    'thruster_3': {'yaw': -1, 'forward': +1, 'lateral': +1},
    'thruster_4': {'yaw': +1, 'forward': +1, 'lateral': -1},
    'thruster_5': {'roll': +1, 'throttle': -1},
    'thruster_6': {'roll': -1, 'throttle': -1},
}


def rotation(rpy):
    """Fixed-axis XYZ rotation matrix from a URDF rpy triple."""
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p),
                              math.sin(p), math.cos(y), math.sin(y))
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp,     cp * sr,                cp * cr),
    )


def apply(rot, v):
    """Rotate a 3-vector."""
    return tuple(sum(rot[i][k] * v[k] for k in range(3)) for i in range(3))


@pytest.fixture(scope='module')
def urdf():
    """Return the assembled default vehicle as a URDF root element."""
    out = subprocess.run(['xacro', str(URDF_XACRO)], check=True,
                         capture_output=True, text=True, timeout=120)
    return ET.fromstring(out.stdout)


def pose_in_base(root, link):
    """Position and +X direction of a link in base_link coordinates."""
    by_child = {}
    for j in root.iter('joint'):
        child = j.find('child').get('link')
        origin = j.find('origin')
        xyz = tuple(float(v) for v in (origin.get('xyz', '0 0 0')).split())
        rpy = tuple(float(v) for v in (origin.get('rpy', '0 0 0')).split())
        by_child[child] = (j.find('parent').get('link'), xyz, rpy)

    pos, rot = (0.0, 0.0, 0.0), ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    node = link
    while node != 'base_link':
        assert node in by_child, f'{link} does not reach base_link'
        parent, xyz, rpy = by_child[node]
        # Compose parent <- node: the accumulated transform is expressed in
        # the parent's frame at each step.
        r = rotation(rpy)
        pos = tuple(xyz[i] + apply(r, pos)[i] for i in range(3))
        rot = tuple(tuple(sum(r[i][k] * rot[k][j] for k in range(3))
                          for j in range(3)) for i in range(3))
        node = parent
    return pos, apply(rot, (1.0, 0.0, 0.0))


def to_ned(v):
    """Our body frame (x fwd, y port, z up) to ArduSub's (x fwd, y stbd, z down)."""
    return (v[0], -v[1], -v[2])


@pytest.mark.parametrize('name,factors', sorted(VECTORED.items()))
def test_thruster_matches_its_ardusub_motor(urdf, name, factors):
    """Each thruster produces the force and moment its ArduSub motor mixes."""
    pos, direction = pose_in_base(urdf, name)
    p, f = to_ned(pos), to_ned(direction)

    # Unit thrust along the propeller's +X; moments about the body origin.
    produced = {
        'forward': f[0],
        'lateral': f[1],
        # ArduSub throttle is positive up, the body frame is positive down.
        'throttle': -f[2],
        'roll': p[1] * f[2] - p[2] * f[1],
        'pitch': p[2] * f[0] - p[0] * f[2],
        'yaw': p[0] * f[1] - p[1] * f[0],
    }
    for axis, expected in factors.items():
        actual = produced[axis]
        assert abs(actual) > 1e-6, (
            f'{name} produces no {axis}, but ArduSub mixes it with '
            f'factor {expected:+d}')
        assert math.copysign(1, actual) == math.copysign(1, expected), (
            f'{name} {axis} is {actual:+.3f}, ArduSub expects the sign of '
            f'{expected:+d}. The thruster is reversed, or it is in the '
            f'wrong slot for Motor {name.split("_")[-1]}.')


def test_channel_order_matches_motor_order(urdf):
    """thruster_N is Motor N, so the frame covers exactly channels 0..N-1."""
    links = {link.get('name') for link in urdf.iter('link')}
    fitted = sorted(n for n in VECTORED if n in links)
    assert fitted == sorted(VECTORED), (
        'the default vehicle no longer fits the six thrusters the Vectored '
        f'frame mixes: missing {sorted(set(VECTORED) - set(fitted))}')
