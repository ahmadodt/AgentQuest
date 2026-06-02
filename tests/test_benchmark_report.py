from src.runner.benchmark_report import (
    build_showcase_failure_reason_rows,
    build_showcase_full_info_failure_rows,
    build_showcase_model_preset_rows,
    build_showcase_model_summary_rows,
    load_benchmark_bundle,
    render_markdown_report,
    render_showcase_markdown,
    summarize_benchmark_bundles,
)
from src.runner.runner_utils import write_json_file


def _write_bundle(tmp_path, name, *, model, records, summary):
    benchmark_dir = tmp_path / name
    benchmark_dir.mkdir()
    write_json_file(
        str(benchmark_dir / "manifest.json"),
        {
            "backend": "llama_cpp",
            "campaign_ids": ["campaign.goblin_den_v1"],
            "character_ids": ["knight.bram"],
            "presets": ["BLIND_ADVENTURER", "BATTLE_PLAN"],
            "prompt_formats": ["json_only"],
            "model": model,
        },
    )
    write_json_file(str(benchmark_dir / "records.json"), records)
    write_json_file(str(benchmark_dir / "summary.json"), summary)
    return str(benchmark_dir)


def test_summarize_benchmark_bundles_groups_by_model_and_preset(tmp_path):
    benchmark_dir = _write_bundle(
        tmp_path,
        "model_a",
        model="model-a",
        records=[
            {
                "preset": "BLIND_ADVENTURER",
                "pass": True,
                "parse_failure": False,
                "latency_seconds": 1.2,
            },
            {
                "preset": "BLIND_ADVENTURER",
                "pass": False,
                "parse_failure": True,
                "reason_code": "json_parse_error",
                "latency_seconds": 1.4,
            },
            {
                "preset": "BATTLE_PLAN",
                "pass": False,
                "parse_failure": False,
                "reason_code": "insufficient_power",
                "latency_seconds": 0.8,
            },
        ],
        summary={"success_rate": 33.3},
    )

    bundle = load_benchmark_bundle(benchmark_dir)
    rows = summarize_benchmark_bundles([bundle])

    assert rows == [
        {
            "model": "model-a",
            "preset": "BATTLE_PLAN",
            "total_scenes": 1,
            "passed_scenes": 0,
            "failed_scenes": 1,
            "parse_failures": 0,
            "success_rate": 0.0,
            "avg_latency_seconds": 0.8,
            "top_reason_codes": "insufficient_power (1)",
        },
        {
            "model": "model-a",
            "preset": "BLIND_ADVENTURER",
            "total_scenes": 2,
            "passed_scenes": 1,
            "failed_scenes": 1,
            "parse_failures": 1,
            "success_rate": 50.0,
            "avg_latency_seconds": 1.2999999999999998,
            "top_reason_codes": "json_parse_error (1)",
        },
    ]


def test_render_markdown_report_lists_models_and_failure_codes(tmp_path):
    dir_a = _write_bundle(
        tmp_path,
        "model_a",
        model="model-a",
        records=[
            {
                "preset": "BATTLE_PLAN",
                "pass": True,
                "parse_failure": False,
                "latency_seconds": 0.5,
            }
        ],
        summary={"success_rate": 100.0},
    )
    dir_b = _write_bundle(
        tmp_path,
        "model_b",
        model="model-b",
        records=[
            {
                "preset": "BATTLE_PLAN",
                "pass": False,
                "parse_failure": False,
                "reason_code": "illegal_tool",
                "latency_seconds": 0.7,
            }
        ],
        summary={"success_rate": 0.0},
    )

    markdown = render_markdown_report(
        [
            load_benchmark_bundle(dir_a, label="Model A"),
            load_benchmark_bundle(dir_b, label="Model B"),
        ],
        title="Small Model Report",
    )

    assert "# Small Model Report" in markdown
    assert "Model A" in markdown
    assert "Model B" in markdown
    assert "illegal_tool" in markdown
    assert "BATTLE_PLAN" in markdown


def test_showcase_summary_groups_model_matrix_records_by_benchmark_model():
    records = [
        {
            "benchmark_model": "model_b",
            "model": "display_b",
            "preset": "FULL_INFO",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 2.0,
        },
        {
            "benchmark_model": "model_b",
            "model": "display_b",
            "preset": "FULL_INFO",
            "pass": False,
            "parse_failure": False,
            "reason_code": "insufficient_effective_power",
            "latency_seconds": 4.0,
        },
        {
            "benchmark_model": "model_a",
            "model": "display_a",
            "preset": "BATTLE_PLAN",
            "pass": True,
            "parse_failure": False,
            "latency_seconds": 1.0,
        },
    ]

    rows = build_showcase_model_summary_rows(records)

    assert rows[0]["model"] == "model_a"
    assert rows[0]["success_rate"] == 100.0
    assert rows[1]["model"] == "model_b"
    assert rows[1]["passed_scenes"] == 1
    assert rows[1]["failed_scenes"] == 1
    assert rows[1]["top_failure_codes"] == "insufficient_effective_power (1)"


def test_showcase_preset_and_failure_reason_rows_separate_presets():
    records = [
        {
            "benchmark_model": "model_a",
            "preset": "FULL_INFO",
            "pass": False,
            "parse_failure": False,
            "reason_code": "wrong_tool",
        },
        {
            "benchmark_model": "model_a",
            "preset": "BATTLE_PLAN",
            "pass": False,
            "parse_failure": True,
            "reason_code": "json_parse_error",
        },
    ]

    preset_rows = build_showcase_model_preset_rows(records)
    reason_rows = build_showcase_failure_reason_rows(records)

    assert {row["preset"] for row in preset_rows} == {"FULL_INFO", "BATTLE_PLAN"}
    assert reason_rows == [
        {"model": "model_a", "preset": "BATTLE_PLAN", "reason_code": "json_parse_error", "count": 1},
        {"model": "model_a", "preset": "FULL_INFO", "reason_code": "wrong_tool", "count": 1},
    ]


def test_showcase_full_info_failure_rows_preserve_tool_context():
    records = [
        {
            "benchmark_model": "model_a",
            "preset": "FULL_INFO",
            "pass": False,
            "scene_index": 2,
            "scene_id": "scene.alpha",
            "character_id": "wizard.ember",
            "selected_tool_id": "wizard.cast_fireball",
            "valid_tools": ["wizard.cast_frostbolt", "wizard.cast_lightning"],
            "reason_code": "insufficient_effective_power",
            "reason": "effective_power=3.0 < min_power_to_defeat=5",
        },
        {
            "benchmark_model": "model_a",
            "preset": "BATTLE_PLAN",
            "pass": False,
            "scene_id": "scene.beta",
        },
    ]

    rows = build_showcase_full_info_failure_rows(records)

    assert rows == [
        {
            "model": "model_a",
            "scene_index": 2,
            "scene_id": "scene.alpha",
            "character_id": "wizard.ember",
            "selected_tool_id": "wizard.cast_fireball",
            "valid_tools": "wizard.cast_frostbolt, wizard.cast_lightning",
            "reason_code": "insufficient_effective_power",
            "reason": "effective_power=3.0 < min_power_to_defeat=5",
        }
    ]


def test_render_showcase_markdown_includes_core_sections(tmp_path):
    benchmark_dir = _write_bundle(
        tmp_path,
        "model_matrix",
        model="",
        records=[
            {
                "benchmark_model": "model_a",
                "preset": "FULL_INFO",
                "pass": False,
                "parse_failure": False,
                "reason_code": "wrong_tool",
                "scene_id": "scene.alpha",
                "character_id": "wizard.ember",
            }
        ],
        summary={"dataset_id": "custom_t1_0"},
    )
    bundle = load_benchmark_bundle(benchmark_dir)

    markdown = render_showcase_markdown(bundle, title="Showcase")

    assert "# Showcase" in markdown
    assert "## Model Leaderboard" in markdown
    assert "## Model By Preset" in markdown
    assert "## Full Info Failures" in markdown
    assert "model_a" in markdown
    assert "wrong_tool" in markdown
