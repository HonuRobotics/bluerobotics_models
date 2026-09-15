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
"""configure_vehicle.py: every config artifact from one config, at any time."""

import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import (get_package_prefix,
                                         get_package_share_directory)
import yaml

GZ_SHARE = Path(get_package_share_directory('bluerov2_gazebo'))
DESC_SHARE = Path(get_package_share_directory('bluerov2_description'))
TOOL = (Path(get_package_prefix('bluerov2_gazebo')) / 'lib' / 'bluerov2_gazebo'
        / 'configure_vehicle.py')
DEFAULT_CONFIG = DESC_SHARE / 'config' / 'bluerov2.yaml'


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
    for name in ('bluerov2.urdf', 'bluerov2.gazebo.urdf', 'model.sdf', 'model.config',
                 'ros_gz_bridge.yaml', 'robot_description.yaml'):
        assert (out / name).is_file(), f'{name} not generated'
    assert links(out / 'bluerov2.urdf') == links(DESC_SHARE / 'urdf' / 'bluerov2.urdf')
    assert yaml.safe_load((out / 'ros_gz_bridge.yaml').read_text()) == \
        yaml.safe_load((GZ_SHARE / 'config' / 'ros_gz_bridge.yaml').read_text())
    generated = ET.parse(out / 'model.sdf').getroot()
    installed = ET.parse(GZ_SHARE / 'models' / 'bluerov2' / 'model.sdf').getroot()
    assert [s.get('name') for s in generated.iter('sensor')] == \
        [s.get('name') for s in installed.iter('sensor')]
    assert len(list(generated.iter('plugin'))) == len(list(installed.iter('plugin')))
    # The generated model merges the generated Gazebo flavoured URDF.
    uri = next(generated.iter('include')).find('uri').text
    assert uri == f'file://{out / "bluerov2.gazebo.urdf"}'
    # Same parts in both flavours; only the glTF visual orientation differs.
    assert links(out / 'bluerov2.gazebo.urdf') == links(out / 'bluerov2.urdf')
    gz_root = ET.parse(out / 'bluerov2.gazebo.urdf').getroot()
    ros_root = ET.parse(out / 'bluerov2.urdf').getroot()
    gz_rpys = {v.find('origin').get('rpy') for v in gz_root.iter('visual')
               if v.find('geometry/mesh') is not None}
    ros_rpys = {v.find('origin').get('rpy') for v in ros_root.iter('visual')
                if v.find('geometry/mesh') is not None}
    assert ros_rpys == {'0 0 0'} and gz_rpys == {'1.5708 0 0'}


def test_custom_config_flows_to_every_artifact(tmp_path):
    """A different config changes URDF, model and bridge consistently."""
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())
    cfg['parts'] = [{'slot': 'camera', 'type': 'none'},
                    {'slot': 'dvl', 'type': 'dvl_a50'}]
    config = tmp_path / 'custom.yaml'
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    out = configure(config, tmp_path / 'v')
    urdf_links = links(out / 'bluerov2.urdf')
    assert 'dvl' in urdf_links and 'camera' not in urdf_links
    model = ET.parse(out / 'model.sdf').getroot()
    sensors = {sensor.get('name') for sensor in model.iter('sensor')}
    assert sensors == {'dvl'}
    # The DVL backend rides along exactly when a DVL is fitted.
    assert [p for p in model.iter('plugin')
            if p.get('filename') == 'gz-sim-dvl-system']
    bridge = yaml.safe_load((out / 'ros_gz_bridge.yaml').read_text())
    topics = {e['ros_topic_name'] for e in bridge}
    assert '/bluerov2/camera/image' not in topics
    assert '/bluerov2/dvl/velocity' in topics
    assert '/bluerov2/thruster_1/thrust' in topics


def test_drivetrain_follows_the_config(tmp_path):
    """An emptied thruster slot drops its Thruster plugin and bridge topic."""
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())
    cfg['parts'] = [{'slot': 'thruster_5', 'type': 'none'}]
    config = tmp_path / 'custom.yaml'
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    out = configure(config, tmp_path / 'v')
    model = ET.parse(out / 'model.sdf').getroot()
    thrusters = [p for p in model.iter('plugin') if p.get('name').endswith('Thruster')]
    joints = {t.find('joint_name').text for t in thrusters}
    assert len(joints) == 5 and 'thruster_5_joint' not in joints
    topics = {e['ros_topic_name'] for e in
              yaml.safe_load((out / 'ros_gz_bridge.yaml').read_text())}
    assert '/bluerov2/thruster_5/thrust' not in topics
    assert '/bluerov2/thruster_6/thrust' in topics


def test_heavy_variant_flows_to_the_model(tmp_path):
    """The heavy base yields eight thrusters and the wider footprint works."""
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())
    cfg['base'] = {'type': 'bluerov2_heavy_chassis', 'name': 'base_link'}
    cfg['buoyancy']['footprint'] = '0.457 0.575'
    config = tmp_path / 'custom.yaml'
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    out = configure(config, tmp_path / 'v')
    model = ET.parse(out / 'model.sdf').getroot()
    thrusters = [p for p in model.iter('plugin') if p.get('name').endswith('Thruster')]
    assert len(thrusters) == 8
    box = model.find('.//link[@name="buoyancy_displacement"]//box/size')
    assert box.text.startswith('0.457 0.575')


def test_mismatched_config_fails_with_the_reason(tmp_path):
    """A slot entry that matches nothing fails the tool (and so the launch)."""
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())
    cfg['parts'] = [{'slot': 'dvll', 'type': 'none'}]
    config = tmp_path / 'custom.yaml'
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    out = subprocess.run([str(TOOL), '--config', str(config), '--out-dir', str(tmp_path / 'v')],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode != 0 and "unknown slot 'dvll'" in out.stderr, out.stderr


def test_cache_mode_prints_only_the_directory():
    """--cache writes under $ROS_HOME, keyed by the config, and prints the path only."""
    with tempfile.TemporaryDirectory() as ros_home:
        env = dict(os.environ, ROS_HOME=ros_home)
        out = subprocess.run([str(TOOL), '--config', str(DEFAULT_CONFIG), '--cache'],
                             capture_output=True, text=True, timeout=180, env=env)
        assert out.returncode == 0, out.stderr
        path = Path(out.stdout)
        assert path.is_dir() and (path / 'model.sdf').is_file()
        assert out.stdout == str(path), 'stdout must be the bare path (launch uses it)'
        assert path.parent == Path(ros_home) / 'bluerov2_gazebo'
        # Same config, same directory: nothing piles up launch after launch.
        again = subprocess.run([str(TOOL), '--config', str(DEFAULT_CONFIG), '--cache'],
                               capture_output=True, text=True, timeout=180, env=env)
        assert again.stdout == out.stdout


def test_name_flows_to_every_artifact(tmp_path):
    """--name renames the instance everywhere at once: model, topics, bridge."""
    out = subprocess.run([str(TOOL), '--config', str(DEFAULT_CONFIG), '--name', 'boat_b',
                          '--out-dir', str(tmp_path / 'v')],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr
    out_dir = tmp_path / 'v'
    # The config that was used, with the name applied, sits next to the artifacts.
    used = yaml.safe_load((out_dir / 'vehicle.yaml').read_text())
    assert used['topic_namespace'] == 'boat_b'
    # The model is named after the instance...
    model = ET.parse(out_dir / 'model.sdf').getroot().find('model')
    assert model.get('name') == 'boat_b'
    assert ET.parse(out_dir / 'model.config').getroot().find('name').text == 'boat_b'
    # ...and so is every topic its plugins and sensors use.
    topics = [t.text for t in model.iter('topic')]
    assert topics and all(t.startswith('boat_b/') for t in topics), topics
    # The bridge agrees, so gz and ROS sides stay in sync.
    bridge = yaml.safe_load((out_dir / 'ros_gz_bridge.yaml').read_text())
    gz_topics = {e['gz_topic_name'] for e in bridge}
    assert any(t.startswith('/boat_b/thruster_1/') for t in gz_topics), gz_topics
    assert not any(t.startswith('/bluerov2/') for t in gz_topics), gz_topics


def test_name_gives_each_instance_its_own_cache_directory():
    """Two names from one config never share a directory; one name always does."""
    with tempfile.TemporaryDirectory() as ros_home:
        env = dict(os.environ, ROS_HOME=ros_home)

        def cache(*extra):
            out = subprocess.run([str(TOOL), '--config', str(DEFAULT_CONFIG), '--cache', *extra],
                                 capture_output=True, text=True, timeout=180, env=env)
            assert out.returncode == 0, out.stderr
            return out.stdout

        default = cache()
        a = cache('--name', 'boat_a')
        b = cache('--name', 'boat_b')
        assert len({default, a, b}) == 3
        assert cache('--name', 'boat_a') == a
        # Without --name the config's own namespace names the instance, as before.
        model = ET.parse(Path(default) / 'model.sdf').getroot().find('model')
        assert model.get('name') == 'bluerov2'


def test_two_instances_from_one_config_share_no_topic(tmp_path):
    """
    Two names from one config, topic overrides included, share no topic.

    A relative override goes under the instance namespace on both sides, so
    a command for one instance never reaches the other; only the fixed
    /clock and /joint_states remain shared.
    """
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())
    cfg['parts'] = [{'slot': 'camera', 'type': 'explorehd_camera', 'topic': 'eye'}]
    config = tmp_path / 'custom.yaml'
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    topics = {}
    for name in ('rov_a', 'rov_b'):
        out = subprocess.run([str(TOOL), '--config', str(config), '--name', name,
                              '--out-dir', str(tmp_path / name)],
                             capture_output=True, text=True, timeout=180)
        assert out.returncode == 0, out.stderr
        model = ET.parse(tmp_path / name / 'model.sdf').getroot()
        mine = {'/' + t.text.lstrip('/') for t in model.iter('topic')}
        for entry in yaml.safe_load((tmp_path / name / 'ros_gz_bridge.yaml').read_text()):
            mine |= {entry['gz_topic_name'], entry['ros_topic_name']}
        topics[name] = mine - {'/clock', '/joint_states'}
    a, b = topics.values()
    assert a and b and not (a & b), a & b
    assert all(t.startswith('/rov_a/') for t in a), a


def test_rejects_a_name_that_is_not_a_ros_name(tmp_path):
    """A name that cannot be a topic prefix or a namespace is refused up front."""
    for bad in ('boat-b', '2boats', 'fleet/boat_b', ''):
        out = subprocess.run([str(TOOL), '--config', str(DEFAULT_CONFIG), '--name', bad,
                              '--out-dir', str(tmp_path / 'v')],
                             capture_output=True, text=True, timeout=180)
        assert out.returncode != 0, bad
        assert 'invalid instance name' in out.stderr, bad
