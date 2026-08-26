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
Headless Gazebo integration: world loads, interfaces up, physics behaves.

Everything here is a hard requirement, including the echosounder render test:
a missing gz CLI or render path fails the suite rather than skipping it, so
a broken environment cannot report green. CI runners render headless via EGL.
The behavior tests measure in SIM time (world stats), so a slow runner with a
low real time factor changes only how long they wait, never what they assert.
"""

import math
import os
from pathlib import Path
import re
import subprocess
import uuid

from ament_index_python.packages import get_package_share_directory
from conftest import launch_sim, make_cli, poll_until
import pytest

WORLD = (Path(get_package_share_directory('blueboat_gazebo'))
         / 'worlds' / 'blueboat_playground.sdf')
WORLD_NAME = 'blueboat_playground'

_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
POSE_TRIPLE = re.compile(rf'({_NUM}) ({_NUM}) ({_NUM})')

gz = make_cli('gz')


def model_pose(env):
    """Vehicle world pose from `gz model -p`: (x, y, z, roll, pitch, yaw)."""
    code, out, err = gz(env, 'model', '-m', 'blueboat', '-p', timeout=15)
    triples = POSE_TRIPLE.findall(out)
    assert code == 0 and len(triples) >= 2, (
        f'cannot read model pose:\n{out}\n{err}')
    return tuple(float(v) for triple in triples[:2] for v in triple)


def sim_seconds(env):
    """Return the current sim time in seconds from the world stats topic."""
    code, out, err = gz(env, 'topic', '-e', '-t',
                        f'/world/{WORLD_NAME}/stats', '-n', '1', timeout=15)
    block = re.search(r'sim_time\s*{([^}]*)}', out)
    assert code == 0 and block, f'cannot read world stats:\n{out}\n{err}'
    # (?<![a-z]) so 'sec:' never matches inside 'nsec:' (protobuf text
    # omits a zero sec field, leaving only nsec in the block).
    sec = re.search(r'(?<![a-z])sec:\s*(\d+)', block.group(1))
    nsec = re.search(r'nsec:\s*(\d+)', block.group(1))
    return (int(sec.group(1)) if sec else 0) + \
        (int(nsec.group(1)) if nsec else 0) / 1e9


def wait_sim_seconds(env, seconds, timeout=120):
    """Block until the sim clock advances `seconds`, whatever the RTF."""
    start = sim_seconds(env)
    poll_until(lambda: sim_seconds(env) - start >= seconds, timeout,
               f'sim advanced less than {seconds}s in {timeout}s of wall time',
               interval=0.5)


def teleport(env, x, y, z):
    """Move the vehicle to a pose with identity orientation."""
    req = (f'name: "blueboat", position: {{x: {x}, y: {y}, z: {z}}}, '
           'orientation: {w: 1}')
    code, out, err = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/set_pose',
                        '--reqtype', 'gz.msgs.Pose',
                        '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '5000', '--req', req, timeout=15)
    assert code == 0 and 'true' in out, f'set_pose failed:\n{out}\n{err}'


def command_motors(env, mapping, repeats=6):
    """
    Latch thrust commands (N), publishing every topic in parallel each round.

    Parallel publication matters: commands latch, so staggered onset applies a
    differential wrench and yaws the boat off its heading. Rounds repeat
    because one-shot publications can lose the discovery race.
    """
    for _ in range(repeats):
        procs = [(side, subprocess.Popen(
            ['gz', 'topic', '-t', f'/blueboat/motor_{side}/thrust',
             '-m', 'gz.msgs.Double', '-p', f'data: {value}'],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True)) for side, value in mapping.items()]
        for side, proc in procs:
            _, err = proc.communicate(timeout=20)
            assert proc.returncode == 0, (
                f'motor {side} command failed ({proc.returncode}): {err}')


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on an isolated partition; yield its env."""
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    # -v 3 so warnings and messages (not just errors) reach the audited log.
    return launch_sim(
        request, 'gz sim',
        ['gz', 'sim', '-s', '-r', '-v', '3', str(WORLD)], env,
        ready=lambda e: 'blueboat' in gz(e, 'model', '--list')[1])


def test_model_loaded(sim):
    """The composed model is in the world."""
    _, out, _ = gz(sim, 'model', '--list')
    assert 'blueboat' in out


def test_interfaces_advertised(sim):
    """Motor commands, speed feedback and the world clock are advertised."""
    needed = ('/blueboat/motor_port/thrust',
              '/blueboat/motor_stbd/thrust',
              '/blueboat/motor_port/thrust/ang_vel',
              '/blueboat/motor_stbd/thrust/ang_vel',
              f'/world/{WORLD_NAME}/clock')
    poll_until(
        lambda: all(t in gz(sim, 'topic', '-l')[1] for t in needed), 30,
        lambda: f'missing topics; last listing:\n{gz(sim, "topic", "-l")[1]}')


def test_physics_steps(sim):
    """Simulation iterations advance (systems survive stepping)."""
    def advancing():
        code, out, _ = gz(sim, 'topic', '-e', '-t',
                          f'/world/{WORLD_NAME}/stats', '-n', '1', timeout=15)
        return (code == 0 and 'iterations' in out
                and int(out.split('iterations:')[1].split()[0]) > 0)
    poll_until(advancing, 30, 'sim iterations did not advance')


def test_echosounder_ranges(sim):
    """The ping sensor streams ranges (gpu_lidar render path required)."""
    code, out, err = gz(sim, 'topic', '-e', '-t', '/blueboat/ping/range',
                        '-n', '1', timeout=30)
    assert code == 0 and 'ranges' in out, (
        f'no ranges: broken sensor config or no usable render path\n{err}')
    assert 'frame' in out


def test_boat_recovers_from_submersion(sim):
    """
    Pushed under, the pontoons drive the boat back to its float equilibrium.

    Only the end state is asserted: the recovery is fast enough that a slow
    runner can miss the submerged baseline between the teleport and the first
    pose read, so any delta assertion races.
    """
    teleport(sim, 0, 0, -1.0)
    t0 = sim_seconds(sim)
    wait_sim_seconds(sim, 6)
    t1, z1 = sim_seconds(sim), model_pose(sim)[2]
    assert z1 > -0.08, (
        f'no reserve buoyancy recovery: z {z1:.2f} after {t1 - t0:.1f} sim s '
        f'(float equilibrium puts base_link at about z 0, the waterline)')


def test_forward_thrust_surges(sim):
    """
    Equal thrust on both motors drives the boat along its nose, without crab.

    Command onset can rotate the heading (see command_motors), so the
    assertion is on the steady state, which is what the model owns: velocity
    aligned with the body x axis and no residual yaw, wherever the nose ended
    up pointing.
    """
    teleport(sim, 0, 0, 0.0)
    wait_sim_seconds(sim, 3)
    command_motors(sim, {'port': 10.0, 'stbd': 10.0})
    wait_sim_seconds(sim, 8)          # onset transient: spin damps, speed builds
    t1 = sim_seconds(sim)
    x1, y1, _, _, _, yaw1 = model_pose(sim)
    wait_sim_seconds(sim, 8)
    t2 = sim_seconds(sim)
    x2, y2, _, _, _, yaw2 = model_pose(sim)
    dx, dy = x2 - x1, y2 - y1
    speed = math.hypot(dx, dy) / (t2 - t1)
    assert speed > 0.05, (
        f'no surge: {speed:.3f} m/s over {t2 - t1:.1f} sim s')
    crab = math.degrees(math.atan2(dy, dx) - yaw2)
    crab = (crab + 180) % 360 - 180
    assert abs(crab) < 20, (
        f'not moving along the nose: crab {crab:+.1f} deg, '
        f'travel ({dx:+.2f},{dy:+.2f}) m at yaw {math.degrees(yaw2):+.1f} deg')
    residual_yaw = math.degrees(yaw2 - yaw1)
    assert abs(residual_yaw) < 20, (
        f'still yawing in steady state: {residual_yaw:+.1f} deg over the window')
