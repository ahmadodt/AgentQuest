import json
import os
from types import SimpleNamespace

from src.runner.benchmark_service import (
    BenchmarkRunError,
    BenchmarkSpec,
    build_benchmark_output_dirs,
    collect_dataset_metadata,
    estimate_benchmark_scene_runs,
    run_benchmark,
    run_benchmark_batch,
)


def _write_custom_data_file(root, filename, version, collection_key):
    path = root / filename
    path.write_text(
        json.dumps(
            {
                "version": version,
                collection_key: [],
            }
        ),
        encoding="utf-8",
    )


def test_collect_dataset_metadata_reads_versions_and_hashes(tmp_path):
    custom_dir = tmp_path / "custom" / "agentquest"
    custom_dir.mkdir(parents=True)
    _write_custom_data_file(custom_dir, "tools.json", "1.4", "tools")
    _write_custom_data_file(custom_dir, "characters.json", "1.2", "characters")
    _write_custom_data_file(custom_dir, "monsters.json", "1.4", "monsters")
    _write_custom_data_file(custom_dir, "scenes.json", "1.2", "scenes")
    _write_custom_data_file(custom_dir, "campaigns.json", "1.1", "campaigns")
    _write_custom_data_file(custom_dir, "damage_profiles.json", "1.0", "profiles")

    metadata = collect_dataset_metadata(str(tmp_path))

    assert metadata["dataset_id"].startswith("custom_t1_4_chars1_2_m1_4_s1_2_camps1_1_dmg1_0_")
    assert len(metadata["dataset_fingerprint"]) == 64
    assert metadata["files"]["tools"]["version"] == "1.4"
    assert metadata["files"]["campaigns"]["path"] == os.path.join("custom", "agentquest", "campaigns.json")
    assert len(metadata["files"]["damage_profiles"]["sha256"]) == 64


def test_collect_dataset_metadata_fingerprint_changes_when_content_changes(tmp_path):
    custom_dir = tmp_path / "custom" / "agentquest"
    custom_dir.mkdir(parents=True)
    _write_custom_data_file(custom_dir, "tools.json", "1.0", "tools")
    _write_custom_data_file(custom_dir, "characters.json", "1.0", "characters")
    _write_custom_data_file(custom_dir, "monsters.json", "1.0", "monsters")
    _write_custom_data_file(custom_dir, "scenes.json", "1.0", "scenes")
    _write_custom_data_file(custom_dir, "campaigns.json", "1.0", "campaigns")

    first = collect_dataset_metadata(str(tmp_path))
    (custom_dir / "tools.json").write_text(
        json.dumps({"version": "1.0", "tools": [{"tool_id": "tool.alpha"}]}),
        encoding="utf-8",
    )
    second = collect_dataset_metadata(str(tmp_path))

    assert first["dataset_id"] != second["dataset_id"]
    assert first["dataset_fingerprint"] != second["dataset_fingerprint"]


def test_build_benchmark_output_dirs_uses_results_benchmarks(monkeypatch, tmp_path):
    monkeypatch.setattr("src.runner.benchmark_service.get_results_dir", lambda: str(tmp_path / "results"))

    output_dir, latest_dir = build_benchmark_output_dirs(
        dataset_id="custom_t1_hash",
        campaign_ids=["campaign.alpha"],
        model_names=["model/alpha"],
        timestamp="20260531_120000",
    )

    expected_base = tmp_path / "results" / "benchmarks" / "custom_t1_hash" / "campaign.alpha" / "model_alpha"
    assert output_dir == str(expected_base / "20260531_120000")
    assert latest_dir == str(expected_base / "latest")


class _FakeHandler:
    def __init__(self, model_name):
        self.model_name = model_name

    def generate(self, messages, max_tokens, temperature):
        return SimpleNamespace(
            raw_text=json.dumps({"tool_id": "common.run", "arguments": {"direction": "backtrack"}}),
            metadata={"model": self.model_name},
        )


class _FailSecondHandler:
    def __init__(self, model_name):
        self.model_name = model_name
        self.calls = 0

    def generate(self, messages, max_tokens, temperature):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("transient model failure")
        return SimpleNamespace(
            raw_text=json.dumps({"tool_id": "common.run", "arguments": {"direction": "backtrack"}}),
            metadata={"model": self.model_name},
        )


def test_run_benchmark_writes_artifacts_and_dataset_id(gamedata, tmp_path):
    campaign_ids = ["campaign.tutorial_v1"]
    character_ids = ["wizard.ember"]
    preset_names = ["BATTLE_PLAN"]
    prompt_formats = ["json_only"]
    model_names = ["fake_model"]
    spec = BenchmarkSpec(
        data_dir="data",
        campaign_ids=campaign_ids,
        character_ids=character_ids,
        preset_names=preset_names,
        prompt_formats=prompt_formats,
        model_names=model_names,
        backend="llama_cpp",
        output_dir=str(tmp_path / "benchmark"),
    )
    dataset = {
        "dataset_id": "custom_test_hash",
        "dataset_fingerprint": "abc123",
        "data_dir": os.path.abspath("data"),
        "runtime_data_dir": os.path.abspath(os.path.join("data", "custom", "agentquest")),
        "files": {},
    }

    result = run_benchmark(
        gamedata=gamedata,
        spec=spec,
        dataset_metadata=dataset,
        handler_factory=lambda model_name: _FakeHandler(model_name),
    )

    expected_records = estimate_benchmark_scene_runs(
        gamedata=gamedata,
        campaign_ids=campaign_ids,
        character_ids=character_ids,
        preset_names=preset_names,
        prompt_formats=prompt_formats,
        model_names=model_names,
    )
    assert len(result["records"]) == expected_records
    assert result["summary"]["dataset_id"] == "custom_test_hash"
    assert result["records"][0]["dataset_id"] == "custom_test_hash"
    assert (tmp_path / "benchmark" / "manifest.json").exists()
    assert (tmp_path / "benchmark" / "records.json").exists()
    assert (tmp_path / "benchmark" / "summary.json").exists()


def test_run_benchmark_emits_scene_progress_events(gamedata, tmp_path):
    spec = BenchmarkSpec(
        data_dir="data",
        campaign_ids=["campaign.tutorial_v1"],
        character_ids=["wizard.ember"],
        preset_names=["BATTLE_PLAN"],
        prompt_formats=["json_only"],
        model_names=["fake_model"],
        backend="llama_cpp",
        output_dir=str(tmp_path / "benchmark"),
    )
    dataset = {
        "dataset_id": "custom_test_hash",
        "dataset_fingerprint": "abc123",
        "data_dir": os.path.abspath("data"),
        "runtime_data_dir": os.path.abspath(os.path.join("data", "custom", "agentquest")),
        "files": {},
    }
    events = []

    result = run_benchmark(
        gamedata=gamedata,
        spec=spec,
        dataset_metadata=dataset,
        handler_factory=lambda model_name: _FakeHandler(model_name),
        progress_callback=events.append,
    )

    assert len(events) == len(result["records"]) * 2
    assert events[0]["event"] == "scene_start"
    assert events[1]["event"] == "scene_finish"
    assert events[0]["scene_id"] == "scene.tutorial.001_goblin_alley"
    assert events[0]["completed"] == 0
    assert events[0]["total"] == len(result["records"])
    assert events[1]["completed"] == 1
    assert events[1]["remaining"] == len(result["records"]) - 1
    assert events[1]["status"] == result["records"][0]["status"]


def test_run_benchmark_batch_checkpoints_and_reruns_failed_scene(gamedata, tmp_path):
    spec = BenchmarkSpec(
        data_dir="data",
        campaign_ids=["campaign.tutorial_v1"],
        character_ids=["wizard.ember"],
        preset_names=["BATTLE_PLAN"],
        prompt_formats=["json_only"],
        model_names=["fake_model"],
        backend="llama_cpp",
        output_dir=str(tmp_path / "benchmark"),
    )
    dataset = {
        "dataset_id": "custom_test_hash",
        "dataset_fingerprint": "abc123",
        "data_dir": os.path.abspath("data"),
        "runtime_data_dir": os.path.abspath(os.path.join("data", "custom", "agentquest")),
        "files": {},
    }
    failing_handler = _FailSecondHandler("fake_model")

    try:
        run_benchmark_batch(
            gamedata=gamedata,
            spec=spec,
            dataset_metadata=dataset,
            handler_factory=lambda model_name: failing_handler,
            max_scene_runs=2,
        )
        assert False, "Expected the second benchmark item to fail"
    except BenchmarkRunError as error:
        partial = error.result

    assert len(partial["records"]) == 1
    assert partial["records"][0]["scene_id"] == "scene.tutorial.001_goblin_alley"
    assert partial["next_item"]["scene_id"] == "scene.tutorial.002_runes_on_wall"
    assert (tmp_path / "benchmark" / "records.json").exists()

    resumed = run_benchmark_batch(
        gamedata=gamedata,
        spec=spec,
        dataset_metadata=dataset,
        handler_factory=lambda model_name: _FakeHandler(model_name),
        max_scene_runs=1,
    )

    assert len(resumed["records"]) == 2
    assert resumed["records"][1]["scene_id"] == "scene.tutorial.002_runes_on_wall"
    assert resumed["summary"]["completed_scene_runs"] == 2
    assert resumed["summary"]["remaining_scene_runs"] == 1
