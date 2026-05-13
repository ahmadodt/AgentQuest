# Prompts Module

This folder contains the prompt construction logic for AgentQuest.

The prompt layer controls what the AI agent sees before choosing a tool. It builds model-facing chat messages from the current character, scene, monster information, and visible tools.

AgentQuest uses this prompt system to make the agent choose exactly one structured tool call:

```json
{"tool_id": "...", "arguments": {...}}
```

The model output is later passed into the validation pipeline.

## Purpose

The prompt system is separated from model inference so that:

- prompt behavior can be tested independently
- formatting bugs can be caught before model integration
- different visibility configurations can be compared cleanly
- knowledge exposure can be controlled

## Architecture Overview

```text
build_messages(...)
    -> PromptConfig
    -> scene renderer
    -> optional monster renderer
    -> tool renderer
```

The system produces OpenAI-style chat messages:

```json
[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."}
]
```

## Prompt Presets

Prompt presets live in:

```text
src/prompts/presets.py
```

Available presets:

- `MINIMAL`
- `MONSTER_BASIC`
- `MONSTER_STATS`
- `MONSTER_FULL`
- `TOOL_CONSTRAINTS`
- `TOOL_EFFECTS`
- `FULL_INFO`

`FULL_INFO` means all currently available prompt metadata is visible. It does not yet mean true tool overload with distractor tools.

## Runner Commands

Run these commands from the repository root:

```bash
cd C:\Programing\AgentQuest\agentquest
```

Preview the prompt:

```bash
python -m src.runner.preview_prompt
```

Examples:

```bash
python -m src.runner.preview_prompt --preset MINIMAL
python -m src.runner.preview_prompt --preset MONSTER_STATS
python -m src.runner.preview_prompt --preset TOOL_EFFECTS
python -m src.runner.preview_prompt --preset FULL_INFO
```

Save a prompt preview:

```bash
python -m src.runner.preview_prompt --preset MINIMAL --save-json runs/prompt_preview.json
```

Related runner commands:

```bash
python -m src.runner.run_one
python -m src.runner.run_campaign
```

`preview_prompt` does not call the model. `run_one` and `run_campaign` do, so they require a working `configs/run_config.json` and model backend dependencies.

## What To Check In A Prompt Preview

- the expected information is visible
- hidden information is actually hidden
- `scene.constraints` are not leaked
- allowed `tool_id` values are correct
- tool schemas are readable
- JSON formatting is clean

## README Changes

This README was updated to:

- point preset documentation at `src/prompts/presets.py`
- replace the outdated preset name with `FULL_INFO`
- add the exact command needed to run `preview_prompt`
- mention the related `run_one` and `run_campaign` commands
