# Prompts Module

This folder contains the prompt construction logic for AgentQuest.

The prompt layer controls what the AI agent sees before choosing a tool. It builds model-facing chat messages from the current character, scene, monster information, and visible tools.

AgentQuest uses this prompt system to make the agent choose exactly one structured tool call:

```json
{"tool_id": "...", "arguments": {...}}
```

The model output is later passed into the validation pipeline.

---

## Purpose

The prompt system is separated from model inference so that:

- prompt behavior can be tested independently,
- formatting bugs can be caught before model integration,
- different visibility configurations can be compared cleanly,
- knowledge exposure can be controlled,
- future modes like tool overload and constraint visibility can be added safely.

The prompt layer answers:

> What information does the agent receive before it chooses a tool?

The validators answer:

> Was the chosen tool call valid, legal, and successful?

---

## Architecture Overview

Prompt generation follows this structure:

```text
build_messages(...)
    ├── PromptConfig
    ├── Scene renderer
    ├── Optional monster renderer
    └── Tool renderer
```

The system produces OpenAI-style chat messages:

```json
[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."}
]
```

The default prompt format is strict JSON-only output.

---

## Files

### `prompt_config.py`

Defines the `PromptConfig` dataclass.

This controls exactly what information appears in the prompt.

Character options:

- `include_inventory`
- `include_traits`

Scene options:

- `include_scene_id`
- `include_title`
- `include_location`
- `include_narrative`
- `include_monster_id`
- `include_knowledge_level`
- `include_success_condition`
- `include_failure_condition`

Important:

```text
scene.constraints are intentionally not rendered.
```

This avoids leaking hidden validator logic directly into the prompt.

---

### Monster Detail Levels

Monster visibility is controlled by:

```python
monster_detail_level: "none" | "basic" | "stats" | "full"
```

Levels:

```text
none  → no monster information
basic → name, type, description
stats → tags, weaknesses, resistances, immunities, special_rules, escape_allowed
full  → full interaction data, such as damage modifiers and minimum power rules
```

UI data is never shown in prompts.

---

### Tool Visibility Options

Tool descriptions and argument schemas are always included.

Optional tool fields:

- `tools_include_label_emoji`
- `tools_include_constraints`
- `tools_include_effects`

This allows testing whether models perform better when they see only tool schemas or when they also see constraints and effects.

---

### `base_prompt.py`

Main entrypoint for prompt construction.

```python
build_messages(
    scene,
    character,
    visible_tools,
    gamedata=None,
    prompt_format="json_only",
    cfg=None,
)
```

This function routes to a specific prompt format implementation in `formats/`.

Currently supported:

```text
json_only
```

---

### `formats/json_only.py`

Strict JSON-output prompt template.

Responsibilities:

- enforce JSON-only output,
- require exactly two keys: `tool_id` and `arguments`,
- force double-quoted JSON,
- reject any extra text or markdown,
- print allowed `tool_id` values as a JSON array,
- render scene information according to `PromptConfig`,
- render optional monster information,
- render visible tool schemas.

This is the default prompt format for AgentQuest.

---

### `tool_renderers/compact_tools.py`

Renders visible tools in a compact, structured format.

Each tool can include:

- `tool_id`
- optional label/emoji
- description
- required arguments
- argument schema
- optional constraints
- optional effects

All lists are rendered as valid JSON arrays.

This renderer is isolated so the project can later test:

- compact vs verbose tool listings,
- different tool ordering strategies,
- grouped tools,
- constraint visibility,
- effect visibility,
- overloaded tool lists.

---

## Prompt Presets

Prompt presets currently live in:

```text
configs/prompt_presets.py
```

Each preset is a `PromptConfig` instance.

Available presets:

```text
MINIMAL
MONSTER_BASIC
MONSTER_STATS
MONSTER_FULL
TOOL_CONSTRAINTS
TOOL_EFFECTS
OVERLOAD_ALL
```

### Current Meaning of Each Preset

| Preset | Purpose |
|---|---|
| `MINIMAL` | Basic character state, scene narrative, success condition, and tool schemas |
| `MONSTER_BASIC` | Adds monster name, type, and description |
| `MONSTER_STATS` | Adds monster weaknesses, resistances, tags, and escape information |
| `MONSTER_FULL` | Adds full monster interaction data |
| `TOOL_CONSTRAINTS` | Shows tool constraints such as class and inventory requirements |
| `TOOL_EFFECTS` | Shows tool effects such as damage type or escape attempt |
| `OVERLOAD_ALL` | Shows all currently available metadata |

Note:

```text
OVERLOAD_ALL currently means “all metadata visible.”
It does not yet mean true tool overload with many distractor tools.
True overload will be added later by expanding the visible tool list.
```

---

## Testing Prompt Output

Use the preview runner:

```bash
python -m src.runner.preview_prompt
```

Examples:

```bash
python -m src.runner.preview_prompt --preset MINIMAL
python -m src.runner.preview_prompt --preset MONSTER_BASIC
python -m src.runner.preview_prompt --preset MONSTER_STATS
python -m src.runner.preview_prompt --preset MONSTER_FULL
python -m src.runner.preview_prompt --preset TOOL_CONSTRAINTS
python -m src.runner.preview_prompt --preset TOOL_EFFECTS
python -m src.runner.preview_prompt --preset OVERLOAD_ALL
```

Optional:

```bash
python -m src.runner.preview_prompt --preset MINIMAL --save-json runs/prompt_preview.json
```

This prints the exact system and user messages that would be sent to the model.

---

## What To Check When Previewing Prompts

For each preset, check:

- the expected information is visible,
- hidden information is actually hidden,
- `scene.constraints` are not leaked,
- allowed `tool_id` values are correct,
- tool schemas are readable,
- enum values are shown correctly,
- JSON formatting is clean,
- the prompt is not unnecessarily long,
- the output instruction is clear.

---

## Design Principles

The prompt system should stay:

- deterministic,
- configurable,
- isolated from model inference,
- easy to inspect,
- compatible with strict JSON validation,
- useful for comparing prompt visibility levels.

The prompt layer should not decide whether a tool call is correct.

It only controls what the model sees.

Correctness belongs to the validation pipeline.

---

## Current Status

Implemented:

- `PromptConfig`
- strict JSON-only prompt format
- scene rendering
- optional monster rendering
- compact tool rendering
- prompt presets
- prompt preview runner
- save-to-JSON preview option

Working presets:

- `MINIMAL`
- `MONSTER_BASIC`
- `MONSTER_STATS`
- `MONSTER_FULL`
- `TOOL_CONSTRAINTS`
- `TOOL_EFFECTS`
- `OVERLOAD_ALL`

---

## Small Next Steps

1. Save prompt previews for the main presets.

```bash
python -m src.runner.preview_prompt --preset MINIMAL --save-json runs/prompt_minimal.json
python -m src.runner.preview_prompt --preset MONSTER_STATS --save-json runs/prompt_monster_stats.json
python -m src.runner.preview_prompt --preset TOOL_EFFECTS --save-json runs/prompt_tool_effects.json
python -m src.runner.preview_prompt --preset OVERLOAD_ALL --save-json runs/prompt_full_info.json
```

2. Manually inspect the saved prompts.

Check whether each preset exposes exactly the intended information.

3. Test one mock model output against the full validator pipeline.

Example:

```json
{"tool_id":"knight.sword_slash","arguments":{"target":"goblin.street_cutpurse"}}
```

4. Add a simple model backend interface.

Start with a local/Ollama backend or a mock backend.

5. Run one real model on one scene.

Measure:

- raw output,
- JSON validity,
- AST pass/fail,
- hard validation pass/fail,
- soft validation pass/fail,
- final outcome,
- latency.

6. After that, compare presets on the same scene.

Start small before adding more scenes or true tool overload.
