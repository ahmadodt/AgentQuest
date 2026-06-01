# Engine Module

The engine layer loads game data and validates model-selected tool calls. It does not call models, build prompts, or render UI.

## Loader

`src/engine/loader.py` loads runtime JSON data, validates it, and builds lookup maps.

Loaded records:

- `tools.json` -> tools list
- `characters.json` -> characters list
- `monsters.json` -> monsters list
- `scenes.json` -> scenes list
- `campaigns.json` -> campaign list when present

Lookup maps:

- `tools_by_id`
- `characters_by_id`
- `monsters_by_id`
- `scenes_by_id`
- `campaigns_by_id`

Loader validation checks:

- required fields exist
- ids exist and are unique
- tool argument schemas are coherent (`required` is a subset of `properties`)
- characters reference valid `tool_ids`
- character class matches tool `allowed_classes`
- scenes reference valid monsters
- scene escape rules are consistent with monster escape rules

The loader only ensures the world data is structurally valid before runners execute.

## Validator Pipeline

The validator system is the deterministic rule engine behind AgentQuest. The LLM chooses an action, then the validator decides whether that action is structurally valid, legally possible, and successful in the current scene.

Pipeline:

```text
AST validation -> hard validation -> soft validation -> final verdict
```

This separation keeps failures easy to diagnose:

- AST validation: bad JSON, unknown tool, invisible tool, or invalid arguments.
- Hard validation: legal tool-call shape, but the character cannot use the tool.
- Soft validation: legal action, but it does not solve the scene.

## Validator Files

`validator.py` contains `ToolCallValidator`, the pipeline class that coordinates all validation stages.

`validation/validator_ast.py` checks:

- output is valid JSON
- output contains exactly `tool_id` and `arguments`
- `tool_id` exists in the tool catalog
- `tool_id` is visible in the current context
- required arguments are present
- extra arguments are rejected
- argument types, enums, minimums, and maximums are respected

`validation/validator_hard.py` checks:

- character exists
- tool exists
- tool is assigned to the character
- class constraints pass
- required inventory is present
- forbidden traits are absent

`validation/validator_soft.py` checks:

- escape attempts against scene and monster rules
- knowledge encounters
- monster defeat using `base_power`, `damage_type`, modifiers, and `min_power_to_defeat`
- scene objective and effect-tag rules

`validation/validator_utils.py` contains shared lookup, verdict, constraint, effect, and power-calculation helpers.

## Boundaries

The engine does not:

- call model backends
- construct prompts
- render Streamlit UI
- write benchmark reports
- decide campaign ordering

Those responsibilities live in `src/models/`, `src/prompts/`, `src/app/`, and `src/runner/`.
