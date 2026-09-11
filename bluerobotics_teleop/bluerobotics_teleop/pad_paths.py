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
Where the gamepad mapping lives.

The mapping is user state, not package data: joy_map writes it under
`$ROS_HOME` (default `~/.ros`), where it survives rebuilds and needs no
permissions from a binary install, following the same pattern as the
vehicles' `configure_vehicle.py --cache`. The files shipped in the
package share (`config/pad/`) are the defaults; the teleop launch loads
the user mapping when it exists and falls back to the shipped one.
"""

import os
import pathlib

from ament_index_python.packages import get_package_share_directory

PAD_FILES = ('joystick.config.yaml', 'twist_to_thrust.yaml')


def user_pad_dir():
    """Return the per user mapping directory under $ROS_HOME."""
    ros_home = pathlib.Path(
        os.environ.get('ROS_HOME', pathlib.Path.home() / '.ros'))
    return ros_home / 'bluerobotics_teleop' / 'pad'


def shipped_pad_dir():
    """Return the package's shipped default mapping directory."""
    return pathlib.Path(
        get_package_share_directory('bluerobotics_teleop')) / 'config' / 'pad'


def resolve_pad_file(name):
    """Return the path the launch should load: user mapping, else shipped."""
    user = user_pad_dir() / name
    return str(user) if user.is_file() else str(shipped_pad_dir() / name)
