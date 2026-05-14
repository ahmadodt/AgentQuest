# AgentQuest

AgentQuest is a playable AI-agent RPG where an LLM controls a fantasy character by choosing structured tool calls.

Each scene presents a fantasy encounter. The agent must return strict JSON containing a selected `tool_id` and arguments. A deterministic validation engine checks whether the output is well-formed, legally possible for the character, and successful in the current scene.

The project makes LLM tool use visible: you can inspect the prompt context, selected tool call, validation stages, and final outcome.

## Running The Runners

Run all commands from the repository root:

```bash
cd C:\Programing\AgentQuest\agentquest
```

### Preview The Prompt

Show the exact messages that would be sent to the model:

```bash
python -m src.runner.preview_prompt
```

Example:

```bash
python -m src.runner.preview_prompt --preset BATTLE_PLAN
```

Save the prompt preview:

```bash
python -m src.runner.preview_prompt --preset BLIND_ADVENTURER --save-json runs/prompt_preview.json
```

### Run One Scene

Run one scene through the configured model backend:

```bash
python -m src.runner.run_one
```

Example:

```bash
python -m src.runner.run_one --character-id knight.bram --scene-id scene.goblin_den.001_outer_watch
```

### Run One Campaign

Run a full campaign through the configured model backend:

```bash
python -m src.runner.run_campaign
```

Example:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram
```

Evaluation-style example that continues after failures:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --continue-on-failure
```

Self-learning example with note writing and retries:

```bash
python -m src.runner.run_campaign --campaign-id campaign.goblin_den_v1 --character-id knight.bram --preset BLIND_ADVENTURER --self-learning --per-scene-retry-limit 3 --total-retry-limit 20
```

### Run The Streamlit Viewer

Install Streamlit if it is not already available:

```bash
pip install streamlit
```

Launch the run viewer:

```bash
streamlit run src/app/ui_streamlit.py
```

The viewer lets you choose:

- a local GGUF model from `local_models/`
- a campaign-first run flow with character selection
- an optional single-scene mode
- a character
- either a campaign or a single scene

The Streamlit app keeps the configured prompt settings from `configs/run_config.json`, uses the selected local GGUF model as a runtime override, and shows ordered campaign progress with per-scene PASS/FAIL results. If `preset` is omitted, it falls back to `BATTLE_PLAN`.
Campaign mode also supports a self-learning run toggle that lets the same model update campaign notes after failed attempts and reuse them on retries.

### Runner Requirements

- `preview_prompt` does not call the model
- `run_one` and `run_campaign` require a valid `configs/run_config.json`
- the configured backend currently expects a local `.gguf` model path
- install `llama-cpp-python` when using the `llama_cpp` backend

## Runtime Data

The runtime uses the hand-authored dataset under `data/custom/agentquest/`.

At load time, AgentQuest also merges in curated generated Open5e content for:

- monsters from `data/generated/open5e/monsters.json`
- spells from `data/generated/open5e/tools_spells.json`

Current merge rules:

- custom records win on exact `monster_id` or `tool_id` collisions
- generated monsters and generated spells are kept alongside custom records when ids differ
- generated weapons are not merged into the runtime yet
- generated monsters are normalized for runtime validation by defaulting `interactions.escape_allowed` to `true`

## Open5e Conversion

Open5e data flow:

- `data/raw/open5e/` = downloaded source data
- `data/curated/open5e/` = selected benchmark subset
- `data/generated/open5e/` = converted AgentQuest-ready data

Commands:

```bash
python -m src.data_pipeline.download_open5e
python -m src.data_pipeline.open5e_converter
python -m src.data_pipeline.open5e_converter --curated
```

This writes:

- `data/generated/open5e/monsters.json`
- `data/generated/open5e/tools_spells.json`
- `data/generated/open5e/tools_weapons.json`

## Core Concepts

AgentQuest separates validation into stages:

1. AST validation
2. Hard validation
3. Soft validation

This separation makes failures easier to diagnose:

- malformed output
- illegal actions
- valid but ineffective decisions
- successful actions

## Project Structure

```text
agentquest/
|-- main.py
|-- README.md
|-- configs/
|-- data/
|   |-- custom/
|   |   `-- agentquest/
|   |-- curated/
|   |   `-- open5e/
|   |-- generated/
|   |   `-- open5e/
|   `-- raw/
|       `-- open5e/
|-- src/
|   |-- data_pipeline/
|   |-- engine/
|   |-- models/
|   |-- prompts/
|   `-- runner/
|-- tests/
`-- runs/
```

## Notes

- loader = load + merge + validate runtime data
- projector = shrink runtime data into the model-facing view
- prompt builder = assemble final messages from character, scene, monster, and visible tool data
- tool visibility is determined before prompt building from the character's `tool_ids`

## README Changes

This README was updated to:

- add the exact commands for `preview_prompt`, `run_one`, and `run_campaign`
- show example invocations for each runner
- document the requirements needed to run the model-backed runners
