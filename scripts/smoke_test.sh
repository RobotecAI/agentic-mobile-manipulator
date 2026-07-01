#!/usr/bin/env bash
# Health-check every local inference endpoint declared in the SSOT (config.toml).
# Endpoint list + ports come from `serve.py --health`, so this never hardcodes
# them — add/move a server in config.toml and the check follows.

GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m'

PASS=0
FAIL=0
CONFIG="${INFERENCE_CONFIG:-config.toml}"

check() {
    local url="$1"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null)
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}[OK]   $url${RESET}"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[FAIL] $url — HTTP $http_code${RESET}"
        FAIL=$((FAIL + 1))
    fi
}

mapfile -t URLS < <(python -m rai_app.inference.serve --health --config "$CONFIG")

echo ""
echo "=== Inference Health Check ($CONFIG) ==="
echo ""

if [ "${#URLS[@]}" -eq 0 ]; then
    echo "  No local endpoints to check (all remote?)."
    echo ""
    exit 0
fi

for url in "${URLS[@]}"; do
    check "$url"
done

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}$PASS up, $FAIL down${RESET}"
else
    echo -e "  ${RED}$PASS up, $FAIL down${RESET}"
fi
echo ""

# Functional check: send a real, type-appropriate inference request to each
# endpoint (llm/vlm chat, embeddings vector, reranker scores, + GBNF grammar on
# NPU). Liveness alone doesn't prove the checkpoint actually serves.
python -m rai_app.inference.serve --check --config "$CONFIG"
CHECK_RC=$?

# Overall pass requires both: all endpoints up AND all functional checks passed.
[ "$FAIL" -eq 0 ] && [ "$CHECK_RC" -eq 0 ]
