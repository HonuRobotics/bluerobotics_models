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


def mapped(steps, results):
    for step, result in zip(steps, results):
        step.result = result
    return steps


def saved_input_side(tmp_path, results):
    from bluerobotics_teleop.joy_map_node import all_steps, save_configs
    import yaml
    _, path = save_configs(mapped(all_steps(), results), str(tmp_path))
    with open(path) as f:
        return yaml.safe_load(f)['twist_to_thrust']['ros__parameters']


STICKS = [MappingResult('button', 5), MappingResult('axis', 4, 1.0),
          MappingResult('axis', 0, 1.0), MappingResult('axis', 3, 1.0),
          MappingResult('axis', 1, 1.0)]


def test_a_hat_d_pad_is_saved_as_the_epa_axis(tmp_path):
    """F310: up and down are one axis, so the buttons stay unused."""
    params = saved_input_side(tmp_path, STICKS + [
        MappingResult('axis', 7, 1.0), MappingResult('axis', 7, -1.0)])
    assert params['axis_epa'] == 7
    assert params['btn_epa_up'] == -1 and params['btn_epa_down'] == -1


def test_a_button_d_pad_is_saved_as_the_epa_buttons(tmp_path):
    params = saved_input_side(tmp_path, STICKS + [
        MappingResult('button', 11), MappingResult('button', 12)])
    assert params['axis_epa'] == -1
    assert params['btn_epa_up'] == 11 and params['btn_epa_down'] == 12
