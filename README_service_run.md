Qwen setup is now working end-to-end on your machine.

Qwen server is running on http://127.0.0.1:8000 with:
python -u -m qwen_tts.cli.demo "models/qwen-tts/Qwen3-TTS-12Hz-0.6B-CustomVoice" --device cpu --dtype float32 --no-flash-attn --ip 127.0.0.1 --port 8000