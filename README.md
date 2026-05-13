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
python -m src.runner.preview_prompt --preset MINIMAL
```

Save the prompt preview:

```bash
python -m src.runner.preview_prompt --preset MINIMAL --save-json runs/prompt_preview.json
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
