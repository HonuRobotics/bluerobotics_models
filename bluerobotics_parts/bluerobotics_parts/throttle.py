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
Normalized throttle commands for thrusters.

Real thrusters are commanded with a normalized signal (ArduPilot scales
every motor output to the -1..1 range; the ESC maps it onto its PWM band),
not with newtons: thrust depends on battery voltage and propeller state, so
no driver can honor a force setpoint. Simulation keeps the same portable
interface by mapping -1..1 on each thruster's `throttle` topic linearly
onto the thrust limits its part declares, publishing the result on the
thruster's `thrust` topic (the gz Thruster plugin's native input, which
stays available as the low level interface).

The mapping is read from the generated model.sdf: every gz Thruster plugin
carries its command topic and the part's declared limits, so the throttle
map always matches the fitted loadout with nothing repeated.
"""

import xml.etree.ElementTree as ET

THRUSTER_PLUGIN = 'gz-sim-thruster-system'
NODE_NAME = 'throttle_to_thrust'


def thrust_from_throttle(throttle, max_thrust, min_thrust):
    """Map a -1..1 command onto asymmetric limits; out of range clamps."""
    cmd = max(-1.0, min(1.0, float(throttle)))
    return cmd * max_thrust if cmd >= 0.0 else -cmd * min_thrust


def thrusters_from_model(model_sdf_text):
    """Every Thruster plugin's absolute thrust topic and declared limits."""
    root = ET.fromstring(model_sdf_text)
    thrusters = []
    for plugin in root.iter('plugin'):
        if plugin.get('filename') != THRUSTER_PLUGIN:
            continue
        topic = plugin.findtext('topic').strip()
        thrusters.append({
            'topic': topic if topic.startswith('/') else '/' + topic,
            'max_thrust': float(plugin.findtext('max_thrust_cmd')),
            'min_thrust': float(plugin.findtext('min_thrust_cmd')),
        })
    return thrusters


def node_params(thrusters):
    """ROS parameter file content for the throttle_to_thrust node."""
    return {NODE_NAME: {'ros__parameters': {
        'thrust_topics': [t['topic'] for t in thrusters],
        'max_thrust': [t['max_thrust'] for t in thrusters],
        'min_thrust': [t['min_thrust'] for t in thrusters],
    }}}
