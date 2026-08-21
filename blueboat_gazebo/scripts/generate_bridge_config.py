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
Generate the ros_gz bridge config from the vehicle parts config.

Run at build time (see CMakeLists.txt): emits /clock, the two thruster command
topics (part of the drivetrain, always present) and one entry per topic of each
sensor part in the assembly. The parts come from the generated URDF's
<assembly_part> manifest (the resolved loadout, defaults included); topic
bases follow /<topic_namespace>/<part name>, overridable per part in the
vehicle config with `topic` (both sides), `gz_topic` (Gazebo side) and
`ros_topic` (ROS side). This is the single point that must agree with the
sensor <topic>s emitted by model.sdf.xacro; both derive from the same
resolution, so they cannot drift.

Usage: generate_bridge_config.py <vehicle_config.yaml> <vehicle.urdf> <output_bridge.yaml>
"""

import sys
import xml.etree.ElementTree as ET

import yaml

# type -> [(topic suffix, ROS type, gz type, direction)]
# Sensor parts (bluerobotics_parts types) and the topics each produces.
PART_TOPICS = {
    'ping_singlebeam': [
        ('range', 'sensor_msgs/msg/LaserScan', 'gz.msgs.LaserScan',
         'GZ_TO_ROS'),
    ],
}


def absolute(topic):
    """Return the topic with a leading slash."""
    return topic if topic.startswith('/') else '/' + topic


# The gz side topics bake the model instance name: worlds must spawn the
# model under this name (the playground does). Per instance parameterization
# is the multi vehicle PR.
MODEL_NAME = 'blueboat'


def instances_from_urdf(path):
    """(type, name) of every part instance recorded in the URDF manifest."""
    root = ET.parse(path).getroot()
    return [(e.get('type'), e.get('name')) for e in root.findall('assembly_part')]


def overrides_for(cfg, name):
    """
    Return the config entry that fitted instance `name`, or {}.

    Slot entries name their occupant after the slot by default.
    """
    for entry in cfg.get('parts') or []:
        if entry.get('name', entry.get('slot')) == name:
            return entry
    return {}


def bridge_entries(cfg, instances):
    """
    Build the bridge entries for a vehicle.

    `cfg` is the parsed vehicle config, `instances` the (type, name) part
    instances of the assembled vehicle.
    """
    ns = cfg.get('topic_namespace', 'blueboat')
    entries = [{
        'ros_topic_name': '/clock',
        'gz_topic_name': '/clock',
        'ros_type_name': 'rosgraph_msgs/msg/Clock',
        'gz_type_name': 'gz.msgs.Clock',
        'direction': 'GZ_TO_ROS',
    }]
    # Motor joint states from the JointStatePublisher plugin, for
    # robot_state_publisher / RViz prop animation.
    entries.append({
        'ros_topic_name': '/joint_states',
        'gz_topic_name': absolute(f'{ns}/joint_states'),
        'ros_type_name': 'sensor_msgs/msg/JointState',
        'gz_type_name': 'gz.msgs.Model',
        'direction': 'GZ_TO_ROS',
    })
    # Twin outboard thrusters: drivetrain, always present. Thrust in newtons.
    for side in ('port', 'stbd'):
        entries.append({
            'ros_topic_name': absolute(f'{ns}/thrusters/{side}/thrust'),
            'gz_topic_name':
                f'/model/{MODEL_NAME}/joint/motor_{side}_joint/cmd_thrust',
            'ros_type_name': 'std_msgs/msg/Float64',
            'gz_type_name': 'gz.msgs.Double',
            'direction': 'ROS_TO_GZ',
        })
    for ptype, name in instances:
        part = overrides_for(cfg, name)
        default_base = f'{ns}/{name}'
        gz_base = part.get('gz_topic', part.get('topic', default_base))
        ros_base = part.get('ros_topic', part.get('topic', default_base))
        for suffix, ros_type, gz_type, direction in PART_TOPICS.get(ptype, []):
            entry = {
                'ros_topic_name': absolute(f'{ros_base}/{suffix}'),
                'gz_topic_name': absolute(f'{gz_base}/{suffix}'),
                'ros_type_name': ros_type,
                'gz_type_name': gz_type,
                'direction': direction,
            }
            if direction == 'GZ_TO_ROS':
                # Defer the gz subscription until a ROS subscriber shows up.
                entry['lazy'] = True
            # Pass-through: native ros_gz_bridge keys from the part's
            # `bridge:` dict override the defaults above.
            entry.update(part.get('bridge') or {})
            entries.append(entry)
    # Verbatim extra entries (native ros_gz_bridge syntax).
    entries.extend(cfg.get('extra_bridge_topics') or [])
    return entries


def main():
    """Read the vehicle config and write the bridge yaml (see module doc)."""
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    with open(sys.argv[1]) as f:
        cfg = yaml.safe_load(f) or {}
    instances = instances_from_urdf(sys.argv[2])
    with open(sys.argv[3], 'w') as f:
        f.write('# GENERATED from the vehicle config '
                '(blueboat_description/config/blueboat.yaml) and the assembled\n'
                '# URDF by generate_bridge_config.py. Do not edit; edit the '
                'vehicle config and rebuild.\n')
        yaml.safe_dump(bridge_entries(cfg, instances), f, sort_keys=False)


if __name__ == '__main__':
    main()
