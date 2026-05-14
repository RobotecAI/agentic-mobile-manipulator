#!/usr/bin/env bash

PASS=0
FAIL=0

check() {
    local name="$1"
    local url="$2"
    local response
    local http_code

    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null)

    if [ "$http_code" = "200" ]; then
        echo "  [OK]   $name ($url)"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $name ($url) — HTTP $http_code"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "=== LLM Server Health Check ==="
echo ""

check "LLM   (GPT-OSS-20B)"        "http://localhost:8080/health"
check "VLM   (LFM2-VL-3B)"         "http://localhost:8081/health"
check "Embed (Qwen3-Embedding-0.6b)" "http://localhost:8082/health"
check "Rerank (Qwen3-Reranker-0.6B)" "http://localhost:8083/health"

echo ""
echo "  $PASS passed, $FAIL failed"
echo ""

[ "$FAIL" -eq 0 ]
