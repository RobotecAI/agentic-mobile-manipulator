#!/usr/bin/env bash
# Build and install FastFlowLM from source (per docs/linux-getting-started.md).
#
# NPU HOST ONLY. The build needs the XRT/NPU dev headers and `flm serve`/`flm run`
# need the amdxdna driver + NPU firmware at runtime. On a machine without an NPU,
# checking out the submodule (`pixi run submodules`) is all that will succeed.
#
# System prerequisites (Ubuntu, one-time, requires sudo + reboot):
#   sudo add-apt-repository ppa:lemonade-team/stable
#   sudo apt update
#   sudo apt install ninja-build libavformat-dev libavutil-dev libavcodec-dev \
#       libswresample-dev libswscale-dev libxrt-dev uuid-dev libdrm-dev \
#       libxrt-npu2 amdxdna-dkms
#   sudo reboot
set -euo pipefail

SRC="${DEMO_ROOT:-$(pwd)}/inference/FastFlowLM/src"
if [ ! -d "$SRC" ]; then
    echo "error: $SRC not found — run 'pixi run submodules' first." >&2
    exit 1
fi

cd "$SRC"
echo "Configuring (cmake --preset linux-default) ..."
cmake --preset linux-default
echo "Building (-j$(nproc)) ..."
cmake --build build -j"$(nproc)"
echo "Installing (requires sudo) ..."
sudo cmake --install build

echo "FastFlowLM installed. Verify the NPU with: flm validate"
