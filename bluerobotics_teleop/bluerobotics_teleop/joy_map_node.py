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
Interactive gamepad mapping for the teleop pipeline.

A curses walkthrough: capture a no touch baseline, then prompt for each
control (deadman, motion axes, EPA clicks), detecting buttons vs axes
against the baseline noise and refusing double assignments. Saving writes
the two input side configs the teleop launch reads, shared by every
vehicle (a vehicle without a motion zeroes it in its mixer gains):

    $ROS_HOME/bluerobotics_teleop/pad/joystick.config.yaml
    $ROS_HOME/bluerobotics_teleop/pad/twist_to_thrust.yaml

The mapping is user state: it lives under $ROS_HOME (default ~/.ros),
survives rebuilds and needs no permissions from a binary install. The
launch prefers it over the defaults shipped in the package share; to
make a mapping the new shipped default, copy the files into the repo's
bluerobotics_teleop/config/pad/ and commit.

The per vehicle mixer config (thruster topics and gains) is model truth,
not user preference, and is never touched here. Run with the joystick
plugged in:

    ros2 run bluerobotics_teleop joy_map

If nothing is publishing /joy, a joy_node is started for the duration of
the walkthrough and stopped on exit, however it ends. A
leftover background joy_node is exactly the thing that used to break the
next teleop session (two publishers interleaving on /joy, one of them
autorepeating stale state), so the tool owns its helper's lifetime.
Running the walkthrough next to a live teleop session still works: its
joy_node is detected and no second one is started.
"""

import argparse
import ctypes
try:
    import curses
except ImportError:  # Windows ships no curses; the windows-curses wheel does.
    curses = None
from dataclasses import dataclass, field
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Optional

from ament_index_python.packages import get_package_prefix
from bluerobotics_teleop import pad_paths
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import yaml


@dataclass
class MappingResult:
    input_type: str   # 'button' or 'axis'
    index: int
    direction: float = 0.0  # +1.0 or -1.0 for axes


@dataclass
class MappingStep:
    name: str
    prompt: str
    hint: str
    prefer_button: bool = True
    result: Optional[MappingResult] = None


@dataclass
class Baseline:
    axes: list = field(default_factory=list)
    buttons: list = field(default_factory=list)
    noise: list = field(default_factory=list)


class JoyMapNode(Node):
    """Buffers the latest /joy message for the curses loop."""

    def __init__(self) -> None:
        super().__init__('joy_map')
        self.create_subscription(Joy, 'joy', self._joy_cb, 10)
        self._lock = threading.Lock()
        self._latest: Optional[Joy] = None

    def _joy_cb(self, msg: Joy) -> None:
        with self._lock:
            self._latest = msg

    def get_latest(self) -> Optional[Joy]:
        with self._lock:
            return self._latest

    def clear_latest(self) -> None:
        with self._lock:
            self._latest = None


COMMON_STEPS = [
    MappingStep(
        'Deadman', 'Press the button for DEADMAN SWITCH',
        'Must be held for any output  [recommended: RB]'),
    MappingStep(
        'Forward', 'Push the axis for FORWARD (surge)',
        'Drives the vehicle along its nose  [recommended: Left stick up]',
        prefer_button=False),
    MappingStep(
        'Yaw', 'Push the axis for YAW LEFT (turn)',
        'Turns the vehicle in place  [recommended: Left stick left]',
        prefer_button=False),
]

PLANE_STEPS = [
    MappingStep(
        'Sway', 'Push the axis for SWAY LEFT (strafe)',
        'Translates sideways  [recommended: Right stick left]',
        prefer_button=False),
    MappingStep(
        'Heave', 'Push the axis for HEAVE UP (ascend)',
        'Climbs the water column  [recommended: Right stick up]',
        prefer_button=False),
]

EPA_STEPS = [
    MappingStep(
        'EPA+', 'Press the input for THRUST EPA UP',
        'Raise the thrust ceiling by 10%  [recommended: D pad up]'),
    MappingStep(
        'EPA-', 'Press the input for THRUST EPA DOWN',
        'Lower the thrust ceiling by 10%  [recommended: D pad down]'),
]


def all_steps():
    """Return the full mapping walk: every function any vehicle uses."""
    return list(COMMON_STEPS) + PLANE_STEPS + EPA_STEPS


def capture_baseline(stdscr, node, steps, n_samples=20, timeout_sec=5.0):
    stdscr.clear()
    draw_header(stdscr, 'Baseline', 0, len(steps))
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(3, 2, 'Before starting, verify your controller:', w - 4)
    stdscr.addnstr(4, 4, '- Back switch set to X or D (keep consistent)',
                   w - 6)
    stdscr.addnstr(5, 4, '- Mode LED off (normal stick/D pad behavior)',
                   w - 6)
    stdscr.addnstr(7, 2, 'Press ENTER when ready, or Q to quit.', w - 4)
    stdscr.nodelay(True)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == ord('\n'):
            break
        elif key == ord('q'):
            return None
        curses.napms(33)

    stdscr.addnstr(7, 2, 'DO NOT TOUCH ANY CONTROLS.' + ' ' * 20,
                   w - 4, curses.A_BOLD)
    stdscr.addnstr(8, 2, 'Capturing baseline...', w - 4)
    stdscr.refresh()

    samples_axes = []
    samples_buttons = []
    waited = 0.0

    while len(samples_axes) < n_samples:
        msg = node.get_latest()
        if msg is not None:
            samples_axes.append(list(msg.axes))
            samples_buttons.append(list(msg.buttons))
            status = f'Samples: {len(samples_axes)}/{n_samples}'
            stdscr.addnstr(10, 2, status + ' ' * 20, w - 4)
            draw_telemetry(stdscr, msg)
            stdscr.refresh()
            node.clear_latest()  # wait for a fresh message

        key = stdscr.getch()
        if key == ord('q'):
            return None

        curses.napms(50)
        waited += 0.05
        if waited > timeout_sec and not samples_axes:
            stdscr.addnstr(12, 2, 'No /joy messages! Is joy_node running?',
                           w - 4, curses.A_BOLD)
            stdscr.refresh()
            curses.napms(3000)
            return None

    n_axes = len(samples_axes[0])
    baseline = Baseline()
    baseline.axes = [
        sum(s[i] for s in samples_axes) / len(samples_axes)
        for i in range(n_axes)]
    baseline.noise = [
        max(abs(s[i] - baseline.axes[i]) for s in samples_axes)
        for i in range(n_axes)]
    baseline.buttons = list(samples_buttons[-1])
    return baseline


def detect_input(msg, baseline, step):
    """Classify the touched control as a button press or an axis push."""
    btn_hits = []
    for i, val in enumerate(msg.buttons):
        if i < len(baseline.buttons) and val == 1 and baseline.buttons[i] == 0:
            btn_hits.append(i)

    axis_hits = []
    for i, val in enumerate(msg.axes):
        if i < len(baseline.axes):
            thresh = max(0.5, 3.0 * baseline.noise[i], 0.15)
            delta = val - baseline.axes[i]
            if abs(delta) > thresh:
                axis_hits.append((i, 1.0 if delta > 0 else -1.0))

    if step.prefer_button:
        if len(btn_hits) == 1:
            return MappingResult('button', btn_hits[0])
        if len(axis_hits) == 1 and not btn_hits:
            idx, d = axis_hits[0]
            return MappingResult('axis', idx, d)
    else:
        if len(axis_hits) == 1:
            idx, d = axis_hits[0]
            return MappingResult('axis', idx, d)
        if len(btn_hits) == 1 and not axis_hits:
            return MappingResult('button', btn_hits[0])

    return None


def conflicts_with(steps, result, step_idx):
    """Name of an earlier step already using this input, if any."""
    for i in range(step_idx):
        prev = steps[i].result
        if prev is None:
            continue
        if prev.input_type != result.input_type:
            continue
        if prev.index != result.index:
            continue
        if prev.input_type == 'axis' and prev.direction != result.direction:
            continue
        return steps[i].name
    return None


def map_step(stdscr, node, baseline, steps, step_idx):
    step = steps[step_idx]
    stdscr.clear()
    draw_header(stdscr, step.name, step_idx + 1, len(steps))
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(3, 2, f'>> {step.prompt}', w - 4, curses.A_BOLD)
    stdscr.addnstr(4, 5, step.hint, w - 7)
    stdscr.addnstr(6, 2, 'Waiting for input...', w - 4)
    draw_keybar(stdscr)
    stdscr.nodelay(True)
    stdscr.refresh()

    result = None
    confirmed = False

    while not confirmed:
        msg = node.get_latest()
        if msg is not None:
            draw_telemetry(stdscr, msg)
            if result is None:
                result = detect_input(msg, baseline, step)
                if result is not None:
                    conflict = conflicts_with(steps, result, step_idx)
                    if conflict:
                        stdscr.addnstr(
                            6, 2,
                            f'Conflict: {format_result(result)} already'
                            f' used by {conflict}' + ' ' * 10,
                            w - 4, curses.A_BOLD)
                        stdscr.addnstr(
                            7, 2,
                            'Try a different input, or Q to quit'
                            + ' ' * 10, w - 4)
                        stdscr.refresh()
                        result = None
                    else:
                        desc = format_result(result)
                        stdscr.addnstr(
                            6, 2, f'Detected: {desc}' + ' ' * 20,
                            w - 4, curses.A_BOLD)
                        stdscr.addnstr(
                            7, 2, 'ENTER to confirm, R to redo', w - 4)
                        stdscr.refresh()

        key = stdscr.getch()
        if key == ord('\n') and result is not None:
            confirmed = True
        elif key == ord('r'):
            result = None
            stdscr.addnstr(6, 2, 'Waiting for input...' + ' ' * 30, w - 4)
            stdscr.addnstr(7, 2, ' ' * 40, w - 4)
            stdscr.refresh()
        elif key == ord('q'):
            return None

        curses.napms(33)

    step.result = result
    return result


def show_summary(stdscr, steps, output_dir):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(0, 2, 'MAPPING COMPLETE', w - 4, curses.A_BOLD)
    stdscr.addnstr(1, 2, '=' * min(40, w - 4), w - 4)

    for i, step in enumerate(steps):
        desc = format_result(step.result) if step.result else 'SKIPPED'
        stdscr.addnstr(3 + i, 2, f'{step.name:12s}  {desc}', w - 4)

    y = 3 + len(steps) + 1
    stdscr.addnstr(y, 2, f'Output: {output_dir}/', w - 4)
    stdscr.addnstr(y + 1, 4, 'joystick.config.yaml  (teleop_twist_joy)',
                   w - 6)
    stdscr.addnstr(y + 2, 4, 'twist_to_thrust.yaml  (twist_to_thrust)',
                   w - 6)
    stdscr.addnstr(y + 4, 2, '[S] Save   [Q] Quit without saving', w - 4)
    stdscr.nodelay(True)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == ord('s'):
            return True
        elif key == ord('q'):
            return False
        curses.napms(33)


def save_configs(steps, output_dir):
    """Write the two input side configs from the confirmed steps."""
    os.makedirs(output_dir, exist_ok=True)
    results = {s.name: s.result for s in steps}
    fwd = results['Forward']
    yaw = results['Yaw']
    sway = results.get('Sway')
    heave = results.get('Heave')
    deadman = results['Deadman']
    epa_up = results['EPA+']

    axis_linear = {'x': fwd.index if fwd else 1}
    scale_linear = {'x': fwd.direction if fwd else 1.0}
    if sway:
        axis_linear['y'] = sway.index
        scale_linear['y'] = sway.direction
    if heave:
        axis_linear['z'] = heave.index
        scale_linear['z'] = heave.direction

    ttj = {
        'teleop_twist_joy_node': {'ros__parameters': {
            'axis_linear': axis_linear,
            'scale_linear': scale_linear,
            'axis_angular': {'yaw': yaw.index if yaw else 0},
            'scale_angular': {'yaw': yaw.direction if yaw else 1.0},
            'enable_button': deadman.index if deadman else 5,
            'enable_turbo_button': -1,
        }}
    }
    path_ttj = os.path.join(output_dir, 'joystick.config.yaml')
    with open(path_ttj, 'w') as f:
        yaml.dump(ttj, f, default_flow_style=False, sort_keys=False)

    ttt = {
        'twist_to_thrust': {'ros__parameters': {
            'cmd_timeout_sec': 0.5,
            'btn_deadman': deadman.index if deadman else 5,
            'axis_epa':
                epa_up.index if epa_up and epa_up.input_type == 'axis'
                else 7,
            'epa_initial': 0.2,
            'epa_step': 0.1,
        }}
    }
    path_ttt = os.path.join(output_dir, 'twist_to_thrust.yaml')
    with open(path_ttt, 'w') as f:
        yaml.dump(ttt, f, default_flow_style=False, sort_keys=False)

    return path_ttj, path_ttt


def format_result(result):
    if result.input_type == 'button':
        return f'Button {result.index}'
    sign = '+' if result.direction > 0 else '-'
    return f'Axis {result.index} ({sign})'


def draw_header(stdscr, name, step_num, total):
    h, w = stdscr.getmaxyx()
    title = 'JOYSTICK MAPPING'
    step_str = f'Step {step_num}/{total}' if step_num > 0 else 'Baseline'
    pad = max(1, w - len(title) - len(step_str) - 4)
    stdscr.addnstr(0, 2, title + ' ' * pad + step_str, w - 4, curses.A_BOLD)
    stdscr.addnstr(1, 2, '=' * min(60, w - 4), w - 4)


def draw_telemetry(stdscr, msg):
    h, w = stdscr.getmaxyx()
    y = max(10, h - 4)
    axes_str = ' '.join(f'{v:+.1f}' for v in msg.axes)
    btns_str = ' '.join(str(b) for b in msg.buttons)
    stdscr.addnstr(y, 2, f'Axes: [{axes_str}]' + ' ' * 10, w - 4)
    stdscr.addnstr(y + 1, 2, f'Btns: [{btns_str}]' + ' ' * 10, w - 4)
    stdscr.refresh()


def draw_keybar(stdscr):
    h, w = stdscr.getmaxyx()
    stdscr.addnstr(h - 1, 2, '[Q] Quit  [R] Redo', w - 4)


def run_curses(stdscr, node, steps, output_dir):
    curses.curs_set(0)
    baseline = capture_baseline(stdscr, node, steps)
    if baseline is None:
        return
    for i in range(len(steps)):
        if map_step(stdscr, node, baseline, steps, i) is None:
            return
    if show_summary(stdscr, steps, output_dir):
        paths = save_configs(steps, output_dir)
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addnstr(1, 2, 'Saved!', w - 4, curses.A_BOLD)
        stdscr.addnstr(3, 2, f'  {paths[0]}', w - 4)
        stdscr.addnstr(4, 2, f'  {paths[1]}', w - 4)
        stdscr.addnstr(6, 2, 'Relaunch teleop to use the new config.', w - 4)
        stdscr.addnstr(8, 2, 'Press any key to exit.', w - 4)
        stdscr.nodelay(False)
        stdscr.refresh()
        stdscr.getch()


def joy_node_command():
    """Return the joy_node command line for this platform."""
    exe = os.path.join(get_package_prefix('joy'), 'lib', 'joy', 'joy_node')
    if sys.platform == 'win32':
        exe += '.exe'
    return [exe, '--ros-args', '-p', 'autorepeat_rate:=20.0']


def spawn_kwargs():
    """
    Return the Popen keywords tying the helper's lifetime to ours.

    On Linux the kernel delivers SIGTERM to the helper when this process
    dies, however it dies (PR_SET_PDEATHSIG). macOS has no parent death
    signal and Windows supports neither process sessions nor pre exec
    hooks, so there the explicit cleanup on exit is the only reaper.
    """
    if sys.platform.startswith('linux'):
        def _die_with_parent():
            libc = ctypes.CDLL('libc.so.6', use_errno=True)
            libc.prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
        return {'start_new_session': True, 'preexec_fn': _die_with_parent}
    if sys.platform == 'win32':
        new_group = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200)
        return {'creationflags': new_group}
    return {'start_new_session': True}  # macOS and other POSIX


def main(args=None):
    if curses is None:
        sys.exit('joy_map needs the curses module; on Windows install the '
                 'windows-curses package (python -m pip install '
                 'windows-curses)')
    parser = argparse.ArgumentParser(
        description='Map a gamepad to the teleop functions')
    _, ros_args = parser.parse_known_args(
        args if args is not None else sys.argv[1:])

    rclpy.init(args=ros_args)
    node = JoyMapNode()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    # Self-contained input: if nobody is publishing /joy (no teleop session
    # up), run our own joy_node for the walkthrough and stop it on exit.
    # autorepeat is required: without it joy_node stays silent while no
    # control moves and the baseline capture times out. The executable is
    # spawned directly (no ros2 run wrapper, which does not forward
    # signals reliably), tied to this process as tightly as the platform
    # allows (see spawn_kwargs).
    joy_proc = None
    time.sleep(0.5)  # let discovery settle before counting publishers
    if node.count_publishers('joy') == 0:
        joy_proc = subprocess.Popen(
            joy_node_command(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **spawn_kwargs())

    def _spin():
        try:
            executor.spin()
        except rclpy.executors.ExternalShutdownException:
            pass

    spin_thread = threading.Thread(target=_spin, daemon=True)
    spin_thread.start()

    steps = all_steps()
    output_dir = str(pad_paths.user_pad_dir())
    try:
        curses.wrapper(
            lambda stdscr: run_curses(stdscr, node, steps, output_dir))
    except KeyboardInterrupt:
        pass
    finally:
        if joy_proc is not None:
            try:
                joy_proc.terminate()
                joy_proc.wait(timeout=3.0)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                joy_proc.kill()
        executor.shutdown()
        spin_thread.join(timeout=2.0)
        node.destroy_node()
        rclpy.try_shutdown()
    print(f'Pad mapping directory: {output_dir}')


if __name__ == '__main__':
    main()
