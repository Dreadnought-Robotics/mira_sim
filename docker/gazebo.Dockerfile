# Minimal Gazebo Harmonic + ArduPilot bridge for mira_sim.
# Bakes the plugin built from src/ardupilot_gazebo and the bluerov2_gz
# models/worlds so `gz sim` finds model://bluerov2_heavy without host mounts.
# Runtime GPU selection is handled by docker-compose (mira-sim-gpu variant)
# and docker/gazebo-entrypoint.sh at container start.
#
# Build: docker build -f docker/gazebo.Dockerfile -t mira_sim-gazebo .
FROM osrf/ros:jazzy-simulation

ENV GZ_VERSION=harmonic
ENV DEBIAN_FRONTEND=noninteractive

# OSRF gazebo repo (provides libgz-sim8-dev for Harmonic on Noble).
# Needed because osrf/ros:jazzy-simulation only vendors gz-sim via ros-jazzy-gz-sim-vendor
# and does not ship -dev headers. Minimal tools to add the repo are installed
# in the same layer and kept only for this build.
RUN apt-get update \
  && apt-get -y --quiet --no-install-recommends install wget gnupg \
  && wget -q https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(. /etc/os-release && echo $VERSION_CODENAME) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null \
  && apt-get update \
  && apt-get -y --quiet --no-install-recommends install \
    build-essential \
    cmake \
    pkg-config \
    libgz-sim8-dev \
    rapidjson-dev \
    libopencv-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-gl \
  && rm -rf /var/lib/apt/lists/*

# -- Build ardupilot_gazebo plugin ----------------------------------------
COPY src/ardupilot_gazebo /workspace/ardupilot_gazebo
RUN cd /workspace/ardupilot_gazebo \
  && mkdir -p build \
  && cd build \
  && cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  && make -j"$(nproc)"

# -- Vendor bluerov2_gz models/worlds ---------------------------------------
COPY src/bluerov2_gz /workspace/bluerov2_gz

# -- Environment for gz sim ------------------------------------------------
ENV GZ_SIM_SYSTEM_PLUGIN_PATH=/workspace/ardupilot_gazebo/build
ENV GZ_SIM_RESOURCE_PATH=/workspace/bluerov2_gz/models:/workspace/bluerov2_gz/worlds:/workspace/worlds:/workspace/common_resources:/workspace/sauvc_sim/models:/workspace/sauvc_sim/worlds
# gz-tools (the `gz` CLI) only registers a subcommand if it finds that
# plugin's <name>.yaml under a directory on GZ_CONFIG_PATH. The apt-installed
# libgz-sim8-dev package (needed for headers to build ardupilot_gazebo) does
# NOT ship sim8.yaml under /usr/share/gz - only ros-jazzy-gz-sim-vendor does,
# under its own prefix. Without this, `gz sim` isn't recognized as a command
# at all (gz --commands silently omits "sim") even though the sim library is
# installed and works fine. GZ_CONFIG_PATH replaces rather than extends the
# built-in search path, so /usr/share/gz must be listed explicitly too or
# every other gz subcommand (fuel, gui, log, msg, param, sdf) disappears.
ENV GZ_CONFIG_PATH=/usr/share/gz:/opt/ros/jazzy/opt/gz_sim_vendor/share/gz

# -- GPU-aware entrypoint ---------------------------------------------------
COPY docker/gazebo-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
