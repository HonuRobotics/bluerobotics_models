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
Shared plumbing for the test modules.

The gz and ros2 suites launch a long-lived process, poll it until ready, and
audit its output; the mechanics live here once so a change to (say) the log
handling cannot drift between the two modules. The vehicle config the
generator tests build on, and the check for what the shipped config fits,
live here for the same reason.
"""

import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import pytest
import yaml

DESC_SHARE = Path(get_package_share_directory('bluerov2_description'))


def kit_config(parts=()):
    """
    Return the tests' own vehicle config, as a dict.

    The shipped hull, namespace and buoyancy, every slot filling with its
    default (six props, their bodies and the camera), plus parts. Independent
    of what the shipped config fits, so the tests follow the generators' rules
    rather than the current product.
    """
    cfg = yaml.safe_load((DESC_SHARE / 'config' / 'bluerov2.yaml').read_text())
    cfg['slot_defaults'] = True
    cfg['parts'] = [dict(p) for p in parts]
    return cfg


def kit_config_text(parts=()):
    """Return kit_config(parts) as YAML text, for the generators that read text."""
    return yaml.safe_dump(kit_config(parts), sort_keys=False)


def shipped_has_camera():
    """Whether the installed (shipped config) URDF has a link named camera."""
    root = ET.parse(DESC_SHARE / 'urdf' / 'bluerov2.urdf').getroot()
    return any(link.get('name') == 'camera' for link in root.iter('link'))


def make_cli(binary, default_timeout=10):
    """Return a runner for `binary` yielding (returncode, stdout, stderr)."""
    def run(env, *args, timeout=default_timeout):
        try:
            out = subprocess.run([binary, *args], env=env, capture_output=True,
                                 text=True, timeout=timeout)
            return out.returncode, out.stdout, out.stderr
        except subprocess.TimeoutExpired:
            return -1, '', f'{binary} {args[0]}: timed out after {timeout}s'
    return run


def poll_until(condition, timeout, message, interval=2):
    """Poll `condition()` until true; fail with `message` after `timeout` s."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return
        time.sleep(interval)
    pytest.fail(message() if callable(message) else message)


def stop_process_group(proc, sig=signal.SIGTERM, grace=10):
    """
    Signal the whole process group and reap it; SIGKILL stragglers.

    gz sim and ros2 launch both spawn children, so signalling only the leader
    can orphan servers that keep running (and keep ports/partitions) after the
    test ends.
    """
    try:
        os.killpg(proc.pid, sig)
        proc.wait(timeout=grace)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)


def launch_sim(request, label, cmd, env, ready, stop=stop_process_group):
    """
    Start `cmd` in its own process group, wait until `ready(env)`, return env.

    Output goes to a tempfile whose tail prints unconditionally at teardown
    (warnings matter even when every assertion passes, and exit codes
    underreport partial failures) and on startup failure. `stop(proc)` must
    take down the whole process tree.
    """
    if shutil.which(cmd[0]) is None:
        pytest.fail(f'{cmd[0]} CLI not available: the suite cannot run')
    log = tempfile.NamedTemporaryFile('w+', suffix='.log', delete=False,
                                      prefix=label.replace(' ', '_') + '_')
    proc = subprocess.Popen(cmd, env=env, start_new_session=True,
                            stdout=log, stderr=subprocess.STDOUT)

    def fail(message):
        log.flush()
        tail = ''.join(open(log.name).readlines()[-40:])
        pytest.fail(f'{message}\nlast {label} output ({log.name}):\n{tail}')

    def teardown():
        stop(proc)
        log.flush()
        tail = ''.join(open(log.name).readlines()[-60:])
        print(f'\n--- {label} output tail ({log.name}) ---\n{tail}')

    request.addfinalizer(teardown)
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            fail(f'{label} exited during startup')
        if ready(env):
            return env
        time.sleep(2)
    fail(f'{label} never became ready')


# Tables a test fills in as it runs, printed together at the very end of the
# session: title -> rows, the first row the header. Printed from the terminal
# summary so they follow the FAILURES section rather than being buried above
# it, and appear with or without -s.
REPORT_TABLES = {}


def pytest_terminal_summary(terminalreporter):
    """Print each report table as aligned columns at the end of the run."""
    for title, rows in REPORT_TABLES.items():
        if len(rows) < 2:
            continue
        widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
        lines = ['  '.join(c.ljust(w) for c, w in zip(r, widths)).rstrip()
                 for r in rows]
        lines.insert(1, '  '.join('-' * w for w in widths))
        terminalreporter.write_sep('=', title)
        for line in lines:
            terminalreporter.write_line(line)
