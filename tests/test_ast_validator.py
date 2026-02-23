import json
import os
import pytest

from src.engine.loader import load_gamedata
from src.engine.validator_ast import ast_validate_tool_call, AstValidationError


def _project_root() -> str:
    # tests/ -> project root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def gamedata():
    data_dir = os.path.join(_project_root(), "data")
    return load_gamedata(data_dir)


def _call(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def test_ast_valid_cast_fireball(gamedata):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = _call({"tool_id": "wizard.cast_fireball", "arguments": {"target": "goblin"}})
    parsed = ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert parsed["tool_id"] == "wizard.cast_fireball"
    assert parsed["arguments"]["target"] == "goblin"


def test_ast_invalid_json(gamedata):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    with pytest.raises(AstValidationError):
        ast_validate_tool_call("{not valid json}", gamedata["tools_by_id"], visible_tool_ids)


def test_ast_missing_required_arg(gamedata):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = _call({"tool_id": "wizard.cast_fireball", "arguments": {}})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "Missing required argument" in str(e.value)


def test_ast_extra_arg_rejected(gamedata):
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = _call({"tool_id": "wizard.cast_fireball", "arguments": {"target": "goblin", "power": 999}})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "Unexpected argument" in str(e.value)


def test_ast_wrong_type_rejected(gamedata):
    """
    Use common.run because it expects direction as a string (and enum).
    Pass an int to trigger type check.
    """
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = _call({"tool_id": "common.run", "arguments": {"direction": 123}})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "wrong type" in str(e.value).lower()


def test_ast_enum_violation_rejected(gamedata):
    """
    direction must be one of the enum options.
    """
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = _call({"tool_id": "common.run", "arguments": {"direction": "teleport"}})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "must be one of" in str(e.value).lower()


def test_ast_tool_not_visible_rejected(gamedata):
    """
    Tool exists globally, but is not visible for wizard in this run context.
    """
    character = gamedata["characters_by_id"]["wizard.ember"]
    visible_tool_ids = character["tool_ids"]

    raw = _call({"tool_id": "knight.sword_slash", "arguments": {"target": "goblin"}})
    with pytest.raises(AstValidationError) as e:
        ast_validate_tool_call(raw, gamedata["tools_by_id"], visible_tool_ids)

    assert "not visible" in str(e.value).lower()