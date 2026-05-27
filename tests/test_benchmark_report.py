from src.runner.benchmark_report import (
    load_benchmark_bundle,
    render_markdown_report,
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
