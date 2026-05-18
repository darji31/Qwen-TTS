#!/usr/bin/env bash
# Use when an external tool runs bare `python` / `python3` on THIS machine (not .venv).
set -euo pipefail
echo "Installing gradio-client for system interpreters (for tools that use plain python)..."
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1; then
    echo "--- $py ($("$py" -c 'import sys; print(sys.executable)'))"
  "$py" -m pip install --user "gradio-client==1.10.3" "requests>=2.28.0" || \
    "$py" -m pip install "gradio-client==1.10.3" "requests>=2.28.0"
    "$py" -c "from gradio_client import Client; print('ok', __import__('gradio_client').__version__)"
  fi
done
echo "Done. External tools using system python on this host should work now."
