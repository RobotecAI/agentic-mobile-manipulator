#!/usr/bin/env bash

GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local url="$2"
    local http_code

    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null)

    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}[OK]   $name ($url)${RESET}"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[FAIL] $name ($url) — HTTP $http_code${RESET}"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "=== LLM Server Health Check ==="
echo ""

check "LLM   (GPT-OSS-20B)"          "http://localhost:8080/health"
check "VLM   (LFM2-VL-3B)"           "http://localhost:8081/health"
check "Embed (Qwen3-Embedding-0.6b)" "http://localhost:8082/health"
check "Rerank (Qwen3-Reranker-0.6B)" "http://localhost:8083/health"

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}$PASS passed, $FAIL failed${RESET}"
else
    echo -e "  ${RED}$PASS passed, $FAIL failed${RESET}"
fi
echo ""

[ "$FAIL" -eq 0 ]
