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
The assembly manifest and the vehicle config check.

urdf/assembly.xacro records the resolved assembly in the URDF it emits:
one <assembly_part type name parent/> per part instance and one
<assembly_slot of name/> per slot it visited (the parts' own and the ad hoc
ones). Both are URDF extension elements urdfdom and Gazebo ignore. This
module reads them and checks a vehicle config against them, catching what
the xacro expansion cannot see across its recursion: an entry addressing a
slot or instance that does not exist, two instances sharing a name, a key
nobody reads. Vehicle builds and launches call `check`; the CLI is

    check_assembly.py <vehicle_config.yaml> <assembled.urdf>
"""

import sys
import xml.etree.ElementTree as ET

import yaml

# Keys each kind of config entry may carry. A key outside its set is a typo
# until proven otherwise; the sets grow with the features.
TOP_KEYS = {'topic_namespace', 'base', 'parts', 'slots', 'hull_displacement',
            'extra_bridge_topics'}
BASE_KEYS = {'type', 'name', 'collision'}
PART_COMMON_KEYS = {'type', 'name', 'xyz', 'rpy', 'collision', 'joint', 'axis',
                    'topic', 'gz_topic', 'ros_topic', 'bridge'}
SLOT_ENTRY_KEYS = PART_COMMON_KEYS | {'slot', 'of'}
FREE_ENTRY_KEYS = PART_COMMON_KEYS | {'parent'}
ADHOC_SLOT_KEYS = {'of', 'name', 'xyz', 'rpy', 'accepts', 'default', 'joint'}


class AssemblyError(Exception):
    """The config does not match the assembly; the message lists why."""


def instances(urdf_root):
    """(type, name, parent) of every part instance in the manifest, in order."""
    return [(e.get('type'), e.get('name'), e.get('parent'))
            for e in urdf_root.findall('assembly_part')]


def slots(urdf_root):
    """{(instance, slot)} for every slot the assembly visited."""
    return {(e.get('of'), e.get('name')) for e in urdf_root.findall('assembly_slot')}


def base_name(cfg):
    """Return the root link name a config asks for."""
    return (cfg.get('base') or {}).get('name', 'base_link')


def problems(cfg, urdf_root):
    """Return the list of mismatches between a config and the assembled URDF."""
    found = []
    root = base_name(cfg)
    parts = instances(urdf_root)
    names = [name for _, name, _ in parts]
    known_slots = slots(urdf_root)

    def keys(entry, allowed, what):
        bad = sorted(str(k) for k in entry if k not in allowed)
        if True in entry:
            found.append(f"{what} has a bare 'on:' key, which YAML reads as true; "
                         "the key is 'of:'")
            bad = [k for k in bad if k != 'True']
        if bad:
            found.append(f'{what} has unknown key(s) {bad} (known: {sorted(allowed)})')

    keys(cfg, TOP_KEYS, 'the config')
    keys(cfg.get('base') or {}, BASE_KEYS, 'base')
    for entry in cfg.get('parts') or []:
        if 'slot' in entry:
            slot, of = entry['slot'], entry.get('of', root)
            keys(entry, SLOT_ENTRY_KEYS, f'slot entry {slot!r} of {of!r}')
            if (of, slot) not in known_slots:
                mine = sorted(s for o, s in known_slots if o == of)
                found.append(
                    f'slot entry {slot!r} of {of!r} matches nothing: '
                    + (f'{of!r} has slots {mine}' if mine
                       else f'no instance named {of!r} (instances: {names})'))
        else:
            keys(entry, FREE_ENTRY_KEYS, f'free entry {entry.get("name")!r}')
            if entry.get('type', 'none') != 'none' and entry.get('name') not in names:
                found.append(f'free entry {entry.get("name")!r} was not assembled')
    for slot in cfg.get('slots') or []:
        of = slot.get('of', root)
        keys(slot, ADHOC_SLOT_KEYS, f'ad hoc slot {slot.get("name")!r} of {of!r}')
        if (of, slot.get('name')) not in known_slots:
            found.append(f'ad hoc slot {slot.get("name")!r} of {of!r} matches nothing: '
                         f'no instance named {of!r} (instances: {names})')
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        found.append(f'instance name(s) {dupes} used more than once (the same part '
                     'fitted twice defaults to the same name; give one a name:)')
    return found


def check(cfg, urdf_root):
    """Raise AssemblyError listing every mismatch between cfg and the URDF."""
    found = problems(cfg, urdf_root)
    if found:
        raise AssemblyError('ASSEMBLY ERROR:\n  ' + '\n  '.join(found))


def main(argv=None):
    """CLI: exit non zero with the problems listed."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        sys.exit(__doc__)
    with open(argv[0]) as f:
        cfg = yaml.safe_load(f) or {}
    try:
        check(cfg, ET.parse(argv[1]).getroot())
    except AssemblyError as e:
        sys.exit(str(e))
    print(f'{argv[0]}: config matches the assembly')


if __name__ == '__main__':
    main()
