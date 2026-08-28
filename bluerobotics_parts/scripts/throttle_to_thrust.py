#!/usr/bin/env python3
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
Map normalized -1..1 throttle commands onto per thruster thrust topics.

For every thruster in the parameters (generated per loadout by
generate_throttle_config.py), a `<thruster>/throttle` Float64 subscription
is relayed to the `<thruster>/thrust` topic with the -1..1 command mapped
linearly onto the part's declared thrust limits. Stateless: one message in,
one message out; the gz Thruster plugin latches the last command, exactly
as it does for direct thrust commands.
"""

from bluerobotics_parts.throttle import NODE_NAME, thrust_from_throttle
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Float64

THRUST_SUFFIX = '/thrust'


class ThrottleToThrust(Node):
    """The relay node; the thruster set comes from parameters."""

    def __init__(self):
        super().__init__(NODE_NAME)
        self.declare_parameter('thrust_topics', [''])
        self.declare_parameter('max_thrust', [0.0])
        self.declare_parameter('min_thrust', [0.0])
        topics = [t for t in self.get_parameter('thrust_topics').value if t]
        maxes = self.get_parameter('max_thrust').value
        mins = self.get_parameter('min_thrust').value
        if not (len(topics) == len(maxes) == len(mins)):
            raise SystemExit('thrust_topics, max_thrust and min_thrust '
                             'must have one entry per thruster')
        self.subs = []
        for topic, max_thrust, min_thrust in zip(topics, maxes, mins):
            if not topic.endswith(THRUST_SUFFIX):
                raise SystemExit(f'thrust topic {topic} does not end in '
                                 f'{THRUST_SUFFIX}')
            base = topic[:-len(THRUST_SUFFIX)]
            # Latched, mirroring the gz Thruster plugin: a late subscriber
            # (the bridge joining, an introspecting tool) sees the command
            # the thruster is holding.
            pub = self.create_publisher(Float64, topic, QoSProfile(
                depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
            self.subs.append(self.create_subscription(
                Float64, base + '/throttle',
                lambda msg, pub=pub, hi=max_thrust, lo=min_thrust:
                    pub.publish(Float64(
                        data=thrust_from_throttle(msg.data, hi, lo))),
                10))
        self.get_logger().info(
            f'relaying {len(topics)} throttle topics onto thrust')


def main():
    rclpy.init()
    try:
        rclpy.spin(ThrottleToThrust())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
