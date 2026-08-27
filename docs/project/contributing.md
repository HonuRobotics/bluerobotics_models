# Contributing

Thanks for improving the Blue Robotics vehicle models.

## Build and test

The project standard is the merged install layout, the same command CI runs:

```bash
colcon build --merge-install
colcon test --merge-install
colcon test-result --verbose
```

The gz integration suites run a headless server; they need the `gz` CLI and
fail (never skip) when the environment is broken. Test logs, including the
sim output tails, land in `log/` and are uploaded as a CI artifact on every
run. `.github/workflows/ci.yml` is the source of truth for the supported
build.

What the suites guard: the config to URDF generation (defaults, slot
overrides, rejections, catalog, hull displacement invariants, the Ping below
the waterline), the composed Gazebo model (plugins, sensors at their frames,
references surviving lumping, topics equal to the bridge's), the bridge
generator, `configure_vehicle.py`, and headless Gazebo and ROS launches that
drive the boat and read the echosounder.

## Pre-commit hooks

Optional but recommended; they mirror the ament linters CI runs plus basic
file hygiene, so a passing pre-commit means a passing lint stage.

```bash
pip install pre-commit
pre-commit install              # from the repo root; runs on every git commit
pre-commit run --all-files      # check everything manually
```

The `ament_*` hooks need a sourced ROS environment; some hooks fix files in
place, so re-stage and re-run after "files were modified by this hook".

## Conventions

- One line commit subjects, signed off (`git commit -s`).
- The URDF xacro is the part; `bluerobotics_parts/urdf/<part>.urdf.xacro`
  is hand maintained source. The bootstrap tool writes it once; never
  regenerate over hand edits.
- Vehicle configuration lives in each description package's `config/*.yaml`;
  the URDF, the composed Gazebo model and the ros_gz bridge config are all
  generated from it. Never hand edit the generated files.
- Slots, accepted types and defaults live in the parts. Adding a part that
  fits a slot means listing it in that slot's `accepts`; the tests check the
  catalog stays coherent.
- Documentation lives on this site (`docs/`); package READMEs are pointers.

## Documentation

The site is built with [honu-docs](https://github.com/HonuRobotics/honu-docs)
(Sphinx + MyST). Every pull request gets a strict build; pushes to a distro
branch deploy that branch. Locally:

```bash
pip install -r docs/requirements.txt
sphinx-build -W docs _build/html && python3 -m http.server -d _build/html
```
