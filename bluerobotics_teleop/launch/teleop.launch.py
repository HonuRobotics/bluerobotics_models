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
(default bluerov2); the argument picks the mixer. The gamepad mapping is
shared by every vehicle: the user mapping under $ROS_HOME when joy_map
has written one, else the shipped defaults (config/pad). Run next to a
running simulation (sim.launch.xml) or a bridged real vehicle.
"""

from bluerobotics_teleop.pad_paths import resolve_pad_file
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([
        FindPackageShare('bluerobotics_teleop'), 'config',
        LaunchConfiguration('vehicle')])
    # The gamepad mapping is user state: joy_map writes it under $ROS_HOME
    # and the launch prefers it, falling back to the shipped defaults.
    joystick_yaml = resolve_pad_file('joystick.config.yaml')
    input_yaml = resolve_pad_file('twist_to_thrust.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'vehicle', default_value='bluerov2',
            choices=['bluerov2', 'bluerov2_heavy', 'blueboat'],
            description='Which vehicle mixer to load.'),
        LogInfo(msg=f'Pad mapping: {joystick_yaml}'),
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_id': 0,
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
                joystick_yaml,
                {'use_sim_time': True},
            ],
        ),
        Node(
            package='bluerobotics_teleop',
            executable='twist_to_thrust',
            name='twist_to_thrust',
            parameters=[
                PathJoinSubstitution([config, 'mixer.yaml']),
                input_yaml,
                {'use_sim_time': True},
            ],
        ),
    ])
