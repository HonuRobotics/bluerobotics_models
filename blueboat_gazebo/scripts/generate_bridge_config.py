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
configured sensor part. Topic bases follow /<topic_namespace>/<part name>,
overridable per part with `topic` (both sides), `gz_topic` (Gazebo side)
and `ros_topic` (ROS side). This is the single point that must agree with the
sensor <topic>s emitted by model.sdf.xacro; both read the same config, so they
cannot drift.

Usage: generate_bridge_config.py <vehicle_config.yaml> <output_bridge.yaml>
"""

import sys

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


def bridge_entries(cfg):
    """Build the list of bridge entries for a parsed vehicle config."""
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
    for part in cfg.get('parts') or []:
        default_base = f"{ns}/{part['name']}"
        gz_base = part.get('gz_topic', part.get('topic', default_base))
        ros_base = part.get('ros_topic', part.get('topic', default_base))
        for suffix, ros_type, gz_type, direction in \
                PART_TOPICS.get(part['type'], []):
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
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1]) as f:
        cfg = yaml.safe_load(f) or {}
    with open(sys.argv[2], 'w') as f:
        f.write('# GENERATED from the vehicle config '
                '(blueboat_description/config/blueboat.yaml)\n'
                '# by generate_bridge_config.py. Do not edit; edit the vehicle '
                'config and rebuild.\n')
        yaml.safe_dump(bridge_entries(cfg), f, sort_keys=False)


if __name__ == '__main__':
    main()
