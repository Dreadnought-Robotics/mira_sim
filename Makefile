.PHONY: master alt_master build source install-deps submodules update install-udev bs fix-vscode dashboard telemetry-viz simulator-gz simulator-tacc-gz simulator-sauvc-gz sitl shell bringup-gz bringup-tacc bringup-sauvc

export FORCE_COLOR=1
export RCUTILS_COLORIZED_OUTPUT=1
export RCUTILS_CONSOLE_OUTPUT_FORMAT={severity} {message}
SHELL := /bin/bash

WS := source .venv/bin/activate && source install/setup.bash

# Check if commands/directories exist at parse time
UV_EXISTS := $(shell command -v uv 2>/dev/null)
VENV_EXISTS := $(wildcard .venv)
ROS_JAZZY_EXISTS := $(wildcard /opt/ros/jazzy)
MAVPROXY_EXISTS := $(shell command -v mavproxy.py 2>/dev/null)$(shell command -v mavproxy 2>/dev/null)

all: build

# Resolve python paths
PYTHON3_PATH   := $(shell command -v python3 2>/dev/null)
PYTHON312_PATH := $(shell command -v python3.12 2>/dev/null)

check-uv:
ifndef UV_EXISTS
	$(error ❌ uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh)
endif

ifndef VENV_EXISTS
	$(warning ⚠️  Python virtual environment not found at .venv. Run make setup or uv sync to make it)
else
	$(info ✅ Virtual environment found at .venv.)
endif

# ---- Python checks ----
ifdef VIRTUAL_ENV
	$(error ❌ Active virtual environment detected ($(VIRTUAL_ENV)). Please run 'deactivate' before running make)
endif

ifeq ($(PYTHON3_PATH),)
	$(error ❌ python3 not found in PATH)
endif

ifeq ($(PYTHON312_PATH),)
	$(error ❌ python3.12 not found in PATH)
endif

IS_VENV := $(shell python3 -c "import sys; print(1 if sys.prefix != getattr(sys, 'base_prefix', sys.prefix) else 0)" 2>/dev/null)
ifeq ($(IS_VENV),1)
	$(error ❌ python3 is running inside a virtual environment ($(PYTHON3_PATH)). Please deactivate the virtual environment before running make)
endif

$(info ✅ python3     → $(PYTHON3_PATH))
$(info ✅ python3.12  → $(PYTHON312_PATH))


check-ros: check-uv
ifndef ROS_JAZZY_EXISTS
	$(error ❌ ROS Jazzy not found at /opt/ros/jazzy. Only ROS Jazzy is supported by this workspace.)
endif
	$(info ✅ ROS Jazzy found.)

# Build the workspace

# Alternativley you can use mold which is a bit faster
LINKER=lld
CMAKE_ARGS:= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
			 -DCMAKE_COLOR_DIAGNOSTICS=ON \
			 -GNinja \
			 -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=$(LINKER) \
			 -DCMAKE_MODULE_LINKER_FLAGS=-fuse-ld=$(LINKER) \
			 -DCMAKE_SHARED_LINKER_FLAGS=-fuse-ld=$(LINKER) \
			 --no-warn-unused-cli

SKIP_PACKAGES ?= vision_boundingbox vision_depth
COLCON_ARGS:= --cmake-args $(CMAKE_ARGS) \
                          --parallel-workers $(shell nproc) \
			  --packages-skip $(SKIP_PACKAGES) \
			  --event-handlers console_cohesion+ \
			  --continue-on-error
# 			  --symlink-install \
			  # --merge-install

build: check-ros
	$(warning If you built in docker last - you'll need to clean and rebuild)
	$(warning If build fails b/c of CMakeCacheList or issues with mismatch for build,log,install, run \`make clean\`)
	$(info Building workspace...)
	@source /opt/ros/jazzy/setup.bash && \
	source .venv/bin/activate && \
	colcon build ${COLCON_ARGS}

repoversion:
	$(info Last commit in repository:)
	@git log -1 --oneline

# --- Gazebo simulators (primary; fully containerized, no host ROS needed) ---
# ArduPilotPlugin talks to ArduSub over JSON/UDP (see the `sitl` target),
# no ROS bridge required for basic vehicle control / depth hold.
# Containers are persistent: `up --no-recreate` keeps the named container
# across runs so Ctrl-C stops it without removing it. Use
# `docker compose build` or `docker compose up --build --no-recreate` after
# editing Dockerfiles/submodules.
#
# GZ_SERVICE auto-selects the correct compose service based on host hardware:
#   - mira-sim-gpu  if nvidia-smi is present and reports a GPU
#   - mira_sim      otherwise (iGPU / software / llvmpipe fallback)
# The same image is used for both; the gpu variant just adds
# `runtime: nvidia` + GPU reservation. Override with:
#   make simulator-gz GZ_SERVICE=mira_sim
#   make simulator-gz GZ_SERVICE=mira-sim-gpu
#   MIRA_GPU=1 make simulator-gz   (force gpu)
#   MIRA_GPU=0 make simulator-gz   (force nogpu)
GZ_ARGS ?= -v3 -r
XAUTH := /tmp/.docker.xauth

# X11 passthrough: ensure xauth cookie and xhost allowance before any
# gazebo target. See docker/x11-setup.sh for details - it handles the
# ffff fix, Wayland/empty DISPLAY, and xhost +local:docker fallback.
# Also requires ipc:host + QT_X11_NO_MITSHM=1 in compose (already set).
check-x11:
	@bash ./docker/x11-setup.sh
	@if [ -z "$${DISPLAY:-}" ]; then \
		echo "⚠️  DISPLAY is empty - Gazebo GUI will not be visible (headless). Use ssh -X or set DISPLAY=:0/:1."; \
	elif ! xauth list "$$DISPLAY" >/dev/null 2>&1; then \
		echo "⚠️  xauth has no cookie for DISPLAY=$$DISPLAY - falling back to xhost +local:docker"; \
		xhost +local:docker >/dev/null 2>&1 || xhost +local: >/dev/null 2>&1 || true; \
	fi
	@chmod a+r $(XAUTH) 2>/dev/null || true

# Explicit override via MIRA_GPU env
ifeq ($(MIRA_GPU),1)
  GZ_SERVICE ?= mira-sim-gpu
else ifeq ($(MIRA_GPU),0)
  GZ_SERVICE ?= mira_sim
else
  # Auto-detect: nvidia-smi present => gpu, else default
  GZ_SERVICE ?= $(shell command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1 && echo mira-sim-gpu || echo mira_sim)
endif

$(XAUTH): check-x11
	@true

simulator-gz: $(XAUTH)
	@echo "🚀 Gazebo service: $(GZ_SERVICE) (MIRA_GPU=$(MIRA_GPU), auto-detect: nvidia-smi)"
	docker compose up --no-recreate -d $(GZ_SERVICE)
	docker compose exec $(GZ_SERVICE) gz sim $(GZ_ARGS) bluerov2_heavy_underwater.world

simulator-tacc-gz: $(XAUTH)
	@echo "🚀 Gazebo service: $(GZ_SERVICE)"
	docker compose up --no-recreate -d $(GZ_SERVICE)
	docker compose exec $(GZ_SERVICE) gz sim $(GZ_ARGS) /workspace/worlds/tacc.world

simulator-sauvc-gz: $(XAUTH)
	@echo "🚀 Gazebo service: $(GZ_SERVICE)"
	docker compose up --no-recreate -d $(GZ_SERVICE)
	docker compose exec $(GZ_SERVICE) gz sim $(GZ_ARGS) /workspace/sauvc_sim/worlds/sauvc25.world

# All three use `up --no-recreate -d` so the container is persistent:
# Ctrl-C stops `gz sim` (the exec) without removing the container; the container
# itself stays `Up` and is reused on next `make simulator-*` without recreation.
# `docker compose stop $(GZ_SERVICE)` / `docker compose down` to fully stop/remove.
# After editing Dockerfiles/submodules: `docker compose build` or
# `docker compose up --build --no-recreate -d $(GZ_SERVICE)`

sitl:
	docker compose up --no-recreate ardupilot-sitl

shell: $(XAUTH)
	@echo "🐚 Shell service: $(GZ_SERVICE)"
	docker compose up --no-recreate -d $(GZ_SERVICE)
	docker compose exec $(GZ_SERVICE) bash

# Raw persistent attach (Ctrl-C stops container without removing it):
#   docker compose up --no-recreate mira_sim
# One-off gz in persistent container:
#   docker compose exec mira_sim gz sim $(GZ_ARGS) <world>

# --- Tmux bringup for competitions (persistent containers, X11 auth) ---
# Each `make bringup-<competition>` spawns a tmux session with 3 windows:
#   0:sitl   - docker compose up --no-recreate ardupilot-sitl
#   1:bridge - ros_gz_bridge if needed, else idle message
#   2:gazebo - docker compose exec gz sim <world>
# All use `up --no-recreate` so containers persist (Ctrl-C stops, not removes).
# Attach: tmux attach -t mira-<competition>  Kill: tmux kill-session -t mira-<competition>
TMUX := $(shell command -v tmux 2>/dev/null)
check-tmux:
ifndef TMUX
	$(error ❌ tmux not found. Install with: sudo apt install tmux)
endif

bringup-gz: check-tmux $(XAUTH)
	@if tmux has-session -t mira-gz 2>/dev/null; then \
		echo "⚠️  tmux session mira-gz already exists. Attach: tmux attach -t mira-gz | Kill: tmux kill-session -t mira-gz"; exit 1; fi
	@echo "🚀 Bringup GZ (bluerov2_heavy) - tmux session mira-gz [$(GZ_SERVICE)]"
	tmux new-session -d -s mira-gz -n sitl 'docker compose up --no-recreate ardupilot-sitl; exec bash'
	tmux new-window -t mira-gz:1 -n bridge 'echo "No bridge required for bluerov2_heavy - ArduPilotPlugin handles FDM over UDP/JSON"; echo "Bridge idle - press Ctrl-C to exit window"; exec bash'
	tmux new-window -t mira-gz:2 -n gazebo 'bash -c "docker compose up --no-recreate -d $(GZ_SERVICE) && docker compose exec $(GZ_SERVICE) gz sim $(GZ_ARGS) bluerov2_heavy_underwater.world; exec bash"'
	tmux select-window -t mira-gz:0
	@if [ -n "$$TMUX" ]; then tmux switch-client -t mira-gz; else tmux attach -t mira-gz; fi

bringup-tacc: check-tmux $(XAUTH)
	@if tmux has-session -t mira-tacc 2>/dev/null; then \
		echo "⚠️  tmux session mira-tacc already exists. Attach: tmux attach -t mira-tacc | Kill: tmux kill-session -t mira-tacc"; exit 1; fi
	@echo "🚀 Bringup TACC - tmux session mira-tacc [$(GZ_SERVICE)]"
	tmux new-session -d -s mira-tacc -n sitl 'docker compose up --no-recreate ardupilot-sitl; exec bash'
	tmux new-window -t mira-tacc:1 -n bridge 'echo "No bridge required for TACC - ArduPilotPlugin handles FDM"; echo "Bridge idle"; exec bash'
	tmux new-window -t mira-tacc:2 -n gazebo 'bash -c "docker compose up --no-recreate -d $(GZ_SERVICE) && docker compose exec $(GZ_SERVICE) gz sim $(GZ_ARGS) /workspace/worlds/tacc.world; exec bash"'
	tmux select-window -t mira-tacc:0
	@if [ -n "$$TMUX" ]; then tmux switch-client -t mira-tacc; else tmux attach -t mira-tacc; fi

bringup-sauvc: check-tmux $(XAUTH)
	@if tmux has-session -t mira-sauvc 2>/dev/null; then \
		echo "⚠️  tmux session mira-sauvc already exists. Attach: tmux attach -t mira-sauvc | Kill: tmux kill-session -t mira-sauvc"; exit 1; fi
	@echo "🚀 Bringup SAUVC - tmux session mira-sauvc [$(GZ_SERVICE)]"
	tmux new-session -d -s mira-sauvc -n sitl 'docker compose up --no-recreate ardupilot-sitl; exec bash'
	tmux new-window -t mira-sauvc:1 -n bridge 'bash -c "echo Waiting for Gazebo to be ready...; sleep 5; source /opt/ros/jazzy/setup.bash && source install/setup.bash 2>/dev/null || source /opt/ros/jazzy/setup.bash; ros2 run ros_gz_bridge parameter_bridge /cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist /realsense/image@sensor_msgs/msg/Image@gz.msgs.Image /realsense/depth_image@sensor_msgs/msg/Image@gz.msgs.Image /realsense/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked /realsense/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo /bottom_cam@sensor_msgs/msg/Image@gz.msgs.Image /side_cam@sensor_msgs/msg/Image@gz.msgs.Image /world/pool_world/create@ros_gz_interfaces/srv/SpawnEntity --ros-args -r __ns:=/sauvc_bridge; exec bash"'
	tmux new-window -t mira-sauvc:2 -n gazebo 'bash -c "docker compose up --no-recreate -d $(GZ_SERVICE) && docker compose exec $(GZ_SERVICE) gz sim $(GZ_ARGS) /workspace/sauvc_sim/worlds/sauvc25.world; exec bash"'
	tmux select-window -t mira-sauvc:0
	@if [ -n "$$TMUX" ]; then tmux switch-client -t mira-sauvc; else tmux attach -t mira-sauvc; fi


changed:
	@packages=$$( \
		git diff --name-only | \
		while read f; do \
			dir=$$(dirname "$$f"); \
			for i in 0 1 2 3; do \
				cand="$$dir"; \
				for j in $$(seq 1 $$i); do \
					cand=$$(dirname "$$cand"); \
				done; \
				if [ -f "$$cand/package.xml" ]; then \
					cd "$$cand" && pwd; \
					break; \
				fi; \
			done; \
		done | sort -u \
	); \
	echo "Packages to build:"; \
	echo "$$packages"

build-docker-container:
	$(info Building Docker container...)
	@docker build -t mira .

UID := $(shell id -u)
GID := $(shell id -g)
build-in-docker:
	$(info Building workspace inside Docker...)
	@docker run \
		--rm \
		-v $(PWD):/workspace \
		-u $(UID):$(GID) \
		-w /workspace mira \
		bash -c "make repoversion && \
		make clean && \
		source /opt/ros/jazzy/setup.bash && \
		source .venv/bin/activate && \
		colcon build ${COLCON_ARGS}"

docker:
	docker run -it --rm \
		-v $(PWD):/workspace \
		-u $(UID):$(GID) \
		-w /workspace mira \
		bash

b: check-ros
	@source /opt/ros/jazzy/setup.bash && \
	source .venv/bin/activate && \
	colcon build ${COLCON_ARGS} --packages-select ${P}

# Install dependencies
install-deps: check-ros check-uv
	$(info Installing Python dependencies...)
	@uv sync
	$(info Installing ROS dependencies...)
	@source /opt/ros/jazzy/setup.bash && \
	rosdep install --from-paths src --ignore-src -r -y

PYTHON_VERSION ?= python3.12
install-mavproxy: check-uv
	$(info Installing mavproxy)
	@uv tool install mavproxy
	
	$(info Applying patch for mavproxy)
	@patch /home/$(USER)/.local/share/uv/tools/mavproxy/lib/$(PYTHON_VERSION)/site-packages/MAVProxy/modules/lib/rline.py < ./misc/patches/mavproxy_rline_fix.patch

proxy-pixhawk:
ifndef LAPTOP_IP
	$(error No LAPTOP_IP set, please set it to your laptop's IP and call the command like this: make proxy-pixhawk LAPTOP_IP=192.168.2.XX)
endif
ifndef MAVPROXY_EXISTS
	$(error ❌ mavproxy not found in PATH. Install with 'make install-mavproxy' or run 'uv tool install mavproxy'.)
endif
	@uv run mavproxy.py --master=/dev/Pixhawk --baudrate 57600 --out udp:$(LAPTOP_IP):14550


# Get submodules
get-submodules:
	$(info Updating git submodules...)
	@git submodule update --init --recursive

# Get latest from remote
force-update:
	$(info Fetching latest changes from remote...)
	@git fetch origin
	@git reset --hard origin/$$(git rev-parse --abbrev-ref HEAD)

# Install udev rules
install-udev:
	$(info Installing udev rules...)
	@sudo cp misc/udev/96-mira.rules /etc/udev/rules.d/
	@sudo udevadm control --reload-rules
	@sudo udevadm trigger

# Fix VSCode settings paths
fix-vscode:
	$(info Fixing VSCode settings paths...)
	@current_dir=$$(realpath .); \
	settings_file=".vscode/settings.json"; \
	if [ -f "$$settings_file" ]; then \
		sed -i "s|/home/david/mira|$$current_dir|g" "$$settings_file"; \
		echo "✅ Updated paths in $$settings_file"; \
	else \
		echo "⚠️  settings.json not found in .vscode directory."; \
	fi

validate-all:
	find ./src -type f -name "package.xml" -exec uv run ./util/package-utils/validate_package.py {} \;

GSTREAMER_FIX=export LD_PRELOAD=$(shell gcc -print-file-name=libunwind.so.8)

camera_2:
	${WS} && \
	${GSTREAMER_FIX} && \
	ros2 launch mira2_perception camera_2.launch

camera_1:
	${WS} && \
	${GSTREAMER_FIX} && \
	ros2 launch mira2_perception camera_1.launch

PIXHAWK_PORT ?= /dev/Pixhawk
alt_master: check-ros
	${WS} && \
	ros2 launch mira2_control_master alt_master.launch pixhawk_address:=${PIXHAWK_PORT}

alt_master_sitl:
	$(info "Assuming Ardupilot SITL to running on same IP as THIS device with port 5760")
	make alt_master PIXHAWK_PORT=tcp:127.0.0.1:5760

teleop: check-ros
	${WS} && ros2 launch mira2_rov teleop.launch

# Dashboard applications
dashboard: check-ros
	${WS} && ros2 run mira2_dashboard mira2_dashboard_exe

telemetry-viz: check-ros
	${WS} && ros2 run mira2_dashboard telemetry_viz

# Development setup
setup: check-ros install-deps submodules build install-udev fix-vscode
	$(info 🚀 Complete workspace setup finished!)

# Clean build artifacts
clean:
	$(info Cleaning build artifacts...)
	@rm -rf build/ install/ log/
	$(info Clean completed.)

# Help target
help:
	$(info Available targets:)
	$(info   build         - Build the ROS workspace)
	$(info   source        - Source the workspace environment)
	$(info   install-deps  - Install ROS dependencies with rosdep)
	$(info   submodules    - Update git submodules)
	$(info   proxy-pixhawk - Download and run mavp2p for Pixhawk telemetry proxying)
	$(info                  Use DEVPATH=/dev/ttyACM0 to specify device path if needed)
	$(info   update        - Get latest changes from remote)
	$(info   install-udev  - Install udev rules)
	$(info   b 		   - Build specific package (set P=package_name))
	$(info   bs            - Build and source workspace)
	$(info   fix-vscode    - Fix VSCode settings paths)
	$(info   setup         - Complete workspace setup)
	$(info   clean         - Clean build artifacts)
	$(info )
	$(info ROS Launch targets:)
	$(info   master        - Launch master control)
	$(info   alt_master    - Launch alternative master control)
	$(info   teleop        - Launch teleoperation)
	$(info )
	$(info Simulator targets (Dockerized, no host ROS needed):)
	$(info   sitl              - Run ArduSub SITL)
	$(info   simulator-gz      - Run Gazebo with the base BlueROV2 Heavy world)
	$(info   simulator-tacc-gz - Run Gazebo with the TACC pipeline world)
	$(info   simulator-sauvc-gz - Run Gazebo with the SAUVC world)
	$(info   bringup-gz        - tmux 3-window bringup (sitl, bridge idle, gazebo bluerov2_heavy))
	$(info   bringup-tacc      - tmux 3-window bringup (sitl, bridge idle, gazebo tacc.world))
	$(info   bringup-sauvc     - tmux 3-window bringup (sitl, bridge ros_gz_bridge, gazebo sauvc25.world))
	$(info     Attach: tmux attach -t mira-<comp>  Detach: Ctrl-b d  Kill: tmux kill-session -t mira-<comp>)
	$(info )
	$(info Dashboard applications:)
	$(info   dashboard     - Launch main dashboard)
	$(info   telemetry-viz - Launch telemetry visualization)
	$(info )
	$(info   help          - Show this help message)

