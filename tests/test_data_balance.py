from src.engine.loader import load_gamedata
from src.engine.validation.validator_soft import soft_validate_tool_call


def _combat_tools_for_character(gamedata: dict, character: dict) -> list[dict]:
    tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]
    return [
        tool
        for tool in tools
        if (tool.get("effects") or {}).get("combat_effect") is True
    ]


def _successful_tool_ids(gamedata: dict, scene_id: str, tools: list[dict]) -> set[str]:
    successful = set()
    for tool in tools:
        verdict = soft_validate_tool_call(gamedata, scene_id, tool["tool_id"])
        if verdict.get("outcome") == "success":
            successful.add(tool["tool_id"])
    return successful


def test_combat_scenes_have_same_category_successes_and_distractors():
    gamedata = load_gamedata("data")
    combat_scenes = [
        scene
        for scene in gamedata["scenes_by_id"].values()
        if (scene.get("success_condition") or {}).get("type") == "defeat_monster"
    ]

    failures = []
    for scene in combat_scenes:
        for character in gamedata["characters_by_id"].values():
            combat_tools = _combat_tools_for_character(gamedata, character)
            successful = _successful_tool_ids(gamedata, scene["scene_id"], combat_tools)
            failed = {tool["tool_id"] for tool in combat_tools}.difference(successful)

            if not successful or not failed:
                failures.append(
                    {
                        "scene_id": scene["scene_id"],
                        "character_id": character["character_id"],
                        "successful": sorted(successful),
                        "failed": sorted(failed),
                    }
                )

    assert failures == []


def test_wizard_has_distinct_elemental_answer_scenes():
    gamedata = load_gamedata("data")
    wizard = gamedata["characters_by_id"]["wizard.ember"]
    combat_tools = _combat_tools_for_character(gamedata, wizard)

    expected_single_success = {
        "scene.goblin_den.002_shadow_scout": "wizard.cast_fireball",
        "scene.tutorial.003_flame_gate": "wizard.cast_water_ball",
        "scene.decision_lab.004b_steam_core": "wizard.cast_ice_spear",
        "scene.decision_lab.004_ice_chain_bridge": "wizard.arcane_bolt",
    }

    for scene_id, expected_tool_id in expected_single_success.items():
        successful = _successful_tool_ids(gamedata, scene_id, combat_tools)
        assert successful == {expected_tool_id}
