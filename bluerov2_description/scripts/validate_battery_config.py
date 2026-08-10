#!/usr/bin/env python3
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
Validate the battery loadout of a vehicle config against the catalog.

Run at build time (CMake) so a bad loadout fails the build with a clear
message instead of generating a silently wrong vehicle. Also usable by hand:

    validate_battery_config.py --vehicle blueboat \
        --config config/blueboat.yaml --catalog config/batteries.yaml

Errors exit nonzero; warnings print to stderr and exit zero.
"""

import argparse
import sys

import yaml

# Absolute cap on |buoyancy_trim| in kg; beyond this it is not trim anymore.
TRIM_LIMIT_KG = 2.0

ENTRY_KEYS = {'pack', 'custom_pack', 'slot', 'name', 'offset'}


def fail(msg):
    print(f'battery config error: {msg}', file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f'battery config warning: {msg}', file=sys.stderr)


def resolve_pack(entry, packs, where):
    """Return the pack dict for a loadout entry, validating its shape."""
    has_pack = 'pack' in entry
    has_custom = 'custom_pack' in entry
    if has_pack == has_custom:
        fail(f'{where}: exactly one of `pack` or `custom_pack` is required')
    if has_pack:
        key = entry['pack']
        if key not in packs:
            fail(f'{where}: unknown pack {key!r}; catalog has '
                 f'{sorted(packs)}')
        if packs[key].get('discontinued'):
            warn(f'{where}: pack {key!r} is discontinued')
        return packs[key]
    pack = entry['custom_pack']
    if not isinstance(pack, dict):
        fail(f'{where}: `custom_pack` must be a mapping')
    if not isinstance(pack.get('mass'), (int, float)) or pack['mass'] <= 0:
        fail(f'{where}: custom_pack needs a positive `mass` in kg')
    size = pack.get('size')
    if (not isinstance(size, list) or len(size) != 3
            or not all(isinstance(v, (int, float)) and v > 0 for v in size)):
        fail(f'{where}: custom_pack needs `size: [x, y, z]` in metres')
    return pack


def validate(vehicle, cfg, db):
    packs = db['battery_packs']
    slots = db['battery_slots']
    max_batteries = db['max_batteries']

    if 'buoyancy_trim' in cfg:
        trim = cfg['buoyancy_trim']
        if vehicle != 'bluerov2':
            fail('`buoyancy_trim` only applies to vehicles with synthetic '
                 'buoyancy sizing (bluerov2); boat trim is controlled by '
                 'loadout placement instead')
        if trim not in ('neutral', 'neutral_plus'):
            try:
                value = float(trim)
            except (TypeError, ValueError):
                fail(f'`buoyancy_trim` must be `neutral`, `neutral_plus` or '
                     f'a number in kg, got {trim!r}')
            if abs(value) > TRIM_LIMIT_KG:
                fail(f'`buoyancy_trim` of {value} kg exceeds the '
                     f'+/-{TRIM_LIMIT_KG} kg sanity limit')

    if 'batteries' in cfg and not cfg['batteries']:
        fail('`batteries: []` is not a runnable vehicle; omit the key '
             'for the default loadout instead')
    loadout = cfg.get('batteries') or db['default_loadout']

    if len(loadout) > max_batteries:
        fail(f'{len(loadout)} batteries configured; {vehicle} supports at '
             f'most {max_batteries}')

    occupied = {}
    names = set()
    side_mass = {'port': 0.0, 'stbd': 0.0}
    masses = []
    for i, entry in enumerate(loadout):
        where = f'batteries[{i}]'
        unknown = set(entry) - ENTRY_KEYS
        if unknown:
            fail(f'{where}: unknown keys {sorted(unknown)}')
        slot_name = entry.get('slot')
        if slot_name not in slots:
            fail(f'{where}: unknown slot {slot_name!r}; {vehicle} has '
                 f'{sorted(slots)}')
        if slot_name in occupied:
            fail(f'{where}: slot {slot_name!r} already holds '
                 f'{occupied[slot_name]!r}')
        pack = resolve_pack(entry, packs, where)
        name = entry.get('name', slot_name)
        if name in names:
            fail(f'{where}: duplicate battery name {name!r}')
        names.add(name)
        occupied[slot_name] = name

        slot = slots[slot_name]
        for axis, pack_dim, env_dim in zip('xyz', pack['size'],
                                           slot['envelope']):
            if pack_dim > env_dim:
                fail(f'{where}: pack does not fit slot {slot_name!r} along '
                     f'{axis} ({pack_dim} > {env_dim} m)')

        offset = entry.get('offset') or {}
        bad_axes = set(offset) - {'x'}
        if bad_axes:
            fail(f'{where}: slot {slot_name!r} only allows an x offset, '
                 f'got {sorted(bad_axes)}')
        if 'x' in offset:
            lo, hi = slot['offset_x']
            if not lo <= float(offset['x']) <= hi:
                fail(f'{where}: x offset {offset["x"]} outside the '
                     f'[{lo}, {hi}] range of slot {slot_name!r}')

        masses.append(pack['mass'])
        for side in side_mass:
            if slot_name.startswith(side + '_'):
                side_mass[side] += pack['mass']

    if vehicle == 'blueboat':
        imbalance = abs(side_mass['port'] - side_mass['stbd'])
        threshold = max(masses)
        if imbalance > threshold:
            warn(f'port/stbd battery mass differs by {imbalance:.2f} kg '
                 f'(more than one pack); the boat will heel')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vehicle', required=True,
                        choices=['blueboat', 'bluerov2'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--catalog', required=True)
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f) or {}
    with open(args.catalog) as f:
        db = yaml.safe_load(f)
    validate(args.vehicle, cfg, db)


if __name__ == '__main__':
    main()
