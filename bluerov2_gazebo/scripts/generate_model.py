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
Generate the composed model.sdf from the config and the assembled URDF.

The buoyancy declaration is solved against the ASSEMBLED mass (the parts'
masses, summed with their mount poses), which xacro cannot read from the
URDF itself; this wrapper computes total mass and center of mass with
bluerobotics_parts.assembly and passes them, plus the URDF uri to merge,
to model.sdf.xacro. Used by the build and by configure_vehicle.py.

Usage: generate_model.py <config.yaml> <vehicle.urdf> <model.sdf.xacro> <out.sdf> [urdf_uri]
"""

import subprocess
import sys
import xml.etree.ElementTree as ET

from bluerobotics_parts import assembly


def main():
    """Compute mass properties and expand the model xacro (see module doc)."""
    if len(sys.argv) not in (5, 6):
        sys.exit(__doc__)
    config, urdf, model_xacro, out = sys.argv[1:5]
    uri = sys.argv[5] if len(sys.argv) == 6 else 'model://bluerov2/bluerov2.urdf'
    total, com = assembly.mass_properties(ET.parse(urdf).getroot())
    run = subprocess.run(
        ['xacro', model_xacro, f'config_file:={config}', f'urdf_uri:={uri}',
         f'total_mass:={total}', f'com:={com[0]} {com[1]} {com[2]}'],
        capture_output=True, text=True)
    if run.returncode != 0:
        sys.exit(f'model generation failed ({run.returncode}):\n{run.stderr}')
    with open(out, 'w') as f:
        f.write(run.stdout)


if __name__ == '__main__':
    main()
