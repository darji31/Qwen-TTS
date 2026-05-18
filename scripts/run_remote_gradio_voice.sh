#!/usr/bin/env bash
# Always use the project venv so gradio_client is available.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "${ROOT}/.venv/bin/python" "${ROOT}/scripts/remote_gradio_voice_client.py" "$@"
