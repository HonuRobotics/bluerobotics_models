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
Regenerate the thruster numbering figures on the actuators page.

Renders each variant top down in Gazebo (built workspace sourced, a GPU
display, the camera slot emptied with `- {slot: camera, type: none}` so no
placeholder cylinder blocks the view) and overlays the thruster numbers at
the slot coordinates the chassis parts declare, then joins both crops into
one row (images/thrusters.png). The pixel calibration (u0, v0, scale) is measured
from the vertical propellers visible in the raw screenshot, whose world
positions are known; re-measure it after changing the camera pose, the
window size or the slot layout.

Usage:
  1. gz sim <top down world with the composed model at the origin,
     camera_pose "0 0 1.05 0 1.5708 0", white background>
  2. xwd -id <gazebo window> | convert xwd:- raw.png
  3. crop the 3D viewport, measure the calibration, run overlay() below.
"""

from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# Slot coordinates from bluerobotics_parts/urdf/bluerov2_*chassis.urdf.xacro.
STANDARD = {1: (0.14, -0.092), 2: (0.14, 0.092), 3: (-0.15, -0.092),
            4: (-0.15, 0.092), 5: (0.015, -0.109), 6: (0.015, 0.109)}
HEAVY = dict(STANDARD, **{5: (0.118, -0.215), 6: (0.118, 0.215),
                          7: (-0.118, -0.215), 8: (-0.118, 0.215)})


def overlay(view_png, out_png, thrusters, u0, v0, scale, crop):
    """Draw numbered markers at the slot positions and a forward arrow."""
    font = ImageFont.truetype(FONT, 34)
    font_s = ImageFont.truetype(FONT, 26)
    img = Image.open(view_png).convert('RGB')
    draw = ImageDraw.Draw(img, 'RGBA')
    for n, (x, y) in thrusters.items():
        u, v = u0 - y * scale, v0 - x * scale
        draw.ellipse([u - 27, v - 27, u + 27, v + 27],
                     fill=(255, 255, 255, 215), outline=(20, 20, 20, 255),
                     width=3)
        draw.text((u, v - 2), str(n), font=font, fill=(10, 10, 10),
                  anchor='mm')
    out = img.crop(crop)
    d = ImageDraw.Draw(out)
    h = out.size[1]
    d.line([44, h - 90, 44, 96], fill=(10, 10, 10), width=5)
    d.polygon([(31, 96), (57, 96), (44, 68)], fill=(10, 10, 10))
    d.text((62, 82), 'forward', font=font_s, fill=(10, 10, 10), anchor='lm')
    out.save(out_png)


if __name__ == '__main__':
    overlay('standard_view.png', 'thrusters_standard.png', STANDARD,
            u0=783, v0=834, scale=780, crop=(483, 530, 1083, 1120))
    overlay('heavy_view.png', 'thrusters_heavy.png', HEAVY,
            u0=780, v0=830, scale=803, crop=(440, 525, 1120, 1115))
