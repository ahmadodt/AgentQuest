import pytest

from src.engine.validation.validator_ast import ast_validate_tool_call, AstValidationError

def test_ast_valid_cast_fireball(gamedata, make_tool_call):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("wizard.cast_fireball", {"target": "goblin"})
    parsed = ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert parsed["tool_id"] == "wizard.cast_fireball"
    assert parsed["arguments"]["target"] == "goblin"


def test_ast_invalid_json(gamedata):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    with pytest.raises(AstValidationError):
        ast_validate_tool_call("{not valid json}", gamedata["tools_by_id"], visible_tool_ids)


def test_ast_missing_required_arg(gamedata, make_tool_call):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("wizard.cast_fireball")
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "Missing required argument" in str(e.value)


def test_ast_extra_arg_rejected(gamedata, make_tool_call):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("wizard.cast_fireball", {"target": "goblin", "power": 999})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "Unexpected argument" in str(e.value)


def test_ast_wrong_type_rejected(gamedata, make_tool_call):
    """
    Use common.run because it expects direction as a string (and enum).
    Pass an int to trigger type check.
    """
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("common.run", {"direction": 123})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "wrong type" in str(e.value).lower()


def test_ast_enum_violation_rejected(gamedata, make_tool_call):
    """
    direction must be one of the enum options.
    """
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("common.run", {"direction": "teleport"})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "must be one of" in str(e.value).lower()


def test_ast_tool_not_visible_rejected(gamedata, make_tool_call):
    """
    Tool exists globally, but is not visible for wizard in this run context.
    """
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = make_tool_call("knight.sword_slash", {"target": "goblin"})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "not visible" in str(e.value).lower()
