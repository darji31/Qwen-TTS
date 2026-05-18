# Running the Qwen Gradio service

## Start the server (Thunder / Linux GPU)

```bash
cd /home/ubuntu/Qwen-TTS
source .venv/bin/activate
pip install "gradio-client==1.10.3" requests   # matches gradio 5.x in this venv

CUDA_LAUNCH_BLOCKING=1 python -u -m qwen_tts.cli.demo \
  "/home/ubuntu/Qwen-TTS/models/qwen-tts/Qwen3-TTS-12Hz-0.6B-CustomVoice" \
  --device cuda:0 --dtype bfloat16 --no-flash-attn --ip 0.0.0.0 --port 8000
```

Public URL example: `https://vtq2qdhv-8000.thundercompute.net`

## Call the server from a client (fixes `ModuleNotFoundError`)

The integration must **not** use bare `python -c ...` with system `python`. Use the venv interpreter or the wrapper script:

```bash
./scripts/run_remote_gradio_voice.sh \
  "https://vtq2qdhv-8000.thundercompute.net" \
  "HI how are you" \
  "soft tone" \
  "English"
```

Or explicitly:

```bash
/home/ubuntu/Qwen-TTS/.venv/bin/python \
  /home/ubuntu/Qwen-TTS/scripts/remote_gradio_voice_client.py \
  "https://vtq2qdhv-8000.thundercompute.net" \
  "HI how are you" \
  "soft tone" \
  "English"
```

On Windows (client machine):

```powershell
C:\path\to\Qwen-TTS\.venv\Scripts\python.exe `
  C:\path\to\Qwen-TTS\scripts\remote_gradio_voice_client.py `
  "https://vtq2qdhv-8000.thundercompute.net" `
  "HI how are you" "soft tone" "English"
```

If your tool has a **Python path** setting, point it at `.venv/bin/python` (Linux) or `.venv\Scripts\python.exe` (Windows).

## External website still shows `python -c` / `ModuleNotFoundError: gradio_client`

Your shell script works because it uses **`.venv/bin/python`**. Many third-party sites run a **hard-coded** command:

```text
python -c import base64, json, ... from gradio_client import Client ...
```

That runs on **their** machine (or system `python` on your box), **not** your venv. Installing packages only in `.venv` does not fix that unless you change the site’s settings.

### Fix A — HTTP bridge (best if the site supports a custom API URL)

On Thunder, in a **second** terminal (keep Gradio on port 8000 running):

```bash
cd /home/ubuntu/Qwen-TTS
chmod +x scripts/run_http_bridge.sh
./scripts/run_http_bridge.sh
```

Open port **7861** in Thunder Compute (same way you exposed 8000).

Test:

```bash
curl -s -X POST "http://127.0.0.1:7861/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"HI how are you","voice_instruction":"soft tone","language":"English"}' \
  | head -c 200
```

In the **other website**, if it has any of these settings, use them instead of the built-in Qwen Python command:

| Setting | Value |
|--------|--------|
| API / webhook URL | `http://YOUR_THUNDER_IP:7861/generate` or public tunnel to that port |
| Method | `POST` |
| Body (JSON) | `{"text":"...","voice_instruction":"...","language":"English"}` |

The response field is `audio_base64` (WAV).

### Fix B — Point the site’s Python to your venv

If the website lets you set **Python path** or **custom command**, use:

```text
/home/ubuntu/Qwen-TTS/.venv/bin/python
```

or replace `python -c ...` with:

```text
/home/ubuntu/Qwen-TTS/scripts/run_remote_gradio_voice.sh "<url>" "<text>" "<instruct>" "<lang>"
```

### Fix C — Install on system `python` (only if the site runs commands on your Thunder VM)

```bash
chmod +x scripts/install_system_python_client.sh
./scripts/install_system_python_client.sh
```

Then verify bare `python3` works:

```bash
python3 -c "from gradio_client import Client; print('ok')"
```

### Fix D — If the site runs Python on your Windows PC

On Windows (not Thunder), in PowerShell:

```powershell
python -m pip install gradio-client==1.10.3 requests
python -c "from gradio_client import Client; print('ok')"
```

### Cannot fix from your side

If the website **only** runs `python -c` on **its own servers** and has **no** custom URL / Python path, you cannot install `gradio_client` there. Use **Fix A** (HTTP bridge) or ask the site vendor for “custom Python path” or “HTTP TTS endpoint”.

## Model note

`0.6B-CustomVoice` supports preset speakers + optional style instruct. For free-form **voice design** from text descriptions only, run the **1.7B-VoiceDesign** checkpoint instead.
