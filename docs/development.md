# Development

## Setup

From the repository root:

```bash
pip install -e .
pip install llama-cpp-python
```

AgentQuest requires Python 3.11 or newer. `streamlit` is declared in `pyproject.toml`. The project currently supports the `llama_cpp` backend for model-backed runs.

For normal manual use, start with Streamlit:

```bash
streamlit run streamlit_app.py
```

The UI exposes the available catalog models, prompt presets, characters, campaigns, scenes, benchmark mode, and self-learning notes. CLI commands are still useful for repeatable experiments and scripted checks.

## Runtime Config

Runtime settings live in `configs/run_config.json`:

```json
{
  "backend": "llama_cpp",
  "model": "qwen3_4b_q4_k_m",
  "preset": "BATTLE_PLAN",
  "prompt_format": "json_only"
}
```

Model names are catalog aliases from `configs/model_catalog.json`.

Useful environment variables:

- `HF_TOKEN`: optional Hugging Face token for downloads or gated models.
- `AGENTQUEST_DATA_DIR`: runtime data root, defaults to `data/`.
- `AGENTQUEST_MODEL`: model catalog alias override.
- `AGENTQUEST_RUNS_DIR`: saved run-log directory, defaults to `runs/`.
- `AGENTQUEST_MODELS_DIR`: legacy local-model directory helper.

CLI and Streamlit entrypoints load `.env` from the repository root when present. Existing shell variables take precedence.

## Common Commands

Preview prompts without model inference:

```bash
python -m src.runner.preview_prompt
python -m src.runner.preview_prompt --preset BLIND_ADVENTURER
python -m src.runner.preview_prompt --preset BATTLE_PLAN --save-json runs/prompt_preview.json
```

Run one scene:

```bash
python -m src.runner.run_one --character-id knight.bram --scene-id scene.goblin_den.001_outer_watch
```

Run one campaign:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram
```

Run self-learning retries:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --self-learning --per-scene-retry-limit 3 --total-retry-limit 20
```

## Benchmarking

Run a benchmark with the configured model:

```bash
python scripts/run_benchmark.py --campaign-id campaign.benchmark_core_v1 --all-characters --preset BATTLE_PLAN --prompt-format json_only
```

Run a model matrix:

```bash
python scripts/run_benchmark.py --campaign-id campaign.benchmark_core_v1 --all-characters --preset BLIND_ADVENTURER --preset BATTLE_PLAN --preset FULL_INFO --prompt-format json_only --model qwen3_4b_q4_k_m --model qwen2_5_3b_instruct_q5_k_m --model llama_3_2_3b_instruct_q4_k_m
```

Render a markdown benchmark report:

```bash
python scripts/render_benchmark_report.py --benchmark-dir results/benchmarks/model_a --label "Model A" --output docs/portfolio_assets/benchmark_report.md
```

## Data Work

Normal development should use the hand-authored custom dataset under `data/custom/agentquest/`.

See `docs/custom_data.md` for how the custom AgentQuest data is organized and how it relates to the RPG evaluation scenarios.

The Open5e pipeline is separate from the normal runtime workflow. See `src/data_pipeline/README.md` before changing raw, curated, or generated Open5e data.

## Development Rules

- Keep CLI runners working.
- Keep Streamlit as a thin layer over shared runner and engine behavior.
- Do not change validator semantics unless the task explicitly asks for it.
- Prefer small, reviewable changes.
- Do not add dependencies unless the task clearly requires them.
