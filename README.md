# AgentQuest
A structured sandbox for studying AI tool selection under constraints, presented as a modular fantasy simulation.




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