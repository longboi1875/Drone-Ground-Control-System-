#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# PX4's nested CMake projects do not quote inherited include paths correctly,
# so keep its checkout in a sibling directory whose path has no spaces.
PX4_DIR="${SKYLINK_PX4_DIR:-$(dirname "$ROOT_DIR")/SkyLink-PX4/PX4-Autopilot}"
PX4_VERSION="${SKYLINK_PX4_VERSION:-v1.17.0}"

mkdir -p "$(dirname "$PX4_DIR")"
if [[ ! -d "$PX4_DIR/.git" ]]; then
  git clone --branch "$PX4_VERSION" --depth 1 \
    https://github.com/PX4/PX4-Autopilot.git "$PX4_DIR"
fi

cd "$PX4_DIR"
git submodule update --init --depth 1 \
  Tools/simulation/gz \
  src/drivers/actuators/vertiq_io/iq-module-communication-cpp \
  src/drivers/cyphal/legacy_data_types \
  src/drivers/cyphal/libcanard \
  src/drivers/cyphal/public_regulated_data_types \
  src/drivers/gps/devices \
  src/drivers/ins/microstrain/mip_sdk \
  src/drivers/uavcan/libdronecan \
  src/lib/cdrstream/cyclonedds \
  src/lib/cdrstream/rosidl \
  src/lib/crypto/libtomcrypt \
  src/lib/crypto/libtommath \
  src/lib/events/libevents \
  src/lib/heatshrink/heatshrink \
  src/modules/uxrce_dds_client/Micro-XRCE-DDS-Client \
  src/modules/zenoh/zenoh-pico
git submodule update --init --force --recursive --depth 1 src/modules/mavlink/mavlink

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

if [[ "${SKYLINK_INSTALL_XQUARTZ:-0}" == "1" ]] && ! brew list --cask xquartz >/dev/null 2>&1; then
  brew install --cask xquartz
elif ! brew list --cask xquartz >/dev/null 2>&1; then
  echo "XQuartz is optional for a visible Gazebo window. Install it later with: brew install --cask xquartz"
fi

if [[ ! -x "$PX4_DIR/.venv/bin/python" ]]; then
  python3.12 -m venv "$PX4_DIR/.venv"
fi
"$PX4_DIR/.venv/bin/pip" install future
"$PX4_DIR/.venv/bin/pip" install -r "$PX4_DIR/Tools/setup/requirements.txt"

# Homebrew's current protobuf/abseil packages require C++17. PX4 main already
# uses it; apply the same compatibility setting to the pinned v1.17 release.
perl -pi -e 's/set\(CMAKE_CXX_STANDARD 14\)/set(CMAKE_CXX_STANDARD 17)/' "$PX4_DIR/CMakeLists.txt"
CMAKE_PREFIX_PATH="$(brew --prefix qt@5):${CMAKE_PREFIX_PATH:-}" \
  LIBRARY_PATH="$(brew --prefix gstreamer)/lib:$(brew --prefix glib)/lib:$(brew --prefix gettext)/lib:${LIBRARY_PATH:-}" \
  PATH="$PX4_DIR/.venv/bin:$PATH" \
  CXXFLAGS="${CXXFLAGS:-} -Wno-error=double-promotion -Wno-error=deprecated-declarations -Wno-error=unused-private-field" \
  make px4_sitl_default

# PX4's OpticalFlow external project names the macOS artifact .dylib, while
# the Gazebo plugin target still looks for the Linux-style .so name.
ln -sf libOpticalFlow.dylib \
  "$PX4_DIR/build/px4_sitl_default/OpticalFlow/install/lib/libOpticalFlow.so"
ln -sf "$PX4_DIR/build/px4_sitl_default/OpticalFlow/install/lib/libOpticalFlow.dylib" \
  "$PX4_DIR/build/px4_sitl_default/external/Install/lib/libOpticalFlow.dylib"

echo "PX4 $PX4_VERSION is ready at $PX4_DIR"
