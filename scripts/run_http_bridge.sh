#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export QWEN_GRADIO_URL="${QWEN_GRADIO_URL:-http://127.0.0.1:8000}"
exec "${ROOT}/.venv/bin/python" "${ROOT}/scripts/qwen_http_bridge.py" --host 0.0.0.0 --port "${QWEN_HTTP_BRIDGE_PORT:-7861}" "$@"
