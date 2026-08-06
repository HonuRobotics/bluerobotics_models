#!/usr/bin/env bash
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
#
# Sources the ROS underlay and this repository's overlay, then execs the
# command. The overlay is sourced only if it exists: with the source tree
# bind-mounted (compose `dev` profile) the workspace may not be built yet.
set -e

source "/opt/ros/${ROS_DISTRO}/setup.bash"

# Both colcon install layouts are supported: the default isolated layout and
# --merge-install both produce ${WORKSPACE}/install/setup.bash.
if [ -f "${WORKSPACE:-/ws}/install/setup.bash" ]; then
  source "${WORKSPACE:-/ws}/install/setup.bash"
fi

exec "$@"
