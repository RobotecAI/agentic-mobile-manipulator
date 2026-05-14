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

download "Qwen3-Embedding-0.6B (Embed)" \
    "https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf?download=true" \
    "$MODELS_DIR/Qwen3-Embedding-0.6B-Q8_0.gguf"

download "Qwen3-Reranker-0.6B (Rerank)" \
    "https://huggingface.co/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/resolve/main/qwen3-reranker-0.6b-q8_0.gguf?download=true" \
    "$MODELS_DIR/qwen3-reranker-0.6b-q8_0.gguf"
