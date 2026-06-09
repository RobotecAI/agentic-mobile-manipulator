#!/usr/bin/env bash
set -euo pipefail

MODELS_DIR="${DEMO_ROOT}/models"
mkdir -p "$MODELS_DIR"

model_names=()
model_urls=()
model_files=()

add_model() {
    model_names+=("$1")
    model_urls+=("$2")
    model_files+=("$3")
}

add_model "GPT-OSS-20B       (LLM,    ~12 GB)" \
    "https://huggingface.co/unsloth/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-Q4_K_M.gguf?download=true" \
    "gpt-oss-20b-Q4_K_M.gguf"

add_model "LFM2-VL-3B        (VLM,    ~3.2 GB)" \
    "https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/LFM2-VL-3B-Q8_0.gguf?download=true" \
    "LFM2-VL-3B-Q8_0.gguf"

add_model "LFM2-VL-3B mmproj (VLM,    ~0.5 GB)" \
    "https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/mmproj-LFM2-VL-3B-Q8_0.gguf?download=true" \
    "mmproj-LFM2-VL-3B-Q8_0.gguf"

add_model "Qwen3-Embedding    (Embed,  ~0.6 GB)" \
    "https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf?download=true" \
    "Qwen3-Embedding-0.6B-Q8_0.gguf"

add_model "Qwen3-Reranker     (Rerank, ~0.6 GB)" \
    "https://huggingface.co/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/resolve/main/qwen3-reranker-0.6b-q8_0.gguf?download=true" \
    "qwen3-reranker-0.6b-q8_0.gguf"

echo ""
echo "=== Downloading models to $MODELS_DIR ==="
echo ""

input_lines=()
for i in "${!model_names[@]}"; do
    dest="$MODELS_DIR/${model_files[$i]}"
    if [ -f "$dest" ]; then
        echo "  [skip]   ${model_names[$i]}"
    else
        echo "  [queue]  ${model_names[$i]}"
        input_lines+=("${model_urls[$i]}")
        input_lines+=("  out=${model_files[$i]}")
    fi
done

if [ ${#input_lines[@]} -eq 0 ]; then
    echo ""
    echo "  All models already present."
    echo ""
    exit 0
fi

echo ""
printf '%s\n' "${input_lines[@]}" | aria2c \
    --input-file=- \
    --dir="$MODELS_DIR" \
    --continue=true \
    --max-concurrent-downloads=5 \
    --max-connection-per-server=4 \
    --split=4 \
    --console-log-level=warn

echo ""
echo "=== All models ready in $MODELS_DIR ==="
echo ""
