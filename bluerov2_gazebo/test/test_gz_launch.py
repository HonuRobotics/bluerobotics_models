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

Everything here is a hard requirement, including the camera render test:
a missing gz CLI or render path fails the suite rather than skipping it, so
a broken environment cannot report green. CI runners render headless via EGL.
The behavior tests measure in SIM time (world stats), so a slow runner with a
low real time factor changes only how long they wait, never what they assert.
"""

import contextlib
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

from ament_index_python.packages import get_package_share_directory
from conftest import launch_sim, make_cli, poll_until
import pytest

WORLD = (Path(get_package_share_directory('bluerov2_gazebo'))
         / 'worlds' / 'bluerov2_playground.sdf')
WORLD_NAME = 'bluerov2_playground'

_NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
POSE_TRIPLE = re.compile(rf'({_NUM}) ({_NUM}) ({_NUM})')

gz = make_cli('gz')


def model_pose(env):
    """Vehicle world pose from `gz model -p`: (x, y, z, roll, pitch, yaw)."""
    code, out, err = gz(env, 'model', '-m', 'bluerov2', '-p', timeout=15)
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
    # \b so 'sec:' cannot match inside 'nsec:' when sec is omitted (== 0).
    sec = re.search(r'\bsec:\s*(\d+)', block.group(1))
    nsec = re.search(r'nsec:\s*(\d+)', block.group(1))
    return (int(sec.group(1)) if sec else 0) + \
        (int(nsec.group(1)) if nsec else 0) / 1e9


def wait_sim_seconds(env, seconds, timeout=120):
    """Block until the sim clock advances `seconds`, whatever the RTF."""
    start = sim_seconds(env)

    def advanced():
        now = sim_seconds(env)
        assert now > start - 1.0, (
            f'sim clock went backward ({start:.3f} -> {now:.3f} s): '
            'server restart or corrupt stats read')
        return now - start >= seconds

    poll_until(advanced, timeout,
               f'sim advanced less than {seconds}s in {timeout}s of wall time',
               interval=0.5)


def teleport(env, x, y, z):
    """Move the vehicle to a pose with identity orientation."""
    req = (f'name: "bluerov2", position: {{x: {x}, y: {y}, z: {z}}}, '
           'orientation: {w: 1}')
    code, out, err = gz(env, 'service', '-s', f'/world/{WORLD_NAME}/set_pose',
                        '--reqtype', 'gz.msgs.Pose',
                        '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '5000', '--req', req, timeout=15)
    assert code == 0 and 'true' in out, f'set_pose failed:\n{out}\n{err}'


def latch_thrusters(env, mapping, period=0.3):
    """
    Hold thrust commands (N) by republishing them until released.

    `gz topic -p` publishes once per invocation, and a single shot can lose
    the transport discovery race under load: a total loss parks the vehicle
    and a partial latch applies an unbalanced wrench that drives it
    diagonally. Republishing in a loop for the whole command window makes
    delivery a matter of time instead of luck. Stop with release_thrusters,
    which latches zero behind the commands.
    """
    procs = []
    for n, value in mapping.items():
        topic = f'/bluerov2/thruster_{n}/thrust'
        loop = (f'while true; do gz topic -t {topic} -m gz.msgs.Double '
                f'-p "data: {value}"; sleep {period}; done')
        procs.append(subprocess.Popen(
            ['bash', '-c', loop], env=env, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    return procs


def _stop_publishers(procs):
    for proc in procs:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
    for proc in procs:
        proc.wait(timeout=10)


def release_thrusters(env, procs, numbers):
    """Stop the publishers and latch zero so the next test starts clean."""
    _stop_publishers(procs)
    zeros = latch_thrusters(env, dict.fromkeys(numbers, 0.0))
    time.sleep(4.0)  # several republish rounds so the zeros land
    _stop_publishers(zeros)


@pytest.fixture(scope='module')
def sim(request):
    """Start a headless gz server on an isolated partition; yield its env."""
    env = dict(os.environ, GZ_PARTITION=f'test_{uuid.uuid4().hex[:8]}')
    # -v 3 so warnings and messages (not just errors) reach the audited log.
    return launch_sim(
        request, 'gz sim',
        ['gz', 'sim', '-s', '-r', '-v', '3', str(WORLD)], env,
        ready=lambda e: 'bluerov2' in gz(e, 'model', '--list')[1])


def test_model_loaded(sim):
    """The composed model is in the world."""
    _, out, _ = gz(sim, 'model', '--list')
    assert 'bluerov2' in out


def test_interfaces_advertised(sim):
    """Thruster commands and sensor topics are advertised."""
    needed = ('/bluerov2/thruster_1/thrust',
              '/bluerov2/thruster_6/thrust',
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


def test_camera_renders(sim):
    """The default loadout's camera streams frames at its configured size."""
    code, out, err = gz(sim, 'topic', '-e', '-t', '/bluerov2/camera/image',
                        '-n', '1', timeout=30)
    assert code == 0 and 'data' in out, (
        f'no camera image: broken sensor config or no usable render path\n{err}')
    assert 'width: 1920' in out


def test_vehicle_slightly_positively_buoyant(sim):
    """Submerged, the near-neutral trim rises slowly: the sizing holds in sim."""
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)           # let the relocation transient damp out
    t0, z0 = sim_seconds(sim), model_pose(sim)[2]
    wait_sim_seconds(sim, 8)
    t1, z1 = sim_seconds(sim), model_pose(sim)[2]
    rate = (z1 - z0) / (t1 - t0)
    assert 0.001 < rate < 0.10, (
        f'rise rate {rate:.4f} m/s outside the near-neutral band '
        f'(z {z0:.3f} -> {z1:.3f} over {t1 - t0:.1f} sim s)')


def test_vertical_thrusters_heave(sim):
    """
    The vertical pair heaves: commanded up, the climb dwarfs the passive rise.

    Positive commands push down (both vertical axes point -z), so up is
    negative. The heavy variant's extra pair (7, 8) is not in the playground's
    standard model and is exercised by the same macro at generation time.
    """
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)
    t0, z0 = sim_seconds(sim), model_pose(sim)[2]
    procs = latch_thrusters(sim, {5: -20.0, 6: -20.0})
    try:
        wait_sim_seconds(sim, 6)
        t1, z1 = sim_seconds(sim), model_pose(sim)[2]
    finally:
        release_thrusters(sim, procs, (5, 6))
    rate = (z1 - z0) / (t1 - t0)
    assert rate > 0.10, (
        f'no heave authority: climbed {rate:.3f} m/s '
        f'(z {z0:.2f} -> {z1:.2f} over {t1 - t0:.1f} sim s)')


def test_forward_thrust_mix_surges(sim):
    """
    The vectored surge mix drives the vehicle along its nose, without crab.

    Command onset can rotate the heading (see latch_thrusters), so the
    assertion is on the steady state, which is what the model owns: velocity
    aligned with the body x axis and no residual yaw, wherever the nose ended
    up pointing.
    """
    teleport(sim, 0, 0, -3.0)
    wait_sim_seconds(sim, 3)
    # 5 N per thruster: the run must FIT IN THE POOL (walls at +/-12.55 m).
    # At 10 N the steady ~1 m/s over both windows reaches the wall and
    # the vehicle slides along it, reading as crab.
    procs = latch_thrusters(sim, {1: -5.0, 2: -5.0, 3: 5.0, 4: 5.0})
    try:
        wait_sim_seconds(sim, 6)      # onset transient: spin damps, speed builds
        t1 = sim_seconds(sim)
        x1, y1, _, _, _, yaw1 = model_pose(sim)
        wait_sim_seconds(sim, 6)
        t2 = sim_seconds(sim)
        x2, y2, _, _, _, yaw2 = model_pose(sim)
    finally:
        release_thrusters(sim, procs, (1, 2, 3, 4))
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
