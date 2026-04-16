# coding=utf-8
# Copyright 2026 The Alibaba Qwen team.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
qwen_tts: Qwen-TTS package.
"""

from importlib import metadata


def _parse_semver(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    parsed = []
    for part in parts[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        parsed.append(int(digits) if digits else 0)
    while len(parsed) < 3:
        parsed.append(0)
    return tuple(parsed)


def _ensure_transformers_version() -> None:
    min_version = (4, 57, 0)
    try:
        installed = metadata.version("transformers")
    except metadata.PackageNotFoundError as exc:
        raise ImportError(
            "qwen_tts requires transformers>=4.57.0, but transformers is not installed. "
            "Run: pip install -U \"transformers>=4.57.0\""
        ) from exc

    if _parse_semver(installed) < min_version:
        raise ImportError(
            f"qwen_tts requires transformers>=4.57.0, found transformers=={installed}. "
            "Run: pip install -U \"transformers>=4.57.0\""
        )


_ensure_transformers_version()

from .inference.qwen3_tts_model import Qwen3TTSModel, VoiceClonePromptItem
from .inference.qwen3_tts_tokenizer import Qwen3TTSTokenizer

__all__ = ["__version__"]