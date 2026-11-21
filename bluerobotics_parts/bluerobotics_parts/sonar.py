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
The sonar parts, driven by gz-maritime's gz_sonar, for both vehicles.

Each sonar part publishes on topics below the part's own, and
kai_sonar_bridge brings each to ROS 2 stamped with a frame of the part's:
an `_acoustic` frame for an image (Z along the beam, X up, as
marine_acoustic_msgs/ProjectedSonarImage expects), the beam frame itself
for a profiler's soundings. The Gazebo side, the sensors each part emits,
is bluerobotics_parts/urdf/gz_sonar.xacro.
"""

from bluerobotics_parts.topics import absolute, overrides_for, under

# Sonar part type -> [(topic below the part's, kai_sonar_bridge kind, frame
# below the instance's)], one per sensor the part carries.
SONAR_PARTS = {
    'sonoptix_echo_multibeam': [('image', 'image', 'acoustic')],
    'omniscan_450_sidescan': [('port/image', 'image', 'port_acoustic'),
                              ('stbd/image', 'image', 'stbd_acoustic')],
    'surveyor_multibeam': [('detections', 'detections', 'beam')],
}


def sonar_entries(cfg, instances, default_ns):
    """
    Return the kai_sonar_bridge parameters for a vehicle's sonars.

    One (gz topic, ROS topic, frame, kind) per sonar sensor, in the lists
    the node takes; the frame is the one TF carries for that sensor's data.
    """
    ns = cfg.get('topic_namespace', default_ns)
    gz_topics, ros_topics, frame_ids, kinds = [], [], [], []
    for ptype, name in instances:
        for suffix, kind, frame in SONAR_PARTS.get(ptype, []):
            part = overrides_for(cfg, name)
            gz_base = under(ns, part.get('gz_topic', part.get('topic', name)))
            ros_base = under(ns, part.get('ros_topic', part.get('topic', name)))
            gz_topics.append(absolute(f'{gz_base}/{suffix}'))
            ros_topics.append(absolute(f'{ros_base}/{suffix}'))
            frame_ids.append(f'{ns}/{name}_{frame}')
            kinds.append(kind)
    params = {'use_sim_time': True}
    # An empty list has no type ROS 2 can infer; with no sonar the node
    # keeps its empty defaults.
    if gz_topics:
        params.update(gz_topics=gz_topics, ros_topics=ros_topics,
                      frame_ids=frame_ids, kinds=kinds)
    return {'sonar_bridge': {'ros__parameters': params}}


def entry_problems(entry, what):
    """
    Return what is wrong with a config entry's `sonar:` settings, if anything.

    They belong only on a sonar part, and each is one key and a plain value,
    the way the model renders them as <gz:sonar> elements.
    """
    settings = entry.get('sonar')
    if settings is None:
        return []
    if entry.get('type') not in SONAR_PARTS:
        return [f'{what} has sonar: settings, but {entry.get("type")!r} is not a sonar '
                f'(sonars: {sorted(SONAR_PARTS)})']
    if not isinstance(settings, dict):
        return [f'{what}: sonar: must be a dict of key: value']
    return [f'{what}: sonar: {key!r} must be a plain value, not {type(v).__name__}'
            for key, v in settings.items() if isinstance(v, (dict, list))]
