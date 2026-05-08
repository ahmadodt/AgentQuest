# Loader (`src/engine/loader.py`)

## Purpose

Loads all game JSON files, validates them, and builds fast lookup maps.

## Files Loaded

- `tools.json` → tools list
- `characters.json` → characters list
- `monsters.json` → monsters list
- `scenes.json` → scenes list

## What It Builds

- `tools_by_id`
- `characters_by_id`
- `monsters_by_id`
- `scenes_by_id`

These convert list-based JSON data into O(1) lookup dictionaries.

## What It Validates

- Required fields exist
- IDs exist and are unique
- Tool argument schemas are coherent (`required ⊆ properties`)
- Characters reference valid `tool_ids`
- Character class matches tool `allowed_classes`
- Scenes reference valid `character_id` and `monster_id`
- Scene `no_escape` is consistent with monster `escape_allowed`

## What It Does NOT Do

- No gameplay execution
- No model/tool-call validation
- No combat resolution
- No scene outcome calculation

The loader only ensures the world data is structurally valid before the engine runs.

---

# Validators (`src/engine/*`)

The validator system is the core rule engine behind AgentQuest.

The LLM chooses an action, but the validator decides whether that action is structurally valid, legally possible, and successful in the current fantasy scene.

## Purpose

Validate an agent/tool output in layers, so failures are easy to diagnose:

- **AST validation** = output format and argument correctness
- **Hard validation** = feasibility and permissions: can the character do it?
- **Soft validation** = scene outcome: does it work in this situation?

This separation lets the engine distinguish between:

1. Bad output shape
2. Illegal action
3. Valid but ineffective decision
4. Successful action

---

## Files

### `validator_ast.py`

**Purpose:** Stage 1 AST validation: tool-call structure and argument correctness.

**Checks**

- Output is valid JSON
- Output contains exactly `tool_id` and `arguments`
- `tool_id` exists in the tools catalog
- `tool_id` is visible/allowed in the current context through `visible_tool_ids`
- Required arguments are present
- Extra arguments are rejected
- Argument types are correct
- Enum, minimum, and maximum rules are respected when defined

**Does NOT**

- Check inventory or trait feasibility
- Check character permissions
- Check scene or monster outcome logic

---

### `validator_hard.py`

**Purpose:** Stage 2 hard feasibility validation: permissions and constraints.

**Checks**

- Character exists
- Tool exists as a safety check
- Tool is available to the character: `tool_id in character.tool_ids`
- Tool class constraint passes through `allowed_classes`
- Required inventory is present
- Forbidden traits are not present

**Does NOT**

- Parse model output or validate JSON structure
- Validate argument types, enums, minimums, or maximums
- Decide whether the action succeeds against the scene or monster

---

### `validator_soft.py`

**Purpose:** Stage 3 soft outcome validation: scene and monster result logic.

**Checks**

- Escape attempts against scene `no_escape` rules
- Escape attempts against monster `escape_allowed` rules
- Knowledge encounters using effects like `knowledge_gain`
- Monster defeat checks using `base_power`, `damage_type`, modifiers, and `min_power_to_defeat`

**Does NOT**

- Parse model output
- Check tool schema correctness
- Enforce character permissions, inventory, or trait constraints

---

### `validator_utils.py`

**Purpose:** Shared helper functions for validator modules.

**Contains helpers for**

- Building invalid verdict dictionaries
- Looking up characters, tools, scenes, and monsters
- Reading tool constraints and effects
- Computing effective attack power against monster modifiers

---

### `validator.py`

**Purpose:** Contains the `ToolCallValidator` pipeline class.

The pipeline runs:

```text
AST validation → hard validation → soft validation → final verdict