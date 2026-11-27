#!/usr/bin/env bash
# Remove the O3DE SDK unpacked by install_o3de.sh.
set -euo pipefail
O3DE_VERSION="${O3DE_VERSION:-26.05}"
O3DE_HOME="${O3DE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/o3de}"
rm -rf "${O3DE_HOME:?}/$O3DE_VERSION"
echo "Removed $O3DE_HOME/$O3DE_VERSION"
