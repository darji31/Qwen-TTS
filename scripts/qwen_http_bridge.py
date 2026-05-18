#!/usr/bin/env python3
"""
HTTP bridge for external tools that cannot run gradio_client themselves.

Start (on Thunder, with venv active):
  .venv/bin/python scripts/qwen_http_bridge.py --port 7861

POST http://YOUR_HOST:7861/generate
  {"text": "HI", "voice_instruction": "soft tone", "language": "English"}
  optional: "server": "https://vtq2qdhv-8000.thundercompute.net"

Returns same JSON as remote_gradio_voice_client.py (audio_base64 or error).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SCRIPT = os.path.join(ROOT, "scripts", "remote_gradio_voice_client.py")
DEFAULT_SERVER = os.environ.get(
    "QWEN_GRADIO_URL", "https://vtq2qdhv-8000.thundercompute.net"
)


def run_client(server: str, text: str, voice_instruction: str, language: str) -> dict:
    proc = subprocess.run(
        [sys.executable, CLIENT_SCRIPT, server, text, voice_instruction, language],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=ROOT,
    )
    raw = (proc.stdout or "").strip()
    if not raw:
        return {
            "error": "Qwen bridge subprocess produced no output",
            "returncode": proc.returncode,
            "stderr": (proc.stderr or "")[-2000:],
            "python": sys.executable,
        }
    # Client prints a single JSON line on success; errors may be last line too.
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {
        "error": "Qwen bridge could not parse client output",
        "returncode": proc.returncode,
        "stdout": raw[-2000:],
        "stderr": (proc.stderr or "")[-2000:],
        "python": sys.executable,
    }


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/health", "/generate"):
            self._send_json(200, {"ok": True, "python": sys.executable})
            return
        self._send_json(404, {"error": "not found", "path": self.path})

    def do_POST(self):
        if self.path.rstrip("/") not in ("", "/generate", "/api/generate"):
            self._send_json(404, {"error": "not found", "path": self.path})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception as exc:
            self._send_json(400, {"error": f"invalid JSON body: {exc}"})
            return

        server = (
            body.get("server")
            or body.get("server_url")
            or body.get("url")
            or DEFAULT_SERVER
        )
        text = body.get("text") or body.get("message") or ""
        instruction = (
            body.get("voice_instruction")
            or body.get("instruct")
            or body.get("instruction")
            or ""
        )
        language = body.get("language") or "English"

        if not str(text).strip():
            self._send_json(400, {"error": "text is required"})
            return

        if not str(server).startswith("http"):
            server = "https://" + str(server).strip()

        result = run_client(server, text, str(instruction), str(language))
        code = 200 if result.get("audio_base64") else 500
        self._send_json(code, result)


def main():
    parser = argparse.ArgumentParser(description="Qwen TTS HTTP bridge")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7861)
    args = parser.parse_args()
    if not os.path.isfile(CLIENT_SCRIPT):
        print(f"Missing client script: {CLIENT_SCRIPT}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Qwen HTTP bridge listening on http://{args.host}:{args.port}/generate\n"
        f"  python={sys.executable}\n"
        f"  default server={DEFAULT_SERVER}",
        file=sys.stderr,
    )
    HTTPServer((args.host, args.port), BridgeHandler).serve_forever()


if __name__ == "__main__":
    main()
