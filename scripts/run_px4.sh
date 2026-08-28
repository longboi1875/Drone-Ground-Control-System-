#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_DIR="${SKYLINK_PX4_DIR:-$ROOT_DIR/.local/PX4-Autopilot}"

if [[ ! -d "$PX4_DIR" ]]; then
  echo "PX4 is not installed. Run: ./scripts/setup_px4.sh" >&2
  exit 1
fi

cd "$PX4_DIR"
export PX4_HOME_LAT=49.2606
export PX4_HOME_LON=-123.2460
export PX4_HOME_ALT=70
make px4_sitl gz_x500
