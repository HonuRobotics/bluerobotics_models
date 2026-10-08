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
thrust it settles at the current's velocity over the ground; under gz-sim's
own Hydrodynamics it would not move. Measured in sim time, so a slow
runner changes how long the test waits, never what it asserts.
"""

import os
from pathlib import Path
import re
import tempfile
import uuid

from ament_index_python.packages import get_package_share_directory
from conftest import launch_sim, make_cli, poll_until
import pytest

SOURCE_WORLD = (Path(get_package_share_directory('bluerov2_gazebo'))
                / 'worlds' / 'bluerov2_water.sdf')
WORLD_NAME = 'bluerov2_water'
MODEL = 'bluerov2'

# The current: 0.5 m/s setting east, the world's +x.
CURRENT_SPEED = 0.5

# The BlueROV2's surge damping is quadratic only (xU 0, xUabsU -33.732), so
# it never quite reaches the current: its speed through the water falls as
# 1 / (1 / u + k t), k = |xUabsU| / m, about 33.732 / 11.54 1/m.
K = 33.732 / 11.54

# Sim seconds before the drift is measured.
SETTLE = 20

# How close the measured drift must be to that curve, m/s.
TOL = 0.01


def expected_drift(t):
    """Return the drift over the ground t seconds after release, m/s."""
    return CURRENT_SPEED - 1.0 / (1.0 / CURRENT_SPEED + K * t)


_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
POSE_TRIPLE = re.compile(rf'({_NUM}) ({_NUM}) ({_NUM})')

gz = make_cli('gz')


def model_position(env):
    """Return the vehicle's world position from `gz model -p`: (x, y, z)."""
    code, out, err = gz(env, 'model', '-m', MODEL, '-p', timeout=15)
    triples = POSE_TRIPLE.findall(out)
    assert code == 0 and triples, f'cannot read the pose of {MODEL}:\n{out}\n{err}'
    return tuple(float(v) for v in triples[0])


def sim_seconds(env):
    """Return the current sim time in seconds from the world stats topic."""
    code, out, err = gz(env, 'topic', '-e', '-t', f'/world/{WORLD_NAME}/stats',
                        '-n', '1', timeout=15)
    block = re.search(r'sim_time\s*{([^}]*)}', out)
    assert code == 0 and block, f'cannot read world stats:\n{out}\n{err}'
    sec = re.search(r'\bsec:\s*(\d+)', block.group(1))
    nsec = re.search(r'nsec:\s*(\d+)', block.group(1))
    return (int(sec.group(1)) if sec else 0) + (int(nsec.group(1)) if nsec else 0) / 1e9


def wait_sim_seconds(env, seconds, timeout=240):
    """Block until the sim clock advances `seconds`, whatever the RTF."""
    start = sim_seconds(env)
    poll_until(lambda: sim_seconds(env) - start >= seconds, timeout,
               f'sim advanced less than {seconds}s in {timeout}s of wall time',
               interval=0.5)


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
      <pose>0 0 -2 0 0 0</pose>
    </include>
  </world>"""
    sdf = sdf.replace('  </world>', include, 1)
    path = Path(directory) / 'bluerov2_water.sdf'
    path.write_text(sdf)
    return path


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on the current world; return its env."""
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    world = world_with_current(tempfile.mkdtemp(prefix='bluerov2_gazebo_'))
    return launch_sim(
        request, 'gz sim', ['gz', 'sim', '-s', '-r', '-v', '3', str(world)], env,
        ready=lambda e: MODEL in gz(e, 'model', '--list')[1])


def test_drifts_with_the_current(sim):
    """With no thrust, the BlueROV2 drifts east as its damping predicts."""
    wait_sim_seconds(sim, SETTLE)
    t1, (x1, y1, _) = sim_seconds(sim), model_position(sim)
    wait_sim_seconds(sim, 5)
    t2, (x2, y2, _) = sim_seconds(sim), model_position(sim)
    vx, vy = (x2 - x1) / (t2 - t1), (y2 - y1) / (t2 - t1)
    expected = expected_drift((t1 + t2) / 2)
    print(f'drift ({vx:+.4f},{vy:+.4f}) m/s, expected {expected:+.4f} east')
    assert vx == pytest.approx(expected, abs=TOL), \
        f'drifting at ({vx:+.3f},{vy:+.3f}) m/s, expected {expected:+.3f} east'
    assert vy == pytest.approx(0.0, abs=TOL), f'drifting at ({vx:+.3f},{vy:+.3f}) m/s'
