from src.engine.validator_utils import (
    build_invalid_verdict,
    get_character_or_error,
    get_tool_constraints,
    get_tool_or_error,
)


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
    # 1) Character exists
    character, error = get_character_or_error(gamedata, character_id)
    if error:
        return error

    # 2) Tool exists (AST should already ensure, but keep it safe)
    tool, error = get_tool_or_error(gamedata, tool_id, layer="hard")
    if error:
        return error
    constraints = get_tool_constraints(tool)

    # 3) Tool availability (character tool list)
    tool_ids = character.get("tool_ids", [])
    if tool_id not in tool_ids:
        return build_invalid_verdict(
            f"Tool '{tool_id}' is not available to character '{character_id}'",
            hard_valid=False,
        )

    # 4) Class allowed (safety; loader should already enforce this)
    allowed_classes = constraints.get("allowed_classes", [])
    char_class = character.get("class")
    if char_class not in allowed_classes:
        return build_invalid_verdict(
            f"Character class '{char_class}' cannot use '{tool_id}'",
            hard_valid=False,
        )

    # 5) Required inventory
    required_inventory = constraints.get("required_inventory", [])
    inv_set = set(character.get("inventory", []))
    missing_items = [item for item in required_inventory if item not in inv_set]
    if missing_items:
        return build_invalid_verdict(
            f"Missing required inventory: {missing_items}",
            hard_valid=False,
        )

    # 6) Forbidden traits
    forbidden_traits = set(constraints.get("forbidden_traits", []))
    traits = set(character.get("traits", []))
    blocked = sorted(list(forbidden_traits.intersection(traits)))
    if blocked:
        return build_invalid_verdict(
            f"Forbidden trait(s) present: {blocked}",
            hard_valid=False,
        )

    return {"hard_valid": True, "outcome": "proceed", "reason": "Hard validation passed"}
