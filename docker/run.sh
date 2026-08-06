#!/usr/bin/env bash
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
#
# Convenience wrapper around `docker compose` for this repository's image.
#
#   ./run.sh build            Build the image
#   ./run.sh sim              Gazebo + GUI       (default when no service given)
#   ./run.sh sim-headless     Gazebo, no GUI
#   ./run.sh rviz             RViz on the description
#   ./run.sh shell            Interactive shell in the built workspace
#   ./run.sh test             colcon test
#   ./run.sh dev              Shell with the host source tree bind-mounted
#   ./run.sh <service> <cmd>  Override the service command
#
# What it does beyond plain `docker compose`: prepares an X cookie the container
# user can actually use, passes the host UID/GID through, and adds sudo when the
# invoking user cannot reach the Docker socket.
set -euo pipefail

readonly HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly XAUTH_FILE="${XAUTH_FILE:-/tmp/.docker.xauth}"

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    echo "==> Docker socket not reachable as $(id -un); using sudo." >&2
    DOCKER=(sudo docker)
  else
    echo "ERROR: cannot reach the Docker daemon and sudo is unavailable." >&2
    exit 1
  fi
fi

# The host X server rejects a client whose credentials it does not know. Rather
# than disabling access control globally (xhost +), copy the current cookie into
# a file the container mounts, rewriting the address family to FamilyWild
# (ffff) so it is accepted regardless of the hostname the container reports.
prepare_xauth() {
  if [ -z "${DISPLAY:-}" ]; then
    echo "==> DISPLAY is unset: GUI services will not be able to open a window." >&2
    echo "    On a pure Wayland session, start XWayland or use sim-headless." >&2
    : > "${XAUTH_FILE}" 2>/dev/null || true
    return
  fi

  if ! command -v xauth >/dev/null 2>&1; then
    echo "==> xauth not found; falling back to 'xhost +local:'." >&2
    command -v xhost >/dev/null 2>&1 && xhost +local: >/dev/null || true
    : > "${XAUTH_FILE}"
    chmod 0644 "${XAUTH_FILE}"
    return
  fi

  rm -f "${XAUTH_FILE}"
  : > "${XAUTH_FILE}"
  # An empty nlist (nothing to merge) is not an error: some setups authorise by
  # host rather than cookie, and the empty file mounts harmlessly.
  xauth nlist "${DISPLAY}" 2>/dev/null \
    | sed -e 's/^..../ffff/' \
    | xauth -f "${XAUTH_FILE}" nmerge - 2>/dev/null || true
  chmod 0644 "${XAUTH_FILE}"
}

prepare_xauth

export XAUTH_FILE
export USER_UID="${USER_UID:-$(id -u)}"
export USER_GID="${USER_GID:-$(id -g)}"
export ROS_DISTRO="${ROS_DISTRO:-lyrical}"

cd "${HERE}"

if [ "${1:-}" = "build" ]; then
  shift
  exec "${DOCKER[@]}" compose build "$@"
fi

service="${1:-sim}"
[ $# -gt 0 ] && shift

# `run --rm` rather than `up`: these are one-shot foreground sessions, and Ctrl-C
# should leave nothing behind.
exec "${DOCKER[@]}" compose run --rm "${service}" "$@"
