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
"""configure_vehicle.py: every loadout artifact from one config, at any time."""

from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import (get_package_prefix,
                                         get_package_share_directory)
import yaml

GZ_SHARE = Path(get_package_share_directory('blueboat_gazebo'))
DESC_SHARE = Path(get_package_share_directory('blueboat_description'))
TOOL = (Path(get_package_prefix('blueboat_gazebo')) / 'lib' / 'blueboat_gazebo'
        / 'configure_vehicle.py')
DEFAULT_CONFIG = DESC_SHARE / 'config' / 'blueboat.yaml'


def configure(config_path, out_dir):
    """Run the tool; fail the test with its stderr."""
    out = subprocess.run([str(TOOL), '--config', str(config_path), '--out-dir', str(out_dir)],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, f'configure_vehicle failed:\n{out.stderr}'
    return Path(out_dir)


def links(urdf_path):
    return {li.get('name') for li in ET.parse(urdf_path).getroot().findall('link')}


def test_default_config_reproduces_the_installed_artifacts(tmp_path):
    """Run on the shipped config, the tool regenerates what the build installed."""
    out = configure(DEFAULT_CONFIG, tmp_path / 'v')
    for name in ('blueboat.urdf', 'blueboat.gazebo.urdf', 'model.sdf', 'model.config',
                 'ros_gz_bridge.yaml'):
        assert (out / name).is_file(), f'{name} not generated'
    assert links(out / 'blueboat.urdf') == links(DESC_SHARE / 'urdf' / 'blueboat.urdf')
    assert yaml.safe_load((out / 'ros_gz_bridge.yaml').read_text()) == \
        yaml.safe_load((GZ_SHARE / 'config' / 'ros_gz_bridge.yaml').read_text())
    generated = ET.parse(out / 'model.sdf').getroot()
    installed = ET.parse(GZ_SHARE / 'models' / 'blueboat' / 'model.sdf').getroot()
    assert [s.get('name') for s in generated.iter('sensor')] == \
        [s.get('name') for s in installed.iter('sensor')]
    assert len(list(generated.iter('plugin'))) == len(list(installed.iter('plugin')))
    # The generated model merges the generated Gazebo flavoured URDF.
    uri = next(generated.iter('include')).find('uri').text
    assert uri == f'file://{out / "blueboat.gazebo.urdf"}'
    # Same parts in both flavours; only the glTF visual orientation differs.
    assert links(out / 'blueboat.gazebo.urdf') == links(out / 'blueboat.urdf')
    gz_root = ET.parse(out / 'blueboat.gazebo.urdf').getroot()
    ros_root = ET.parse(out / 'blueboat.urdf').getroot()
    gz_rpys = {v.find('origin').get('rpy') for v in gz_root.iter('visual')
               if v.find('geometry/mesh') is not None}
    ros_rpys = {v.find('origin').get('rpy') for v in ros_root.iter('visual')
                if v.find('geometry/mesh') is not None}
    assert ros_rpys == {'0 0 0'} and gz_rpys == {'1.5708 0 0'}


def test_custom_loadout_flows_to_every_artifact(tmp_path):
    """A different loadout changes URDF, model and bridge consistently."""
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())
    cfg['parts'] = [{'slot': 'ping_mount', 'type': 'none'},
                    {'slot': 'mast', 'type': 'blueboat_antenna_mast'}]
    config = tmp_path / 'custom.yaml'
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    out = configure(config, tmp_path / 'v')
    urdf_links = links(out / 'blueboat.urdf')
    assert 'mast' in urdf_links and 'ping' not in urdf_links
    assert not list(ET.parse(out / 'model.sdf').getroot().iter('sensor'))
    bridge = yaml.safe_load((out / 'ros_gz_bridge.yaml').read_text())
    topics = {e['ros_topic_name'] for e in bridge}
    assert '/blueboat/ping/range' not in topics
    assert '/blueboat/thrusters/port/thrust' in topics


def test_temp_mode_prints_only_the_directory():
    """--temp creates a fresh directory and prints its path, nothing else."""
    out = subprocess.run([str(TOOL), '--config', str(DEFAULT_CONFIG), '--temp'],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr
    path = Path(out.stdout)
    assert path.is_dir() and (path / 'model.sdf').is_file()
    assert out.stdout == str(path), 'stdout must be the bare path (launch uses it)'
    subprocess.run(['rm', '-rf', str(path)], check=False)
    assert tempfile.gettempdir() in str(path)
