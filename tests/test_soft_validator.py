import copy
import json
import os
import pytest

from src.engine.loader import load_gamedata
from src.engine.validator import validate
from src.engine.validator_soft import soft_validate_tool_call


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def gamedata():
    data_dir = os.path.join(_project_root(), "data")
    return load_gamedata(data_dir)


def _call(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def test_soft_attack_succeeds_when_effective_power_meets_threshold(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.001.goblin_alley",
        tool_id="knight.sword_slash",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"
    assert "Monster defeated" in verdict["reason"]


def test_soft_attack_fails_when_effective_power_is_too_low(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.001.goblin_alley",
        tool_id="wizard.cast_fireball",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert "too weak" in verdict["reason"]


def test_soft_knowledge_scene_accepts_knowledge_tool(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.002.runes_on_wall",
        tool_id="wizard.read_runes",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"


def test_soft_knowledge_scene_rejects_non_knowledge_tool(gamedata):
    gd = copy.deepcopy(gamedata)
    character_id = "wizard.ember"

    raw = _call({"tool_id": "wizard.arcane_shield", "arguments": {}})
    verdict = validate(
        gamedata=gd,
        character_id=character_id,
        scene_id="scene.002.runes_on_wall",
        visible_tool_ids=gd["characters_by_id"][character_id]["tool_ids"],
        raw_model_output=raw,
    )

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is True
    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert "knowledge-oriented" in verdict["reason"]


def test_soft_escape_fails_when_scene_forbids_escape(gamedata):
    gd = copy.deepcopy(gamedata)
    character_id = "knight.bram"

    raw = _call({"tool_id": "common.run", "arguments": {"direction": "toward_exit"}})
    verdict = validate(
        gamedata=gd,
        character_id=character_id,
        scene_id="scene.003.flame_gate",
        visible_tool_ids=gd["characters_by_id"][character_id]["tool_ids"],
        raw_model_output=raw,
    )

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is True
    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert "forbids escape" in verdict["reason"]


def test_soft_escape_succeeds_when_allowed(gamedata):
    gd = copy.deepcopy(gamedata)
    character_id = "wizard.ember"

    raw = _call({"tool_id": "common.run", "arguments": {"direction": "backtrack"}})
    verdict = validate(
        gamedata=gd,
        character_id=character_id,
        scene_id="scene.001.goblin_alley",
        visible_tool_ids=gd["characters_by_id"][character_id]["tool_ids"],
        raw_model_output=raw,
    )

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is True
    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"
