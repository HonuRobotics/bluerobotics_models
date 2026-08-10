# bluerobotics_common

Shared resources for the Blue Robotics vehicle packages. Currently the
pool environment (`models/pool`, `models/deck`) that both playground
worlds include; the package's environment hooks put `models/` on
`GZ_SIM_RESOURCE_PATH` so `model://pool` and `model://deck` resolve for
any consumer. Add future shared assets (worlds, materials, media) here
rather than to a vehicle package.
