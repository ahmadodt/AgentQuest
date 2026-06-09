# Custom AgentQuest Data

The normal runtime dataset lives in `data/custom/agentquest/`. This data is the primary source for local scenes, characters, campaigns, tools, monsters, and validation-oriented RPG scenarios.

The custom dataset is not a raw copy of external RPG data. Some ideas are inspired by familiar tabletop fantasy patterns, but the records are rewritten for AgentQuest's evaluation goals: constrained tool calls, implicit information, knowledge gating, class and inventory checks, and explainable validation.

## What Belongs Here

- Characters with distinct classes, traits, inventories, and available tools.
- Scenes that require a model to choose one structured action from visible options.
- Campaigns that chain scenes together for retry and note-taking experiments.
- Monsters, hazards, and interactions that support hard and soft validation.
- Hand-authored records that override or specialize generated data when ids collide.

## How It Differs From Open5e Data

Open5e ingestion is a separate pipeline for downloading, curating, and converting external source data. The generated Open5e files are useful as supporting material, but normal AgentQuest development should work from `data/custom/agentquest/`.

Use the custom data when changing playable evaluation scenarios. Use the Open5e pipeline only when the task is specifically about ingestion, conversion, generated data debugging, or dataset cleanup.

## Editing Guidance

- Keep records small enough to inspect and reason about.
- Preserve stable ids unless a migration is intentional.
- Make knowledge gates and hidden information explicit in the data fields that validators and prompts already use.
- Prefer adding focused scenarios over broad data rewrites.
- Run prompt preview, validation reports, or targeted tests after changing scenario data.

## Scene Mechanics

Scenes should describe the objective and local hazards, while tools and monsters provide the reusable mechanics.

- Defeat scenes use combat tool effects such as `damage_type` and `base_power`, then compare the resolved power against the monster's damage modifiers and `interactions.min_power_to_defeat`.
- Knowledge scenes use `validation_rules.mode: "knowledge_check"` and expect a tool with `knowledge_gain` or a `knowledge` effect tag.
- Survival scenes use `validation_rules.mode: "survival_check"` and expect defensive tools with a `defense` effect tag and positive `mitigation`.
- Escape scenes use `validation_rules.mode: "escape_check"`, `escape_attempt`, `allow_escape_as_success`, and monster `interactions.escape_allowed`.
- Hazard scenes use `validation_rules.forbidden_effect_tags` to reject otherwise useful tools in local contexts, such as forbidding `elemental_fire` near powder casks or `elemental_water` on an icy bridge.

Keep `required_effect_tags` and `forbidden_effect_tags` aligned with real tool `effects.effect_tags`. The validator checks exact tag names; it does not infer that a made-up tag should match a related damage type.
