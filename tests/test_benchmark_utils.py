from src.runner.benchmark_utils import aggregate_benchmark_records, build_benchmark_record


def test_build_benchmark_record_captures_parse_failure_and_effective_power():
    record = build_benchmark_record(
        campaign_id="campaign.alpha",
        scene_run={
            "scene_id": "scene.alpha",
            "scene_index": 0,
            "status": "PARSE_ERROR",
            "parsed_tool_call": None,
            "validation": {
                "ast_valid": False,
                "reason": "AST error: Invalid JSON",
                "reason_code": None,
                "effective_power": 4.5,
            },
            "raw_model_output": "{bad json",
        },
        character_id="wizard.ember",
        preset="BATTLE_PLAN",
        prompt_format="json_only",
        model="C:/models/test.gguf",
        valid_tools=["wizard.arcane_bolt"],
        latency_seconds=0.25,
    )

    assert record["campaign_id"] == "campaign.alpha"
    assert record["scene_id"] == "scene.alpha"
    assert record["pass"] is False
    assert record["parse_failure"] is True
    assert record["effective_power"] == 4.5
    assert record["valid_tools"] == ["wizard.arcane_bolt"]


def test_aggregate_benchmark_records_groups_failures():
    summary = aggregate_benchmark_records(
        [
            {
                "campaign_id": "campaign.alpha",
                "scene_id": "scene.alpha",
                "character_id": "wizard.ember",
                "preset": "BATTLE_PLAN",
                "prompt_format": "json_only",
                "pass": True,
                "parse_failure": False,
                "reason_code": None,
            },
            {
                "campaign_id": "campaign.alpha",
                "scene_id": "scene.beta",
                "character_id": "wizard.ember",
                "preset": "BATTLE_PLAN",
                "prompt_format": "json_only",
                "pass": False,
                "parse_failure": False,
                "reason_code": "insufficient_effective_power",
            },
            {
                "campaign_id": "campaign.beta",
                "scene_id": "scene.gamma",
                "character_id": "knight.bram",
                "preset": "FULL_INFO",
                "prompt_format": "json_only",
                "pass": False,
                "parse_failure": True,
                "reason_code": "unknown_reason",
            },
        ]
    )

    assert summary["total_scenes"] == 3
    assert summary["passed_scenes"] == 1
    assert summary["failed_scenes"] == 2
    assert summary["parse_failures"] == 1
    assert round(summary["success_rate"], 1) == 33.3
    assert summary["failures_by_reason_code"]["insufficient_effective_power"] == 1
    assert summary["failures_by_reason_code"]["unknown_reason"] == 1
    assert summary["failures_by_preset"]["BATTLE_PLAN"] == 1
    assert summary["failures_by_character"]["wizard.ember"] == 1
    assert summary["first_failed_scene"]["scene_id"] == "scene.beta"
