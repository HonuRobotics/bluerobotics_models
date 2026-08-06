# syntax=docker/dockerfile:1
#
# GPU-capable image for the Blue Robotics models: ROS 2 Lyrical + Gazebo Jetty
# with the two packages of this repository built into an overlay workspace.
#
# The build reproduces the README's from-source quick start (rosdep update,
# rosdep install, colcon build) inside the image, so `docker run` lands in a
# shell where `ros2 launch bluerov2_gazebo sim.launch.xml` just works.
#
# GPU access is provided at RUN time by the NVIDIA container runtime
# (`--gpus all`); the NVIDIA_* variables below tell it to expose the graphics
# and display driver capabilities, not only compute. Without a GPU the image
# still runs: Mesa's llvmpipe provides a software GL path (slow, but the
# camera / RGBD / gpu_lidar sensors in the playground world still render).

ARG ROS_DISTRO=lyrical
FROM ros:${ROS_DISTRO}
ARG ROS_DISTRO

LABEL org.opencontainers.image.title="bluerobotics_models" \
      org.opencontainers.image.description="BlueROV2 ROS 2 + Gazebo simulation, GPU-ready" \
      org.opencontainers.image.source="https://github.com/HonuRobotics/bluerobotics_models" \
      org.opencontainers.image.licenses="Apache-2.0"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# ARG, not ENV: keep noninteractive out of the runtime environment.
ARG DEBIAN_FRONTEND=noninteractive

# Two groups of packages:
#  - build tooling (colcon/rosdep/vcstool) - the ros:* base tags are not
#    guaranteed to carry them, mirroring what setup-ros installs in CI;
#  - the GL/Vulkan/X11 runtime that Gazebo's ogre2 render path and the Qt GUIs
#    (gz sim -g, RViz) need. libglvnd is the dispatch layer the NVIDIA runtime
#    injects libGLX_nvidia into; mesa-*-drivers stay as the no-GPU fallback.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3-colcon-common-extensions \
      python3-rosdep \
      python3-vcstool \
      sudo \
      passwd \
      libglvnd0 \
      libgl1 \
      libglx0 \
      libegl1 \
      libgles2 \
      libglu1-mesa \
      libgl1-mesa-dri \
      libvulkan1 \
      mesa-vulkan-drivers \
      mesa-utils \
      vulkan-tools \
      libx11-6 \
      libxext6 \
      libxrender1 \
      libxrandr2 \
      libxi6 \
      libxcursor1 \
      libxinerama1 \
      libxkbcommon-x11-0 \
      x11-utils

# Unprivileged user matching the host UID/GID, so a bind-mounted source tree
# (see compose.yaml's `dev` profile) does not end up with root-owned build/
# and install/ directories. Ubuntu 26.04 base images already ship a UID 1000
# user, so rename it rather than colliding with it.
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
RUN set -eux; \
    if getent group "${USER_GID}" >/dev/null; then \
      current="$(getent group "${USER_GID}" | cut -d: -f1)"; \
      [ "${current}" = "${USERNAME}" ] || groupmod -n "${USERNAME}" "${current}"; \
    else \
      groupadd -g "${USER_GID}" "${USERNAME}"; \
    fi; \
    if getent passwd "${USER_UID}" >/dev/null; then \
      current="$(getent passwd "${USER_UID}" | cut -d: -f1)"; \
      if [ "${current}" != "${USERNAME}" ]; then \
        usermod -l "${USERNAME}" -d "/home/${USERNAME}" -m -g "${USER_GID}" "${current}"; \
      fi; \
    else \
      useradd -m -u "${USER_UID}" -g "${USER_GID}" -s /bin/bash "${USERNAME}"; \
    fi; \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}"; \
    chmod 0440 "/etc/sudoers.d/${USERNAME}"

# Overlay workspace. Sources land under src/ exactly as the README lays them out.
ENV WORKSPACE=/ws
WORKDIR ${WORKSPACE}
COPY --chown=${USER_UID}:${USER_GID} . src/bluerobotics_models/

# rosdep update refreshes the dependency database first: skipping it in a fresh
# container is the usual cause of "Cannot locate rosdep definition" errors.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    rosdep update --rosdistro "${ROS_DISTRO}" && \
    rosdep install --from-paths src --ignore-packages-from-source --default-yes

RUN source "/opt/ros/${ROS_DISTRO}/setup.bash" && \
    colcon build --event-handlers console_cohesion+ && \
    chown -R "${USER_UID}:${USER_GID}" "${WORKSPACE}"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# NVIDIA container runtime hints. `all` covers compute+utility+graphics+display,
# and graphics/display are the ones ogre2 and the Qt GUIs actually need.
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=all

# MIT-SHM does not survive the container/host X boundary; Qt falls back to plain
# X11 transport with this set.
ENV QT_X11_NO_MITSHM=1

USER ${USERNAME}
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
