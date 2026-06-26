#!/usr/bin/env bash
# Downloads released gems from the O3DE gem catalogue and registers local
# submodule gems with the O3DE engine.
# Requires O3DE_ENGINE_PATH to be set (done automatically by pixi activation).
# Run after fetch-deps: pixi run register-gems

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPS_DIR="$PROJECT_ROOT/deps"
O3DE_CLI="$O3DE_ENGINE_PATH/scripts/o3de.sh"

if [[ ! -f "$O3DE_CLI" ]]; then
    echo "ERROR: O3DE CLI not found at $O3DE_CLI"
    echo "       Make sure O3DE is installed and O3DE_ENGINE_PATH is set correctly."
    exit 1
fi

# ── Step 1: Register the gem repo ───────────────────────────────────────────
# Required so that `o3de download` can resolve gem names to download URLs.

O3DE_REPO_URI="https://canonical.o3de.org"
if grep -q "$O3DE_REPO_URI" ~/.o3de/o3de_manifest.json 2>/dev/null; then
    echo "O3DE gem repo already registered."
else
    echo "Registering O3DE gem repo: $O3DE_REPO_URI"
    "$O3DE_CLI" register --repo-uri "$O3DE_REPO_URI"
fi

# ── Step 2: Download released gems from the gem catalogue ───────────────────

RELEASED_GEMS=(
    "ROS2==4.2.0"
    "ROS2Sensors==1.0.1"
    "ROS2Controllers==1.1.0"
    "LevelGeoreferencing==1.0.0"
    "ROS2SampleRobots==1.2.0"
    "SimulationInterfaces==2.2.0"
    "WarehouseAssets==2.0.4"
)

echo "=== Downloading O3DE Gems ==="
for gem in "${RELEASED_GEMS[@]}"; do
    gem_name="${gem%%==*}"
    if grep -q "/Gems/$gem_name/" "$HOME/.o3de/o3de_manifest.json" 2>/dev/null; then
        echo "  Already registered, skipping: $gem"
    else
        echo "  Downloading: $gem"
        "$O3DE_CLI" download --gem-name "$gem" -f
    fi
done

# ── Step 3: Register local submodule gems ───────────────────────────────────

register_gem() {
    local gem_path="$1"
    if [[ ! -d "$gem_path" ]]; then
        echo "ERROR: Gem directory not found: $gem_path"
        echo "       Run 'pixi run fetch-deps' first."
        exit 1
    fi
    echo "  Registering: $gem_path"
    "$O3DE_CLI" register --gem-path "$gem_path"
}

echo ""
echo "=== All gems downloaded and registered successfully ==="
