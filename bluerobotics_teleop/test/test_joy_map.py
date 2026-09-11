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
"""The walkthrough tells a stick push from a D pad hat landing."""

from bluerobotics_teleop.joy_map_node import (
    COMMON_STEPS, hat_suspect, MappingResult)
from sensor_msgs.msg import Joy

FORWARD = COMMON_STEPS[1]   # a stick step
DEADMAN = COMMON_STEPS[0]   # a button step


def joy(n_axes):
    msg = Joy()
    msg.axes = [0.0] * n_axes
    return msg


def test_stick_on_the_left_stick_is_fine():
    assert not hat_suspect(joy(8), MappingResult('axis', 1, 1.0), FORWARD)


def test_stick_on_the_hat_is_the_d_pad():
    """F310 in X mode with the Mode LED lit: the left stick reads on 6, 7."""
    assert hat_suspect(joy(8), MappingResult('axis', 7, 1.0), FORWARD)
    assert hat_suspect(joy(8), MappingResult('axis', 6, 1.0), FORWARD)


def test_pads_without_a_hat_are_not_second_guessed():
    assert not hat_suspect(joy(4), MappingResult('axis', 3, 1.0), FORWARD)


def test_button_steps_are_not_checked():
    assert not hat_suspect(joy(8), MappingResult('axis', 7, 1.0), DEADMAN)
