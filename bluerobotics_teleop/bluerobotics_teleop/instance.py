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
The instance a teleop stack binds to.

One name per vehicle instance: it is the Gazebo model name, the topic
prefix, the ROS namespace and the TF prefix. The teleop launch runs its
nodes in the /<name> namespace, so the mixer's relative thruster topics
resolve to that instance and nothing else, and two stacks, one per name,
drive two vehicles side by side.
"""

import yaml

# The name a vehicle's own sim launch spawns it under, used when the teleop
# launch is not given one. The heavy ROV is a loadout of the BlueROV2.
DEFAULT_NAMES = {
    'blueboat': 'blueboat',
    'bluerov2': 'bluerov2',
    'bluerov2_heavy': 'bluerov2',
}


def default_name(vehicle):
    """Return the instance name the teleop launch binds to by default."""
    return DEFAULT_NAMES[vehicle]


def under(name, topic):
    """Return `topic`, relative to an instance, as the absolute ROS topic."""
    return f'/{name}/{topic.lstrip("/")}'


def node_params(path, node):
    """
    Return the `ros__parameters` of `node` in the parameter file at `path`.

    The shipped configs and the mappings joy_map writes are keyed on the
    bare node name (`twist_to_thrust:`), which a parameter file applies
    only to a node in the root namespace. Handing the values to the node as
    a dictionary instead applies them under any instance namespace, so the
    files keep their format and old mappings keep working.
    """
    with open(path) as f:
        return yaml.safe_load(f)[node]['ros__parameters']
