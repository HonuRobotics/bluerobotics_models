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
Start kai_sonar_bridge for one vehicle's sonars, or nothing when it has none.

Both vehicles' sim launches include this with the sonar_bridge.yaml their
bridge generator wrote (bluerobotics_parts.sonar.write_bridge_params). With
use_composition the bridge joins the vehicle's container; without, it is a
process of its own, so a vehicle with no sonar would otherwise run one that
does nothing.
"""

from bluerobotics_parts.sonar import params_have_sonars
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode


def _bridge(context):
    params = LaunchConfiguration('params_file').perform(context)
    if not params_have_sonars(params):
        return []
    composed = LaunchConfiguration('use_composition').perform(context).lower()
    if composed in ('true', '1'):
        return [LoadComposableNodes(
            target_container=LaunchConfiguration('container_name').perform(context),
            composable_node_descriptions=[ComposableNode(
                package='kai_sonar_bridge', plugin='kai_sonar_bridge::SonarBridge',
                name='sonar_bridge', parameters=[params])])]
    return [Node(package='kai_sonar_bridge', executable='sonar_bridge',
                 name='sonar_bridge', parameters=[params])]


def generate_launch_description():
    """Declare the arguments and start the bridge only for a vehicle with sonars."""
    return LaunchDescription([
        DeclareLaunchArgument('params_file',
                              description="The vehicle's generated sonar_bridge.yaml."),
        DeclareLaunchArgument('use_composition', default_value='true',
                              description='Load into the container rather than run a process.'),
        DeclareLaunchArgument('container_name', default_value='ros_gz_container',
                              description='The container to load into when composing.'),
        OpaqueFunction(function=_bridge),
    ])
