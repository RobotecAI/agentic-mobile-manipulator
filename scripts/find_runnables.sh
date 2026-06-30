#!/usr/bin/env bash
# Check the demo's built runnables and print OK/ERROR per component. Found via
# the build trees (robust to the build-config dir). Runs at the end of `single-pc`
# setup. Informational — never fails setup (FastFlowLM is a separate NPU step).
set -uo pipefail
ROOT="${DEMO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
green='\033[0;32m'; red='\033[0;31m'; reset='\033[0m'

check() {  # label  search-root  filename-glob
    if find "$ROOT/$2" -type f -executable -name "$3" 2>/dev/null | grep -q .; then
        printf "  %-13s [${green}OK${reset}]\n" "$1"
    else
        printf "  %-13s [${red}ERROR${reset}]\n" "$1"
    fi
}

echo "Checking for built runnables:"
check "llama.cpp"    "inference/llama.cpp/build"      "llama-server"
check "FastFlowLM"   "inference/FastFlowLM/src/build" "flm"
check "GameLauncher" "sim/build"                      "*.GameLauncher"
