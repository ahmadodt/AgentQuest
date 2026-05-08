# Loader (src/engine/loader.py)

## Purpose
Loads all game JSON files, validates them, and builds fast lookup maps.

## Files Loaded
- tools.json → tools list
- characters.json → characters list
- monsters.json → monsters list
- scenes.json → scenes list

## What It Builds
- tools_by_id
- characters_by_id
- monsters_by_id
- scenes_by_id

(Converts lists into O(1) lookup dictionaries.)

## What It Validates
- Required fields exist
- IDs exist and are unique
- Tool arg schemas are coherent (required ⊆ properties)
- Characters reference valid tool_ids
- Character class matches tool allowed_classes
- Scenes reference valid character_id and monster_id
- Scene `no_escape` matches monster `escape_allowed`

## What It Does NOT Do
- No gameplay logic
- No tool-call validation
- No combat resolution
- No scene execution

It only ensures the world data is structurally valid before the engine runs.


# Validators (src/engine/*)
The validator system is the core rule engine behind AgentQuest.

The LLM chooses an action, but the validator decides whether that action is structurally valid, legally possible, and successful in the current fantasy scene.

## Purpose
Validate an agent/tool output in **layers**, so failures are easy to diagnose:
- **AST validation** = output format + argument correctness
- **Hard validation** = feasibility / permissions (can the character do it?)
- **Soft validation** = situation outcome (does it work in this scene/monster?) *(later)*

This separation lets you tell whether a failure is:
1) bad output shape, 2) illegal action, or 3) bad decision.

---

## Files

### validator_ast.py
**Purpose:** Stage 1 “AST” validation (tool-call structure + args correctness).

**Checks**
- Output is valid JSON
- Must contain exactly: `tool_id` and `arguments`
- `tool_id` exists in tools catalog
- `tool_id` is visible/allowed in the current context (`visible_tool_ids`)
- Required args are present
- No extra args
- Arg types are correct
- Enum / min / max rules are respected (if defined)

**Does NOT**
- Check inventory / traits feasibility
- Check scene/monster outcome logic

---

### validator_hard.py
**Purpose:** Stage 2 hard feasibility validation (permissions + constraints).

**Checks**
- Character exists
- Tool exists (safety check)
- Tool is available to the character (`tool_id in character.tool_ids`)
- Tool class constraint passes (`allowed_classes`)
- Required inventory is present
- Forbidden traits are not present

**Does NOT**
- Parse model output / validate JSON structure
- Validate argument types/enum/min/max (AST already did)
- Decide success/failure vs monster or scene logic

---

### validator_soft.py *(planned)*
**Purpose:** Stage 3 outcome validation (scene + monster rules).

**Examples of checks (later)**
- Escape allowed vs `no_escape` + monster `escape_allowed`
- Damage type modifiers / immunities / weaknesses
- `min_power_to_defeat` logic
- Puzzle/knowledge encounters (e.g. preferred_effects like `knowledge_gain`)

**Does NOT**
- Enforce permissions/constraints that belong to hard validation

---

### validator.py *(optional orchestrator)*
**Purpose:** One entry point that runs the pipeline:
1) AST → 2) Hard → 3) Soft (later)

**Typical output**
- `ast_valid` + error reason if failed
- `hard_valid` + error reason if failed
- `outcome` and reason (once soft validation exists)

---

## Recommended Pipeline (current)
1) Loader builds indexed gamedata (`tools_by_id`, `characters_by_id`, etc.)
2) Runner builds run context:
   - `character_id`
   - `scene_id`
   - `visible_tool_ids` (what the agent is allowed to pick)
3) Validate:
   - AST: shape + args correctness
   - Hard: feasibility/constraints

Soft validation will be added later once scene/monster logic is implemented.


Model Output
     ↓
AST Validator   →  “Is the output structurally correct?”
     ↓
Hard Validator  →  “Is this action legally possible?”
     ↓
Soft Validator  →  “Does this succeed in this situation?” (next step)