# Docker (GPU)

A container image with ROS 2 Lyrical, Gazebo Jetty and both packages of this
repository already built, set up for hardware-accelerated rendering and GUIs on
the host display. It runs the same from-source steps as the root README's quick
start (`rosdep update`, `rosdep install`, `colcon build`), just inside an image.

## Requirements

| | |
|---|---|
| Docker Engine | 20.10+ with Compose v2+ (`docker compose version`) |
| GPU (NVIDIA) | proprietary driver on the host + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| GUI | an X server on the host; a Wayland session works through XWayland |

The GPU is optional. Without it, `sim-cpu` renders through Mesa's llvmpipe:
everything works, slowly.

Check the toolkit is wired into Docker before building:

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

If that prints your GPU, you are ready. If it errors with `could not select
device driver`, install the toolkit and run
`sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`.

## Quick start

```bash
cd docker
./run.sh build       # ~10-20 min the first time; rosdep pulls ros_gz + gz vendor pkgs
./run.sh sim         # Gazebo with the BlueROV2 in the playground world
```

`run.sh` prepares an X cookie the container can use, forwards your UID/GID and
falls back to `sudo docker` when your user is not in the `docker` group.

## Services

| Command | What it runs |
|---------|--------------|
| `./run.sh sim` | `ros2 launch bluerov2_gazebo sim.launch.xml` — server, GUI, bridge, RSP |
| `./run.sh sim-headless` | the same with `gui:=false`; sensors still render |
| `./run.sh rviz` | `ros2 launch bluerov2_description display.launch.xml` |
| `./run.sh shell` | interactive shell, ROS underlay + this overlay sourced |
| `./run.sh test` | `colcon test` over the built workspace (what CI runs) |
| `./run.sh dev` | shell with the **host** source tree bind-mounted at `/ws/src` |

Anything after the service name replaces the command, so ad-hoc runs work too:

```bash
./run.sh shell ros2 topic list
./run.sh sim ros2 launch bluerov2_gazebo sim.launch.xml gui:=false use_composition:=false
```

Plain `docker compose` works as well if you prefer it — `run.sh` only adds the
X cookie and UID/GID plumbing. Create the cookie file first: Docker would
otherwise create a *directory* at that path, and `XAUTHORITY` pointing at a
directory breaks the GUIs.

```bash
touch /tmp/.docker.xauth
xhost +local:
docker compose run --rm sim
```

## Verifying the GPU is actually being used

From inside the container:

```bash
./run.sh shell
nvidia-smi                               # the host GPU, as seen by the container
glxinfo -B | grep -E 'OpenGL (vendor|renderer)'   # must name the discrete GPU
vulkaninfo --summary | head              # ogre2 can also use the Vulkan path
```

Three outcomes, only one of which is right:

| `OpenGL renderer` | Meaning |
|---|---|
| `NVIDIA GeForce ...` | Correct — the discrete GPU is rendering |
| `llvmpipe` | Software rendering: `--gpus` or the `graphics` driver capability did not get through |
| an integrated GPU (`AMD Radeon 780M`, `Mesa Intel ...`) | **Hybrid-laptop trap** — see below |

### The hybrid-laptop trap

On a laptop with a discrete NVIDIA GPU *and* an integrated one, everything looks
healthy — `nvidia-smi` works in the container, `/dev/nvidia*` exists, the NVIDIA
libraries are injected, and the processes even open `/dev/nvidiactl` — while
rendering silently runs on the **integrated** GPU. libglvnd resolves GLX to
`libGLX_mesa`, which takes the `/dev/dri` render node this compose file maps in;
`libGLX_nvidia` is never loaded. Open file descriptors on `/dev/nvidia*` prove
nothing: libglvnd opens them just to *probe* the EGL vendor.

The compose file pins the vendor explicitly (`x-env-nvidia`):

```yaml
__NV_PRIME_RENDER_OFFLOAD: 1
__GLX_VENDOR_LIBRARY_NAME: nvidia
__EGL_VENDOR_LIBRARY_FILENAMES: /usr/share/glvnd/egl_vendor.d/10_nvidia.json
```

To confirm from the host while the sim runs, watch both GPUs — only one should
be busy:

```bash
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
cat /sys/class/drm/card*/device/gpu_busy_percent    # integrated GPU load
```

Or check which vendor library the process actually mapped, which is conclusive:

```bash
grep -c libGLX_nvidia /proc/<gz-sim-pid>/maps   # 0 means Mesa won
```

Note that the NVIDIA **Vulkan** ICD is not injected by the container runtime
(`/usr/share/vulkan/icd.d/` holds only Mesa ICDs), so the Vulkan render path
would land on Mesa regardless. Gazebo's default OpenGL path is unaffected.

## Development loop

`dev` mounts the host checkout over the image's copy, so edits on the host are
what gets built. `build/` and `install/` live in named volumes, keeping the host
tree clean and preserving incremental builds between runs:

```bash
./run.sh dev
colcon build --event-handlers console_cohesion+
source install/setup.bash
ros2 launch bluerov2_gazebo sim.launch.xml
```

To start that workspace over: `docker compose down -v`.

## Configuration

Build arguments (`docker compose build --build-arg ...`, or environment
variables that `run.sh` forwards):

| Variable | Default | Purpose |
|----------|---------|---------|
| `ROS_DISTRO` | `lyrical` | Base image tag and the distro built against |
| `USER_UID` / `USER_GID` | your host IDs | Ownership of bind-mounted files |
| `ROS_DOMAIN_ID` | `0` | DDS domain (runtime) |
| `XAUTH_FILE` | `/tmp/.docker.xauth` | Where `run.sh` writes the X cookie |

Custom accessory loadouts do not need a rebuild — pass the launch arguments the
package READMEs document:

```bash
./run.sh sim ros2 launch bluerov2_gazebo sim.launch.xml \
  config_file:=/path/inside/container/my_bluerov2.yaml
```

Note the caveat in `sim.launch.xml`: `config_file` affects
`robot_state_publisher` and the bridge, while the Gazebo-side model comes from
the world's `model://bluerov2_gazebo` include.

## Inspecting a running sim from the host

`network_mode: host` plus `ipc: host` put the container on the host's network and
IPC namespaces, so host tooling can see straight into the simulation.

ROS 2 needs nothing special (a matching distro on the host, same `ROS_DOMAIN_ID`):

```bash
source /opt/ros/lyrical/setup.bash
ros2 node list          # /gz_server /ros_gz_bridge /robot_state_publisher ...
ros2 topic hz /clock    # ~1000 Hz for the default 1 ms step
```

Gazebo transport needs the container's partition. gz-transport defaults to
`<hostname>:<username>`, and the container user is `ros`, not your host user:

```bash
GZ_PARTITION=$(hostname):ros gz topic -l
GZ_PARTITION=$(hostname):ros gz topic -e -t /world/bluerov2_playground/stats -n 1
```

Without `GZ_PARTITION` the topic list comes back empty even though the sim is
running perfectly.

One gotcha when measuring: `ros2 topic hz` block-buffers stdout when piped, so
`timeout 5 ros2 topic hz /clock | tail` prints nothing and looks like a dead
topic. Use `PYTHONUNBUFFERED=1`, or `ros2 topic echo --once`.

## Troubleshooting

**`Authorization required, but no authorization protocol specified`** — the X
cookie did not reach the container. Re-run through `run.sh`, or use
`xhost +local:` before `docker compose run`.

**GUI never appears on a Wayland session** — `DISPLAY` must point at XWayland
(`:0` typically). `echo $DISPLAY` on the host; if it is empty, use
`sim-headless`.

**`could not select device driver "" with capabilities: [[gpu]]`** — the NVIDIA
Container Toolkit is missing or Docker was not reconfigured after installing it.

**Rendering works but is very slow** — check `glxinfo -B` as above. On a hybrid
laptop the container may have landed on the integrated GPU; see "The
hybrid-laptop trap". Note that rendering on one GPU while the display is driven
by the other adds a per-frame cross-GPU copy on top of the slower rendering.

**`Cannot locate rosdep definition`** during build — a stale rosdep cache in the
build layer; rebuild with `docker compose build --no-cache`.
