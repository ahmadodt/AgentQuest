from src.engine.validator_ast import ast_validate_tool_call
from src.engine.validator_hard import hard_validate_tool_call

def test_hard_passes_for_wizard_fireball(gamedata_copy, make_tool_call):
    gd = gamedata_copy

    character_id = "wizard.ember"
    visible_tool_ids = gd["characters_by_id"][character_id]["tool_ids"]

    raw = make_tool_call("wizard.cast_fireball", {"target": "goblin"})
    parsed = ast_validate_tool_call(raw, gd["tools_by_id"], visible_tool_ids)

    verdict = hard_validate_tool_call(gd, character_id, parsed["tool_id"])
    assert verdict["hard_valid"] is True
    assert verdict["outcome"] == "proceed"


def test_hard_rejects_tool_not_in_character_tool_ids_even_if_visible(gamedata_copy, make_tool_call):
    """
    Demonstrates separation:
    - AST checks 'visible_tool_ids'
    - Hard checks character permissions (character.tool_ids)

    We intentionally allow the tool to be visible but not actually owned/allowed by the character.
    """
    gd = gamedata_copy

    character_id = "wizard.ember"
    character = gd["characters_by_id"][character_id]

    # Make knight tool visible to pass AST, but do NOT add it to character.tool_ids
    visible_tool_ids = character["tool_ids"] + ["knight.sword_slash"]

    raw = make_tool_call("knight.sword_slash", {"target": "goblin"})
    parsed = ast_validate_tool_call(raw, gd["tools_by_id"], visible_tool_ids)

    verdict = hard_validate_tool_call(gd, character_id, parsed["tool_id"])
    assert verdict["hard_valid"] is False
    assert "not available" in verdict["reason"].lower()


def test_hard_rejects_forbidden_trait(gamedata_copy, make_tool_call):
    gd = gamedata_copy

    character_id = "wizard.ember"
    character = gd["characters_by_id"][character_id]

    # Add forbidden trait for fireball
    character["traits"] = character.get("traits", []) + ["low_mana"]

    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("wizard.cast_fireball", {"target": "goblin"})
    parsed = ast_validate_tool_call(raw, gd["tools_by_id"], visible_tool_ids)

    verdict = hard_validate_tool_call(gd, character_id, parsed["tool_id"])
    assert verdict["hard_valid"] is False
    assert "forbidden trait" in verdict["reason"].lower()


def test_hard_rejects_missing_required_inventory(gamedata_copy, make_tool_call):
    """
    Force an inventory failure by:
    - temporarily requiring wand for wizard.cast_fireball
    - removing wand from Ember inventory
    """
    gd = gamedata_copy

    character_id = "wizard.ember"
    character = gd["characters_by_id"][character_id]

    # Remove wand
    character["inventory"] = []

    # Force tool to require wand
    tool = gd["tools_by_id"]["wizard.cast_fireball"]
    tool["constraints"]["required_inventory"] = ["wand"]

    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("wizard.cast_fireball", {"target": "goblin"})
    parsed = ast_validate_tool_call(raw, gd["tools_by_id"], visible_tool_ids)

    verdict = hard_validate_tool_call(gd, character_id, parsed["tool_id"])
    assert verdict["hard_valid"] is False
    assert "missing required inventory" in verdict["reason"].lower()
