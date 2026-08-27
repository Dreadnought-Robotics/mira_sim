#!/usr/bin/env bash
# Generates /tmp/.docker.xauth so Gazebo's GUI can connect to the host X server
# from inside the mira_sim container (rootless, network_mode:host, X11 passthrough).
# Pattern from src/bluerov2_gz/docker/run.sh with hardening for Wayland/XWayland.
set -e

XAUTH=/tmp/.docker.xauth

# Always (re)generate when DISPLAY is set - stale cookies after VT switch /
# display-manager restart cause "Invalid MIT-MAGIC-COOKIE-1". Remove stale file first.
if [ -n "${DISPLAY:-}" ] && command -v xauth >/dev/null 2>&1; then
  rm -f "$XAUTH"
  # ffff fix converts the FamilyLocal (0x0100) to FamilyWild (0xffff) so the
  # cookie is accepted inside the container's network namespace (harmless with host mode).
  if xauth_list=$(xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/'); then
    if [ -n "$xauth_list" ]; then
      echo "$xauth_list" | xauth -f "$XAUTH" nmerge - 2>/dev/null || true
    fi
  fi
  # nlist can return empty on Wayland/XWayland with no cookie - fallback to xhost
  if [ ! -s "$XAUTH" ]; then
    touch "$XAUTH"
    # Allow local docker containers to connect without a cookie (least-privilege,
    # only if xhost is available and we couldn't extract a cookie).
    if command -v xhost >/dev/null 2>&1; then
      xhost +local:docker >/dev/null 2>&1 || xhost +local: >/dev/null 2>&1 || true
    fi
  fi
  chmod a+r "$XAUTH" 2>/dev/null || true
else
  # No DISPLAY (headless / pure Wayland) or no xauth - create empty file with
  # permissive xhost so Gazebo can still try software rendering without X.
  if [ -z "${DISPLAY:-}" ]; then
    echo "[x11-setup] WARNING: DISPLAY is empty (headless/Wayland?). Gazebo GUI will not show." >&2
  fi
  touch "$XAUTH"
  chmod a+r "$XAUTH" 2>/dev/null || true
  if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
  fi
fi
