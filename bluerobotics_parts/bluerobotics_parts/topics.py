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

"""Topic names for a vehicle's parts: the rules both vehicles' bridge generators share."""


def absolute(topic):
    """Return the topic with a leading slash."""
    return topic if topic.startswith('/') else '/' + topic


def under(ns, base):
    """Return `base` under namespace `ns`, or as given when it starts with a slash."""
    return base if base.startswith('/') else f'{ns}/{base}'


def overrides_for(cfg, name):
    """
    Return the config entry that fitted instance `name`, or {}.

    Slot entries name their occupant after the slot by default.
    """
    for entry in cfg.get('parts') or []:
        if entry.get('name', entry.get('slot')) == name:
            return entry
    return {}
