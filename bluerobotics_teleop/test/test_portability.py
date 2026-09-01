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
"""The joy_node helper spawn adapts to each platform."""

import sys

from bluerobotics_teleop import joy_map_node
import pytest


def test_linux_ties_the_helper_with_the_parent_death_signal(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    kwargs = joy_map_node.spawn_kwargs()
    assert kwargs['start_new_session'] is True
    assert callable(kwargs['preexec_fn'])
    assert not joy_map_node.joy_node_command()[0].endswith('.exe')


def test_macos_has_no_parent_death_signal(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'darwin')
    kwargs = joy_map_node.spawn_kwargs()
    assert kwargs == {'start_new_session': True}


def test_windows_uses_a_process_group_and_the_exe_suffix(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    kwargs = joy_map_node.spawn_kwargs()
    assert 'preexec_fn' not in kwargs and 'start_new_session' not in kwargs
    assert kwargs['creationflags']
    assert joy_map_node.joy_node_command()[0].endswith('.exe')


def test_missing_curses_fails_with_the_install_hint(monkeypatch):
    monkeypatch.setattr(joy_map_node, 'curses', None)
    with pytest.raises(SystemExit, match='windows-curses'):
        joy_map_node.main([])
