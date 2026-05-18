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

## Model note

`0.6B-CustomVoice` supports preset speakers + optional style instruct. For free-form **voice design** from text descriptions only, run the **1.7B-VoiceDesign** checkpoint instead.
