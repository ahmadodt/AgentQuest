# AgentQuest Data And Validation Mechanics Plan

## Purpose

AgentQuest is a deterministic tool-use benchmark wrapped in a playable RPG. The game framing is useful because it makes the dataset easier to reason about, expand, and demo, but the benchmark goal is narrower:

- Can a small local model emit one valid structured tool call?
- Can it choose from the tools visible to the current character?
- Can it infer which tool mechanics solve the current scene?
- Can it recover from failure when prompts, notes, or retries give it more information?

The dataset should grow as a rule-driven system, not as a hand-written answer key. A scene should not need to list every winning tool for every character. Instead, tools declare what they do, monsters declare how they respond, scenes declare what kind of objective must be satisfied, and the validator derives success from those mechanics.

## Design Principle

A correct answer is not "the model picked a tool from a prewritten winning list."

A correct answer is:

1. The model returned strict JSON in the expected shape.
2. The selected `tool_id` exists and is visible in the current prompt context.
3. The tool arguments match the tool schema.
4. The character can legally use the selected tool.
5. The tool's effects satisfy the scene objective under the monster and scene rules.

This keeps the benchmark scalable. If a new tool is added later, it should automatically become valid in any scene where its effects satisfy the same rules. If a new monster or hazard is added, it should interact with existing tools through damage profiles, effect tags, escape rules, and objective modes.

## Validation Layers

AgentQuest should keep the current layered validation model because it makes failures explainable.

### AST Validation

AST validation checks whether the model produced a valid tool-call object.

It answers: did the model follow the interface?

Failures here test structured output behavior:

- invalid JSON
- missing top-level keys
- extra top-level keys
- unknown `tool_id`
- invisible tool
- missing required arguments
- extra arguments
- wrong argument types
- enum, minimum, or maximum violations

This layer is about function-calling discipline, not tactical quality.

### Hard Validation

Hard validation checks whether the chosen action is legally available to the current character.

It answers: can this character do this action at all?

Failures here test whether the model respects tool availability and character constraints:

- unknown character
- tool not assigned to the character
- character class not allowed
- missing required inventory
- blocked by forbidden traits

This layer should stay independent of scene outcome. A knight can legally swing a sword even if the sword is a bad answer for the scene.

### Soft Validation

Soft validation checks whether the legal action solves the current encounter.

It answers: was this a good decision for this scene?

Failures here test situational reasoning:

- choosing a non-combat tool in a defeat scene
- using a damage type the monster resists too strongly
- attacking a knowledge puzzle
- trying to escape when escape is not the objective
- using a forbidden effect in a hazard scene
- defending when the scene requires retreat

This layer is where the RPG mechanics become benchmark signals.

## Data Contracts

The data should stay simple JSON, but each object type should have a clear role.

### Tools

Tools describe capabilities. They are not scene-specific answers.

Important fields:

- `tool_id`: stable identifier used by model output
- `category`: broad grouping such as `attack`, `defense`, `utility`, or `movement`
- `args`: JSON-style argument schema used by AST validation
- `constraints.allowed_classes`: classes allowed to use the tool
- `constraints.required_inventory`: inventory needed for hard validation
- `constraints.forbidden_traits`: character states that block the tool
- `effects`: mechanical behavior used by soft validation

Important effect fields:

- `combat_effect`: whether this is a combat action
- `damage_type`: damage family such as `slashing`, `fire`, `water`, or `magic`
- `base_power`: raw power before monster modifiers
- `knowledge_gain`: whether the tool can solve knowledge encounters
- `mitigation`: defensive strength for survival encounters
- `escape_attempt`: whether the tool attempts to leave the encounter
- `effect_tags`: extensible semantic tags used by scene rules

Tool effects should be general. For example, a new lightning spell should not say "beats scene X." It should declare fields such as `damage_type`, `base_power`, `combat_effect`, and tags such as `ranged`, `magical`, `elemental_lightning`, or `single_target`.

### Monsters

Monsters describe how targets respond to tool mechanics.

Important fields:

- `damage_profile`: default damage modifiers
- `damage_modifier_overrides`: monster-specific modifier changes
- `interactions.min_power_to_defeat`: threshold for defeat scenes
- `interactions.escape_allowed`: whether escape can work against this monster
- `weaknesses`, `resistances`, `immunities`: model-facing explanation fields
- `tags` and `special_rules`: model-facing hints and analysis labels

Damage profiles are the main scalable combat mechanism. A tool's effective power is:

```text
effective_power = tool.effects.base_power * monster.resolved_damage_modifier[tool.effects.damage_type]
```

The monster is defeated when `effective_power >= min_power_to_defeat`.

### Scenes

Scenes describe objectives and local constraints.

Important fields:

- `success_condition.type`: broad goal, such as `defeat_monster` or `solve_encounter`
- `constraints.no_escape`: local hard scene rule for escape attempts
- `validation_rules.mode`: soft-validation mode
- `validation_rules.allow_escape_as_success`: whether escape can satisfy the objective
- `validation_rules.required_effect_tags`: tags the tool must provide
- `validation_rules.forbidden_effect_tags`: tags that fail the scene even if other mechanics look valid

Scenes should describe what kind of solution is needed, not which tool is correct.

Good scene rule:

```json
{
  "success_condition": {"type": "solve_encounter"},
  "validation_rules": {
    "mode": "knowledge_check",
    "required_effect_tags": ["knowledge"],
    "forbidden_effect_tags": []
  }
}
```

Bad scene rule:

```json
{
  "winning_tool_ids": ["wizard.read_runes", "knight.inspect_runes"]
}
```

### Campaigns

Campaigns organize scenes into benchmark slices.

They should answer:

- Is this a tutorial sequence?
- Is this a story sequence?
- Is this a benchmark slice?
- Which model capability is this sequence intended to stress?

Campaigns should avoid encoding validation behavior. Their job is ordering and evaluation grouping.

## Correctness Rules

### Defeat Monster

A defeat scene tests whether the model can choose an action whose mechanical effect overcomes the monster.

Correct when:

- the tool has `combat_effect: true`
- the tool has a valid `damage_type`
- the tool has a numeric `base_power`
- the monster has a resolved modifier for that damage type
- the scene does not forbid the tool's effect tags
- `base_power * damage_modifier >= min_power_to_defeat`

Wrong when:

- the model chooses a non-combat tool
- the tool lacks damage fields
- the monster has no matching damage modifier
- the tool's effective power is too low
- a hazard forbids the tool's tags

What this tests:

- mapping tool effects to monster weaknesses
- avoiding resisted or immune damage
- reading enough scene context to avoid dangerous mechanics
- choosing among several legal tools instead of simply choosing any attack

### Knowledge Check

A knowledge scene tests whether the model can recognize that force is the wrong abstraction.

Correct when:

- the scene uses `mode: knowledge_check`
- the selected tool provides `knowledge_gain` or a `knowledge` effect tag
- all required knowledge tags are present
- no forbidden tags are present

Wrong when:

- the model attacks the puzzle
- the model escapes when escape is not the objective
- the model chooses a utility tool without the required knowledge capability

What this tests:

- objective reading
- non-combat tool selection
- natural-language clue interpretation
- avoiding the common model habit of attacking every encounter

Future extension:

- Keep generic `knowledge` for simple scenes.
- Add granular tags only when needed, such as `runes`, `ritual`, `clues`, `inspection`, or `arcane`.
- Do not add granular tags just to make answer keys. Add them only when the scene is meant to distinguish different knowledge tools.

### Survival Check

A survival scene tests whether the model can choose defense when winning means enduring a hazard.

Correct when:

- the scene uses `mode: survival_check`
- the selected tool has a `defense` effect tag
- the selected tool has positive numeric `mitigation`
- all required defensive tags are present
- no forbidden tags are present

Wrong when:

- the model attacks a hazard that must be survived
- the model chooses knowledge when the scene asks for immediate defense
- the model attempts escape when the scene forbids escape

What this tests:

- recognizing defensive objectives
- using tool categories other than attack
- following scene text that says survival matters more than damage

Future extension:

- Add `incoming_threat_power` only if numeric defensive difficulty becomes useful.
- For now, tag plus positive mitigation is enough and keeps the system simple.

### Escape Check

An escape scene tests whether the model can recognize retreat as success.

Correct when:

- the selected tool has `escape_attempt: true`
- the scene does not set `constraints.no_escape`
- the monster has `interactions.escape_allowed: true`
- the scene has `allow_escape_as_success: true`
- required escape tags are present

Wrong when:

- the model attacks a scene that explicitly rewards retreat
- the model escapes from a scene where escape is allowed but not successful
- the model escapes from a no-escape scene

What this tests:

- reading the actual objective instead of defaulting to combat
- distinguishing "can flee" from "fleeing solves the encounter"
- using movement tools as first-class actions

### Hazard And Forbidden Effects

Hazard rules test whether the model can avoid actions that are mechanically powerful but contextually wrong.

Correct when:

- the selected tool solves the main objective
- none of its effect tags overlap with `forbidden_effect_tags`

Wrong when:

- a tool would otherwise work, but its tags trigger a hazard failure

Examples:

- A powder room forbids `elemental_fire`.
- An icy bridge forbids `elemental_water`.
- A fragile archive might forbid `area`.

What this tests:

- multi-condition reasoning
- avoiding superficially strong tools
- reading scene-specific warnings

## Benchmark Metadata

Metadata can help organize the dataset without becoming an answer key.

Optional scene metadata should be analysis-only unless explicitly exposed by a debug preset.

Recommended fields:

- `benchmark_focus`: the model capability being tested
- `mechanic_family`: broad validator family
- `intended_signal`: short human explanation of why the scene exists
- `prompt_leakage`: notes about which prompt presets should reveal or hide exact mechanics

Example:

```json
{
  "benchmark_focus": "hazard_avoidance",
  "mechanic_family": "combat",
  "intended_signal": "The model must avoid fire even though fire is often a strong combat option.",
  "prompt_leakage": "Do not expose forbidden tags outside FULL_INFO; rely on narrative warning in lower presets."
}
```

This metadata should be used for reports, dataset audits, and portfolio explanation. It should not be used by the validator to determine success.

## Scenario Families

### Tutorial Encounters

Purpose:

- prove the interface works
- test simple JSON discipline
- introduce combat, knowledge, and no-escape logic

Expected signal:

- stronger models should pass most tutorial scenes in high-information presets
- parse failures or wrong schemas are more interesting than deep tactical failures here

### Goblin Den

Purpose:

- test basic combat reasoning over a small story arc
- increase enemy complexity gradually
- check whether the model learns that not every goblin has the same weakness

Expected signal:

- good models should map shields and armor toward blunt force
- good models should notice fire-sensitive or fire-dangerous scenes
- weak models may overuse the first plausible attack

### Sewers And Rats

Purpose:

- test transfer across related enemies
- make the model distinguish rats, giant rats, swarms, wererats, and bosses

Expected signal:

- good models should change choices based on swarm, disease, precision, or magic clues
- weak models may treat every rat-like enemy as the same target

### Decision Lab

Purpose:

- test decision quality beyond combat
- isolate knowledge, defense, escape, and hazard reasoning
- make failures easier to classify

Expected signal:

- good models should stop defaulting to attacks
- good models should pick retreat when retreat is the actual objective
- good models should avoid forbidden effects even when the tool is strong elsewhere

### Class Identity Trials

Purpose:

- test whether the same scene is solved differently by different characters
- show that the validator rewards mechanics, not one canonical tool

Expected signal:

- each class may solve the same scene through different legal tools
- a scene can be fair even when the exact selected tool differs by character

## Prompt Presets As Experiments

The prompt presets are experimental controls.

### Blind Adventurer

Tests:

- narrative inference
- basic tool descriptions
- ability to recover through self-learning notes

Expected failures:

- legal but tactically wrong actions
- wrong damage type
- missed hidden resistances

### Tool Manual

Tests:

- understanding tool mechanics when monster mechanics are still partly hidden
- whether the model can use schemas and effects correctly

Expected failures:

- picking a mechanically clear tool for the wrong monster

### Scout Report

Tests:

- using monster weaknesses and resistances with natural-language tool descriptions
- mapping concepts without exact tool effects

Expected failures:

- choosing a tool whose description sounds right but has weak hidden mechanics

### Battle Plan

Tests:

- upper-middle benchmark mode where correct choices should be mechanically inferable
- comparing small models under fair information

Expected failures:

- reasoning failures more than information failures
- context overload for smaller models

### Full Info

Tests:

- debug ceiling
- whether the model can succeed when nearly all relevant mechanics are visible

Expected failures:

- parse issues
- instruction-following issues
- context handling failures

## Dataset Growth Rules

When adding a new tool:

- define constraints first
- define effects in reusable mechanical terms
- add effect tags that describe behavior, not scene-specific answers
- verify it becomes valid in existing scenes only when that makes mechanical sense

When adding a new monster:

- choose or add a damage profile
- override modifiers only where the monster meaningfully differs
- set `min_power_to_defeat` deliberately
- set `escape_allowed` deliberately
- make weaknesses and resistances match the resolved modifiers closely enough for prompt-based reasoning

When adding a new scene:

- decide what model capability it tests
- choose a validator mode
- express the objective through generic mechanics
- use forbidden tags for contextual hazards
- avoid listing winning tools
- run deterministic solvability checks across characters

When adding a new campaign:

- group scenes by evaluation purpose
- keep tutorial, story, and benchmark campaigns separate when possible
- make benchmark campaigns short enough to compare across models repeatedly

## Dataset Audit Goals

The dataset should be audited through derived mechanics, not stored answer keys.

Useful audit outputs:

- number of mechanically winning tools per scene and character
- scenes with no valid winning tool for a character
- scenes with too many winning tools to be discriminative
- forbidden tags that do not match any tool tag
- required tags that no available tool can provide
- monsters whose weakness/resistance text disagrees with resolved modifiers

These reports can calculate winning tools internally, but the source data should not store them.

## Known Consistency Issues To Review

### Goblin Alchemist Hazard Tags

Current concern:

- The Goblin Alchemist scene forbids `area_fire`.
- Existing tools use tags such as `elemental_fire` and `area`.
- Fireball has both `elemental_fire` and `area`, but other fire tools may only have `elemental_fire`.

Decision needed:

- If any open flame should fail, forbid `elemental_fire`.
- If only area fire should fail, forbid both `elemental_fire` and `area` through a future compound rule, or introduce a clear tag such as `volatile_fire`.
- For the current simple validator, prefer direct tags that actually exist on tools.

### Forbidden Tag Audit

All `forbidden_effect_tags` should be checked against real `effect_tags`.

Decision rule:

- If a forbidden tag is intended to matter now, it must exist on at least one tool.
- If it is future-facing, document it as reserved instead of silently leaving it ineffective.

### Escape Tool Availability

Current shape:

- `common.run` is available to Wizard and Knight.
- Rogue and Cleric have class-specific escape tools.

Decision needed:

- Keep this if the intent is class identity.
- Change it if `run` is meant to be a universal fallback.

Benchmark implication:

- Class-specific escape tools are more interesting, but they make escape scenes test tool availability as well as objective recognition.

### Knowledge Granularity

Current shape:

- Knowledge scenes mostly accept generic `knowledge`.

Decision needed:

- Keep generic knowledge for broad early scenes.
- Add granular required tags only when a scene is intentionally testing the difference between, for example, arcane runes, religious omens, and trap clues.

Benchmark implication:

- Generic knowledge is easier and fairer across classes.
- Granular knowledge creates stronger class identity but can reduce cross-character solvability.

## Acceptance Criteria For A Good Benchmark Slice

A benchmark slice is ready when:

- every scene has a clear mechanic family
- every scene has a clear model capability it is testing
- correctness can be derived from tool effects, monster interactions, and scene rules
- no scene depends on stored per-character answer keys
- every intentional class limitation is documented
- every accidental unsolved character-scene pair is fixed
- prompt presets reveal different amounts of information in a controlled way
- benchmark reports can separate parse failures, hard validation failures, and soft reasoning failures

## Near-Term Work

1. Add analysis-only scene metadata for benchmark organization.
2. Build or extend a deterministic custom-data audit report.
3. Fix forbidden tag mismatches.
4. Decide whether `common.run` should remain class-limited.
5. Decide where generic knowledge is enough and where granular knowledge tags are worth adding.
6. Use the audit report before adding larger datasets or more generated content.
