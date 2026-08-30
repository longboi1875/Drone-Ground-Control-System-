#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_DIR="${SKYLINK_PX4_DIR:-$(dirname "$ROOT_DIR")/SkyLink-PX4/PX4-Autopilot}"

if [[ ! -d "$PX4_DIR" ]]; then
  echo "PX4 is not installed. Run: ./scripts/setup_px4.sh" >&2
  exit 1
fi

cd "$PX4_DIR"
export PX4_HOME_LAT=49.2606
export PX4_HOME_LON=-123.2460
export PX4_HOME_ALT=70
export GZ_IP="${GZ_IP:-127.0.0.1}"
export PATH="$PX4_DIR/.venv/bin:$PATH"
export CMAKE_PREFIX_PATH="$(brew --prefix qt@5):${CMAKE_PREFIX_PATH:-}"
export LIBRARY_PATH="$(brew --prefix gstreamer)/lib:$(brew --prefix glib)/lib:$(brew --prefix gettext)/lib:${LIBRARY_PATH:-}"
export DYLD_LIBRARY_PATH="$(brew --prefix gstreamer)/lib:$(brew --prefix glib)/lib:$(brew --prefix gettext)/lib:${DYLD_LIBRARY_PATH:-}"
export CXXFLAGS="${CXXFLAGS:-} -Wno-error=double-promotion -Wno-error=deprecated-declarations -Wno-error=unused-private-field"
ln -sf libOpticalFlow.dylib \
  "$PX4_DIR/build/px4_sitl_default/OpticalFlow/install/lib/libOpticalFlow.so"
ln -sf "$PX4_DIR/build/px4_sitl_default/OpticalFlow/install/lib/libOpticalFlow.dylib" \
  "$PX4_DIR/build/px4_sitl_default/external/Install/lib/libOpticalFlow.dylib"

if [[ "${HEADLESS:-}" == "1" ]]; then
  # Gazebo's rendering plugins require a window server on macOS. Start a
  # physics-only server and let PX4 attach to it in standalone mode.
  export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:-}"
  export GZ_SIM_SYSTEM_PLUGIN_PATH="${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
  export GZ_SIM_SERVER_CONFIG_PATH="${GZ_SIM_SERVER_CONFIG_PATH:-}"
  source "$PX4_DIR/build/px4_sitl_default/rootfs/gz_env.sh"
  export GZ_SIM_SERVER_CONFIG_PATH="$ROOT_DIR/scripts/px4-server-headless.config"
  export PX4_GZ_STANDALONE=1
  export PX4_GZ_WORLD=default
  gz sim --verbose="${GZ_VERBOSE:-1}" -r -s "$PX4_GZ_WORLDS/default.sdf" &
  GZ_SERVER_PID=$!
  trap 'kill "$GZ_SERVER_PID" 2>/dev/null || true' EXIT INT TERM
fi

make px4_sitl gz_x500
