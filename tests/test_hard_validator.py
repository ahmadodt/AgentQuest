from src.engine.validation.validator_hard import hard_validate_tool_call

def test_hard_passes_for_wizard_fireball(gamedata_copy):
    gd = gamedata_copy

    character_id = "wizard.ember"

    verdict = hard_validate_tool_call(gd, character_id, "wizard.cast_fireball")
    assert verdict["hard_valid"] is True
    assert verdict["outcome"] == "proceed"


def test_hard_rejects_tool_not_in_character_tool_ids(gamedata_copy):
    """
    Hard validation checks character permissions independently of AST visibility.
    """
    gd = gamedata_copy

    character_id = "wizard.ember"

    verdict = hard_validate_tool_call(gd, character_id, "knight.sword_slash")
    assert verdict["hard_valid"] is False
    assert verdict["reason_code"] == "tool_not_available_to_character"
    assert "not available" in verdict["reason"].lower()


def test_hard_rejects_forbidden_trait(gamedata_copy):
    gd = gamedata_copy

    character_id = "wizard.ember"
    character = gd["characters_by_id"][character_id]

    # Add forbidden trait for fireball
    character["traits"] = character.get("traits", []) + ["low_mana"]

    verdict = hard_validate_tool_call(gd, character_id, "wizard.cast_fireball")
    assert verdict["hard_valid"] is False
    assert verdict["reason_code"] == "forbidden_trait"
    assert "forbidden trait" in verdict["reason"].lower()


def test_hard_rejects_missing_required_inventory(gamedata_copy):
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

    verdict = hard_validate_tool_call(gd, character_id, "wizard.cast_fireball")
    assert verdict["hard_valid"] is False
    assert verdict["reason_code"] == "missing_required_inventory"
    assert "missing required inventory" in verdict["reason"].lower()


def test_hard_rejects_unknown_character_with_reason_code(gamedata):
    verdict = hard_validate_tool_call(gamedata, "wizard.unknown", "wizard.cast_fireball")

    assert verdict["hard_valid"] is False
    assert verdict["reason_code"] == "unknown_character"
    assert "unknown character_id" in verdict["reason"].lower()
