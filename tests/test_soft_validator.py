from src.engine.validation.validator_soft import soft_validate_tool_call
from src.prompts.presets import BATTLE_PLAN, BLIND_ADVENTURER


def test_soft_attack_succeeds_when_effective_power_meets_threshold(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.001_goblin_alley",
        tool_id="knight.sword_slash",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"
    assert "Monster defeated" in verdict["reason"]


def test_soft_attack_fails_when_effective_power_is_too_low(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.001_goblin_alley",
        tool_id="wizard.cast_fireball",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert verdict["reason_code"] == "insufficient_effective_power"


def test_soft_attack_failure_uses_numeric_reason_for_high_information_presets(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.001_goblin_alley",
        tool_id="wizard.cast_fireball",
        prompt_cfg=BATTLE_PLAN,
    )

    assert verdict["reason_code"] == "insufficient_effective_power"
    assert "effective_power=" in verdict["reason"]
    assert "min_power_to_defeat=" in verdict["reason"]


def test_soft_attack_failure_uses_natural_language_reason_for_low_information_presets(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.001_goblin_alley",
        tool_id="wizard.cast_fireball",
        prompt_cfg=BLIND_ADVENTURER,
    )

    assert verdict["reason_code"] == "insufficient_effective_power"
    assert "effective_power=" not in verdict["reason"]
    assert "min_power_to_defeat=" not in verdict["reason"]
    assert "too weak" in verdict["reason"].lower()


def test_soft_knowledge_scene_accepts_knowledge_tool(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.002_runes_on_wall",
        tool_id="wizard.read_runes",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"


def test_soft_knowledge_scene_accepts_knight_knowledge_tool(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.002_runes_on_wall",
        tool_id="knight.inspect_runes",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"


def test_soft_knowledge_scene_rejects_non_knowledge_tool(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.002_runes_on_wall",
        tool_id="wizard.arcane_shield",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert verdict["reason_code"] == "missing_required_effect_tag"


def test_soft_escape_fails_when_scene_forbids_escape(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.003_flame_gate",
        tool_id="common.run",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert verdict["reason_code"] == "escape_not_success"


def test_soft_escape_does_not_count_as_success_when_scene_allows_escape_but_not_success(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.tutorial.001_goblin_alley",
        tool_id="common.run",
    )

    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert verdict["reason_code"] == "escape_not_success"


def test_soft_defense_scene_accepts_defense_tool(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.decision_lab.005_mirror_beam_hall",
        tool_id="wizard.arcane_shield",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"


def test_soft_escape_counts_as_success_when_scene_allows_escape_as_success(gamedata):
    verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.decision_lab.007_collapsing_tunnel",
        tool_id="common.run",
    )

    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"
    assert verdict["reason"] == "Escape attempt succeeded"


def test_new_characters_have_valid_tools_in_new_scene(gamedata):
    rogue_verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.decision_lab.003_powder_keg_walkway",
        tool_id="rogue.precise_stab",
    )
    cleric_verdict = soft_validate_tool_call(
        gamedata=gamedata,
        scene_id="scene.decision_lab.005_mirror_beam_hall",
        tool_id="cleric.sanctuary_barrier",
    )

    assert rogue_verdict["soft_valid"] is True
    assert rogue_verdict["outcome"] == "success"
    assert cleric_verdict["soft_valid"] is True
    assert cleric_verdict["outcome"] == "success"
