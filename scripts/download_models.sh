#!/usr/bin/env bash
set -e

MODELS_DIR="${DEMO_ROOT}/models"
mkdir -p "$MODELS_DIR"

download() {
    local name="$1"
    local url="$2"
    local dest="$3"
    if [ -f "$dest" ]; then
        echo "  [skip] $name — already exists"
    else
        echo "  [download] $name"
        wget -q --show-progress -c -O "$dest" "$url"
    fi
}

echo ""
echo "=== Downloading models to $MODELS_DIR ==="
echo ""

download "GPT-OSS-20B (LLM)" \
    "https://huggingface.co/unsloth/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-Q4_K_M.gguf?download=true" \
    "$MODELS_DIR/gpt-oss-20b-Q4_K_M.gguf"

download "LFM2-VL-3B (VLM)" \
    "https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/LFM2-VL-3B-Q8_0.gguf?download=true" \
    "$MODELS_DIR/LFM2-VL-3B-Q8_0.gguf"

download "LFM2-VL-3B mmproj" \
    "https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/mmproj-LFM2-VL-3B-Q8_0.gguf?download=true" \
    "$MODELS_DIR/mmproj-LFM2-VL-3B-Q8_0.gguf"

echo ""
echo "=== Manual downloads required ==="
echo ""
echo "  The following models must be downloaded manually and placed in $MODELS_DIR/:"
echo ""
echo "  Qwen3-Embedding-0.6b:"
echo "  https://robotecai-my.sharepoint.com/:u:/g/personal/bartlomiej_boczek_robotec_ai/IQB7tkMkmi34Q6xtTB89N1LxAfod0sMpGT4uTffjo6iW7qc?e=6kLoTi"
echo ""
echo "  Qwen3-Reranker-0.6B:"
echo "  https://robotecai-my.sharepoint.com/:u:/g/personal/bartlomiej_boczek_robotec_ai/IQAgWOVPiyS8RZ1QUVVx6N9gAaOGGrvDnk7Qa0IpSbhlp_8?e=P0b1Ak"
echo ""
