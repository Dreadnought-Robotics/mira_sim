.PHONY: master alt_master build source install-deps submodules update install-udev bs fix-vscode dashboard telemetry-viz

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
ifeq ($(PYTHON3_PATH),)
	$(error ❌ python3 not found in PATH)
endif

ifeq ($(PYTHON312_PATH),)
	$(error ❌ python3.12 not found in PATH)
endif

ifneq ($(PYTHON3_PATH),/usr/bin/python3)
	$(error ❌ python3 resolves to $(PYTHON3_PATH). Expected /usr/bin/python3 (not ~/.local/bin))
endif

ifneq ($(PYTHON312_PATH),/usr/bin/python3.12)
	$(error ❌ python3.12 resolves to $(PYTHON312_PATH). Expected /usr/bin/python3.12 (not ~/.local/bin))
endif

$(info ✅ python3     → $(PYTHON3_PATH))
$(info ✅ python3.12  → $(PYTHON312_PATH))


check-ros: check-uv
ifndef ROS_JAZZY_EXISTS
	$(error ❌ ROS Jazzy not found at /opt/ros/jazzy. Only ROS Jazzy is supported by this workspace.)
endif
	$(info ✅ ROS Jazzy found.)

# Build the workspace

# Detect ninja and lld; use if available, fallback gracefully.
# In CI (GITHUB_ACTIONS=true) we require them for speed/reproducibility.
NINJA_EXISTS := $(shell command -v ninja 2>/dev/null)
LLD_EXISTS := $(shell command -v lld 2>/dev/null || command -v ld.lld 2>/dev/null)

# Ninja generator (optional) - only if installed, else fallback to Unix Makefiles
# No hard requirement in CI or locally; just print status (per user: don't install unnecessary stuff)
ifdef NINJA_EXISTS
  NINJA_FLAG := -GNinja
  $(info ✅ Ninja found at $(NINJA_EXISTS) - using -GNinja)
else
  NINJA_FLAG :=
  $(info ⚠️  Ninja not found - using default Unix Makefiles generator (install ninja-build for faster builds if desired))
endif

# lld/mold linker (optional, faster) - only if installed
ifdef LLD_EXISTS
  LINKER := lld
  LLD_FLAGS := -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=$(LINKER) -DCMAKE_MODULE_LINKER_FLAGS=-fuse-ld=$(LINKER) -DCMAKE_SHARED_LINKER_FLAGS=-fuse-ld=$(LINKER)
  $(info ✅ lld found at $(LLD_EXISTS) - using -fuse-ld=lld)
else
  LLD_FLAGS :=
  $(info ⚠️  lld not found - using default linker (install lld/mold for faster links if desired))
endif

# Alternatively you can use mold which is a bit faster (set LINKER=mold if installed)
CMAKE_ARGS:= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
			 -DCMAKE_COLOR_DIAGNOSTICS=ON \
			 $(NINJA_FLAG) \
			 $(LLD_FLAGS) \
			 --no-warn-unused-cli

SKIP_PACKAGES ?= vision_boundingbox vision_depth
COLCON_ARGS:= --cmake-args $(CMAKE_ARGS) \
                           --parallel-workers $(shell nproc) \
			  --packages-skip $(SKIP_PACKAGES) \
			  --event-handlers console_cohesion+ \
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

# Perf profiles: auto (detect GPU/CPU), nogpu (software), low, medium, high
# Usage: make simulator-sauvc PROFILE=high  or  STONEFISH_PROFILE=nogpu make simulator-tac
# Auto-detect mirrors Gazebo entrypoint (nvidia-smi / /dev/dri) + python perf_profiles.py
PROFILE ?= auto
export STONEFISH_PROFILE ?= $(PROFILE)

simulator-sauvc:
	${WS} && \
	ros2 launch dnt_simulator sauvc.launch.py profile:=$(PROFILE)

simulator-tac:
	${WS} && \
	ros2 launch dnt_simulator tac.launch.py profile:=$(PROFILE)

simulator-tac-docking:
	${WS} && \
	ros2 launch dnt_simulator tac_docking.launch.py profile:=$(PROFILE)

simulator-tank:
	${WS} && \
	ros2 launch dnt_simulator bluerov2_sim.py profile:=$(PROFILE)
simulator-tac-pipeline:
	${WS} && \
	ros2 launch dnt_simulator tac_pipeline.launch.py profile:=$(PROFILE)

# Convenience aliases for each profile (e.g. make simulator-sauvc-low)
simulator-sauvc-nogpu: ; $(MAKE) simulator-sauvc PROFILE=nogpu
simulator-sauvc-low: ; $(MAKE) simulator-sauvc PROFILE=low
simulator-sauvc-medium: ; $(MAKE) simulator-sauvc PROFILE=medium
simulator-sauvc-high: ; $(MAKE) simulator-sauvc PROFILE=high
simulator-tac-nogpu: ; $(MAKE) simulator-tac PROFILE=nogpu
simulator-tac-low: ; $(MAKE) simulator-tac PROFILE=low
simulator-tac-medium: ; $(MAKE) simulator-tac PROFILE=medium
simulator-tac-high: ; $(MAKE) simulator-tac PROFILE=high
simulator-tank-nogpu: ; $(MAKE) simulator-tank PROFILE=nogpu
simulator-tank-low: ; $(MAKE) simulator-tank PROFILE=low
simulator-tank-medium: ; $(MAKE) simulator-tank PROFILE=medium
simulator-tank-high: ; $(MAKE) simulator-tank PROFILE=high

# Show detected profile
detect-profile:
	@python3 -c "import sys; sys.path.insert(0,'src/dnt_simulator'); from dnt_simulator.perf_profiles import detect_profile, PROFILES; p=detect_profile(); print(f'Detected profile: {p}'); print(PROFILES[p])" 2>/dev/null || echo "Run 'make build' first or check python path"
	@echo "Override: make simulator-sauvc PROFILE=high  |  STONEFISH_PROFILE=nogpu make simulator-tac"

sitl:
	${WS} && \
	docker-compose up ardupilot-sitl


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
	$(info   build         - Build the ROS workspace (auto-detects ninja/lld, falls back if missing))
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
	$(info Stonefish perf profiles (auto-detect GPU/CPU, or set PROFILE=):)
	$(info   nogpu         - Software rendering 60Hz 640x480 low (LIBGL_ALWAYS_SOFTWARE))
	$(info   low           - iGPU/low-end 80Hz 800x600 low)
	$(info   medium        - Balanced default 100Hz 960x600 low (auto))
	$(info   high          - Discrete GPU 200Hz 1280x720 high)
	$(info   Usage: make simulator-sauvc PROFILE=high | PROFILE=nogpu make simulator-tac | ros2 launch dnt_simulator sauvc.launch.py profile:=medium)
	$(info   Detect: make detect-profile)
	$(info )
	$(info ROS Launch targets:)
	$(info   master        - Launch master control)
	$(info   alt_master    - Launch alternative master control)
	$(info   teleop        - Launch teleoperation)
	$(info   simulator-sauvc/tac/tank - Launch with PROFILE=$(PROFILE) (default auto))
	$(info )
	$(info Dashboard applications:)
	$(info   dashboard     - Launch main dashboard)
	$(info   telemetry-viz - Launch telemetry visualization)
	$(info )
	$(info   help          - Show this help message)

