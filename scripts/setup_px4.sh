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

# PX4 v1.17's macOS helper still points at Homebrew meta-formulae that became
# no-ops in 2026. Install the simulator dependencies explicitly so this pinned
# release remains reproducible.
brew tap PX4/px4
brew tap osrf/simulation
if brew trust --help >/dev/null 2>&1; then
  brew trust PX4/px4
  brew trust osrf/simulation
fi
brew install \
  astyle ccache cmake fastdds flock genromfs kconfig-frontends ncurses ninja \
  exiftool glog graphviz gstreamer opencv@4 osrf/simulation/gz-harmonic protobuf

if ! brew list --cask xquartz >/dev/null 2>&1; then
  brew install --cask xquartz
fi

if [[ ! -x "$PX4_DIR/.venv/bin/python" ]]; then
  python3.12 -m venv "$PX4_DIR/.venv"
fi
"$PX4_DIR/.venv/bin/pip" install future
"$PX4_DIR/.venv/bin/pip" install -r "$PX4_DIR/Tools/setup/requirements.txt"

PATH="$PX4_DIR/.venv/bin:$PATH" make px4_sitl_default

echo "PX4 $PX4_VERSION is ready at $PX4_DIR"
