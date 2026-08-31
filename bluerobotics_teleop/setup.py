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

from glob import glob

from setuptools import find_packages, setup

package_name = 'bluerobotics_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config/bluerov2',
         glob('config/bluerov2/*.yaml')),
        ('share/' + package_name + '/config/bluerov2_heavy',
         glob('config/bluerov2_heavy/*.yaml')),
        ('share/' + package_name + '/config/blueboat',
         glob('config/blueboat/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Carlos Aguero',
    maintainer_email='caguero@honurobotics.com',
    description='Gamepad teleoperation for the BlueROV2 and BlueBoat.',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'twist_to_thrust = '
            'bluerobotics_teleop.twist_to_thrust_node:main',
            'joy_calibrate = '
            'bluerobotics_teleop.joy_calibrate_node:main',
        ],
    },
)
