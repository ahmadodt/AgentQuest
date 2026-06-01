from src.runner.benchmark_utils import (
    build_benchmark_failure_rows,
    build_benchmark_model_preset_rows,
    build_benchmark_model_summary_rows,
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


def test_benchmark_model_summary_rows_rank_by_success_parse_failures_and_latency():
    records = [
        {
            "benchmark_model": "model_b",
            "model": "display_b",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 2.0,
        },
        {
            "benchmark_model": "model_b",
            "model": "display_b",
            "pass": False,
            "parse_failure": False,
            "reason_code": "wrong_tool",
            "latency_seconds": 1.0,
        },
        {
            "benchmark_model": "model_a",
            "model": "display_a",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 0.5,
        },
        {
            "benchmark_model": "model_a",
            "model": "display_a",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 0.7,
        },
        {
            "benchmark_model": "model_c",
            "model": "display_c",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 0.3,
        },
        {
            "benchmark_model": "model_c",
            "model": "display_c",
            "pass": False,
            "parse_failure": True,
            "reason_code": "json_parse_error",
            "latency_seconds": 0.4,
        },
    ]

    rows = build_benchmark_model_summary_rows(records)

    assert [row["model"] for row in rows] == ["model_a", "model_b", "model_c"]
    assert rows[0]["success_rate"] == 100.0
    assert rows[0]["avg_latency_seconds"] == 0.6
    assert rows[1]["top_failure_codes"] == "wrong_tool (1)"
    assert rows[2]["parse_failures"] == 1


def test_benchmark_model_preset_rows_group_by_model_and_preset():
    records = [
        {
            "benchmark_model": "model_a",
            "preset": "BATTLE_PLAN",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 1.0,
        },
        {
            "benchmark_model": "model_a",
            "preset": "BLIND_ADVENTURER",
            "pass": False,
            "parse_failure": True,
            "reason_code": "json_parse_error",
            "latency_seconds": 2.0,
        },
    ]

    rows = build_benchmark_model_preset_rows(records)

    assert rows == [
        {
            "model": "model_a",
            "total_scenes": 1,
            "passed_scenes": 1,
            "failed_scenes": 0,
            "parse_failures": 0,
            "success_rate": 100.0,
            "avg_latency_seconds": 1.0,
            "top_failure_codes": "-",
            "preset": "BATTLE_PLAN",
        },
        {
            "model": "model_a",
            "total_scenes": 1,
            "passed_scenes": 0,
            "failed_scenes": 1,
            "parse_failures": 1,
            "success_rate": 0.0,
            "avg_latency_seconds": 2.0,
            "top_failure_codes": "json_parse_error (1)",
            "preset": "BLIND_ADVENTURER",
        },
    ]


def test_benchmark_failure_rows_keep_only_debugging_columns():
    records = [
        {
            "benchmark_model": "model_a",
            "model": "display_a",
            "preset": "BATTLE_PLAN",
            "campaign_id": "campaign.tutorial_v1",
            "character_id": "wizard.ember",
            "scene_id": "scene.tutorial.001_goblin_alley",
            "selected_tool_id": "common.run",
            "pass": False,
            "reason_code": "wrong_tool",
            "reason": "Expected a safer action.",
            "raw_model_output": "large noisy text",
        },
        {
            "benchmark_model": "model_a",
            "pass": True,
            "reason": "",
        },
    ]

    rows = build_benchmark_failure_rows(records)

    assert rows == [
        {
            "model": "model_a",
            "preset": "BATTLE_PLAN",
            "campaign_id": "campaign.tutorial_v1",
            "character_id": "wizard.ember",
            "scene_id": "scene.tutorial.001_goblin_alley",
            "selected_tool_id": "common.run",
            "reason_code": "wrong_tool",
            "reason": "Expected a safer action.",
        }
    ]
