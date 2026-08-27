#!/usr/bin/env bash
# Auto-detects GPU availability inside the container and configures Gazebo's
# rendering accordingly, so the same image works on modest/integrated
# hardware (software rendering fallback) and on a real GPU (hardware
# rendering) without any manual flags.
set -e

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  echo "[gazebo-entrypoint] NVIDIA GPU detected via nvidia-smi, using hardware rendering (ogre2)"
  export GZ_RENDER_ENGINE=ogre2
elif [ -e /dev/dri ]; then
  echo "[gazebo-entrypoint] /dev/dri present, using hardware rendering (ogre2)"
  export GZ_RENDER_ENGINE=ogre2
else
  echo "[gazebo-entrypoint] No GPU device found, falling back to software rendering (llvmpipe/ogre)"
  export LIBGL_ALWAYS_SOFTWARE=1
  export GZ_RENDER_ENGINE=ogre
fi

exec "$@"
