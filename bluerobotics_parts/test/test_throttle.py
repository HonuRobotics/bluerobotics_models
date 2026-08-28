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
"""The normalized throttle mapping and its per loadout parameter file."""

from bluerobotics_parts import throttle
import pytest

MODEL = """
<sdf version="1.12">
  <model name="vehicle">
    <plugin filename="gz-sim-thruster-system" name="gz::sim::systems::Thruster">
      <joint_name>thruster_1_joint</joint_name>
      <topic>vehicle/thruster_1/thrust</topic>
      <max_thrust_cmd>50.0</max_thrust_cmd>
      <min_thrust_cmd>-40.0</min_thrust_cmd>
    </plugin>
    <plugin filename="gz-sim-other-system" name="other">
      <topic>vehicle/other</topic>
    </plugin>
    <plugin filename="gz-sim-thruster-system" name="gz::sim::systems::Thruster">
      <joint_name>thruster_2_joint</joint_name>
      <topic>/vehicle/thruster_2/thrust</topic>
      <max_thrust_cmd>9.9</max_thrust_cmd>
      <min_thrust_cmd>-9.9</min_thrust_cmd>
    </plugin>
  </model>
</sdf>
"""


def test_mapping_is_linear_and_asymmetric():
    """+1 is the forward limit, -1 the reverse limit, 0 stops."""
    assert throttle.thrust_from_throttle(0.0, 50.0, -40.0) == 0.0
    assert throttle.thrust_from_throttle(1.0, 50.0, -40.0) == 50.0
    assert throttle.thrust_from_throttle(-1.0, 50.0, -40.0) == -40.0
    assert throttle.thrust_from_throttle(0.5, 50.0, -40.0) == pytest.approx(25.0)
    assert throttle.thrust_from_throttle(-0.5, 50.0, -40.0) == pytest.approx(-20.0)


def test_out_of_range_commands_clamp():
    """Commands beyond -1..1 saturate at the declared limits."""
    assert throttle.thrust_from_throttle(3.0, 50.0, -40.0) == 50.0
    assert throttle.thrust_from_throttle(-3.0, 50.0, -40.0) == -40.0


def test_thrusters_come_from_the_model_plugins():
    """Only Thruster plugins are read; topics come out absolute."""
    thrusters = throttle.thrusters_from_model(MODEL)
    assert [t['topic'] for t in thrusters] == [
        '/vehicle/thruster_1/thrust', '/vehicle/thruster_2/thrust']
    assert thrusters[0]['max_thrust'] == 50.0
    assert thrusters[0]['min_thrust'] == -40.0


def test_node_params_shape():
    """The parameter file drives the relay node, one entry per thruster."""
    params = throttle.node_params(throttle.thrusters_from_model(MODEL))
    inner = params['throttle_to_thrust']['ros__parameters']
    assert inner['thrust_topics'] == [
        '/vehicle/thruster_1/thrust', '/vehicle/thruster_2/thrust']
    assert inner['max_thrust'] == [50.0, 9.9]
    assert inner['min_thrust'] == [-40.0, -9.9]
