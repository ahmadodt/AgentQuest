from src.engine.validator import validate
from src.engine.validator_soft import soft_validate_tool_call


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


def test_soft_knowledge_scene_rejects_non_knowledge_tool(gamedata_copy, make_tool_call):
    gd = gamedata_copy
    character_id = "wizard.ember"

    raw = make_tool_call("wizard.arcane_shield")
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


def test_soft_escape_fails_when_scene_forbids_escape(gamedata_copy, make_tool_call):
    gd = gamedata_copy
    character_id = "knight.bram"

    raw = make_tool_call("common.run", {"direction": "toward_exit"})
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


def test_soft_escape_succeeds_when_allowed(gamedata_copy, make_tool_call):
    gd = gamedata_copy
    character_id = "wizard.ember"

    raw = make_tool_call("common.run", {"direction": "backtrack"})
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
