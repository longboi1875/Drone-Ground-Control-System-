#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

check() {
  local label="$1"
  local command_name="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf "[ok]      %-12s %s\n" "$label" "$(command -v "$command_name")"
  else
    printf "[missing] %-12s %s\n" "$label" "$command_name"
  fi
}

check "Node 22+" node
check "npm" npm
check "Python 3.12" python3.12
check "Git" git
check "CMake" cmake
check "Gazebo" gz

PX4_DIR="${SKYLINK_PX4_DIR:-$(dirname "$ROOT_DIR")/SkyLink-PX4/PX4-Autopilot}"
if [[ -x "$PX4_DIR/build/px4_sitl_default/bin/px4" ]]; then
  printf "[ok]      %-12s %s\n" "PX4 SITL" "$PX4_DIR"
else
  printf "[missing] %-12s run scripts/setup_px4.sh\n" "PX4 SITL"
fi
