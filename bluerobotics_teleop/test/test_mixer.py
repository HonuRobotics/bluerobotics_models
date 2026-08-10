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
"""Unit tests for the pure mixing and EPA math."""

from bluerobotics_teleop.twist_to_thrust_node import mix, step_epa
import pytest

# The blueboat differential matrix, as (lx, ly, lz, az) per thruster.
BOAT = [(1.0, 0.0, 0.0, -1.0),   # port
        (1.0, 0.0, 0.0, 1.0)]    # stbd


def test_pure_surge_is_symmetric():
    assert mix(BOAT, (1.0, 0.0, 0.0, 0.0), 10.0, -40.0, 50.0) == [10.0, 10.0]


def test_yaw_left_is_differential():
    port, stbd = mix(BOAT, (0.0, 0.0, 0.0, 1.0), 10.0, -40.0, 50.0)
    assert port == -10.0 and stbd == 10.0


def test_combined_maneuver_clamps_to_envelope():
    port, stbd = mix(BOAT, (1.0, 0.0, 0.0, 1.0), 45.0, -40.0, 50.0)
    assert port == 0.0        # 45 - 45
    assert stbd == 50.0       # 45 + 45 = 90, clamped to the T200 forward max


def test_reverse_clamp_uses_the_asymmetric_envelope():
    port, stbd = mix(BOAT, (-1.0, 0.0, 0.0, 0.0), 50.0, -40.0, 50.0)
    assert port == -40.0 and stbd == -40.0


def test_zero_twist_is_zero_thrust():
    assert mix(BOAT, (0.0, 0.0, 0.0, 0.0), 50.0, -40.0, 50.0) == [0.0, 0.0]


def test_epa_steps_and_saturates():
    pct = 0.2
    pct = step_epa(pct, 1.0, 0.1)
    assert pct == pytest.approx(0.3)
    for _ in range(20):
        pct = step_epa(pct, 1.0, 0.1)
    assert pct == 1.0
    for _ in range(20):
        pct = step_epa(pct, -1.0, 0.1)
    assert pct == pytest.approx(0.1)   # never reaches zero: EPA is a ceiling
    assert step_epa(pct, 0.0, 0.1) == pct
