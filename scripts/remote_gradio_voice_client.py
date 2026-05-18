#!/usr/bin/env python3
"""
Call a remote (or local) Qwen3-TTS Gradio server and print JSON with audio_base64.

Usage:
  python scripts/remote_gradio_voice_client.py <server_url> <text> <voice_instruction> <language>

Use the same Python that has gradio_client installed (e.g. .venv/bin/python).
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from urllib.request import urlopen

import requests
from gradio_client import Client


def normalize_type(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def get_component_map(cfg):
    out = {}
    for c in cfg.get("components", []):
        try:
            out[int(c.get("id"))] = c
        except Exception:
            pass
    return out


def dependency_input_types(dep, comp_map):
    out = []
    for input_id in dep.get("inputs", []):
        comp = comp_map.get(int(input_id), {})
        out.append(normalize_type(comp.get("type")))
    return out


def dependency_output_types(dep, comp_map):
    out = []
    for output_id in dep.get("outputs", []):
        comp = comp_map.get(int(output_id), {})
        out.append(normalize_type(comp.get("type")))
    return out


def safe_first_choice(value):
    if isinstance(value, (list, tuple)) and value:
        first = value[0]
        if isinstance(first, (list, tuple)) and first:
            return first[-1]
        if isinstance(first, dict):
            return first.get("value") or first.get("label") or ""
        return first
    return ""


def component_default(comp):
    props = comp.get("props", {}) if isinstance(comp, dict) else {}
    value = props.get("value")
    if value is not None and value != "":
        return value
    choice = safe_first_choice(props.get("choices"))
    if choice not in (None, ""):
        return choice
    return ""


def select_language_for_component(comp, preferred_language):
    preferred = (preferred_language or "").strip()
    props = comp.get("props", {}) if isinstance(comp, dict) else {}
    choices = props.get("choices") or []
    normalized = {}
    ordered = []
    for raw in choices:
        if isinstance(raw, (list, tuple)) and raw:
            val = raw[-1]
        elif isinstance(raw, dict):
            val = raw.get("value") or raw.get("label")
        else:
            val = raw
        if val is None:
            continue
        s = str(val)
        ordered.append(s)
        normalized[s.lower()] = s
    for candidate in [preferred, "English", "Auto"]:
        if candidate and candidate.lower() in normalized:
            return normalized[candidate.lower()]
    if ordered:
        return ordered[0]
    return component_default(comp) or preferred or "Auto"


def is_language_dropdown(comp):
    props = comp.get("props", {}) if isinstance(comp, dict) else {}
    choices = props.get("choices") or []
    for raw in choices:
        if isinstance(raw, (list, tuple)) and raw:
            val = raw[-1]
        elif isinstance(raw, dict):
            val = raw.get("value") or raw.get("label")
        else:
            val = raw
        s = str(val or "").strip().lower()
        if s in (
            "auto",
            "english",
            "chinese",
            "japanese",
            "korean",
            "german",
            "french",
            "russian",
            "portuguese",
            "spanish",
            "italian",
        ):
            return True
    return False


def build_args_for_dependency(dep, comp_map, text_value, instruction_value, preferred_language):
    args = []
    textbox_seen = 0
    for input_id in dep.get("inputs", []):
        comp = comp_map.get(int(input_id), {})
        ctype = normalize_type(comp.get("type"))
        if ctype == "textbox":
            if textbox_seen == 0:
                args.append(text_value)
            else:
                args.append(instruction_value)
            textbox_seen += 1
            continue
        if ctype == "dropdown":
            if is_language_dropdown(comp):
                args.append(select_language_for_component(comp, preferred_language))
            else:
                args.append(component_default(comp))
            continue
        if ctype in ("file", "audio"):
            args.append(None)
            continue
        if ctype == "checkbox":
            args.append(True)
            continue
        args.append(component_default(comp))
    return args


def retry_variants_for_args(dep, comp_map, base_args):
    variants = []
    input_ids = dep.get("inputs", [])
    lang_idx = None
    instruction_idx = None
    speaker_idx = None
    textbox_seen = 0
    for i, input_id in enumerate(input_ids):
        comp = comp_map.get(int(input_id), {})
        ctype = normalize_type(comp.get("type"))
        if ctype == "dropdown" and is_language_dropdown(comp) and lang_idx is None:
            lang_idx = i
        elif ctype == "dropdown" and speaker_idx is None:
            speaker_idx = i
        if ctype == "textbox":
            if textbox_seen >= 1 and instruction_idx is None:
                instruction_idx = i
            textbox_seen += 1

    if instruction_idx is not None:
        v = list(base_args)
        v[instruction_idx] = ""
        variants.append(v)
    if lang_idx is not None:
        v = list(base_args)
        v[lang_idx] = "Auto"
        variants.append(v)
    if instruction_idx is not None or lang_idx is not None:
        v = list(base_args)
        if instruction_idx is not None:
            v[instruction_idx] = ""
        if lang_idx is not None:
            v[lang_idx] = "Auto"
        variants.append(v)

    if speaker_idx is not None:
        speaker_comp = comp_map.get(int(input_ids[speaker_idx]), {})
        choices = (speaker_comp.get("props", {}) or {}).get("choices", [])
        speaker_values = []
        for raw in choices:
            if isinstance(raw, (list, tuple)) and raw:
                val = raw[-1]
            elif isinstance(raw, dict):
                val = raw.get("value") or raw.get("label")
            else:
                val = raw
            if val is None:
                continue
            speaker_values.append(str(val))
        current_speaker = str(base_args[speaker_idx]) if speaker_idx < len(base_args) else ""
        for alt_speaker in speaker_values:
            if not alt_speaker or alt_speaker == current_speaker:
                continue
            v1 = list(base_args)
            v1[speaker_idx] = alt_speaker
            variants.append(v1)
            v2 = list(base_args)
            v2[speaker_idx] = alt_speaker
            if instruction_idx is not None:
                v2[instruction_idx] = ""
            if lang_idx is not None:
                v2[lang_idx] = "Auto"
            variants.append(v2)
            if len(variants) >= 10:
                break

    uniq = []
    seen = set()
    for item in variants:
        key = json.dumps(item, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    return uniq


def extract_audio_path(result):
    if isinstance(result, (list, tuple)):
        audio_obj = result[0] if len(result) > 0 else None
        status = result[1] if len(result) > 1 else ""
    else:
        audio_obj = result
        status = ""
    if isinstance(audio_obj, dict):
        audio_obj = audio_obj.get("url") or audio_obj.get("name") or audio_obj.get("path")
    return audio_obj, status


def with_prefix(prefix, path):
    p = str(prefix or "").strip()
    if not p:
        return path
    if not p.startswith("/"):
        p = "/" + p
    p = p.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{p}{path}"


def predict_via_http(server_url, fn_index, args, dep=None, api_prefix=""):
    base = (server_url or "").rstrip("/")
    api_name = ""
    if isinstance(dep, dict):
        api_name = str(dep.get("api_name") or "").strip("/")
    candidate_paths = []
    if api_name:
        candidate_paths.extend(
            [
                with_prefix(api_prefix, f"/api/{api_name}"),
                with_prefix(api_prefix, f"/run/{api_name}"),
                with_prefix(api_prefix, f"/call/{api_name}"),
                with_prefix(api_prefix, f"/call/{api_name}/"),
            ]
        )
    candidate_paths.extend(
        [
            with_prefix(api_prefix, "/api/predict"),
            with_prefix(api_prefix, "/run/predict"),
            with_prefix(api_prefix, "/api/predict/"),
            with_prefix(api_prefix, "/run/predict/"),
        ]
    )
    payload_variants = [{"fn_index": fn_index, "data": args}, {"data": args}]
    for path in candidate_paths:
        for payload_json in payload_variants:
            try:
                resp = requests.post(
                    f"{base}{path}",
                    json=payload_json,
                    timeout=180,
                    headers={"Accept": "application/json"},
                )
                if resp.status_code >= 400:
                    continue
                payload = resp.json() if resp.content else {}
                data = payload.get("data")
                if data is None and isinstance(payload.get("output"), dict):
                    data = payload["output"].get("data")
                if data is None:
                    data = payload.get("result")
                if data is None:
                    continue
                return data
            except Exception:
                continue
    raise RuntimeError("HTTP predict fallback failed")


def emit_audio(server, audio_path, status):
    if isinstance(audio_path, str) and audio_path.startswith("data:"):
        try:
            header, payload = audio_path.split(",", 1)
            if ";base64" in header.lower():
                audio_bytes = base64.b64decode(payload)
            else:
                from urllib.parse import unquote_to_bytes

                audio_bytes = unquote_to_bytes(payload)
            print(json.dumps({"audio_base64": base64.b64encode(audio_bytes).decode("utf-8"), "status": status}))
            sys.exit(0)
        except Exception as e:
            return f"failed to decode data-url audio: {e}"

    if isinstance(audio_path, str) and audio_path.startswith(("http://", "https://")):
        fd, tmp_audio_file = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Referer": server.rstrip("/") + "/",
        }
        try:
            resp = requests.get(audio_path, headers=headers, timeout=180)
            resp.raise_for_status()
            with open(tmp_audio_file, "wb") as dst:
                dst.write(resp.content)
        except Exception:
            with urlopen(audio_path) as src, open(tmp_audio_file, "wb") as dst:
                dst.write(src.read())
        audio_path = tmp_audio_file

    if audio_path and os.path.exists(str(audio_path)):
        with open(str(audio_path), "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        print(json.dumps({"audio_base64": audio_b64, "status": status}))
        sys.exit(0)
    return f"audio path missing on disk: {audio_path} status={status}"


def should_retry_variant(status_or_err: str) -> bool:
    status_text = str(status_or_err or "")
    return (
        "Expected size for first two dimensions" in status_text
        or "RuntimeError" in status_text
        or "tensor" in status_text.lower()
    )


def make_client(server: str) -> Client:
    # Reason: public Gradio URLs via tunnel often exceed httpx default (~5s) on first /config fetch.
    try:
        return Client(server, verbose=False, httpx_kwargs={"timeout": 300.0})
    except TypeError:
        return Client(server, verbose=False)


def run_generation(server: str, text: str, voice_instruction: str, language: str) -> None:
    client = make_client(server)
    attempt_errors = []
    config = client.config or {}
    comp_map = get_component_map(config)
    api_prefix = str(config.get("api_prefix") or "").strip()

    for idx, dep in enumerate(config.get("dependencies", [])):
        input_types = dependency_input_types(dep, comp_map)
        output_types = dependency_output_types(dep, comp_map)
        if "textbox" not in input_types or input_types.count("textbox") < 1:
            continue
        if not any(t in ("audio", "file") for t in output_types):
            continue

        args = build_args_for_dependency(dep, comp_map, text, voice_instruction, language)
        if not args:
            continue

        try:
            result = client.predict(*args, fn_index=idx)
            if result is None:
                raise RuntimeError("empty result")
            audio_path, status = extract_audio_path(result)
            if not audio_path:
                if should_retry_variant(str(status or "")):
                    recovered = _retry_with_variants(
                        server, client, idx, dep, comp_map, args, api_prefix, attempt_errors, "status-variant"
                    )
                    if recovered:
                        continue
                attempt_errors.append(f"fn{idx} invalid audio path: {audio_path} status={status}; args={args}")
                continue
            failure = emit_audio(server, audio_path, status)
            attempt_errors.append(failure)
        except Exception as e:
            err_text = str(e)
            if "WebSocket" in err_text or "websocket" in err_text:
                if _try_http_fallback(server, idx, dep, comp_map, args, api_prefix, attempt_errors, err_text):
                    continue
            if should_retry_variant(err_text):
                if _retry_with_variants(
                    server, client, idx, dep, comp_map, args, api_prefix, attempt_errors, "variant"
                ):
                    continue
            attempt_errors.append(f"fn{idx} error: {e}; args={args}")

    print(
        json.dumps(
            {
                "error": "Qwen voice design failed",
                "python": sys.executable,
                "config_input_shapes": [
                    dependency_input_types(dep, get_component_map(config))
                    for dep in config.get("dependencies", [])
                ][:8],
                "attempt_errors": attempt_errors[-10:],
            }
        )
    )
    sys.exit(1)


def _retry_with_variants(server, client, idx, dep, comp_map, args, api_prefix, attempt_errors, label):
    for alt_args in retry_variants_for_args(dep, comp_map, args):
        try:
            alt_result = predict_via_http(server, idx, alt_args, dep, api_prefix)
            alt_audio_path, alt_status = extract_audio_path(alt_result)
            if alt_audio_path:
                failure = emit_audio(server, alt_audio_path, alt_status)
                attempt_errors.append(f"fn{idx} recovered via {label} args={alt_args}; note={failure}")
                return True
            attempt_errors.append(
                f"fn{idx} {label} invalid audio path: {alt_audio_path} status={alt_status}; args={alt_args}"
            )
        except Exception as variant_err:
            attempt_errors.append(f"fn{idx} {label} error: {variant_err}; args={alt_args}")
    return False


def _try_http_fallback(server, idx, dep, comp_map, args, api_prefix, attempt_errors, ws_error):
    try:
        result = predict_via_http(server, idx, args, dep, api_prefix)
        audio_path, status = extract_audio_path(result)
        if audio_path:
            failure = emit_audio(server, audio_path, status)
            attempt_errors.append(failure)
            return True
        if should_retry_variant(str(status or "")):
            if _retry_with_variants(
                server, None, idx, dep, comp_map, args, api_prefix, attempt_errors, "ws-http status-variant"
            ):
                return True
        attempt_errors.append(f"fn{idx} http fallback invalid audio path: {audio_path} status={status}; args={args}")
        return True
    except Exception as http_err:
        attempt_errors.append(f"fn{idx} websocket+http fallback failed: {http_err}; ws_error={ws_error}; args={args}")
    return False


def main():
    if len(sys.argv) < 5:
        print(
            json.dumps(
                {
                    "error": "usage",
                    "message": (
                        "remote_gradio_voice_client.py <server_url> <text> "
                        "<voice_instruction> <language>"
                    ),
                    "python": sys.executable,
                }
            )
        )
        sys.exit(2)

    server = sys.argv[1].strip()
    if not server.startswith("http"):
        server = "https://" + server
    text = sys.argv[2]
    voice_instruction = (sys.argv[3] or "").strip()
    language = sys.argv[4]
    try:
        run_generation(server, text, voice_instruction, language)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "server": server,
                    "python": sys.executable,
                    "hint": "If bridge runs on the same VM as Gradio, use server http://127.0.0.1:8000",
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
