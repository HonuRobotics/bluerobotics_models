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
Drive one body axis through the teleop mixer, without a gamepad.

    ros2 run bluerobotics_teleop axis_command x 0.5
    ros2 run bluerobotics_teleop axis_command yaw -0.5 --timeout 10
    ros2 run bluerobotics_teleop axis_command z 0.5 --timeout -1

Sends each thruster what the twist_to_thrust mixer would send for an effort
on a single axis (REP 103: x forward, y port, z up, yaw counter-clockwise),
at full stick and a 100% ceiling. Publishes over Gazebo transport, so it
works against a bare `gz sim` with no ROS bridge. Republishes for
--timeout seconds (default 1; -1 holds until Ctrl+C), then sends zeros so
the vehicle stops. Ctrl+C or a kill (SIGINT or SIGTERM) ends the hold
early the same way. Both are ignored while the zeros go out: `ros2 run`
forwards a second SIGINT, which would otherwise cut the stop short and
leave some thrusters running.
"""

import argparse
import os
import signal
import time

from ament_index_python.packages import get_package_share_directory
from bluerobotics_teleop.instance import default_name, DEFAULT_NAMES, node_params, under
from bluerobotics_teleop.twist_to_thrust_node import mix
from gz.msgs.double_pb2 import Double
from gz.transport import Node

AXES = ('x', 'y', 'z', 'yaw')  # the mixer's Twist order
RATE_HZ = 10.0
STOP_SEC = 0.5
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class _Stop(Exception):
    pass


def _raise_stop(signum, frame):
    raise _Stop()


def thruster_commands(params, axis, effort):
    """Return [(topic, command)] for an effort on one axis."""
    twist = [0.0] * len(AXES)
    twist[AXES.index(axis)] = effort
    gains = list(zip(*(params[f'gains_{k}'] for k in
                       ('linear_x', 'linear_y', 'linear_z', 'angular_z'))))
    values = mix(gains, twist, 1.0, params['max_thrust_reverse'],
                 params['max_thrust_forward'])
    return list(zip(params['thruster_topics'], values))


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Drive one body axis through the teleop mixer.')
    parser.add_argument('axis', choices=AXES)
    parser.add_argument('effort', type=float, help='normalized, in [-1, 1]')
    parser.add_argument('--vehicle', default='bluerov2', choices=sorted(DEFAULT_NAMES),
                        help='which mixer config to use (default: bluerov2)')
    parser.add_argument('--name', default='',
                        help="instance to drive (default: the vehicle's own name)")
    parser.add_argument('-t', '--timeout', type=float, default=1.0,
                        help='seconds to hold the command; -1 holds until Ctrl+C '
                             '(default: 1)')
    opts = parser.parse_args(args)
    if not -1.0 <= opts.effort <= 1.0:
        parser.error('effort must be in [-1, 1]')
    if opts.timeout <= 0 and opts.timeout != -1:
        parser.error('timeout must be positive, or -1 to hold until Ctrl+C')

    name = opts.name or default_name(opts.vehicle)
    config = os.path.join(get_package_share_directory('bluerobotics_teleop'),
                          'config', opts.vehicle, 'mixer.yaml')
    commands = [(under(name, topic), value) for topic, value in
                thruster_commands(node_params(config, 'twist_to_thrust'),
                                  opts.axis, opts.effort)]

    node = Node()
    publishers = [(node.advertise(topic, Double), value) for topic, value in commands]
    print(f'{opts.axis} {opts.effort:+g} on /{name}:')
    for topic, value in commands:
        print(f'  {topic}  {value:+.3f}')
    print('Holding until Ctrl+C.' if opts.timeout == -1
          else f'Holding {opts.timeout:g} s (Ctrl+C stops early).')

    def send(zero=False):
        for pub, value in publishers:
            msg = Double()
            msg.data = 0.0 if zero else float(value)
            pub.publish(msg)

    # Set explicitly rather than relying on Python's default, which a process
    # started with SIGINT ignored (a background job, a launcher) inherits off.
    for sig in STOP_SIGNALS:
        signal.signal(sig, _raise_stop)
    end = None if opts.timeout == -1 else time.monotonic() + opts.timeout
    try:
        while end is None or time.monotonic() < end:
            send()
            time.sleep(1.0 / RATE_HZ)
    except _Stop:
        pass
    finally:
        for sig in STOP_SIGNALS:
            signal.signal(sig, signal.SIG_IGN)
        stop = time.monotonic() + STOP_SEC
        while time.monotonic() < stop:
            send(zero=True)
            time.sleep(1.0 / RATE_HZ)
        print('Stopped: all thrusters at 0.')


if __name__ == '__main__':
    main()
