#!/usr/bin/env bash
# Clone o3de-extras (ROS2, SimulationInterfaces, etc.) into external/o3de-extras
# at a pinned ref, project-local. No o3de.sh calls — gems are registered purely
# via external_subdirectories in sim/project.json.
# Idempotent: skips the clone if already at the pinned ref.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
O3DE_EXTRAS_URL="${O3DE_EXTRAS_URL:-https://github.com/o3de/o3de-extras.git}"
O3DE_EXTRAS_REF="${O3DE_EXTRAS_REF:-2942b796c4fe4a8b9e255be1b315df79393d9c39}"
O3DE_EXTRAS_PATH="${O3DE_EXTRAS_PATH:-$REPO_ROOT/external/o3de-extras}"
PROJECT_JSON="$REPO_ROOT/sim/project.json"

# ── Clone / reconcile o3de-extras ───────────────────────────────────────────
if [[ -d "$O3DE_EXTRAS_PATH/.git" ]]; then
    CURRENT_REF=$(git -C "$O3DE_EXTRAS_PATH" rev-parse HEAD)
    EXPECTED_REF=$(git -C "$O3DE_EXTRAS_PATH" rev-parse "$O3DE_EXTRAS_REF" 2>/dev/null || echo "")
    if [[ "$CURRENT_REF" == "$EXPECTED_REF" && -n "$EXPECTED_REF" ]]; then
        echo "o3de-extras at pinned ref ${O3DE_EXTRAS_REF:0:12} ($O3DE_EXTRAS_PATH)"
    else
        if ! git -C "$O3DE_EXTRAS_PATH" diff --quiet HEAD --; then
            echo "ERROR: o3de-extras has uncommitted changes at $O3DE_EXTRAS_PATH." >&2
            echo "Commit/stash them or move the clone aside, then re-run." >&2
            exit 1
        fi
        echo "o3de-extras HEAD (${CURRENT_REF:0:12}) != pinned (${O3DE_EXTRAS_REF:0:12}); reconciling..."
        git -C "$O3DE_EXTRAS_PATH" fetch --quiet origin "$O3DE_EXTRAS_REF" || \
            git -C "$O3DE_EXTRAS_PATH" fetch --quiet origin
        git -C "$O3DE_EXTRAS_PATH" checkout --quiet "$O3DE_EXTRAS_REF"
    fi
else
    echo "Cloning o3de-extras into $O3DE_EXTRAS_PATH..."
    mkdir -p "$(dirname "$O3DE_EXTRAS_PATH")"
    git clone "$O3DE_EXTRAS_URL" "$O3DE_EXTRAS_PATH"
    git -C "$O3DE_EXTRAS_PATH" checkout "$O3DE_EXTRAS_REF"
fi

# ── Validate all external_subdirectories exist ──────────────────────────────
# Fail here with a clear message rather than silently mid-CMake-configure.
echo "Validating gem paths from sim/project.json..."
while IFS= read -r rel; do
    gem_path="$REPO_ROOT/sim/$rel"
    if [[ ! -d "$gem_path" ]]; then
        echo "ERROR: gem path not found: $gem_path" >&2
        if [[ "$gem_path" == *"o3de-extras"* ]]; then
            echo "       Check O3DE_EXTRAS_REF — the pinned commit may not contain this gem." >&2
        else
            echo "       Run 'pixi run clone-gems' first to clone local gems." >&2
        fi
        exit 1
    fi
done < <(python3 -c '
import json, sys
proj = json.load(open(sys.argv[1]))
for d in proj.get("external_subdirectories", []):
    print(d)
' "$PROJECT_JSON")

echo "All gem paths verified. o3de-extras ready: $O3DE_EXTRAS_PATH"
