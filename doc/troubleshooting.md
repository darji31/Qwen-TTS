# Troubleshooting

## Common Issues

### AttributeError: 'Qwen3TTSTalkerConfig' object has no attribute 'pad_token_id'

**Cause**: This error typically occurs due to version mismatches between your environment and the expected dependencies.

**Solutions**:

1. **Update transformers** (Recommended):
   ```bash
   pip install --upgrade transformers>=4.57.3
   ```

2. **Clear model cache and re-download**:
   - Delete the `models/qwen-tts` folder
   - Restart ComfyUI to trigger fresh downloads

3. **Check your transformers version**:
   ```python
   import transformers
   print(transformers.__version__)  # Should be >= 4.57.0
   ```

4. **Verify model files**:
   - Ensure all model files are completely downloaded
   - Check `models/qwen-tts/*/config.json` files are valid JSON

### `ModuleNotFoundError: No module named 'gradio_client'`

**Cause**: A tool is calling a remote Qwen Gradio server (for example Thunder Compute or `run_qwen_api.ps1`-style HTTP clients) with a Python helper that needs `gradio_client`, but that package is not installed in the **same** interpreter the tool uses.

**Solutions**:

1. **Install into the Python that runs the command** (use the full path if your app bundles another Python):

   ```powershell
   python -m pip install gradio_client requests
   ```

   Or install everything from this repo:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. **Confirm the interpreter**:

   ```powershell
   python -c "import sys; print(sys.executable); from gradio_client import Client; print('gradio_client ok')"
   ```

   If that fails, you are not using the environment where you installed packages. Point your tool at `C:\Program Files\Python311\python.exe` (or your venv’s `python.exe`) or run `pip install` with that executable explicitly:

   ```powershell
   & "C:\Path\To\Your\python.exe" -m pip install gradio_client requests
   ```

3. **Use the repo script with the venv interpreter** (do not use bare `python -c`):

   ```bash
   ./scripts/run_remote_gradio_voice.sh "https://YOUR-HOST" "text" "instruction" "English"
   ```

   Or: `.venv/bin/python scripts/remote_gradio_voice_client.py ...`

   The JSON error payload includes `"python": "..."` so you can see which interpreter failed.

### `gradio 5.x requires gradio-client==1.10.3` (pip dependency conflict)

**Cause**: Upgrading only `gradio_client` to 2.x (for example `pip install "gradio_client>=0.15.0" --upgrade`) while `gradio` 5.x stays installed. Gradio 5 pins `gradio-client` 1.10.x; client 2.x belongs with Gradio 6+.

**Fix (recommended if this venv runs the local Qwen demo and remote client)** — reinstall the matched pair:

```powershell
python -m pip install "gradio-client==1.10.3"
```

`1.10.3` is enough for remote Gradio servers and matches `gradio` 5.34.2.

**Alternative (upgrade both together)** — only if you want Gradio 6 in this venv:

```powershell
python -m pip install "gradio>=6.14" "gradio-client>=2.5"
```

Do not leave `gradio` 5.x and `gradio-client` 2.x installed together.

### Other Issues

If you encounter other problems, please:
1. Check the ComfyUI console for detailed error messages
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Report issues at: https://github.com/flybirdxx/ComfyUI-Qwen-TTS/issues
