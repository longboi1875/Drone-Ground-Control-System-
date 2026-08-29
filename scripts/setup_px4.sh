#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_DIR="${SKYLINK_PX4_DIR:-$ROOT_DIR/.local/PX4-Autopilot}"
PX4_VERSION="${SKYLINK_PX4_VERSION:-v1.17.0}"

mkdir -p "$(dirname "$PX4_DIR")"
if [[ ! -d "$PX4_DIR/.git" ]]; then
  git clone --branch "$PX4_VERSION" --depth 1 \
    https://github.com/PX4/PX4-Autopilot.git "$PX4_DIR"
fi

cd "$PX4_DIR"
git submodule update --init --depth 1 \
  Tools/simulation/gz \
  src/lib/events/libevents \
  src/modules/mavlink/mavlink
./Tools/setup/macos.sh --sim-tools
make px4_sitl_default

echo "PX4 $PX4_VERSION is ready at $PX4_DIR"
