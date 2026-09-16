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
Gamepad teleop bring up: joy_node -> teleop_twist_joy -> twist_to_thrust.

Select the vehicle with vehicle:=bluerov2|bluerov2_heavy|blueboat
(default bluerov2); the argument picks the mixer. The stack binds to one
vehicle instance, name:= (default: the vehicle's own name), and runs under
/<name>, so its topics and the mixer's thruster commands land on that
instance alone; a second stack under another name drives a second vehicle.
The gamepad mapping is shared by every vehicle: the user mapping under
$ROS_HOME when joy_map has written one, else the shipped defaults
(config/pad). Run next to a running simulation (sim.launch.xml, or
gz-maritime's spawn launch) or a bridged real vehicle.
"""

import os

from ament_index_python.packages import get_package_share_directory
from bluerobotics_teleop.instance import default_name, node_params
from bluerobotics_teleop.pad_paths import resolve_pad_file
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def teleop_stack(context):
    """Return the three nodes, in the namespace of the instance they drive."""
    vehicle = LaunchConfiguration('vehicle').perform(context)
    name = LaunchConfiguration('name').perform(context) or default_name(vehicle)
    device_id = int(LaunchConfiguration('device_id').perform(context))
    mixer_yaml = os.path.join(get_package_share_directory('bluerobotics_teleop'),
                              'config', vehicle, 'mixer.yaml')
    # The gamepad mapping is user state: joy_map writes it under $ROS_HOME
    # and the launch prefers it, falling back to the shipped defaults. The
    # files are keyed on the bare node names, so their values are passed as
    # dictionaries, which apply under the instance namespace.
    joystick_yaml = resolve_pad_file('joystick.config.yaml')
    input_yaml = resolve_pad_file('twist_to_thrust.yaml')
    return [
        LogInfo(msg=f'Teleop for {vehicle} bound to /{name}, pad {device_id}, '
                    f'mapping {joystick_yaml}'),
        GroupAction([
            # Everything under /<name>: joy, cmd_vel, the nodes, and the
            # mixer's relative thruster topics, which land on this instance.
            PushRosNamespace(name),
            Node(
                package='joy',
                executable='joy_node',
                name='joy_node',
                parameters=[{
                    'device_id': device_id,
                    'deadzone': 0.1,
                    'autorepeat_rate': 20.0,
                    'use_sim_time': True,
                }],
            ),
            Node(
                package='teleop_twist_joy',
                executable='teleop_node',
                name='teleop_twist_joy_node',
                parameters=[
                    node_params(joystick_yaml, 'teleop_twist_joy_node'),
                    {'use_sim_time': True},
                ],
            ),
            Node(
                package='bluerobotics_teleop',
                executable='twist_to_thrust',
                name='twist_to_thrust',
                parameters=[
                    node_params(mixer_yaml, 'twist_to_thrust'),
                    node_params(input_yaml, 'twist_to_thrust'),
                    {'use_sim_time': True},
                ],
            ),
        ]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'vehicle', default_value='bluerov2',
            choices=['bluerov2', 'bluerov2_heavy', 'blueboat'],
            description='Which vehicle mixer to load.'),
        DeclareLaunchArgument(
            'name', default_value='',
            description='Instance to drive: the name it was spawned under. '
                        'Empty picks the vehicle default (blueboat, bluerov2).'),
        DeclareLaunchArgument(
            'device_id', default_value='0',
            description='Gamepad index for joy_node; a second stack takes '
                        'a second pad.'),
        OpaqueFunction(function=teleop_stack),
    ])
