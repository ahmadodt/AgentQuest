import json
import os

from src.runner.benchmark_history import (
    compare_dataset_metadata,
    discover_benchmark_bundles,
    publish_benchmark_showcase,
)
from src.runner.benchmark_service import collect_dataset_metadata
from src.runner.runner_utils import write_json_file


def _write_bundle(path, dataset, *, timestamp="2026-06-02T08:00:00Z"):
    path.mkdir(parents=True)
    write_json_file(
        str(path / "manifest.json"),
        {
            "timestamp": timestamp,
            "data_dir": "C:/private/data",
            "dataset_id": dataset["dataset_id"],
            "dataset": dataset,
            "models": ["model_a"],
            "campaign_ids": ["campaign.alpha"],
            "character_ids": ["character.alpha"],
            "presets": ["BATTLE_PLAN"],
        },
    )
    write_json_file(str(path / "summary.json"), {"success_rate": 100.0})
    write_json_file(str(path / "records.json"), [{"pass": True, "benchmark_model": "model_a"}])


def test_compare_dataset_metadata_reports_exact_mismatch_and_unknown():
    current = {
        "dataset_fingerprint": "current",
        "files": {"tools": {"version": "1.2", "sha256": "new"}},
    }

    exact = compare_dataset_metadata({"dataset": current}, current)
    mismatch = compare_dataset_metadata(
        {"dataset": {"dataset_fingerprint": "old", "files": {"tools": {"version": "1.1", "sha256": "old"}}}},
        current,
    )
    unknown = compare_dataset_metadata({}, current)

    assert exact["status"] == "exact"
    assert exact["matches"] is True
    assert mismatch["status"] == "mismatch"
    assert mismatch["differences"] == ["tools: 1.1 -> 1.2"]
    assert unknown["status"] == "unknown"


def test_discovery_prefers_curated_duplicate_and_skips_latest(tmp_path):
    data_dir = os.path.abspath("data")
    dataset = collect_dataset_metadata(data_dir)
    curated = tmp_path / "showcase" / "core"
    local = tmp_path / "results" / "dated"
    latest = tmp_path / "results" / "latest"
    _write_bundle(curated, dataset)
    _write_bundle(local, dataset)
    _write_bundle(latest, dataset, timestamp="2026-06-03T08:00:00Z")

    bundles = discover_benchmark_bundles(
        data_dir=data_dir,
        showcase_dir=str(tmp_path / "showcase"),
        local_dir=str(tmp_path / "results"),
    )

    assert len(bundles) == 1
    assert bundles[0]["source"] == "curated"
    assert bundles[0]["compatibility"]["status"] == "exact"


def test_publish_showcase_sanitizes_machine_paths_and_keeps_source(tmp_path):
    dataset = collect_dataset_metadata(os.path.abspath("data"))
    dataset["data_dir"] = "C:/private/data"
    dataset["runtime_data_dir"] = "C:/private/data/custom/agentquest"
    source = tmp_path / "source"
    _write_bundle(source, dataset)
    destination = publish_benchmark_showcase(
        str(source),
        showcase_id="core-matrix",
        title="Core Matrix",
        description="Three-model comparison.",
        showcase_dir=str(tmp_path / "showcase"),
    )

    with open(os.path.join(destination, "manifest.json"), "r", encoding="utf-8") as file_obj:
        manifest = json.load(file_obj)
    with open(os.path.join(destination, "summary.json"), "r", encoding="utf-8") as file_obj:
        summary = json.load(file_obj)
    with open(os.path.join(destination, "showcase.json"), "r", encoding="utf-8") as file_obj:
        showcase = json.load(file_obj)

    assert "data_dir" not in manifest
    assert "data_dir" not in manifest["dataset"]
    assert "runtime_data_dir" not in manifest["dataset"]
    assert "data_dir" not in summary["dataset"]
    assert "runtime_data_dir" not in summary["dataset"]
    assert showcase["title"] == "Core Matrix"
    assert (source / "manifest.json").exists()
    assert sorted(os.listdir(destination)) == ["manifest.json", "records.json", "showcase.json", "summary.json"]
