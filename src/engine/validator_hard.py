class HardValidationError(Exception):
    pass


def hard_validate_tool_call(gamedata: dict, character_id: str, tool_id: str) -> dict:
    """
    Stage 2: Hard validator (feasibility / permissions).

    Assumes Stage 1 (AST) already validated:
    - tool call JSON format
    - tool_id exists in tools_by_id
    - tool_id is visible/allowed in the current context (if you enforce that in AST)
    - arguments have correct keys, no extras, correct types/enums/min/max

    This stage checks:
    - character exists
    - tool is available to character (tool_id in character.tool_ids)
    - tool constraints pass (allowed_classes, required_inventory, forbidden_traits)
    """
    characters_by_id = gamedata["characters_by_id"]
    tools_by_id = gamedata["tools_by_id"]

    # 1) Character exists
    if character_id not in characters_by_id:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Unknown character_id '{character_id}'",
        }

    character = characters_by_id[character_id]

    # 2) Tool exists (AST should already ensure, but keep it safe)
    if tool_id not in tools_by_id:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Unknown tool_id '{tool_id}'",
        }

    tool = tools_by_id[tool_id]
    constraints = tool.get("constraints", {})

    # 3) Tool availability (character tool list)
    tool_ids = character.get("tool_ids", [])
    if tool_id not in tool_ids:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Tool '{tool_id}' is not available to character '{character_id}'",
        }

    # 4) Class allowed (safety; loader should already enforce this)
    allowed_classes = constraints.get("allowed_classes", [])
    char_class = character.get("class")
    if char_class not in allowed_classes:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Character class '{char_class}' cannot use '{tool_id}'",
        }

    # 5) Required inventory
    required_inventory = constraints.get("required_inventory", [])
    inv_set = set(character.get("inventory", []))
    missing_items = [item for item in required_inventory if item not in inv_set]
    if missing_items:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Missing required inventory: {missing_items}",
        }

    # 6) Forbidden traits
    forbidden_traits = set(constraints.get("forbidden_traits", []))
    traits = set(character.get("traits", []))
    blocked = sorted(list(forbidden_traits.intersection(traits)))
    if blocked:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Forbidden trait(s) present: {blocked}",
        }

    return {"hard_valid": True, "outcome": "proceed", "reason": "Hard validation passed"}
    """
    Stage 2: Hard validator (feasibility)

    Assumes Stage 1 (AST) already validated:
    - JSON structure
    - tool exists
    - arguments contain required keys, no extra keys, correct types/enums/min/max

    This stage checks:
    - scene exists
    - scene's character exists
    - tool is available to that character (character.tool_ids)
    - tool constraints pass (class, inventory, forbidden traits)
    """
    scenes_by_id = gamedata["scenes_by_id"]
    characters_by_id = gamedata["characters_by_id"]
    tools_by_id = gamedata["tools_by_id"]

    # Guard: scene exists
    if scene_id not in scenes_by_id:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Unknown scene_id '{scene_id}'",
        }

    scene = scenes_by_id[scene_id]
    character_id = scene.get("character_id")

    # Guard: character exists
    if character_id not in characters_by_id:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Scene references unknown character_id '{character_id}'",
        }

    character = characters_by_id[character_id]

    # Guard: tool exists (AST should already ensure, but keep it safe)
    if tool_id not in tools_by_id:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Unknown tool_id '{tool_id}'",
        }

    tool = tools_by_id[tool_id]

    # 1) Tool availability (current mode: character has explicit tool_ids list)
    if tool_id not in character.get("tool_ids", []):
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Tool '{tool_id}' is not available to character '{character_id}'",
        }

    constraints = tool.get("constraints", {})

    # 2) Class allowed (should already be consistent by loader, but keep as safety)
    allowed_classes = constraints.get("allowed_classes", [])
    if character.get("class") not in allowed_classes:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Character class '{character.get('class')}' cannot use '{tool_id}'",
        }

    # 3) Required inventory
    required_inventory = constraints.get("required_inventory", [])
    inv_set = set(character.get("inventory", []))
    missing_items = [item for item in required_inventory if item not in inv_set]
    if missing_items:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Missing required inventory: {missing_items}",
        }

    # 4) Forbidden traits
    forbidden_traits = set(constraints.get("forbidden_traits", []))
    traits = set(character.get("traits", []))
    blocked = sorted(list(forbidden_traits.intersection(traits)))
    if blocked:
        return {
            "hard_valid": False,
            "outcome": "invalid",
            "reason": f"Forbidden trait(s) present: {blocked}",
        }

    return {
        "hard_valid": True,
        "outcome": "proceed",
        "reason": "Hard validation passed",
    }