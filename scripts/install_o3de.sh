#!/usr/bin/env bash
# Download the O3DE SDK .deb and unpack it into a per-user directory (no root,
# no apt: the pixi env provides the system libraries the .deb declares).
# Skips everything when the engine is present.
#
# Overrides: O3DE_HOME (install root), O3DE_DEB_FILE (use a local .deb instead
# of downloading).

set -euo pipefail

O3DE_VERSION="${O3DE_VERSION:-26.05}"
O3DE_DEB_URL="${O3DE_DEB_URL:-https://o3debinaries.org/main/Latest/Linux/o3de_2605_0.deb}"
O3DE_HOME="${O3DE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/o3de}"
O3DE_ENGINE="$O3DE_HOME/$O3DE_VERSION"

if [[ -f "$O3DE_ENGINE/engine.json" ]]; then
    echo "O3DE SDK already installed at $O3DE_ENGINE."
else
    mkdir -p "$O3DE_HOME"
    staging=$(mktemp -d "$O3DE_HOME/.install-$O3DE_VERSION.XXXXXX")
    trap 'rm -rf "$staging"' EXIT

    deb="${O3DE_DEB_FILE:-}"
    if [[ -z "$deb" ]]; then
        deb="$staging/o3de.deb"
        echo "Downloading O3DE SDK (~3 GB) from: $O3DE_DEB_URL"
        curl -fSL --progress-bar -o "$deb" "$O3DE_DEB_URL"
    fi

    # Unpack the payload only. The package's maintainer scripts add desktop
    # integration (/usr/local/bin links, a .desktop file) the project never uses.
    echo "Unpacking O3DE SDK into $O3DE_ENGINE (~9 GB)..."
    if command -v dpkg-deb >/dev/null; then
        dpkg-deb -x "$deb" "$staging/root"
    else
        mkdir -p "$staging/root"
        ar p "$deb" data.tar.gz | tar -xz -C "$staging/root"
    fi
    mv "$staging/root/opt/O3DE/$O3DE_VERSION" "$O3DE_ENGINE"
fi

[[ -f "$O3DE_ENGINE/engine.json" ]] || { echo "ERROR: no engine.json in $O3DE_ENGINE." >&2; exit 1; }

# CMake configure runs O3DE's bundled Python; bootstrap it once.
if "$O3DE_ENGINE/python/python.sh" --version &>/dev/null; then
    echo "O3DE Python already bootstrapped."
else
    echo "Bootstrapping O3DE Python..."
    "$O3DE_ENGINE/python/get_python.sh"
fi

echo "O3DE SDK ready: $O3DE_ENGINE"
