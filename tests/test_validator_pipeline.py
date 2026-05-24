def test_validator_pipeline_returns_ast_error_verdict(validator_factory, gamedata):
    validator = validator_factory(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.tutorial.001_goblin_alley",
    )

    verdict = validator.validate("{not valid json}")

    assert verdict["ast_valid"] is False
    assert verdict["hard_valid"] is None
    assert verdict["soft_valid"] is None
    assert verdict["outcome"] == "invalid"
    assert verdict["parsed_tool_call"] is None
    assert verdict["character_id"] == "wizard.ember"
    assert verdict["scene_id"] == "scene.tutorial.001_goblin_alley"
    assert "AST error:" in verdict["reason"]


def test_validator_pipeline_stops_after_hard_failure(
    validator_factory,
    gamedata_copy,
    make_tool_call,
):
    gd = gamedata_copy
    character_id = "wizard.ember"
    visible_tool_ids = gd["characters_by_id"][character_id]["tool_ids"] + ["knight.sword_slash"]
    validator = validator_factory(
        gamedata=gd,
        character_id=character_id,
        scene_id="scene.tutorial.001_goblin_alley",
        visible_tool_ids=visible_tool_ids,
    )

    verdict = validator.validate(make_tool_call("knight.sword_slash", {"target": "goblin"}))

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is False
    assert verdict["soft_valid"] is None
    assert verdict["outcome"] == "invalid"
    assert verdict["parsed_tool_call"] == {
        "tool_id": "knight.sword_slash",
        "arguments": {"target": "goblin"},
    }
    assert "not available" in verdict["reason"].lower()


def test_validator_pipeline_returns_soft_failure_after_ast_and_hard_pass(
    validator_factory,
    gamedata,
    make_tool_call,
):
    validator = validator_factory(
        gamedata=gamedata,
        character_id="knight.bram",
        scene_id="scene.tutorial.003_flame_gate",
    )

    verdict = validator.validate(make_tool_call("common.run", {"direction": "toward_exit"}))

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is True
    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert verdict["parsed_tool_call"] == {
        "tool_id": "common.run",
        "arguments": {"direction": "toward_exit"},
    }
    assert "forbids escape" in verdict["reason"]


def test_validator_pipeline_returns_soft_success_for_valid_action(
    validator_factory,
    gamedata,
    make_tool_call,
):
    validator = validator_factory(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.tutorial.001_goblin_alley",
    )

    verdict = validator.validate(make_tool_call("wizard.arcane_bolt", {"target": "goblin"}))

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is True
    assert verdict["soft_valid"] is True
    assert verdict["outcome"] == "success"
    assert verdict["parsed_tool_call"] == {
        "tool_id": "wizard.arcane_bolt",
        "arguments": {"target": "goblin"},
    }
    assert "Monster defeated" in verdict["reason"]


def test_validator_pipeline_uses_natural_language_soft_failure_for_low_information_presets(
    validator_factory,
    gamedata,
    make_tool_call,
):
    from src.prompts.presets import BLIND_ADVENTURER

    validator = validator_factory(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.tutorial.001_goblin_alley",
        prompt_cfg=BLIND_ADVENTURER,
    )

    verdict = validator.validate(make_tool_call("wizard.cast_fireball", {"target": "goblin"}))

    assert verdict["soft_valid"] is False
    assert verdict["reason_code"] == "insufficient_effective_power"
    assert "effective_power=" not in verdict["reason"]
    assert "min_power_to_defeat=" not in verdict["reason"]


def test_validator_pipeline_returns_scene_specific_soft_reason_for_survival_scene(
    validator_factory,
    gamedata,
    make_tool_call,
):
    validator = validator_factory(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.decision_lab.005_mirror_beam_hall",
    )

    verdict = validator.validate(make_tool_call("wizard.arcane_bolt", {"target": "warden"}))

    assert verdict["ast_valid"] is True
    assert verdict["hard_valid"] is True
    assert verdict["soft_valid"] is False
    assert verdict["outcome"] == "failure"
    assert verdict["reason_code"] == "missing_defense_effect"
