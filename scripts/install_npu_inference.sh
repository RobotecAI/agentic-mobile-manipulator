#!/usr/bin/env bash
# Install AMD Ryzen AI NPU drivers + FastFlowLM for NPU inference.
# Idempotent — skips drivers/packages that are already installed.

set -euo pipefail

FFLM_REPO="${FFLM_REPO:-https://github.com/RobotecAI/FastFlowLM.git}"
PROJECT_ROOT="${PIXI_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
FFLM_SRC="${FFLM_SRC:-$PROJECT_ROOT/inference/FastFlowLM}"

SUDO=""
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    SUDO="sudo"
fi

REBOOT_NEEDED=0

# ── Step 1: NPU drivers (libxrt-npu2, amdxdna-dkms) ─────────────────────────
if dpkg -s libxrt-npu2 amdxdna-dkms >/dev/null 2>&1; then
    echo "NPU drivers already installed, skipping."
else
    $SUDO add-apt-repository -y ppa:lemonade-team/stable
    $SUDO apt update
    $SUDO apt install -y libxrt-npu2 amdxdna-dkms
    REBOOT_NEEDED=1
    echo ">>> NPU drivers installed. A REBOOT is required before they take effect."
fi

# ── Step 2: FastFlowLM (build from source) ──────────────────────────────────
if command -v flm >/dev/null 2>&1; then
    echo "flm already installed, skipping build."
else
    $SUDO apt install -y ninja-build \
        libavformat-dev libavutil-dev libavcodec-dev libswresample-dev \
        libswscale-dev libxrt-dev uuid-dev libdrm-dev

    if [[ ! -d "$FFLM_SRC/.git" ]]; then
        git clone --recursive "$FFLM_REPO" "$FFLM_SRC"
    fi

    cd "$FFLM_SRC/src"
    cmake --preset linux-default
    cd build
    cmake --build . -j"$(nproc)"
    $SUDO cmake --install .
    cd "$PROJECT_ROOT"
fi

# ── Step 3: memlock limit ───────────────────────────────────────────────────
# NPU inference needs unlimited locked memory.
memlock="$(ulimit -l)"
if [[ "$memlock" != "unlimited" ]]; then
    limits="/etc/security/limits.conf"
    if ! grep -qE '^\*[[:space:]]+(soft|hard)[[:space:]]+memlock[[:space:]]+unlimited' "$limits"; then
        echo "*    soft    memlock    unlimited" | $SUDO tee -a "$limits" >/dev/null
        echo "*    hard    memlock    unlimited" | $SUDO tee -a "$limits" >/dev/null
        echo ">>> Added memlock=unlimited to $limits."
    fi
    REBOOT_NEEDED=1
    echo ">>> memlock limit is '$memlock' (need 'unlimited'). A REBOOT is required."
fi

if [[ "$REBOOT_NEEDED" -eq 1 ]]; then
    echo
    echo "============================================================"
    echo " Setup incomplete: please REBOOT, then re-run to verify."
    echo "============================================================"
    exit 0
fi

# ── Step 4: validate (only meaningful once drivers are active) ───────────────
# Diagnostics only — don't abort if no NPU device is present yet.
# Capture output; only show it on failure, otherwise a clean status line.
xrt_out="$(xrt-smi examine 2>&1)"; xrt_rc=$?
flm_out="$(flm validate 2>&1)"; flm_rc=$?

if [[ "$xrt_rc" -eq 0 && "$flm_rc" -eq 0 ]]; then
    printf '\033[32m✓ NPU visible & ready\033[0m\n'
    printf '\033[32m✓ FLM ready\033[0m\n'
else
    echo "$xrt_out"
    echo "$flm_out"
    cat <<'EOF'

============================================================
 No NPU device found. Troubleshooting:

 1. Is the amdxdna kernel module loaded?
      lsmod | grep amdxdna
    If not:  sudo modprobe amdxdna
    Persist: echo amdxdna | sudo tee /etc/modules-load.d/amdxdna.conf

 2. Does xrt-smi see the device? (look for RyzenAI-npu under
    "Device(s) Present" in the output above)
      xrt-smi examine

 More:
   https://github.com/FastFlowLM/FastFlowLM/blob/main/docs/linux-getting-started.md
   https://lemonade-server.ai/flm_npu_linux.html
============================================================
EOF
fi
