#!/usr/bin/env bash
# Build and install FastFlowLM from source (per docs/linux-getting-started.md).
#
# NPU HOST ONLY. The build needs the XRT/NPU dev headers and `flm serve`/`flm run`
# need the amdxdna driver + NPU firmware at runtime. On a machine without an NPU,
# checking out the submodule (`pixi run init-submodules`) is all that will succeed.
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
    echo "error: $SRC not found — run 'pixi run init-submodules' first." >&2
    exit 1
fi

cd "$SRC"

# Build flm with the SYSTEM compiler, not pixi's conda toolchain. flm is a
# standalone binary (run directly, never linked into the RoboStack) that links
# the host's XRT + NPU libs built against the system glibc; the conda compiler's
# older glibc sysroot can't link them (undefined __libc_csu_init/fini at link).
# System gcc also finds the apt-installed XRT headers under /usr natively, so no
# XRT path overrides are needed. Override FLM_CC/FLM_CXX for a different compiler.
FLM_CC="${FLM_CC:-/usr/bin/gcc}"
FLM_CXX="${FLM_CXX:-/usr/bin/g++}"
[ -f /usr/include/xrt/xrt_bo.h ] || { echo "error: XRT dev headers missing — install libxrt-dev." >&2; exit 1; }

# Switching toolchains invalidates the CMake cache, so configure fresh.
rm -rf build
echo "Configuring (cmake --preset linux-default, system $FLM_CXX) ..."
cmake --preset linux-default -DCMAKE_C_COMPILER="$FLM_CC" -DCMAKE_CXX_COMPILER="$FLM_CXX"
echo "Building (-j$(nproc)) ..."
cmake --build build -j"$(nproc)"

# flm looks next to its executable for model_list.json (the model registry, used
# by `flm serve` and `flm pull`) and for xclbins/ (the per-model NPU kernels).
# We run the build-tree binary, so put both beside it: copy the small registry,
# symlink the large shipped xclbins dir rather than duplicating it.
cp model_list.json build/model_list.json
ln -sfn ../xclbins build/xclbins

# Build-only — deliberately NO `sudo cmake --install`. The dispatcher runs the
# repo binary directly (inference/FastFlowLM/src/build/flm), so a system-wide
# install (which would clobber an existing /usr/local/bin/flm) is never needed.
echo "FastFlowLM built at: $SRC/build/flm"
echo "Verify the NPU with: $SRC/build/flm validate"
