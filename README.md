# AgentQuest

AgentQuest is a playable AI-agent RPG for structured tool-use evaluation. A model receives a fantasy scene, sees a constrained set of visible tools, and must answer with strict JSON:

```json
{"tool_id": "...", "arguments": {...}}
```

The engine validates that output in three stages:

1. AST validation: is the JSON well-formed and schema-correct?
2. Hard validation: can this character legally use that tool here?
3. Soft validation: does the action solve the scene?

The project is runner-first. The CLI runners, benchmark scripts, Streamlit UI, prompt builder, model backend, loader, and validator all use the same execution path.

## Quick Start

Install the project from the repository root:

```bash
pip install -e .
```

For model-backed runs, install the llama.cpp backend:

```bash
pip install llama-cpp-python
```

Preview a prompt without calling a model:

```bash
python -m src.runner.preview_prompt
```

Launch the Streamlit UI:

```bash
streamlit run streamlit_app.py
```

Run the test suite:

```bash
pytest
```

## Configure A Run

Runtime settings live in `configs/run_config.json`:

```json
{
  "backend": "llama_cpp",
  "model": "qwen3_4b_q4_k_m",
  "preset": "BATTLE_PLAN",
  "prompt_format": "json_only"
}
```

Model aliases are defined in `configs/model_catalog.json`. The current backend is `llama_cpp`.

Useful environment variables:

- `HF_TOKEN`: optional Hugging Face token for downloads or gated models
- `AGENTQUEST_DATA_DIR`: runtime data root, defaults to `data/`
- `AGENTQUEST_MODEL`: model catalog alias override
- `AGENTQUEST_RUNS_DIR`: saved run-log directory, defaults to `runs/`
- `AGENTQUEST_MODELS_DIR`: legacy local-model directory helper

CLI and Streamlit entrypoints load `.env` from the repository root when present. Existing shell variables take precedence.

## Common Commands

Preview the exact prompt messages:

```bash
python -m src.runner.preview_prompt --preset BATTLE_PLAN
python -m src.runner.preview_prompt --character-id knight.bram --scene-id scene.goblin_den.001_outer_watch
python -m src.runner.preview_prompt --save-json runs/prompt_preview.json
```

Run one scene:

```bash
python -m src.runner.run_one --character-id knight.bram --scene-id scene.goblin_den.001_outer_watch
```

Run one campaign:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --continue-on-failure
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --self-learning --per-scene-retry-limit 3 --total-retry-limit 20
```

Run a benchmark sweep:

```bash
python scripts/run_benchmark.py --campaign-id campaign.benchmark_core_v1 --all-characters --preset BATTLE_PLAN --prompt-format json_only --model qwen3_4b_q4_k_m
```

Generate a deterministic validation report:

```bash
python scripts/generate_validation_report.py
```

## Streamlit UI

The Streamlit app is a thin viewer over shared runner/service logic. It supports:

- configured catalog model selection
- exposed prompt presets: `BLIND_ADVENTURER`, `BATTLE_PLAN`, and `FULL_INFO`
- single-scene, campaign, and benchmark modes
- raw output, parsed tool call, prompt, validation, and retry inspection
- saved run logs for scene and campaign runs

## Documentation

- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Local development: [`docs/development.md`](docs/development.md)
- Testing: [`docs/testing.md`](docs/testing.md)
- Docker: [`docs/docker.md`](docs/docker.md)
- Models: [`docs/models.md`](docs/models.md)
- Prompt system: [`src/prompts/README.md`](src/prompts/README.md)
- Engine and validators: [`src/engine/README.md`](src/engine/README.md)
- Open5e data pipeline: [`src/data_pipeline/README.md`](src/data_pipeline/README.md)
- Portfolio materials: [`docs/portfolio.md`](docs/portfolio.md)

## Project Layout

```text
agentquest/
|-- configs/
|-- data/
|-- docs/
|-- scripts/
|-- src/
|   |-- app/
|   |-- data_pipeline/
|   |-- engine/
|   |-- models/
|   |-- prompts/
|   `-- runner/
|-- tests/
|-- main.py
`-- streamlit_app.py
```

Generated outputs such as run logs, caches, local models, and generated Open5e data are intentionally kept out of the main documentation path.
