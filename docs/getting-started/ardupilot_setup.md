# ArduPilot SITL setup

Setting up ArduPilot optional.

Not necessary to simuate many robots, but ArduPilot is the default for many low-level control and navigation solutions.  Therefore, as reference implmentations, we illustrate how to integrate the Gazebo robot simuation with ArduPilot software in the loop (SITL).

Set up ArduPilot SITL and the Gazebo plugin, so a vehicle in these models can be driven by the same autopilot firmware it runs on the water. 

Two ways to work, and the build commands are identical in both. On a host already set up for this repository — Ubuntu 26.04 with ROS 2 Lyrical and `ros_gz`, per [Requirements](requirements.md) — everything below runs directly. In [drydock](https://github.com/HonuRobotics/drydock), the same commands run inside the `maritime` container. Only the prerequisite step differs.

## What you are installing

Four pieces, which stay separate:

| Piece | What it is | How it is installed | Where it goes |
|---|---|---|---|
| ArduPilot firmware | the real flight code compiled for x86 — `ardurover`, plus `sim_vehicle.py` | source, built with `waf` | `~/maritime_ws/thirdparty/ardupilot` |
| `ardupilot_gazebo` | a Gazebo system plugin that speaks ArduPilot's UDP protocol and drives model joints | source, built with `cmake` | `~/maritime_ws/thirdparty/ardupilot_gazebo` |
| MAVProxy | command-line ground station; comes up with `sim_vehicle.py` | pip, by ArduPilot's prereq script | that script's Python environment |
| QGroundControl | GUI ground station, what a BlueBoat operator uses | AppImage download | anywhere; not needed for the smoke test |

Neither source build is a colcon package, so neither belongs in `src/`. For this example, those source repositories are cloned in `~/maritime_ws/thirdparty/`, but it can be located in another location.   We build from this source, but do not anticipate making commits.

```bash
mkdir -p ~/maritime_ws/thirdparty
```

## Host/Container prerequisites

`ardupilot_gazebo` needs a few development packages beyond what this repository already requires. Gazebo itself is not among them: it arrives as `ros_gz`'s dependency, as [Requirements](requirements.md) describes.

On a host:

```bash
sudo apt install cmake rapidjson-dev libopencv-dev \
                 libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

In drydock they are listed in `projects/maritime/apt-packages.txt`, so rebuilding the image is all that is needed:

```bash
~/maritime_ws/tools/drydock/drydock build maritime
```


GStreamer is required unconditionally by the plugin's CMakeLists, even though
only its optional camera plugin uses it. A configure that stops at
`gstreamer-1.0 not found` means these packages are missing, not that anything
is wrong with your Gazebo.

### Source repo clones

 Both checkouts are pinned: ArduPilot to the `Rover-4.7.1` release tag, and the `ardupilot_gazebo` clone is fixed by commit hash. 

```bash
cd ~/maritime_ws/thirdparty
git clone https://github.com/ArduPilot/ardupilot.git
git -C ardupilot checkout Rover-4.7.1
git -C ardupilot submodule update --init --recursive
git clone https://github.com/ArduPilot/ardupilot_gazebo.git
git -C ardupilot_gazebo checkout 082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5
```

`Rover-4.7.1` is the 4.7 release the Blue Robotics parameter sets in this repository are derived from; `Sub-4.7.1` and `Copter-4.7.1` are the same commit, so the one checkout serves every both boat and ROV. 

## Build the Gazebo plugin

From host (or in drydock, attach to the container first with `~/maritime_ws/tools/drydock/drydock join maritime`.)

```bash
cd ~/maritime_ws/thirdparty/ardupilot_gazebo

export GZ_VERSION=jetty
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j$(nproc)
```

```{important}
`GZ_VERSION=jetty` is not optional. With the variable unset, `ardupilot_gazebo`'s
CMakeLists falls through to its Harmonic branch and looks for `gz-sim8`, which
does not exist here — the failure reads as a missing Gazebo rather than a wrong
one.
```

(The reason is that Jetty dropped the version suffix from its CMake package names. `ardupilot_gazebo`'s Jetty branch accordingly calls `find_package(gz-sim)` with no number and sets its version variables to the empty string, where the Harmonic and Ionic branches ask for `gz-sim8` and `gz-sim9`. That holds whether Gazebo came from upstream packages or, as under ROS 2 Lyrical, from `ros-lyrical-gz-sim-vendor` — both install `gz-sim-config.cmake`.)

The resulting shared libraries are in `build/`, e.g.,  `libArduPilotPlugin.so`.

## Build the ArduPilot firmware

```bash
cd ~/maritime_ws/thirdparty/ardupilot

# Create the venv inside the checkout; the prereq script finds and uses it.
python3 -m venv --system-site-packages venv-ardupilot

DO_PYTHON_VENV_ENV=0 Tools/environment_install/install-prereqs-ubuntu.sh -y

source venv-ardupilot/bin/activate
./waf configure --board sitl
./waf rover
```

Also build ArduCopter
```bash
./waf copter
``` 
to rund the Iris UAV test below

Ubuntu 26.04 ("resolute") is on the prereq script's supported list, so it should not need coaxing.

The venv is not optional and is worth understanding; see [Why a venv](#why-a-venv) below if the reason matters to you.

The script offers to edit your shell login file twice — once to activate its venv in every terminal, once to add `Tools/autotest` to `PATH`. Decline both. `DO_PYTHON_VENV_ENV=0` handles the first; answer `N` to the second if you are prompted, and note that plain `-y` answers `y` to it. Both edits go to the host's `~/.profile` through the bind mount, and both are handled instead by the environment script below.

### Verify the Python environment

The prereq script installs its Python dependencies as a single `pip install`, and if that resolution fails part-way it leaves an incomplete environment without stopping the script. This is worth checking rather than discovering later as an import error inside MAVProxy.

With the venv active:

```bash
for m in future pymavlink serial MAVProxy em pexpect lxml numpy psutil yaml; do
  python3 -c "import $m" 2>/dev/null || echo "MISSING $m"
done
```

Install anything it reports. Each package installs cleanly on its own — the failure is in the batch, not in the packages, so there is nothing to work around.

Two are worth knowing about specifically. **MAVProxy** is often absent, and **`future`** is a MAVProxy dependency that MAVProxy does not declare, so installing MAVProxy alone does not bring it and the first symptom is `ModuleNotFoundError: No module named 'future'` from `rline.py`.

```bash
pip install MAVProxy future
```

`--map` and `--console` additionally need wxPython, which comes from apt rather than pip — the pip build compiles wxWidgets and takes the best part of an hour, while the venv's `--system-site-packages` makes the apt module visible from inside it. It is in drydock's package list; on a host, `sudo apt install python3-wxgtk4.0`.

ArduPilot's list also includes `dronecan`, `geocoder`, `tabulate`, `wsproto`, `junitparser` and `intelhex`. None are needed for SITL — they cover CAN peripherals, map geocoding, autotest reporting and hex generation for real flight boards — so leave them missing unless something asks.

```{warning}
Do not inspect this venv from the host. It is created with
`--system-site-packages`, so a `pip list` run outside the container reports
the host's packages as though they were the venv's, and a module can appear
installed when it is not.
```

## Environment

SITL needs four things on the environment that nothing else in this workspace wants: the Gazebo variables, `Tools/autotest` on `PATH`, and the ArduPilot venv. Put them in one script rather than in a shell login file — under drydock, `$HOME` is shared with the host, so a login file is the wrong place for paths that only make sense inside the container.

```bash
cat > ~/maritime_ws/thirdparty/setup-ardupilot.sh <<'EOF'
# Source before running gz sim or sim_vehicle.py.
AP=$HOME/maritime_ws/thirdparty/ardupilot
AP_GZ=$HOME/maritime_ws/thirdparty/ardupilot_gazebo

# Activate the venv FIRST. Sourcing activate restores PATH to its pre-venv
# value, so anything added before it is silently discarded.
[ "$VIRTUAL_ENV" = "$AP/venv-ardupilot" ] || . "$AP/venv-ardupilot/bin/activate"

export GZ_VERSION=jetty
export GZ_SIM_SYSTEM_PLUGIN_PATH=$AP_GZ/build${GZ_SIM_SYSTEM_PLUGIN_PATH:+:$GZ_SIM_SYSTEM_PLUGIN_PATH}
export GZ_SIM_RESOURCE_PATH=$AP_GZ/models:$AP_GZ/worlds${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}
export SDF_PATH=$GZ_SIM_RESOURCE_PATH

case ":$PATH:" in
  *":$AP/Tools/autotest:"*) ;;
  *) export PATH="$AP/Tools/autotest:$PATH" ;;
esac
EOF
```

The venv activation has to come before the `PATH` line, not after. A venv's `activate` restores `PATH` to its pre-activation value when it runs, so a `PATH` entry added first disappears the moment the venv is activated — and only in shells where the venv was already active, which makes it look intermittent. The `case` guard keeps repeated sourcing from stacking duplicate entries.

Then, in every shell doing SITL work:

```bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
```

## Smoke test - Iris UAV


Two shells. In the first:

```bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
gz sim -v4 -r iris_runway.sdf
```

You should see the Iris UAV on a runway:

```{figure} images/iris_gazebo.png
:alt: The Iris quadcopter standing on a runway in the Gazebo viewport

The `iris_runway` world with the Iris model loaded, before SITL connects. The
vehicle sits inert at this point: the plugin is listening on UDP 9002 and
nothing is commanding it.
```

In  second terminal:

```bash
source ~/maritime_ws/thirdparty/setup-ardupilot.sh
AP=$HOME/maritime_ws/thirdparty/ardupilot/Tools/autotest/default_params
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --console --map -w \
  --add-param-file=$AP/copter.parm \
  --add-param-file=$AP/gazebo-iris.parm
```

The two `--add-param-file` arguments layer the frame's parameter files on top of whatever `sim_vehicle.py` loads for `-f gazebo-iris` model.

`ardupilot_gazebo`'s README leaves the parameter files out. At the pin its command works; on newer ArduPilot it will not arm.

`-w` wipes the EEPROM so the parameter files are reloaded. Worth using on the first run and after any aborted one: defaults are only written to a *fresh* EEPROM, and an EEPROM left can introduce stale information. 

Then at the MAVProxy prompt:

```
mode guided
arm throttle
takeoff 5
```

The quadcopter should lift off in the Gazebo window and hold five meters.

```{figure} images/iris_takeoff.png
:alt: The Iris quadcopter hovering above the runway, with the MAVProxy console and map alongside

The Iris holding altitude under ArduCopter. This is phase 0 complete: the
firmware, the plugin and the ground station are all talking, on a vehicle
nobody here has modified.
```

## Troubleshooting

**`Could NOT find gz-sim8`** — `GZ_VERSION` is unset or not `jetty`. See above.

**`gstreamer-1.0` not found at configure time** — the GStreamer development packages are missing; see Container prerequisites. The plugin requires them unconditionally, even though only the camera plugin uses them.

**`[Errno 2] No such file or directory: 'mavproxy.py'`**, or **`ModuleNotFoundError: No module named 'future'`** from `rline.py` — the prereq script's batch install left gaps. Run the verification above; both install cleanly on their own.

**`sim_vehicle.py: command not found`** — `setup-ardupilot.sh` has not been sourced in this shell. The prereq script only adds `Tools/autotest` to `PATH` if you accept its prompt, which under drydock you should not.

**`you need to install pexpect with 'python3 -m pip install pexpect'`** — the prereq script has not been run, or its venv is not active. If `venv-ardupilot` does not exist, the script has not run; it is what creates it. `source ~/venv-ardupilot/bin/activate` and try again. Resist the suggestion in the message: a system-wide pip install is refused on Ubuntu 26.04, and forcing it past that puts ArduPilot's pinned dependencies alongside ROS's.

**Gazebo starts but the vehicle never arms, and MAVProxy reports no heartbeat from the physics backend** — the two processes are not talking. SITL sends to UDP 9002 and the plugin listens there; check that the model's `<fdm_addr>` is `127.0.0.1` and that both are running inside the same container.

**`PreArm: Motors: Check frame class and type`** — the frame's parameters were never applied. Either the checkout is not at the pin (`git -C ~/maritime_ws/thirdparty/ardupilot describe --tags` should say `Rover-4.7.1`; newer ArduPilot does not load frame defaults when `--model` is given) or the `--add-param-file` arguments were dropped. Keep both arguments; `-w` alone does not help, because there are no defaults for it to reload.

**The vehicle arms but does not move** — usually the frame argument. The frame passed to `sim_vehicle.py` has to match the model's `<control>` channel wiring, and `--model JSON` has to be present or SITL uses its own internal physics and ignores Gazebo entirely.

**The vehicle arms, the thruster topics carry commands, and still nothing moves** — the thruster plugin is not loaded. Check that `GZ_SIM_SYSTEM_PLUGIN_PATH` still contains the workspace's `install/lib` after sourcing this script; if it holds only `ardupilot_gazebo/build`, the script is overwriting it rather than appending, and `gz-maritime-thruster-system` cannot be found. Commands keep flowing because `ArduPilotPlugin` publishes them regardless of whether anything is listening.

## Reference

Optional background. None of it is needed to follow the steps above.

(why-a-venv)=
### Why a venv, and why not to skip it

On Ubuntu 24.04 and later the script installs ArduPilot's Python dependencies into a virtual environment at `~/venv-ardupilot` rather than into the system Python. That is worth understanding rather than working around. The system Python is externally managed, so `pip install` into it is refused without `--break-system-packages`; and ArduPilot pins `empy==3.3.4` while ROS 2's `ament` uses empy 4.x, so installing their list system-wide would break colcon in a way that is unpleasant to diagnose.

The venv is created with `--system-site-packages`, so ROS stays visible from inside it. Activate it before `waf` and before `sim_vehicle.py` — a build outside it fails on a missing `pexpect` import.

Left to itself the script creates `~/venv-ardupilot`, but it looks in the ArduPilot checkout first: if `venv-ardupilot`, `venv` or `.venv` already exists there it uses that instead. Creating it in the checkout is worth the extra line. It keeps the venv beside the source it belongs to rather than loose in a home directory that, under drydock, is shared with the host and already full of things that are not container-specific.


```{warning}
For drydock: `$HOME` is bind-mounted into the drydock container at the same path, so
anything the prereq script writes to your home directory appears on the host
too. Run with `-y` alone and it answers yes to both of its shell-login
prompts, appending a venv activation and a `PATH` line to your `~/.profile` —
so every *host* terminal would then try to activate a venv built against the
container's Python. `DO_PYTHON_VENV_ENV=0` suppresses the venv one; decline
the `PATH` one. Set both explicitly in the environment script instead.
```

Building `rover` alone is enough for the BlueBoat. `./waf copter` as well if you want the Iris smoke test below.
