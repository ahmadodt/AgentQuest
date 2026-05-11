# AgentQuest

AgentQuest is a playable AI-agent RPG where an LLM controls a fantasy character by choosing structured tool calls.

Each scene presents a fantasy encounter. The agent must return strict JSON containing a selected `tool_id` and arguments. A deterministic validation engine checks whether the output is well-formed, legally possible for the character, and successful in the current scene.

The project makes LLM tool use visible: users can inspect the prompt context, selected tool call, validation stages, and final outcome.

## Open5e Conversion

AgentQuest includes a local Open5e conversion path for larger external RPG datasets without changing the live runtime path.

* Raw Open5e JSON files live under `data/raw/open5e/`
* Converted AgentQuest-shaped outputs are written under `data/generated/open5e/`
* Generated files do not overwrite the hand-written `data/*.json` dataset by default
* Conversion is deterministic and uses local JSON files only
* Monster weaknesses, resistances, and immunities come only from structured Open5e fields
* Description fields are copied in full with no summarization or truncation
* No free-text inference is done yet for monster damage modifiers

Run the converter with:

```bash
python -m src.data_pipeline.open5e_converter
```

This writes:

* `data/generated/open5e/monsters.json`
* `data/generated/open5e/tools_spells.json`
* `data/generated/open5e/tools_weapons.json`

The main runtime still loads `data/tools.json`, `data/characters.json`, `data/monsters.json`, and `data/scenes.json`, so the current one-run flow remains unchanged. A later enrichment step can add smarter extraction if needed, but the baseline converter is intentionally simple and explainable.

## What Is AgentQuest?

AgentQuest is an experimental framework for analyzing how AI agents:

* Select tools from a constrained set
* Respect structural and logical constraints
* Fail due to syntax, feasibility, or reasoning errors
* Make suboptimal but valid decisions

The system is intentionally layered to separate:

1. World structure validation
2. Tool-call syntax validation
3. Character/tool feasibility checks
4. Scene and monster outcome logic

This design makes agent failures easier to diagnose and measure.

---

## Core Concepts

AgentQuest separates validation into stages.

### AST Validation

Ensures the model output is structurally correct and matches the tool schema.

This stage checks that:

* The output is valid JSON
* The response contains exactly `tool_id` and `arguments`
* The selected tool exists
* The selected tool is visible in the current context
* Required arguments are present
* Extra arguments are rejected
* Argument types, enums, and numeric limits are valid

### Hard Validation

Ensures the selected tool is legally available to the character.

This stage checks:

* The character exists
* The tool exists
* The tool is available to the character
* Class restrictions are satisfied
* Required inventory items are present
* Forbidden traits are not present

### Soft Validation

Determines whether the chosen action succeeds in the current scene.

This stage handles scene-level outcome logic such as:

* Escape attempts
* Knowledge-based encounters
* Monster defeat checks
* Damage type modifiers
* Minimum power thresholds

This layered approach allows distinguishing between:

* Malformed output
* Illegal actions
* Valid but ineffective decisions
* Successful actions

---

## Project Structure

```text
agentquest/
│
├── main.py
├── README.md
│
├── data/                # Static world definition
│   ├── tools.json
│   ├── characters.json
│   ├── monsters.json
│   └── scenes.json
│
├── src/
│   └── engine/          # Core engine logic
│       ├── loader.py
│       ├── validator.py
│       ├── validator_ast.py
│       ├── validator_hard.py
│       ├── validator_soft.py
│       ├── validator_utils.py
│       └── README.md
│
├── tests/               # Automated tests for loader and validators
│
├── prompts/             # Agent prompt templates
├── runs/                # Execution logs
└── utils/               # Shared utilities
