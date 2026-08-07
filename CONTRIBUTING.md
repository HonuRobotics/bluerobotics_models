# Contributing

Thanks for improving the Blue Robotics vehicle models. This page covers the
developer workflow; using the models is documented in the [README](README.md)
and each package README, and releases in [RELEASING.md](RELEASING.md).

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
run. The CI workflow in `.github/workflows/ci.yml` is the source of truth for
the supported build.

## Pre-commit hooks

Optional but recommended: install the pre-commit hooks. They mirror the ament
linters that CI runs (plus basic file hygiene), so a passing pre-commit means a
passing lint stage.

```bash
pip install pre-commit
pre-commit install              # from the repo root; runs on every git commit
```

To check manually at any time:

```bash
pre-commit run --all-files      # everything, staged or not
pre-commit run                  # staged files only
pre-commit run ament_flake8 --all-files   # a single hook
```

The `ament_*` hooks need a sourced ROS environment; some hooks fix files in
place (trailing whitespace, end of file), so re-stage and re-run after a
failure that says "files were modified by this hook".

## Conventions

- One-line commit subjects, signed off (`git commit -s`).
- Vehicle configuration lives in each description package's `config/*.yaml`;
  the URDF, the composed Gazebo model and the ros_gz bridge config are all
  GENERATED from it at build time. Never hand-edit the generated files.
- Every accessory type is a same-named xacro macro; the tests enforce that the
  config catalog, the mass table and the macros stay in sync.
