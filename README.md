
# AgentQuest

AgentQuest is a playable AI-agent RPG where an LLM controls a fantasy character by choosing structured tool calls.

Each scene presents a fantasy encounter. The agent must return strict JSON containing a selected `tool_id` and arguments. A deterministic validation engine checks whether the output is well-formed, legally possible for the character, and successful in the current scene.

The project makes LLM tool use visible: users can see the prompt context, selected tool call, validation stages, and final outcome.

## What Is AgentQuest?

AgentQuest is an experimental framework for analyzing how AI agents:

* Select tools from a constrained set
* Respect structural and logical constraints
* Fail due to syntax, feasibility, or reasoning errors
* Make suboptimal but valid decisions

The system is intentionally layered to clearly separate:

1. World structure validation
2. Tool-call syntax validation
3. Feasibility constraints
4. Scene/monster outcome logic (planned)

This design makes agent failures diagnosable and measurable.

---

## Core Concepts

AgentQuest separates validation into stages:

### AST Validation

Ensures the model output is structurally correct and matches the tool schema.

### Hard Validation

Ensures the character is allowed to use the selected tool
(inventory, traits, permissions).

### Soft Validation *(planned)*

Determines whether the chosen action succeeds within the scene context.

This layered approach allows distinguishing between:

* Malformed output
* Illegal actions
* Poor decisions

---

## Project Structure

```
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
│       ├── validator_ast.py
│       ├── validator_hard.py
│       ├── validator.py
│       └── README.md
│
├── tests/               # Unit tests (AST + Hard validation)
│
├── prompts/             # Agent prompt templates (future)
├── runs/                # Execution logs (future)
└── utils/               # Utilities (future)
```

---

## Engine Overview

### Loader

Loads JSON world data, validates structural integrity, and builds indexed lookup maps.

### Validators

* `validator_ast.py` → tool-call structure + argument correctness
* `validator_hard.py` → character/tool feasibility checks
* `validator.py` → orchestrates validation stages

---

## How to Run

Load and test the engine:

```bash
python main.py
```

Run automated tests:

```bash
pytest -q
```

---

## Design Philosophy

* Deterministic
* Layered validation
* Fail-fast data integrity
* Explicit separation of syntax, feasibility, and reasoning
* Built for experimentation and analysis




