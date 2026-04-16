# Task Tracker

## Completed
- [x] 2026-04-10: Fix `transformers` compatibility checks for CLI startup and document minimum required version (`>=4.57.0`).
- [x] 2026-04-10: Validate Windows CPU demo startup command reaches Gradio launch on port 8000.
- [x] 2026-04-10: Handle busy Gradio port in CLI demo by retrying with an auto-selected port.
- [x] 2026-04-10: Remove deprecated `layer_type_validation` usage in config for newer `transformers`.
- [x] 2026-04-10: Make `run_qwen_api.ps1` robust to Gradio fn_index drift and local-file response formats.
- [x] 2026-04-10: Replace deprecated `input_embeds` mask kwargs to `inputs_embeds` in model/tokenizer code.

## Discovered During Work
- [ ] Consider pinning or isolating dependencies for external packages (`indextts`, `styletts2`, `moshi`) that conflict with this project's `transformers` range.
