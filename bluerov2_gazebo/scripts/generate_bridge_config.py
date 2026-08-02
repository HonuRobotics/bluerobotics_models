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
Generate the ros_gz bridge config from the vehicle accessory config.

Run at build time (see CMakeLists.txt): reads bluerov2.yaml and emits one bridge
entry per topic of each configured accessory, plus /clock. Topic bases follow
/<topic_namespace>/<accessory name>, overridable per accessory with `topic`
(both sides), `gz_topic` (Gazebo side) and `ros_topic` (ROS side). This is the
single point that must agree with the sensor <topic>s emitted by
model.sdf.xacro; both read the same config, so they cannot drift.

Usage: generate_bridge_config.py <vehicle_config.yaml> <output_bridge.yaml>
"""

import sys

import yaml

# type -> [(topic suffix ('' = the base itself), ROS type, gz type, direction)]
ACCESSORY_TOPICS = {
    'explorehd_camera': [
        ('image', 'sensor_msgs/msg/Image', 'gz.msgs.Image', 'GZ_TO_ROS'),
        ('camera_info', 'sensor_msgs/msg/CameraInfo', 'gz.msgs.CameraInfo',
         'GZ_TO_ROS'),
    ],
    'marinesitu_c3': [
        ('image', 'sensor_msgs/msg/Image', 'gz.msgs.Image', 'GZ_TO_ROS'),
        ('depth_image', 'sensor_msgs/msg/Image', 'gz.msgs.Image', 'GZ_TO_ROS'),
        ('points', 'sensor_msgs/msg/PointCloud2', 'gz.msgs.PointCloudPacked',
         'GZ_TO_ROS'),
        ('camera_info', 'sensor_msgs/msg/CameraInfo', 'gz.msgs.CameraInfo',
         'GZ_TO_ROS'),
    ],
    'ping360': [
        ('scan', 'sensor_msgs/msg/LaserScan', 'gz.msgs.LaserScan', 'GZ_TO_ROS'),
    ],
    'dvl_a50': [
        ('velocity', 'marine_acoustic_msgs/msg/Dvl',
         'gz.msgs.DVLVelocityTracking', 'GZ_TO_ROS'),
    ],
    'newton_gripper': [
        ('cmd_pos', 'std_msgs/msg/Float64', 'gz.msgs.Double', 'ROS_TO_GZ'),
    ],
    'sediment_sampler': [
        ('cmd_pos', 'std_msgs/msg/Float64', 'gz.msgs.Double', 'ROS_TO_GZ'),
    ],
}


def absolute(topic):
    """Return the topic with a leading slash."""
    return topic if topic.startswith('/') else '/' + topic


def bridge_entries(cfg):
    """Build the list of bridge entries for a parsed vehicle config."""
    ns = cfg.get('topic_namespace', 'bluerov2')
    entries = [{
        'ros_topic_name': '/clock',
        'gz_topic_name': '/clock',
        'ros_type_name': 'rosgraph_msgs/msg/Clock',
        'gz_type_name': 'gz.msgs.Clock',
        'direction': 'GZ_TO_ROS',
    }]
    for acc in cfg.get('accessories') or []:
        default_base = f"{ns}/{acc['name']}"
        gz_base = acc.get('gz_topic', acc.get('topic', default_base))
        ros_base = acc.get('ros_topic', acc.get('topic', default_base))
        for suffix, ros_type, gz_type, direction in \
                ACCESSORY_TOPICS.get(acc['type'], []):
            entry = {
                'ros_topic_name': absolute(f'{ros_base}/{suffix}'),
                'gz_topic_name': absolute(f'{gz_base}/{suffix}'),
                'ros_type_name': ros_type,
                'gz_type_name': gz_type,
                'direction': direction,
            }
            if direction == 'GZ_TO_ROS':
                # Defer the gz subscription until a ROS subscriber shows up, so
                # unwatched sensors (e.g. camera streams) cost nothing to bridge.
                entry['lazy'] = True
            # Pass-through: native ros_gz_bridge keys (lazy, subscriber_queue,
            # publisher_queue, ...) from the accessory's `bridge:` dict override
            # the defaults above.
            entry.update(acc.get('bridge') or {})
            entries.append(entry)
    # Verbatim extra entries (native ros_gz_bridge syntax) for anything outside
    # the accessory system, e.g. thruster commands or odometry.
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
                '(bluerov2_description/config/bluerov2.yaml)\n'
                '# by generate_bridge_config.py. Do not edit; edit the vehicle '
                'config and rebuild.\n')
        yaml.safe_dump(bridge_entries(cfg), f, sort_keys=False)


if __name__ == '__main__':
    main()
