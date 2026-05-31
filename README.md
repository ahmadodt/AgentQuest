# AgentQuest

AgentQuest is a playable AI-agent RPG for structured tool-use evaluation. It is built to study how small instruction models handle constrained decision-making, structured outputs, and failure recovery inside a deterministic game world.

The RPG wrapper is intentional, but the engineering goal is narrower: evaluate whether a model can choose valid tool calls, operate under different information presets, and recover after failure in a reproducible runtime. The project stays runner-first so prompts, validation, run logs, benchmarks, and the Streamlit UI all reflect the same execution path.

A model receives a fantasy scene plus a constrained set of visible tools, then must answer with strict JSON:

```json
{"tool_id": "...", "arguments": {...}}
```

The engine validates that output in stages:

1. AST validation: is the JSON well-formed and schema-correct?
2. Hard validation: can this character legally use that tool here?
3. Soft validation: does the action actually succeed in the scene?

The project is built to make model behavior inspectable. You can preview prompts, run a single scene, run full campaigns, benchmark presets and characters, inspect validation output, and use a Streamlit UI as a thin viewer over the same runner logic.

## Why This Repo Exists

AgentQuest is aimed at questions like:

- How much structured reasoning survives in smaller quantized models?
- Does more visible context help, or overload the model?
- Are failures mostly formatting errors, illegal actions, or bad scene reasoning?
- Can the model write useful notes after failure and improve on retry?

Quantized `llama_cpp` runs are still part of the point, not a workaround. The current model catalog keeps selection reproducible across Hugging Face-hosted GGUF variants while preserving cheap, inspectable local-style inference.

## Portfolio Path

If you are reviewing this as a portfolio project, start here:

- Case study: [`docs/case_study.md`](docs/case_study.md)
- LinkedIn post sequence: [`docs/linkedin_series.md`](docs/linkedin_series.md)
- Portfolio artifacts: [`docs/portfolio_assets/README.md`](docs/portfolio_assets/README.md)

Recommended reviewer flow:

1. Read the case study for the benchmark framing.
2. Run `python -m src.runner.preview_prompt` to inspect a prompt without calling a model.
3. Run `python scripts/generate_validation_report.py` to inspect deterministic solvability.
4. Run model-backed benchmarks and combine them with `python scripts/render_benchmark_report.py`.

## What The Repo Can Do

- Load and validate custom AgentQuest runtime data.
- Merge generated Open5e monsters and spells into the runtime data view.
- Build prompt messages with multiple visibility presets.
- Run one scene through a configured model backend.
- Run a full campaign across ordered scenes.
- Run campaigns in continue-on-failure mode for evaluation.
- Run self-learning campaigns that write notes after failures and retry scenes.
- Launch a Streamlit run viewer for campaign and single-scene evaluation.
- Save prompt previews and run logs as JSON.
- Generate deterministic validation coverage reports for scene/character pairs.
- Run benchmark sweeps across campaigns, characters, presets, and prompt formats.
- Render portfolio-ready markdown reports from one or more saved benchmark runs.
- Convert Open5e source data into AgentQuest-ready generated content.

## Current Runtime Scope

- Supported model backend: `llama_cpp`
- Model selection source: `configs/model_catalog.json`
- Default runtime data root: `data/`
- Primary hand-authored dataset: `data/custom/agentquest/`
- Default runs output directory: `runs/`

The runtime is driven by `configs/run_config.json`, with environment variable overrides for data, model, models directory, and run-log paths.

## Current Portfolio Story

The strongest current use of the repo is a small-model reasoning case study:

- run the same campaign slice across at least 3 quantized local models
- compare `BLIND_ADVENTURER`, `BATTLE_PLAN`, and `FULL_INFO`
- inspect where each model fails in the AST, hard-validation, or soft-validation stages
- test whether self-learning notes improve retries in a measurable way

## Install

From the repository root:

```bash
cd C:\Programing\AgentQuest\agentquest
pip install -e .
```

For model-backed runs, install `llama-cpp-python` as well:

```bash
pip install llama-cpp-python
```

`streamlit` is already declared in `pyproject.toml`.

## Configure A Run

The runtime config lives in `configs/run_config.json`:

```json
{
  "backend": "llama_cpp",
  "model": "qwen3_4b_q4_k_m",
  "preset": "TOOL_MANUAL",
  "prompt_format": "json_only"
}
```

Notes:

- `backend` must currently be `llama_cpp`.
- `model` must match a configured alias in `configs/model_catalog.json`.
- `preset` selects a prompt visibility preset.
- `prompt_format` is passed into the prompt builder and runners.

## Environment Variables

- `AGENTQUEST_DATA_DIR`: runtime data root. Defaults to `data/`
- `AGENTQUEST_MODEL`: model alias override
- `AGENTQUEST_RUNS_DIR`: directory for saved run logs. Defaults to `runs/`
- `AGENTQUEST_MODELS_DIR`: legacy local-model directory helper

Model selection now resolves through `configs/model_catalog.json` and `docs/models.md`.

## CLI Entry Points

### Preview A Prompt

Show the exact chat messages that would be sent to the model:

```bash
python -m src.runner.preview_prompt
```

Examples:

```bash
python -m src.runner.preview_prompt --preset BLIND_ADVENTURER
python -m src.runner.preview_prompt --character-id knight.bram --scene-id scene.goblin_den.001_outer_watch
python -m src.runner.preview_prompt --save-json runs/prompt_preview.json
```

Important flags:

- `--data-dir`
- `--character-id`
- `--scene-id`
- `--prompt-format`
- `--preset`
- `--save-json`

`preview_prompt` does not call the model.

### Run One Scene

Run a single scene through the configured model backend:

```bash
python -m src.runner.run_one
```

Examples:

```bash
python -m src.runner.run_one --character-id knight.bram --scene-id scene.goblin_den.001_outer_watch
python -m src.runner.run_one --preset BATTLE_PLAN --save-run runs/one_scene.json
python -m src.runner.run_one --model-key llama_cpp --max-tokens 128 --temperature 0.0
```

Outputs:

- raw model output
- final verdict JSON
- metadata JSON
- optional saved run log

Important flags:

- `--data-dir`
- `--character-id`
- `--scene-id`
- `--prompt-format`
- `--preset`
- `--model-key`
- `--max-tokens`
- `--temperature`
- `--save-run`

### Run One Campaign

Run an ordered campaign through the model backend:

```bash
python -m src.runner.run_campaign
```

Examples:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --continue-on-failure
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --self-learning --per-scene-retry-limit 3 --total-retry-limit 20
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --self-learning --initial-notes "Avoid slashing against skeleton-like enemies."
```

Campaign output includes:

- per-scene statuses
- summary counts
- success rate
- optional stop scene / first failed scene
- final learning notes in self-learning mode
- optional saved campaign run log

Important flags:

- `--data-dir`
- `--campaign-id`
- `--character-id`
- `--prompt-format`
- `--preset`
- `--model-key`
- `--max-tokens`
- `--temperature`
- `--continue-on-failure`
- `--self-learning`
- `--per-scene-retry-limit`
- `--total-retry-limit`
- `--initial-notes`
- `--save-run`

### Manual Validator Harness

There is also a simple interactive script at the repo root:

```bash
python main.py
```

It loads game data, picks a sample character and scene, and lets you paste a raw tool-call JSON string to inspect the validator pipeline manually.

## Streamlit UI

Launch the app with:

```bash
streamlit run streamlit_app.py
```

The UI supports:

- selecting a configured catalog model alias
- selecting a prompt preset
- selecting a character
- campaign mode and single-scene mode
- running the current campaign scene
- stepping through campaign scenes
- running remaining scenes
- resetting and rerunning a full campaign
- self-learning campaign runs with editable initial notes
- saved run logs for single scenes and campaigns
- inspection of raw model output, parsed tool call JSON, validation result, prompt messages, and learning attempts

Campaign mode is the primary UI flow. The app uses shared runner/service logic rather than a separate validation path.

## Prompt Presets

The current prompt presets are defined in `src/prompts/presets.py`:

- `BLIND_ADVENTURER`: basic monster info, normal tool descriptions, useful for hard-mode and self-learning runs
- `TOOL_MANUAL`: basic monster info plus full tool details
- `SCOUT_REPORT`: stronger monster detail, but limited explicit tool mechanics
- `BATTLE_PLAN`: monster stats plus tool effects; default benchmark-friendly mode
- `FULL_INFO`: full debug mode with maximal scene, monster, and tool detail

The default preset constant is `BATTLE_PLAN`.

For prompt-only documentation, see `src/prompts/README.md`.

## Benchmarking And Validation Reports

### Generate A Deterministic Validation Report

Check whether each scene/character pair has at least one valid tool according to the engine:

```bash
python scripts/generate_validation_report.py
```

Optional data-dir override:

```bash
python scripts/generate_validation_report.py --data-dir data
```

This prints:

- valid tool counts per scene/character pair
- invalid tools and reason codes
- a solvability summary

It exits non-zero if any scene/character pair is unsolved.

### Run A Benchmark Sweep

Run model-backed benchmarks across campaigns, characters, presets, and prompt formats:

```bash
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --character-id knight.bram
```

Examples:

```bash
python scripts/run_benchmark.py --all-campaigns --all-characters
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --all-characters --preset BATTLE_PLAN --preset FULL_INFO
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --character-id knight.bram --prompt-format json_only
python scripts/run_benchmark.py --campaign-id campaign.goblin_den_v1 --character-id knight.bram --output-dir runs/benchmarks/manual
```

Benchmark outputs:

- `manifest.json`
- `records.json`
- `summary.json`

The default output directory is timestamped under `runs/benchmarks/`.

### Render A Portfolio Benchmark Report

Combine one or more saved benchmark directories into a markdown summary suitable for documentation or a LinkedIn case study:

```bash
python scripts/render_benchmark_report.py --benchmark-dir runs/benchmarks/model_a --label "Model A" --benchmark-dir runs/benchmarks/model_b --label "Model B" --output docs/portfolio_assets/benchmark_report.md
```

Optional output:

- `--summary-json docs/portfolio_assets/benchmark_report.json`

This is intended for cross-model comparison after you run the same benchmark slice with multiple local models.

## Runtime Data

The normal runtime uses the hand-authored dataset under `data/custom/agentquest/`.

At load time, AgentQuest also merges generated Open5e content for:

- monsters from `data/generated/open5e/monsters.json`
- spells from `data/generated/open5e/tools_spells.json`

Current merge behavior:

- custom records win on exact `monster_id` or `tool_id` collisions
- generated monsters and generated spells are kept when ids differ
- generated weapons are produced by the converter but are not merged into runtime yet
- generated monsters are normalized for runtime validation by defaulting `interactions.escape_allowed` to `true`

## Open5e Pipeline

The repository includes a small data pipeline for Open5e ingestion and conversion.

Layout:

- `data/raw/open5e/`: downloaded source data
- `data/curated/open5e/`: selected subset
- `data/generated/open5e/`: converted AgentQuest-ready data

Commands:

```bash
python -m src.data_pipeline.download_open5e
python -m src.data_pipeline.open5e_converter
python -m src.data_pipeline.open5e_converter --curated
```

Generated outputs:

- `data/generated/open5e/monsters.json`
- `data/generated/open5e/tools_spells.json`
- `data/generated/open5e/tools_weapons.json`

For pipeline-specific details, see `src/data_pipeline/README.md`.

## Docker

The repository includes a local/demo Docker flow for the Streamlit app.

### Build

Create a local environment file:

```bash
copy .env.example .env
```

Build the image:

```bash
docker compose build
```

### Run

Start the app:

```bash
docker compose up
```

Then open `http://localhost:8501`.

### Mounted Volumes

The compose file mounts:

- `./data` to `/app/data`
- `./local_models` to `/app/local_models` as read-only
- `./runs` to `/app/runs`

Example `.env` model alias:

```bash
AGENTQUEST_MODEL=qwen3_4b_q4_k_m
```

Notes:

- `local_models/` is excluded from the Docker build context
- the image installs `llama-cpp-python`
- the container command runs `streamlit run streamlit_app.py`

## Tests

Run the test suite with:

```bash
pytest
```

Current tests cover at least:

- loader merge behavior
- AST, hard, soft, and pipeline validation
- campaign runner behavior
- model registry behavior
- Streamlit utility helpers
- benchmark utility helpers
- Open5e conversion

## Project Layout

```text
agentquest/
|-- configs/
|-- data/
|-- local_models/
|-- runs/
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

Useful module docs:

- `src/engine/README.md`
- `src/prompts/README.md`
- `src/data_pipeline/README.md`

## Practical Notes

- `preview_prompt` is safe for prompt inspection because it does not call the model.
- `run_one`, `run_campaign`, the Streamlit UI, and `scripts/run_benchmark.py` require a valid model config and backend dependency setup.
- Backend overrides are validated against `configs/run_config.json`; the runtime does not support arbitrary backend switching.
- Tool visibility is resolved before prompt building from the character's visible `tool_ids`.
- The Streamlit app is a viewer over runner behavior, not a separate rules engine.
