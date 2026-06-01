from src.runner.benchmark_utils import (
    build_benchmark_progress_state,
    update_benchmark_progress_from_records,
    update_benchmark_progress_state,
)


def test_benchmark_progress_state_tracks_current_and_completed_counts(gamedata):
    state = build_benchmark_progress_state(
        gamedata=gamedata,
        model_names=["fake_model"],
        preset_names=["BATTLE_PLAN"],
        campaign_ids=["campaign.tutorial_v1"],
        character_ids=["wizard.ember"],
        prompt_formats=["json_only"],
    )

    assert state["total"] == 3
    assert state["completed"] == 0
    assert state["remaining"] == 3

    base_event = {
        "model": "fake_model",
        "preset": "BATTLE_PLAN",
        "campaign_id": "campaign.tutorial_v1",
        "character_id": "wizard.ember",
        "prompt_format": "json_only",
        "scene_id": "scene.tutorial.001_goblin_alley",
        "scene_index": 0,
        "scene_title": "Alley Ambush",
    }

    update_benchmark_progress_state(state, {"event": "scene_start", **base_event})

    scene = state["index"][
        (
            "fake_model",
            "BATTLE_PLAN",
            "campaign.tutorial_v1",
            "wizard.ember",
            "json_only",
            "scene.tutorial.001_goblin_alley",
        )
    ]
    assert scene["status"] == "RUNNING"
    assert state["current"]["scene_id"] == "scene.tutorial.001_goblin_alley"

    update_benchmark_progress_state(
        state,
        {
            "event": "scene_finish",
            **base_event,
            "status": "PASS",
            "reason": "ok",
            "selected_tool_id": "common.run",
            "parse_failure": False,
        },
    )

    assert scene["status"] == "PASS"
    assert scene["selected_tool_id"] == "common.run"
    assert state["completed"] == 1
    assert state["remaining"] == 2
    assert state["passed"] == 1
    assert state["failed"] == 0


def test_benchmark_progress_state_counts_failed_parse_scene(gamedata):
    state = build_benchmark_progress_state(
        gamedata=gamedata,
        model_names=["fake_model"],
        preset_names=["BATTLE_PLAN"],
        campaign_ids=["campaign.tutorial_v1"],
        character_ids=["wizard.ember"],
        prompt_formats=["json_only"],
    )

    update_benchmark_progress_state(
        state,
        {
            "event": "scene_finish",
            "model": "fake_model",
            "preset": "BATTLE_PLAN",
            "campaign_id": "campaign.tutorial_v1",
            "character_id": "wizard.ember",
            "prompt_format": "json_only",
            "scene_id": "scene.tutorial.001_goblin_alley",
            "status": "PARSE_ERROR",
            "reason": "invalid JSON",
            "parse_failure": True,
        },
    )

    assert state["completed"] == 1
    assert state["passed"] == 0
    assert state["failed"] == 1
    assert state["parse_failures"] == 1


def test_benchmark_progress_state_rebuilds_from_records(gamedata):
    state = build_benchmark_progress_state(
        gamedata=gamedata,
        model_names=["fake_model"],
        preset_names=["BATTLE_PLAN"],
        campaign_ids=["campaign.tutorial_v1"],
        character_ids=["wizard.ember"],
        prompt_formats=["json_only"],
    )

    update_benchmark_progress_from_records(
        state,
        [
            {
                "benchmark_model": "fake_model",
                "model": "display_model",
                "preset": "BATTLE_PLAN",
                "campaign_id": "campaign.tutorial_v1",
                "character_id": "wizard.ember",
                "prompt_format": "json_only",
                "scene_id": "scene.tutorial.001_goblin_alley",
                "status": "PASS",
                "selected_tool_id": "common.run",
                "parse_failure": False,
            }
        ],
    )

    scene = state["index"][
        (
            "fake_model",
            "BATTLE_PLAN",
            "campaign.tutorial_v1",
            "wizard.ember",
            "json_only",
            "scene.tutorial.001_goblin_alley",
        )
    ]
    assert scene["status"] == "PASS"
    assert scene["selected_tool_id"] == "common.run"
    assert state["completed"] == 1
    assert state["remaining"] == 2
