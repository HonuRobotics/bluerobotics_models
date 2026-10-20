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
The BlueROV2 in an ocean current, headless.

bluerov2_water.sdf is copied with gz-maritime's ocean current set to 0.5 m/s setting
east (towards +x) and the BlueROV2 included. Its Hydrodynamics,
gz-maritime's, damps it against the water rather than the ground, so with no
thrust it is carried east, ever closer to the current's speed; under gz-sim's
own Hydrodynamics it would not move.

The world starts paused, so the vehicle is released at sim time 0. The
expected path comes from the generated model itself, its surge coefficient
and its mass, so it follows the next identification without an edit here.
Each sample's time and position come from one dynamic_pose message, the
time from its header stamp, so a slow runner changes how long the test waits,
never what it asserts.
"""

import math
import os
from pathlib import Path
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from conftest import launch_sim, make_cli, poll_until
import pytest

GZ_SHARE = Path(get_package_share_directory('bluerov2_gazebo'))
SOURCE_WORLD = GZ_SHARE / 'worlds' / 'bluerov2_water.sdf'
WORLD_NAME = 'bluerov2_water'
MODEL = 'bluerov2'
MODEL_SDF = GZ_SHARE / 'models' / MODEL / 'model.sdf'
START = '0 0 -2 0 0 0'

# The current: 0.5 m/s setting east, the world's +x.
CURRENT_SPEED = 0.5

# Sim seconds after release the position is checked at: early, while the
# vehicle still speeds up, where its path depends most on its damping.
CHECK_AT = 5.0

# How close the position must be to the expected path: what a surge
# coefficient 5 % off would move it by at CHECK_AT.
COEFFICIENT_ERROR = 0.05


def surge_damping_rate():
    """
    Return k = |xUabsU| / m, 1/m, from the generated model.

    The surge damping must be quadratic only (xU 0) for the path below.
    """
    text = MODEL_SDF.read_text()
    root = ET.fromstring(text)
    plugins = [p for p in root.iter('plugin')
               if p.get('filename') == 'gz-maritime-hydrodynamics-system']
    assert len(plugins) == 1, f'{MODEL_SDF} has {len(plugins)} Hydrodynamics plugins'
    assert float(plugins[0].findtext('xU', '0')) == 0.0, 'surge damping has a linear term'
    x_uabs_u = float(plugins[0].findtext('xUabsU'))
    mass = re.search(r'^  total mass: +(\S+) kg$', text, re.M)
    assert mass, f'{MODEL_SDF} has no total mass in its specs comment'
    return abs(x_uabs_u) / float(mass.group(1))


def expected_drift(t, k):
    """
    Return how far the vehicle has been carried t seconds after release, m.

    Released at rest in a current u, its speed through the water w obeys
    dw/dt = -k w |w| from w = u, so w = 1 / (1 / u + k t), and over the
    ground it has gone u t - ln(1 + k u t) / k.
    """
    u = CURRENT_SPEED
    return u * t - math.log(1.0 + k * u * t) / k


_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'

gz = make_cli('gz')


def stamped_position(env):
    """
    Return (sim time, x, y) of the vehicle from one dynamic_pose message.

    Text format leaves out fields that are zero, so a missing one reads 0.
    """
    code, out, err = gz(env, 'topic', '-e', '-n', '1',
                        '-t', f'/world/{WORLD_NAME}/dynamic_pose/info', timeout=15)
    stamp = re.search(r'header\s*{\s*stamp\s*{([^}]*)}', out)
    pose = re.search(rf'name: "{MODEL}"\s*id: \d+\s*position\s*{{([^}}]*)}}', out)
    assert code == 0 and stamp and pose, \
        f'cannot read the pose of {MODEL}:\n{out}\n{err}'

    def field(block, name):
        match = re.search(rf'\b{name}:\s*({_NUM})', block)
        return float(match.group(1)) if match else 0.0

    t = field(stamp.group(1), 'sec') + field(stamp.group(1), 'nsec') / 1e9
    return t, field(pose.group(1), 'x'), field(pose.group(1), 'y')


def world_with_current(directory):
    """Write the world with a current set and the vehicle in it; return it."""
    sdf = SOURCE_WORLD.read_text()
    start = sdf.index('filename="gz-maritime-ocean-current-system"')
    end = sdf.index('</plugin>', start)
    block = sdf[start:end]
    block = re.sub(r'<speed>[^<]*</speed>', f'<speed>{CURRENT_SPEED}</speed>', block)
    block = re.sub(r'<direction>[^<]*</direction>', '<direction>90</direction>', block)
    sdf = sdf[:start] + block + sdf[end:]
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
    """Start a headless gz server, paused, on the current world; return its env."""
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    world = world_with_current(tempfile.mkdtemp(prefix='bluerov2_gazebo_'))
    return launch_sim(
        request, 'gz sim', ['gz', 'sim', '-s', '-v', '3', str(world)], env,
        ready=lambda e: MODEL in gz(e, 'model', '--list')[1])


def test_drifts_with_the_current(sim):
    """With no thrust, the BlueROV2 is carried east as its damping predicts."""
    k = surge_damping_rate()
    tol = abs(expected_drift(CHECK_AT, k * (1.0 + COEFFICIENT_ERROR))
              - expected_drift(CHECK_AT, k))

    t0, x0, y0 = stamped_position(sim)
    assert t0 == 0.0, f'the world was not paused at release: sim time {t0}'
    code, out, err = gz(sim, 'service', '-s', f'/world/{WORLD_NAME}/control',
                        '--reqtype', 'gz.msgs.WorldControl',
                        '--reptype', 'gz.msgs.Boolean', '--timeout', '5000',
                        '--req', 'pause: false', timeout=15)
    assert code == 0 and 'true' in out, f'cannot unpause the world:\n{out}\n{err}'

    sample = []

    def reached():
        sample[:] = stamped_position(sim)
        return sample[0] >= CHECK_AT
    poll_until(reached, 240, f'sim did not reach {CHECK_AT}s in 240s of wall time',
               interval=0.2)
    t, x, y = sample
    expected = expected_drift(t, k)
    print(f'k {k:.4f} 1/m: at {t:.3f}s carried ({x - x0:+.4f},{y - y0:+.4f}) m, '
          f'expected {expected:+.4f} east, tolerance {tol:.4f}')
    assert x - x0 == pytest.approx(expected, abs=tol), \
        f'carried {x - x0:+.4f} m east at {t:.3f}s, expected {expected:+.4f}'
    assert y - y0 == pytest.approx(0.0, abs=tol), \
        f'carried {y - y0:+.4f} m north at {t:.3f}s, expected none'
