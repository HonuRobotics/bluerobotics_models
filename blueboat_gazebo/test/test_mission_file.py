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
"""Static checks on the installed waypoint mission (no autopilot needed)."""

import math
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
import pytest

MISSION = (Path(get_package_share_directory('blueboat_gazebo'))
           / 'missions' / 'lawnmower.waypoints')

# The home the walkthrough pins with sim_vehicle.py --custom-location.
HOME = (1.287684290, 103.856013589)
WP_RADIUS = 1.0          # m, blueboat_sitl.params
WATER_HALF_SIZE = 100.0  # m, the 200 x 200 m water plane in blueboat_sitl.sdf
MARGIN = 10.0            # m kept clear of the plane's edge
MAV_CMD_NAV_WAYPOINT = 16


def _items():
    lines = MISSION.read_text().splitlines()
    assert lines[0].strip() == 'QGC WPL 110'
    return [line.split('\t') for line in lines[1:] if line.strip()]


def _north_east(lat, lon):
    """Metres north and east of HOME, flat-earth (fine at this scale)."""
    r = 6378137.0
    north = math.radians(lat - HOME[0]) * r
    east = math.radians(lon - HOME[1]) * r * math.cos(math.radians(HOME[0]))
    return north, east


def test_items_are_well_formed():
    items = _items()
    assert len(items) == 7, 'home plus six waypoints'
    for seq, item in enumerate(items):
        assert len(item) == 12
        assert int(item[0]) == seq
        assert int(item[3]) == MAV_CMD_NAV_WAYPOINT


def test_home_is_the_pinned_location():
    home = _items()[0]
    assert float(home[8]) == pytest.approx(HOME[0], abs=1e-7)
    assert float(home[9]) == pytest.approx(HOME[1], abs=1e-7)


def test_waypoints_stay_on_the_water():
    for item in _items()[1:]:
        north, east = _north_east(float(item[8]), float(item[9]))
        assert abs(north) < WATER_HALF_SIZE - MARGIN
        assert abs(east) < WATER_HALF_SIZE - MARGIN


def test_consecutive_waypoints_are_distinct_targets():
    points = [(0.0, 0.0)] + [_north_east(float(i[8]), float(i[9]))
                             for i in _items()[1:]]
    for a, b in zip(points, points[1:]):
        assert math.dist(a, b) > 2 * WP_RADIUS
