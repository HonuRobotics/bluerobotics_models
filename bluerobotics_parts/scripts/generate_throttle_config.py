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
Generate the throttle_to_thrust parameter file from a generated model.sdf.

Reads every gz Thruster plugin (command topic, declared thrust limits) and
writes the ROS parameter file the throttle_to_thrust node consumes, so the
normalized -1..1 interface always matches the fitted loadout.

Usage: generate_throttle_config.py <model.sdf> <output_throttle.yaml>
"""

import pathlib
import sys

from bluerobotics_parts import throttle
import yaml


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    model_sdf, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    thrusters = throttle.thrusters_from_model(model_sdf.read_text())
    out.write_text(yaml.safe_dump(throttle.node_params(thrusters),
                                  default_flow_style=False, sort_keys=False))


if __name__ == '__main__':
    main()
