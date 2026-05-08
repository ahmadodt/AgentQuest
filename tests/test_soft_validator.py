from src.engine.validation.validator_soft import soft_validate_tool_call


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
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.002.runes_on_wall",
        tool_id="wizard.arcane_shield",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert "knowledge-oriented" in verdict["reason"]


def test_soft_escape_fails_when_scene_forbids_escape(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.003.flame_gate",
        tool_id="common.run",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert "forbids escape" in verdict["reason"]


def test_soft_escape_succeeds_when_allowed(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.001.goblin_alley",
        tool_id="common.run",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"