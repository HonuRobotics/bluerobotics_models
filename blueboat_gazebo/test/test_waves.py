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
The BlueBoat on the waves, headless.

blueboat_waves.sdf is copied with the sea set still (sea state 0) and the
BlueBoat included. gz-maritime's wave buoyancy floats it by the pontoon
boxes it marks gz:buoyancy="true", under the wave surface.

  * On still water it rests at its static draft: the depth at which the
    marked boxes displace its weight of seawater, worked out here from the
    generated model itself, its mass and its marked boxes, so it follows the
    next identification without an edit here.
  * Raised to sea state 4 while running, it rides the waves: it heaves about
    as much as the sea does, and stays upright and afloat. On gz-sim's flat
    buoyancy it would not move at all.

The world starts paused, so the vehicle is released at sim time 0. Each
sample's time and pose come from one dynamic_pose message, the time from its
header stamp, so a slow runner changes how long the test waits, never what
it asserts.
"""

import math
import os
from pathlib import Path
import re
import statistics
import tempfile
import uuid
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from conftest import launch_sim, make_cli, poll_until
import pytest

GZ_SHARE = Path(get_package_share_directory('blueboat_gazebo'))
SOURCE_WORLD = GZ_SHARE / 'worlds' / 'blueboat_waves.sdf'
WORLD_NAME = 'blueboat_waves'
MODEL = 'blueboat'
MODEL_SDF = GZ_SHARE / 'models' / MODEL / 'model.sdf'
START = '0 0 0.05 0 0 0'
WATER_DENSITY = 1025.0
BUOYANCY_MARK = '{http://gazebosim.org/schema}buoyancy'

# Still water: settled after SETTLE sim seconds, then watched for WATCH.
SETTLE = 8.0
WATCH = 4.0
# How close to the static draft it must rest, m.
DRAFT_TOLERANCE = 0.005

# The rough sea: the state, its significant wave height from gz_waves'
# sea-state table, how long it is given to ramp in (tau 2 s) and how long it
# is watched for: several of its peak periods (about 7 s).
SEA_STATE = 4
SEA_STATE_HS = 1.875
RAMP = 12.0
RIDE = 30.0
# The heave's standard deviation, against the sea's (Hs / 4): the boat is
# short against the waves, so it follows them (with the sea right above it,
# its heave matches the surface's to within 1 %). The range is wide for the
# sea itself: over a watch of a few waves its height spreads, measured from
# 0.77 to 1.16 times Hs / 4 here. On flat buoyancy the heave is 0.
HEAVE_RANGE = (0.4, 1.6)
# Upright: neither roll nor pitch ever passes this, degrees.
MAX_TILT = 30.0

_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'

gz = make_cli('gz')


def static_rest_height():
    """
    Return the model's height at rest on still water, m.

    The marked boxes all have the same bottom, so on still water they are
    under to the depth d where they displace the boat's weight:
    d = m / (rho * A), A their total waterplane area. The model then rests
    with those bottoms at -d.
    """
    text = MODEL_SDF.read_text()
    mass = re.search(r'^  total mass: +(\S+) kg$', text, re.M)
    assert mass, f'{MODEL_SDF} has no total mass in its specs comment'
    root = ET.fromstring(text)
    area, bottoms = 0.0, set()
    for link in root.iter('link'):
        link_pose = [float(v) for v in link.findtext('pose', '0 0 0 0 0 0').split()]
        assert link_pose[3:] == [0.0, 0.0, 0.0], f'link {link.get("name")} is rotated'
        for col in link.iter('collision'):
            if col.get(BUOYANCY_MARK) != 'true':
                continue
            size = col.find('geometry/box/size')
            assert size is not None, f'marked collision {col.get("name")} is not a box'
            sx, sy, sz = (float(v) for v in size.text.split())
            pose = [float(v) for v in col.findtext('pose', '0 0 0 0 0 0').split()]
            assert pose[3:] == [0.0, 0.0, 0.0], f'{col.get("name")} is rotated'
            area += sx * sy
            bottoms.add(round(link_pose[2] + pose[2] - sz / 2.0, 6))
    assert area > 0.0, f'{MODEL_SDF} marks no buoyancy boxes'
    assert len(bottoms) == 1, f'the marked boxes have different bottoms: {bottoms}'
    draft = float(mass.group(1)) / (WATER_DENSITY * area)
    return -(bottoms.pop() + draft)


def stamped_pose(env):
    """
    Return (sim time, z, roll, pitch) of the vehicle from one dynamic_pose.

    Text format leaves out fields that are zero, so a missing one reads 0
    (and a missing w, 1 only when the whole orientation is left out).
    """
    code, out, err = gz(env, 'topic', '-e', '-n', '1',
                        '-t', f'/world/{WORLD_NAME}/dynamic_pose/info', timeout=15)
    stamp = re.search(r'header\s*{\s*stamp\s*{([^}]*)}', out)
    pose = re.search(
        rf'name: "{MODEL}"\s*id: \d+\s*position\s*{{([^}}]*)}}\s*'
        rf'(?:orientation\s*{{([^}}]*)}})?', out)
    assert code == 0 and stamp and pose, \
        f'cannot read the pose of {MODEL}:\n{out}\n{err}'

    def field(block, name, default=0.0):
        match = re.search(rf'\b{name}:\s*({_NUM})', block or '')
        return float(match.group(1)) if match else default

    t = field(stamp.group(1), 'sec') + field(stamp.group(1), 'nsec') / 1e9
    q = pose.group(2)
    x, y, z = (field(q, k) for k in ('x', 'y', 'z'))
    w = field(q, 'w', 1.0 if q is None else 0.0)
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
    return t, field(pose.group(1), 'z'), math.degrees(roll), math.degrees(pitch)


def watch(env, start, until):
    """Sample the pose from sim time `start` until `until`; return the samples."""
    samples = []

    def reached():
        s = stamped_pose(env)
        if s[0] >= start:
            samples.append(s)
        return s[0] >= until
    poll_until(reached, 600, f'sim did not reach {until}s in 600s of wall time',
               interval=0.1)
    assert len(samples) >= 20, f'only {len(samples)} samples from {start}s to {until}s'
    return samples


def sim_time(env):
    return stamped_pose(env)[0]


def world_still_with_boat(directory):
    """Write the world with still water and the vehicle in it; return it."""
    sdf = SOURCE_WORLD.read_text()
    sdf, n = re.subn(r'<sea_state>[^<]*</sea_state>', '<sea_state>0</sea_state>', sdf)
    assert n == 1, f'{SOURCE_WORLD} sets the sea state {n} times'
    include = f"""
    <include>
      <uri>model://{MODEL}</uri>
      <pose>{START}</pose>
    </include>
  </world>"""
    sdf = sdf.replace('  </world>', include, 1)
    path = Path(directory) / f'{WORLD_NAME}.sdf'
    path.write_text(sdf)
    return path


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server, paused, on the still world; return its env."""
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    world = world_still_with_boat(tempfile.mkdtemp(prefix='blueboat_gazebo_'))
    env = launch_sim(
        request, 'gz sim', ['gz', 'sim', '-s', '-v', '3', str(world)], env,
        ready=lambda e: MODEL in gz(e, 'model', '--list')[1])
    code, out, err = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/control',
                        '--reqtype', 'gz.msgs.WorldControl',
                        '--reptype', 'gz.msgs.Boolean', '--timeout', '5000',
                        '--req', 'pause: false', timeout=15)
    assert code == 0 and 'true' in out, f'cannot unpause the world:\n{out}\n{err}'
    return env


def test_rests_at_its_draft_on_still_water(sim):
    """On sea state 0 the boat settles where its marked boxes hold it up."""
    expected = static_rest_height()
    samples = watch(sim, SETTLE, SETTLE + WATCH)
    z = [s[1] for s in samples]
    print(f'still water: z mean {statistics.fmean(z):+.4f} m, sd '
          f'{statistics.pstdev(z):.4f}, expected {expected:+.4f}')
    assert statistics.fmean(z) == pytest.approx(expected, abs=DRAFT_TOLERANCE), \
        f'rests at z {statistics.fmean(z):+.4f} m, expected {expected:+.4f}'
    assert statistics.pstdev(z) < DRAFT_TOLERANCE, 'moves on still water'


def test_rides_the_waves(sim):
    """At sea state 4 the boat heaves with the sea, upright and afloat."""
    code, out, err = gz(
        sim, 'service', '-s', f'/world/{WORLD_NAME}/wave/set_parameters',
        '--reqtype', 'gz.msgs.Param', '--reptype', 'gz.msgs.Boolean',
        '--timeout', '5000', '--req',
        f'params {{ key: "sea_state" value {{ type: INT32 int_value: {SEA_STATE} }} }}',
        timeout=15)
    assert code == 0 and 'true' in out, f'cannot set the sea state:\n{out}\n{err}'
    start = sim_time(sim) + RAMP
    samples = watch(sim, start, start + RIDE)
    z = [s[1] for s in samples]
    heave = statistics.pstdev(z) / (SEA_STATE_HS / 4.0)
    tilt = max(max(abs(s[2]), abs(s[3])) for s in samples)
    print(f'sea state {SEA_STATE}: {len(samples)} samples, heave sd '
          f'{statistics.pstdev(z):.3f} m = {heave:.2f} x Hs/4, z from '
          f'{min(z):+.2f} to {max(z):+.2f}, tilt up to {tilt:.1f} deg')
    assert HEAVE_RANGE[0] <= heave <= HEAVE_RANGE[1], \
        f'heaves {heave:.2f} x Hs/4 of the sea, expected {HEAVE_RANGE}'
    assert tilt < MAX_TILT, f'tilted {tilt:.1f} deg'
    assert min(z) > -SEA_STATE_HS, f'went down to {min(z):+.2f} m'
