# Data Pipeline

This folder contains the Open5e ingestion and conversion scripts used to prepare external RPG data for AgentQuest.

The pipeline is intentionally separate from the main runtime. The live game uses the hand-authored runtime files first:

- preferred: `data/custom/agentquest/`
- fallback: legacy top-level `data/*.json`

The Open5e pipeline exists to import larger source material, curate a benchmark subset, and generate AgentQuest-shaped JSON without replacing the custom dataset by default. Generated monsters and generated spells are merged into the runtime catalog at load time, while generated weapons remain outside the runtime flow for now.

## Files

- `download_open5e.py`
  Downloads raw Open5e endpoint data into local JSON files.
- `open5e_converter.py`
  Converts raw or curated Open5e data into AgentQuest-compatible monster and tool payloads.
- `__init__.py`
  Package marker.

## Data Flow

The Open5e pipeline uses three layers of data:

1. Raw source data
   `data/raw/open5e/`

   This is downloaded source material.
   It should be treated as external input, not hand-edited project content.

2. Curated benchmark selection
   `data/curated/open5e/`

   This is where we choose the subset of monsters, spells, and weapons that we want to use for experiments.

3. Generated AgentQuest-ready data
   `data/generated/open5e/`

   This is the output of the converter.
   These files remain generated artifacts even though some of them are merged into the runtime later.

## Directory Layout

```text
data/
  raw/
    open5e/
      monsters.json
      spells.json
      weapons.json
      ...
  curated/
    open5e/
      selected_monsters.json
      selected_spells.json
      selected_weapons.json
  generated/
    open5e/
      monsters.json
      tools_spells.json
      tools_weapons.json
```

## Main Commands

Download raw Open5e data:

```bash
python -m src.data_pipeline.download_open5e
```

Download only one endpoint:

```bash
python -m src.data_pipeline.download_open5e --endpoint monsters
python -m src.data_pipeline.download_open5e --endpoint spells
python -m src.data_pipeline.download_open5e --endpoint weapons
```

Limit download size for quick experiments:

```bash
python -m src.data_pipeline.download_open5e --max-pages 1
```

Run full conversion of all local raw records:

```bash
python -m src.data_pipeline.open5e_converter
```

Run curated conversion only:

```bash
python -m src.data_pipeline.open5e_converter --curated
```

Override directories if needed:

```bash
python -m src.data_pipeline.open5e_converter --input-dir data/raw/open5e --curated-dir data/curated/open5e --output-dir data/generated/open5e --curated
```

Run tests:

```bash
pytest -q
```

## Curated Selection Files

The curated files define which raw Open5e records are included in the benchmark subset.

Current files:

- `data/curated/open5e/selected_monsters.json`
- `data/curated/open5e/selected_spells.json`
- `data/curated/open5e/selected_weapons.json`

Format:

```json
{
  "version": "1.0",
  "source": "open5e",
  "selected": [
    {
      "slug": "battleaxe",
      "notes": "Initial curated weapon example"
    }
  ]
}
```

Overrides are supported per selected item:

```json
{
  "slug": "battleaxe",
  "overrides": {
    "constraints": {
      "allowed_classes": ["Knight"]
    }
  }
}
```

Override behavior is simple and deterministic:

- If both existing value and override value are dictionaries, keys are merged recursively.
- Otherwise, the override replaces the original value.

If a selected slug is missing from the raw source file, conversion raises a clear error instead of silently skipping it.

## Conversion Modes

`open5e_converter.py` supports two modes.

### Full conversion

Default behavior:

```bash
python -m src.data_pipeline.open5e_converter
```

This converts every record found in:

- `data/raw/open5e/monsters.json`
- `data/raw/open5e/spells.json`
- `data/raw/open5e/weapons.json`

This is useful for exploration, inspection, and debugging.
It is not the preferred benchmark mode.

### Curated conversion

Preferred benchmark behavior:

```bash
python -m src.data_pipeline.open5e_converter --curated
```

This:

- loads the full raw Open5e files
- loads the selected slug lists from `data/curated/open5e/`
- converts only the selected records
- applies optional per-item overrides
- writes generated outputs into `data/generated/open5e/`

This is the expected workflow for the current project state because the runtime merge assumes curated generated monsters and spells rather than the full corpus.

## Current Conversion Rules

The converter is intentionally simple.
It is not trying to simulate full D&D rules.

### Monsters

Monsters are converted into AgentQuest monster records with fields like:

- `monster_id`
- `source_slug`
- `name`
- `type`
- `description`
- `tags`
- `weaknesses`
- `resistances`
- `immunities`
- `condition_immunities`
- `interactions`

Important rules:

- `monster_id` is deterministic: `open5e.monster.<slug>`
- `description` copies the full Open5e `desc` value
- no truncation is done
- no summarization is done
- no LLM rewriting is done
- weaknesses come only from `damage_vulnerabilities`
- resistances come only from `damage_resistances`
- immunities come only from `damage_immunities`
- condition immunities come only from `condition_immunities`
- text like "fear of fire" does not create a fire weakness unless the structured field says so

Monster interaction damage modifiers are deterministic:

- vulnerability -> `2.0`
- resistance -> `0.5`
- immunity -> `0.0`

Current generated monster interactions include:

- `damage_type_modifiers`
- `min_power_to_defeat`
- `knowledge_tools_help`

The converter does not write monster-level `escape_allowed`.
The runtime loader adds `escape_allowed: true` when generated monsters are merged so they remain valid under the current validation rules.

### Spells

Spells are converted into AgentQuest tool records.

Important rules:

- `tool_id` is deterministic: `open5e.spell.<slug>`
- `description` copies the full Open5e `desc` value
- class restrictions come from structured spell class fields
- if a damage pattern can be found deterministically in the spell description, the converter sets:
  - `effects.damage_type`
  - `effects.base_power`
- otherwise the spell defaults to a simple utility or non-combat shape

The current tool argument schema for converted spells is:

- required `target: string`
- optional `slot_level: integer`

### Weapons

Weapons are also converted into AgentQuest tool records.

Important rules:

- `tool_id` is deterministic: `open5e.weapon.<slug>`
- description is generated mechanically from structured fields
- `required_inventory` defaults to the weapon slug
- `base_power` is derived deterministically from the weapon damage dice

Current class rule:

- simple weapons -> `["Knight", "Wizard"]`
- martial weapons -> `["Knight"]`
- unclear category -> `["Knight"]`

This rule is intentionally rough and easy to change later.

## Generated Outputs

The converter writes:

- `data/generated/open5e/monsters.json`
- `data/generated/open5e/tools_spells.json`
- `data/generated/open5e/tools_weapons.json`

These are generated files.
They are useful for inspection, experiments, and later integration work.

Current runtime behavior after generation:

- generated monsters are merged into the live monster catalog
- generated spells are merged into the live tool catalog
- custom records win on exact id collisions
- generated weapons are not merged into the runtime yet

## What This Pipeline Does Not Do

- It does not call the Open5e API during conversion.
- It does not use LLM extraction or rewriting.
- It does not infer weaknesses or resistances from free text.
- It does not try to implement full D&D combat rules.
- It does not merge generated weapons into the runtime.

## Practical Workflow

Typical usage:

1. Download or refresh raw Open5e source data.
2. Edit the curated selection files to choose the benchmark monsters and spells you want.
3. Run curated conversion.
4. Inspect the generated outputs under `data/generated/open5e/`.
5. Run tests or prompt previews against the merged runtime catalog.

Example:

```bash
python -m src.data_pipeline.download_open5e
python -m src.data_pipeline.open5e_converter --curated
pytest -q
```

## Notes For Future Work

Likely future extensions:

- richer curated override options
- optional enrichment passes
- explicit scene-generation helpers
- better spell effect extraction
- more detailed weapon and monster balancing

The current baseline should stay deterministic, readable, and easy to debug.
