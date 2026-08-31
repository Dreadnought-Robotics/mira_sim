# Mira Simulator

A fully containerized underwater robotics simulator for the BlueROV2 based on **Gazebo Harmonic** and **ArduPilot SITL**.

![Mira Simulator with QGroundControl](./Screenshot%20from%202026-08-31%2017-43-31.png)

## Overview

Mira combines Gazebo Harmonic, ArduPilot SITL, and the BlueROV2 model into a complete simulation environment. Everything runs in Docker—no ROS installation needed on your host.

**Key Features:**
- Real-time 3D physics with multiple underwater worlds
- MAVLink integration with QGroundControl
- Auto-detected GPU rendering (NVIDIA/Intel iGPU/software fallback)
- Persistent containers for interrupted session recovery

## Requirements

- **Docker & Docker Compose** (v2.0+)
- **X11 server** (for GUI; use `ssh -X` if remote)
- **4+ CPU cores, 8GB RAM** minimum
- **Linux** (tested on Ubuntu 22.04+)
- Optional: **QGroundControl** (download from [qgroundcontrol.com](https://qgroundcontrol.com))
- Optional: **NVIDIA GPU + NVIDIA Container Toolkit** (auto-detected if present)

## Quick Start

```bash
# Clone and initialize submodules
git clone <repo-url> && cd mira_sim
git submodule update --init --recursive

# Terminal 1: Start ArduPilot SITL (autopilot)
make sitl

# Terminal 2: Start Gazebo simulator
make simulator-gz

# Terminal 3: Launch QGroundControl on your host
qgroundcontrol  # or download from qgroundcontrol.com
```

**That's it!** QGC auto-connects to the simulator on `127.0.0.1:14550` (UDP).

## Available Worlds

```bash
make simulator-gz        # BlueROV2 Heavy (default)
make simulator-tacc-gz   # TACC pipeline world
make simulator-sauvc-gz  # SAUVC competition world
```

## Container Management

```bash
# Restart containers (surviving Ctrl-C)
make shell              # Attach shell to Gazebo container
docker compose stop     # Stop all services
docker compose down     # Stop and remove containers
docker compose build    # Rebuild images locally
```

**Services:**
- `ardupilot-sitl` — Autopilot (listening on 14550/UDP)
- `mira_sim` — Gazebo simulator (auto-detects GPU)
- `mira-sim-gpu` — Explicit NVIDIA GPU variant

Force GPU selection:
```bash
MIRA_GPU=1 make simulator-gz    # Force NVIDIA
MIRA_GPU=0 make simulator-gz    # Force software rendering
```

## Competition Bringup

Tmux sessions with persistent containers:

```bash
make bringup-gz      # 3-window session: sitl, bridge, gazebo
make bringup-tacc    # TACC world
make bringup-sauvc   # SAUVC world (with ros_gz_bridge)

tmux attach -t mira-gz    # Attach to session
tmux kill-session -t mira-gz  # Kill session
```

## Troubleshooting

For detailed troubleshooting steps (X11 issues, QGC connection, performance tuning, etc.), see [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md).

## Structure

```
mira_sim/
├── docker-compose.yml            # Service definitions
├── docker/                        # Dockerfiles & startup scripts
├── worlds/                        # Custom Gazebo world files
├── ardupilot/                     # SITL config directory
├── src/
│   ├── bluerov2_gz/              # BlueROV2 model (submodule)
│   ├── ardupilot_gazebo/         # FDM bridge (submodule)
│   └── sauvc_sim/                # SAUVC models (submodule)
├── Makefile
├── GAZEBO_NOTES.md               # Technical integration notes
└── docs/
    └── TROUBLESHOOTING.md        # Detailed debugging guide
```

## Building Locally

Rebuild Docker images after editing code:

```bash
docker compose build
docker compose up --build --no-recreate -d
```

First build takes 30-45 minutes (ArduPilot compilation).

## Learn More

- [GAZEBO_NOTES.md](./GAZEBO_NOTES.md) — Technical background on Gazebo Harmonic migration & known fixes
- [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) — Debugging guide
- [Gazebo Docs](https://gazebosim.org)
- [ArduPilot Docs](https://ardupilot.org)
- [ArduSub Manual](https://www.ardusub.com)

## License

Apache License 2.0. See [LICENSE](./LICENSE).
