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

### Prompt Presets

AgentQuest uses prompt presets to control how much information the agent receives before choosing a tool. The presets are designed as an analysis ladder: each one targets a different failure mode or reasoning scenario.

- `blind_adventurer`: Shows only basic monster information and normal tool descriptions. This is the hardest mode and is useful for self-learning agent experiments. The agent may make a wrong choice because it does not yet know the monster's weaknesses or resistances. After failing, it can store a note such as "this monster resisted slashing" and try a different damage type in a later run.
- `tool_manual`: Keeps monster information limited, but reveals full tool details such as constraints and effects. This tests whether the agent understands the available tools. For example, the agent may know that one tool does piercing damage and another does slashing damage, but it still does not know which damage type the monster resists.
- `scout_report`: Reveals monster weaknesses, resistances, immunities, and special rules, while keeping tool mechanics mostly implicit. This tests whether the agent can infer the right tool from monster information and natural-language tool descriptions.
- `battle_plan`: Reveals both monster stats and tool effects. This is the default benchmark mode because the correct tool choice should be mechanically inferable. The agent has enough information to compare damage types and choose the tool with the best expected effect.
- `full_info`: Reveals all scene, monster, and tool details, including scene constraints, full monster interactions, and exact tool constraints/effects. This is mainly used as a debug or upper-bound mode, where the agent has maximum information and should make the correct choice unless the prompt or model itself fails.

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
python -m src.runner.preview_prompt --preset BLIND_ADVENTURER
python -m src.runner.preview_prompt --preset SCOUT_REPORT
python -m src.runner.preview_prompt --preset BATTLE_PLAN
python -m src.runner.preview_prompt --preset FULL_INFO
```

Save a prompt preview:

```bash
python -m src.runner.preview_prompt --preset BATTLE_PLAN --save-json runs/prompt_preview.json
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
- `scene.constraints` are hidden unless you are explicitly using `FULL_INFO`
- allowed `tool_id` values are correct
- tool schemas are readable
- JSON formatting is clean

## README Changes

This README was updated to:

- point preset documentation at `src/prompts/presets.py`
- replace the outdated preset examples with the current preset names
- add the exact command needed to run `preview_prompt`
- mention the related `run_one` and `run_campaign` commands
