# Prompts Module

This folder contains prompt construction logic for AgentQuest.

The goal is to generate model-facing prompts (usually chat messages) that:
- describe the current character + scene,
- list the visible tools and their argument schemas,
- enforce strict output formatting (JSON tool call).

This is intentionally separated from model calling so prompt bugs can be tested in isolation.

## Files

### `base_prompt.py`
Single entrypoint for building prompts.
- `build_messages(scene, character, visible_tools, prompt_format=...) -> List[{role, content}]`

Routes to a specific format in `formats/`.

### `formats/json_only.py`
Strict JSON-output prompt template.
- Instructs the model to output **ONLY** a JSON object of shape:
  `{"tool_id": "...", "arguments": {...}}`
- No prose, no markdown.
- If a tool has no args, `arguments` must be `{}`.

### `tool_renderers/compact_tools.py`
Renders the visible tool list into a compact, readable block:
- tool_id
- description (if available)
- required args
- arg schema summary (type / enum / min / max)

Tool renderers exist so we can later experiment with:
- compact vs verbose listings
- different ordering/grouping
- adding UI emojis or labels (optional, for readability)

## Testing

Use:

`python -m src.runner.preview_prompt`

This prints the generated system/user messages for a chosen `(character_id, scene_id)` and optionally saves them as JSON.