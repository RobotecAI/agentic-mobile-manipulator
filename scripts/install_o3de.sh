#!/usr/bin/env bash

# O3DE SDK .deb download URL. Override with the O3DE_DEB_URL env var.
O3DE_DEB_URL="${O3DE_DEB_URL:-https://o3debinaries.org/main/Latest/Linux/o3de_2605_0.deb}"
O3DE_REQUIRED_VERSION="26.05"

# ── Step 1: Install the .deb package ────────────────────────────────────────

# Check whether the required version is already installed. There may be
# multiple versions under /opt/O3DE/; only a directory whose name contains
# the required version string (e.g. "26.05") satisfies the check.
if ls -d /opt/O3DE/*/ &>/dev/null && \
       ls -d /opt/O3DE/*/ | grep -q "$O3DE_REQUIRED_VERSION"; then
    echo "O3DE SDK $O3DE_REQUIRED_VERSION already installed: $(ls -d /opt/O3DE/*/ | grep "$O3DE_REQUIRED_VERSION")"
else
    if ls -d /opt/O3DE/*/ &>/dev/null; then
        echo "O3DE SDK found but version $O3DE_REQUIRED_VERSION is required. Installed: $(ls -d /opt/O3DE/*/)"
    fi
    echo "Downloading O3DE SDK from: $O3DE_DEB_URL"
    TMP_DEB=$(mktemp --suffix=.deb)
    trap 'rm -f "$TMP_DEB"' EXIT

    curl -fsSL -o "$TMP_DEB" "$O3DE_DEB_URL"
    chmod 644 "$TMP_DEB"

    echo "Installing O3DE SDK (requires sudo)..."
    sudo apt-get install -y "$TMP_DEB"

    echo "O3DE SDK installed: $(ls -d /opt/O3DE/*/)"
fi

O3DE_ENGINE=$(ls -d /opt/O3DE/*/ | grep "$O3DE_REQUIRED_VERSION" | head -1 | sed 's:/$::')

# ── Step 2: Bootstrap O3DE's bundled Python ─────────────────────────────────
# The .deb does not ship Python; get_python.sh downloads it and creates a
# venv. Needed before o3de.sh (which is a Python wrapper) can run.

if [[ -d "$HOME/.o3de/Python/packages" ]]; then
    echo "O3DE Python already bootstrapped."
else
    echo "Bootstrapping O3DE Python..."
    "$O3DE_ENGINE/python/get_python.sh"
fi

# ── Step 3: Register the engine ─────────────────────────────────────────────
# Makes the SDK discoverable by cmake and o3de.sh project commands.

if grep -q "$O3DE_ENGINE" ~/.o3de/o3de_manifest.json 2>/dev/null; then
    echo "O3DE engine already registered."
else
    echo "Registering O3DE engine..."
    "$O3DE_ENGINE/scripts/o3de.sh" register --this-engine
fi

echo "O3DE SDK ready: $O3DE_ENGINE"
