# Architecture

AgentQuest is a runner-first evaluation app. The UI is intentionally thin: it calls shared runner and benchmark services instead of reimplementing prompt construction, model calls, validation, or campaign rules.

## Core Flow

```text
data files
  -> loader
  -> prompt builder
  -> model backend
  -> validator pipeline
  -> runner result / run log / Streamlit display
```

The model sees an RPG scene and a constrained list of visible tools. It must return one JSON object:

```json
{"tool_id": "...", "arguments": {...}}
```

The validator then decides whether that tool call is parseable, legal, and successful.

## Main Subsystems

- `src/engine/`: game-data loading and validation pipeline.
- `src/prompts/`: prompt configuration, projections, and message rendering.
- `src/models/`: model catalog, runtime model config, and backend adapters.
- `src/runner/`: CLI runners, shared execution helpers, benchmark services, and report utilities.
- `src/app/`: Streamlit UI entrypoints and mode renderers.
- `configs/`: runtime config and model catalog.
- `data/custom/agentquest/`: primary hand-authored runtime dataset.

## Validation Layers

AgentQuest separates failures into three layers:

- AST validation: JSON shape, known tool id, visible tool id, argument schema.
- Hard validation: character permissions, class constraints, inventory, forbidden traits.
- Soft validation: scene outcome, monster interactions, escape rules, knowledge checks, and combat effectiveness.

This separation keeps benchmark results explainable. A run can fail because the model ignored the output interface, chose an illegal action, or chose a legal but ineffective action.

## Runtime Data

The normal runtime uses hand-authored data under `data/custom/agentquest/`.

Generated Open5e content can be merged into the runtime view:

- generated monsters from `data/generated/open5e/monsters.json`
- generated spells from `data/generated/open5e/tools_spells.json`

Custom records win on exact id collisions. Generated weapons are produced by the converter but are not part of the runtime merge yet.

## Streamlit Boundary

The Streamlit UI should remain a viewer and controller over existing runtime services. It should not become the source of truth for:

- prompt construction
- validation rules
- campaign execution
- benchmark aggregation
- model backend selection

When UI behavior needs runner behavior, add or reuse shared service functions in `src/runner/`.
