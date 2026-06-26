#!/usr/bin/env bash
# Download and install the O3DE SDK, scoped to this project.
# Idempotent — skips steps that are already done.

set -euo pipefail

O3DE_VERSION="${O3DE_VERSION:-26.05}"
O3DE_DEB_URL="${O3DE_DEB_URL:-https://o3debinaries.org/main/Latest/Linux/o3de_2605_0.deb}"
O3DE_ENGINE="/opt/O3DE/$O3DE_VERSION"

PROJECT_ROOT="${PIXI_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Container builds run as root and ship no sudo binary.
SUDO=""
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    SUDO="sudo"
fi

# ── Step 1: Unpack the .deb into /opt/O3DE/<version> ────────────────────────
# Use dpkg-deb -x (payload only, no apt database entry, no postinst) so the
# install does not create a system package record. SDK binaries use
# $ORIGIN-relative RUNPATHs and run from the install path without further patching.

if [[ -d "$O3DE_ENGINE" ]]; then
    echo "O3DE SDK already installed at $O3DE_ENGINE."
else
    echo "Downloading O3DE SDK from: $O3DE_DEB_URL"
    TMP_DEB=$(mktemp --suffix=.deb)
    TMP_EXTRACT=$(mktemp -d)
    trap 'rm -rf "$TMP_DEB" "$TMP_EXTRACT"' EXIT

    curl -fsSL -o "$TMP_DEB" "$O3DE_DEB_URL"

    echo "Unpacking O3DE SDK into /opt/O3DE..."
    dpkg-deb -x "$TMP_DEB" "$TMP_EXTRACT"

    # Locate the engine root by engine.json rather than trusting the version string.
    src_engine=$(dirname "$(find "$TMP_EXTRACT/opt/O3DE" -maxdepth 2 -name engine.json 2>/dev/null | head -1)")
    if [[ ! -f "$src_engine/engine.json" ]]; then
        echo "ERROR: no engine.json found in the .deb payload under opt/O3DE." >&2
        exit 1
    fi

    $SUDO mkdir -p /opt/O3DE
    $SUDO cp -a "$src_engine" "$O3DE_ENGINE"
    echo "O3DE SDK installed: $O3DE_ENGINE"

    # Install the SDK's declared system dependencies. dpkg-deb -x skips dependency
    # resolution, so install them explicitly from the .deb metadata.
    deps=$(dpkg-deb -f "$TMP_DEB" Depends | tr ',' '\n' | sed 's/([^)]*)//g' | xargs)
    echo "Installing SDK system dependencies: $deps"
    $SUDO apt-get install -y --no-install-recommends $deps
fi

# ── Fix editable-install egg-info dirs ──────────────────────────────────────
# CMake configure runs `pip install -e` against three engine-bundled Python
# packages. setuptools writes a <package>.egg-info/ directory next to the source
# as a side effect. The .deb installs the engine root-owned, so a non-root pip
# either fails to create the dir or can't update its mtime. Making the three
# parent dirs world-writable lets any user create their own egg-info without
# chowning the engine tree (which would break shared machines).
# Remove any root-owned egg-info residue first so setuptools doesn't hit a
# permission error on an existing directory it doesn't own.
# Upstream issue: o3de/o3de#19752.
EDITABLE_DIRS=(
    "$O3DE_ENGINE/Tools/LyTestTools"
    "$O3DE_ENGINE/Tools/RemoteConsole/ly_remote_console"
    "$O3DE_ENGINE/scripts/o3de"
)
for dir in "${EDITABLE_DIRS[@]}"; do
    [[ -d "$dir" ]] || continue
    if [[ -n "$(find "$dir" -maxdepth 1 -type d -name '*.egg-info' -uid 0 2>/dev/null)" ]]; then
        $SUDO find "$dir" -maxdepth 1 -type d -name '*.egg-info' -uid 0 \
            -exec rm -rf {} + 2>/dev/null || true
    fi
    if [[ ! -w "$dir" ]]; then
        echo "Making $dir world-writable..."
        $SUDO chmod o+w "$dir"
    fi
done

# ── Step 2: Bootstrap O3DE's bundled Python ─────────────────────────────────
# Probe via the python.sh wrapper so a stale packages dir from a removed engine
# doesn't cause us to skip venv creation for this engine.
if "$O3DE_ENGINE/python/python.sh" -c 'pass' &>/dev/null; then
    echo "O3DE Python already bootstrapped for $O3DE_ENGINE."
else
    echo "Bootstrapping O3DE Python..."
    "$O3DE_ENGINE/python/get_python.sh"
fi

# ── Step 3: Record engine path in sim/user/project.json ─────────────────────
# EngineFinder.cmake Option 2 reads engine_path from this file, so engine
# selection stays project-local and nothing is written to ~/.o3de.
USER_PROJECT_JSON="$PROJECT_ROOT/sim/user/project.json"
mkdir -p "$(dirname "$USER_PROJECT_JSON")"
printf '{\n    "engine_path": "%s"\n}\n' "$O3DE_ENGINE" > "$USER_PROJECT_JSON"
echo "Engine path recorded in $USER_PROJECT_JSON"

echo "O3DE SDK ready: $O3DE_ENGINE"
