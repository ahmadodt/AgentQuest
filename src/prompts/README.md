Prompts Module

This folder contains prompt construction logic for AgentQuest.

The purpose of this module is to generate model-facing prompts (chat messages) in a controlled, configurable way.

The prompt system is intentionally separated from model inference so that:

Prompt behavior can be tested independently.

Formatting bugs can be caught before model integration.

Different visibility configurations can be benchmarked cleanly.

Future experiments (knowledge gating, overload, constraint leakage) are easy to implement.

Architecture Overview

Prompt generation follows this structure:

build_messages(...)
    ├── PromptConfig (controls visibility)
    ├── Scene renderer
    ├── Optional monster renderer
    └── Tool renderer

The system produces OpenAI-style chat messages:

[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."}
]

The model is required to output:

{"tool_id": "...", "arguments": {...}}

Strict JSON formatting is enforced.

Files
prompt_config.py

Defines the PromptConfig dataclass.

This controls exactly what information appears in the prompt.

Key configuration options include:

Character

include_inventory

include_traits

Scene

include_scene_id

include_title

include_location

include_narrative

include_monster_id

include_knowledge_level

include_success_condition

include_failure_condition

Note: scene.constraints are intentionally not rendered.

Monster Detail Levels

Controlled by:

monster_detail_level: "none" | "basic" | "stats" | "full"

none: no monster information

basic: name, type, description

stats: + tags, weaknesses, resistances, immunities, special_rules, escape_allowed

full: + full interactions data (damage modifiers, min power, etc.)

UI data is never shown in prompts.

Tools

tools_include_label_emoji

tools_include_constraints

tools_include_effects

Tool descriptions and argument schemas are always included.

base_prompt.py

Single entrypoint for prompt construction.

build_messages(
    scene,
    character,
    visible_tools,
    gamedata=None,
    prompt_format="json_only",
    cfg=None
)

Routes to a specific format implementation in formats/.

formats/json_only.py

Strict JSON-output prompt template.

Responsibilities:

Enforce "JSON only" output.

Require exactly two keys: tool_id and arguments.

Force double-quoted JSON.

Reject any additional text.

Print allowed tool_ids as a JSON array.

Render scene, optional monster info, and tool schemas according to PromptConfig.

This is the default and recommended format for AST + Hard validation testing.

tool_renderers/compact_tools.py

Renders visible tools in a compact, structured format:

tool_id

optional label/emoji

description

required arguments

argument schema (type / enum / min / max)

optional constraints

optional effects

All lists are printed as proper JSON arrays (no single quotes).

Tool renderers are isolated so we can later experiment with:

compact vs verbose listings

ordering/grouping strategies

constraint leakage experiments

effect visibility experiments

Prompt Presets

Prompt presets live in:

configs/prompt_presets.py

Each preset is a PromptConfig instance.

Example:

PROMPT_MINIMAL = PromptConfig(
    include_scene_id=False,
    include_title=False,
    include_location=False,
    monster_detail_level="none",
)

Preview runner supports:

--preset PRESET_NAME
Testing

Use:

python -m src.runner.preview_prompt

Examples:

python -m src.runner.preview_prompt --preset default
python -m src.runner.preview_prompt --preset PROMPT_MINIMAL
python -m src.runner.preview_prompt --character-id wizard.ember --scene-id scene.001.goblin_alley

Optional:

--save-json runs/prompt_preview.json

This prints the exact system/user messages that would be sent to the model.

Design Principles

Prompt behavior is deterministic.

All visibility is configurable.

No UI fields leak into prompts.

JSON formatting is standardized.

Scene constraints are not part of the prompt.

Tool argument schemas are always visible.

Monster detail exposure is controlled explicitly.

This makes the prompt layer:

Experiment-ready

Benchmark-friendly

Easy to evolve

Isolated from inference logic