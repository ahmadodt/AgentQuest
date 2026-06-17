from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from src.engine.validation.report_utils import collect_scene_character_tool_results
from src.models.config import RuntimeModelConfig
from src.models.registry import build_handler
from src.runner.benchmark_utils import (
    aggregate_benchmark_records,
    benchmark_item_key,
    benchmark_record_key,
    build_benchmark_record,
)
from src.runner.power import prevent_system_sleep
from src.runner.runner_utils import (
    ensure_dir,
    execute_learning_scene,
    execute_scene_run,
    get_campaign_scene_ids,
    get_results_dir,
    load_preset,
    safe_path_segment,
    timestamp_for_filename,
    write_json_file,
)


CUSTOM_DATA_FILES = [
    ("tools", "tools.json", "t"),
    ("characters", "characters.json", "chars"),
    ("monsters", "monsters.json", "m"),
    ("scenes", "scenes.json", "s"),
    ("campaigns", "campaigns.json", "camps"),
    ("damage_profiles", "damage_profiles.json", "dmg"),
]


@dataclass(frozen=True)
class BenchmarkSpec:
    data_dir: str
    campaign_ids: list[str]
    character_ids: list[str]
    preset_names: list[str]
    prompt_formats: list[str]
    model_names: list[str]
    backend: str
    max_tokens: int = 128
    temperature: float = 0.0
    self_learning_enabled: bool = False
    per_scene_retry_limit: int = 3
    total_retry_limit: int = 20
    initial_notes: str = ""
    output_dir: str = ""


class BenchmarkRunError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        failed_item: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        super().__init__(message)
        self.failed_item = failed_item
        self.result = result


def _runtime_data_dir(data_dir: str) -> str:
    return os.path.join(os.path.abspath(data_dir), "custom", "agentquest")


def _version_slug(version: str) -> str:
    return safe_path_segment((version or "unversioned").replace(".", "_"))


def collect_dataset_metadata(data_dir: str) -> dict[str, Any]:
    runtime_data_dir = _runtime_data_dir(data_dir)
    file_entries: dict[str, dict[str, str]] = {}
    combined = hashlib.sha256()
    version_segments: list[str] = []

    for key, filename, slug_prefix in CUSTOM_DATA_FILES:
        path = os.path.join(runtime_data_dir, filename)
        if not os.path.exists(path):
            if key == "damage_profiles":
                continue
            raise FileNotFoundError(path)

        with open(path, "rb") as file_obj:
            content = file_obj.read()
        digest = hashlib.sha256(content).hexdigest()
        combined.update(filename.encode("utf-8"))
        combined.update(b"\0")
        combined.update(content)
        combined.update(b"\0")

        try:
            raw = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

        version = raw.get("version", "")
        if not isinstance(version, str):
            version = str(version)

        relative_path = os.path.relpath(path, os.path.abspath(data_dir))
        file_entries[key] = {
            "path": relative_path,
            "version": version,
            "sha256": digest,
        }
        version_segments.append(f"{slug_prefix}{_version_slug(version)}")

    fingerprint = combined.hexdigest()
    dataset_id = safe_path_segment(f"custom_{'_'.join(version_segments)}")
    return {
        "dataset_id": dataset_id,
        "dataset_fingerprint": fingerprint,
        "data_dir": os.path.abspath(data_dir),
        "runtime_data_dir": runtime_data_dir,
        "files": file_entries,
    }


def estimate_benchmark_scene_runs(
    *,
    gamedata: dict,
    campaign_ids: list[str],
    character_ids: list[str],
    preset_names: list[str],
    prompt_formats: list[str],
    model_names: list[str],
) -> int:
    scene_count = sum(len(get_campaign_scene_ids(gamedata, campaign_id)) for campaign_id in campaign_ids)
    return scene_count * len(character_ids) * len(preset_names) * len(prompt_formats) * len(model_names)


def build_benchmark_output_dirs(
    *,
    dataset_id: str,
    campaign_ids: list[str],
    model_names: list[str],
    timestamp: str | None = None,
) -> tuple[str, str]:
    campaign_segment = campaign_ids[0] if len(campaign_ids) == 1 else "all_campaigns"
    model_segment = model_names[0] if len(model_names) == 1 else "model_matrix"
    benchmark_dir = os.path.join(
        get_results_dir(),
        "benchmarks",
        safe_path_segment(dataset_id),
        safe_path_segment(campaign_segment),
        safe_path_segment(model_segment),
    )
    return (
        os.path.join(benchmark_dir, timestamp or timestamp_for_filename()),
        os.path.join(benchmark_dir, "latest"),
    )


def build_benchmark_manifest(
    *,
    spec: BenchmarkSpec,
    dataset_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data_dir": os.path.abspath(spec.data_dir),
        "dataset": dataset_metadata,
        "dataset_id": dataset_metadata["dataset_id"],
        "campaign_ids": spec.campaign_ids,
        "character_ids": spec.character_ids,
        "presets": spec.preset_names,
        "prompt_formats": spec.prompt_formats,
        "models": spec.model_names,
        "backend": spec.backend,
        "max_tokens": spec.max_tokens,
        "temperature": spec.temperature,
        "self_learning_enabled": spec.self_learning_enabled,
        "per_scene_retry_limit": spec.per_scene_retry_limit,
        "total_retry_limit": spec.total_retry_limit,
        "initial_notes": spec.initial_notes,
    }


def _write_artifacts(
    *,
    output_dir: str,
    latest_dir: str,
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    ensure_dir(output_dir)
    write_json_file(os.path.join(output_dir, "manifest.json"), manifest)
    write_json_file(os.path.join(output_dir, "records.json"), records)
    write_json_file(os.path.join(output_dir, "summary.json"), summary)
    if latest_dir:
        ensure_dir(latest_dir)
        write_json_file(os.path.join(latest_dir, "manifest.json"), manifest)
        write_json_file(os.path.join(latest_dir, "records.json"), records)
        write_json_file(os.path.join(latest_dir, "summary.json"), summary)


def _read_records(path: str) -> list[dict[str, Any]]:
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError(f"Benchmark records file must contain a list: {path}")
    return [item for item in raw if isinstance(item, dict)]


def _build_benchmark_items(*, gamedata: dict, spec: BenchmarkSpec) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for model_name in spec.model_names:
        for campaign_id in spec.campaign_ids:
            scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
            for character_id in spec.character_ids:
                for preset_name in spec.preset_names:
                    for prompt_format in spec.prompt_formats:
                        for scene_index, scene_id in enumerate(scene_ids):
                            scene = gamedata["scenes_by_id"].get(scene_id, {})
                            items.append(
                                {
                                    "model": model_name,
                                    "preset": preset_name,
                                    "campaign_id": campaign_id,
                                    "character_id": character_id,
                                    "prompt_format": prompt_format,
                                    "scene_id": scene_id,
                                    "scene_index": scene_index,
                                    "scene_title": scene.get("title", scene_id),
                                    "benchmark_tags": dict(scene.get("benchmark_tags") or {}),
                                }
                            )
    return items


def _item_key(item: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return benchmark_item_key(
        model=item["model"],
        preset=item["preset"],
        campaign_id=item["campaign_id"],
        character_id=item["character_id"],
        prompt_format=item["prompt_format"],
        scene_id=item["scene_id"],
    )


def _completed_record_keys(records: list[dict[str, Any]]) -> set[tuple[str, str, str, str, str, str]]:
    return {benchmark_record_key(record) for record in records}


def _build_summary(
    *,
    records: list[dict[str, Any]],
    dataset_metadata: dict[str, Any],
    spec: BenchmarkSpec,
    total_scene_runs: int,
    complete: bool,
) -> dict[str, Any]:
    summary = aggregate_benchmark_records(records)
    summary["dataset"] = dataset_metadata
    summary["dataset_id"] = dataset_metadata["dataset_id"]
    summary["self_learning_enabled"] = spec.self_learning_enabled
    summary["completed_scene_runs"] = len(records)
    summary["expected_scene_runs"] = total_scene_runs
    summary["remaining_scene_runs"] = max(total_scene_runs - len(records), 0)
    summary["benchmark_complete"] = complete
    if spec.self_learning_enabled:
        summary["per_scene_retry_limit"] = spec.per_scene_retry_limit
        summary["total_retry_limit"] = spec.total_retry_limit
        summary["total_retries_used"] = sum(record.get("retry_count") or 0 for record in records)
    return summary


def _result_payload(
    *,
    output_dir: str,
    latest_dir: str,
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    next_item: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "output_dir": output_dir,
        "latest_dir": latest_dir,
        "manifest": manifest,
        "records": records,
        "summary": summary,
        "complete": bool(summary.get("benchmark_complete")),
        "next_item": next_item,
    }


def _write_checkpoint(
    *,
    output_dir: str,
    latest_dir: str,
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    dataset_metadata: dict[str, Any],
    spec: BenchmarkSpec,
    total_scene_runs: int,
    complete: bool,
    next_item: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = _build_summary(
        records=records,
        dataset_metadata=dataset_metadata,
        spec=spec,
        total_scene_runs=total_scene_runs,
        complete=complete,
    )
    _write_artifacts(
        output_dir=output_dir,
        latest_dir=latest_dir,
        manifest=manifest,
        records=records,
        summary=summary,
    )
    return _result_payload(
        output_dir=output_dir,
        latest_dir=latest_dir,
        manifest=manifest,
        records=records,
        summary=summary,
        next_item=next_item,
    )


def run_benchmark(
    *,
    gamedata: dict,
    spec: BenchmarkSpec,
    dataset_metadata: dict[str, Any] | None = None,
    handler_factory: Callable[[str], Any] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    with prevent_system_sleep():
        return _run_benchmark_batch(
            gamedata=gamedata,
            spec=spec,
            dataset_metadata=dataset_metadata,
            handler_factory=handler_factory,
            progress_callback=progress_callback,
            max_scene_runs=None,
            resume=False,
        )


def run_benchmark_batch(
    *,
    gamedata: dict,
    spec: BenchmarkSpec,
    dataset_metadata: dict[str, Any] | None = None,
    handler_factory: Callable[[str], Any] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    max_scene_runs: int = 1,
    resume: bool = True,
) -> dict[str, Any]:
    with prevent_system_sleep():
        return _run_benchmark_batch(
            gamedata=gamedata,
            spec=spec,
            dataset_metadata=dataset_metadata,
            handler_factory=handler_factory,
            progress_callback=progress_callback,
            max_scene_runs=max_scene_runs,
            resume=resume,
        )


def _run_benchmark_batch(
    *,
    gamedata: dict,
    spec: BenchmarkSpec,
    dataset_metadata: dict[str, Any] | None = None,
    handler_factory: Callable[[str], Any] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    max_scene_runs: int | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    if max_scene_runs is not None and max_scene_runs < 1:
        raise ValueError("max_scene_runs must be at least 1.")

    dataset_metadata = dataset_metadata or collect_dataset_metadata(spec.data_dir)
    output_dir, latest_dir = (
        (os.path.abspath(spec.output_dir), "")
        if spec.output_dir
        else build_benchmark_output_dirs(
            dataset_id=dataset_metadata["dataset_id"],
            campaign_ids=spec.campaign_ids,
            model_names=spec.model_names,
        )
    )
    manifest = build_benchmark_manifest(spec=spec, dataset_metadata=dataset_metadata)
    items = _build_benchmark_items(gamedata=gamedata, spec=spec)
    records = _read_records(os.path.join(output_dir, "records.json")) if resume else []
    deterministic_valid_tools: dict[str, list[str]] = {}
    total_scene_runs = len(items)
    completed_keys = _completed_record_keys(records)
    handlers: dict[str, Any] = {}
    preset_cache = {preset_name: load_preset(preset_name) for preset_name in spec.preset_names}
    ran_scene_count = 0

    for item in items:
        if _item_key(item) in completed_keys:
            continue
        if max_scene_runs is not None and ran_scene_count >= max_scene_runs:
            break

        model_name = item["model"]
        campaign_id = item["campaign_id"]
        character_id = item["character_id"]
        preset_name = item["preset"]
        prompt_format = item["prompt_format"]
        scene_id = item["scene_id"]
        scene_index = item["scene_index"]
        benchmark_tags = item.get("benchmark_tags") or {}
        cfg = preset_cache[preset_name]
        handler = handlers.get(model_name)
        if handler is None:
            handler = handler_factory(model_name) if handler_factory else build_handler(model_name_override=model_name)
            handlers[model_name] = handler

        base_event = {
            **item,
            "completed": len(records),
            "total": total_scene_runs,
            "remaining": total_scene_runs - len(records),
        }
        if progress_callback:
            progress_callback({"event": "scene_start", **base_event})

        valid_tools_key = f"{scene_id}::{character_id}"
        if valid_tools_key not in deterministic_valid_tools:
            tool_results = collect_scene_character_tool_results(
                gamedata,
                scene_id=scene_id,
                character_id=character_id,
            )
            deterministic_valid_tools[valid_tools_key] = [
                item["tool_id"] for item in tool_results["valid_tools"]
            ]

        previous_records = [
            record
            for record in records
            if record.get("model") == model_name
            and record.get("campaign_id") == campaign_id
            and record.get("character_id") == character_id
            and record.get("preset") == preset_name
            and record.get("prompt_format") == prompt_format
        ]
        notes = previous_records[-1].get("final_notes", spec.initial_notes) if previous_records else spec.initial_notes
        total_retries_used = sum(record.get("retry_count") or 0 for record in previous_records)

        start_time = time.perf_counter()
        try:
            if spec.self_learning_enabled:
                scene_learning = execute_learning_scene(
                    gamedata=gamedata,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_id=scene_id,
                    scene_index=scene_index,
                    prompt_format=prompt_format,
                    cfg=cfg,
                    model_key="",
                    max_tokens=spec.max_tokens,
                    temperature=spec.temperature,
                    current_notes=notes,
                    per_scene_retry_limit=spec.per_scene_retry_limit,
                    total_retry_limit_remaining=max(spec.total_retry_limit - total_retries_used, 0),
                    model_name_override=model_name,
                    handler=handler,
                )
                scene_run = scene_learning["scene_result"]
                notes = scene_learning["updated_notes"]
                total_retries_used += scene_learning["retries_used"]
                scene_run["total_retries_used"] = total_retries_used
                scene_run["initial_notes"] = spec.initial_notes
                scene_run["final_notes"] = notes
            else:
                scene_run = execute_scene_run(
                    gamedata=gamedata,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_id=scene_id,
                    scene_index=scene_index,
                    prompt_format=prompt_format,
                    cfg=cfg,
                    model_key="",
                    max_tokens=spec.max_tokens,
                    temperature=spec.temperature,
                    model_name_override=model_name,
                    handler=handler,
                )
        except Exception as exc:
            result = _write_checkpoint(
                output_dir=output_dir,
                latest_dir=latest_dir,
                manifest=manifest,
                records=records,
                dataset_metadata=dataset_metadata,
                spec=spec,
                total_scene_runs=total_scene_runs,
                complete=False,
                next_item=item,
            )
            raise BenchmarkRunError(
                f"Benchmark scene failed before a record could be written: {exc}",
                failed_item=item,
                result=result,
            ) from exc

        latency_seconds = time.perf_counter() - start_time
        model_label = scene_run.get("model") or model_name
        record = build_benchmark_record(
            campaign_id=campaign_id,
            scene_run=scene_run,
            character_id=character_id,
            preset=preset_name,
            prompt_format=prompt_format,
            model=model_label,
            valid_tools=deterministic_valid_tools[valid_tools_key],
            latency_seconds=latency_seconds,
            dataset_id=dataset_metadata["dataset_id"],
            benchmark_tags=benchmark_tags,
        )
        record["benchmark_model"] = model_name
        records.append(record)
        completed_keys.add(_item_key(item))
        ran_scene_count += 1

        next_item = next((candidate for candidate in items if _item_key(candidate) not in completed_keys), None)
        result = _write_checkpoint(
            output_dir=output_dir,
            latest_dir=latest_dir,
            manifest=manifest,
            records=records,
            dataset_metadata=dataset_metadata,
            spec=spec,
            total_scene_runs=total_scene_runs,
            complete=next_item is None,
            next_item=next_item,
        )
        if progress_callback:
            progress_callback(
                {
                    "event": "scene_finish",
                    **base_event,
                    "model_label": model_label,
                    "completed": len(records),
                    "remaining": total_scene_runs - len(records),
                    "status": record.get("status"),
                    "reason": record.get("reason", ""),
                    "reason_code": record.get("reason_code"),
                    "selected_tool_id": record.get("selected_tool_id"),
                    "parse_failure": record.get("parse_failure"),
                    "latency_seconds": latency_seconds,
                }
            )

    next_item = next((candidate for candidate in items if _item_key(candidate) not in completed_keys), None)
    return _write_checkpoint(
        output_dir=output_dir,
        latest_dir=latest_dir,
        manifest=manifest,
        records=records,
        dataset_metadata=dataset_metadata,
        spec=spec,
        total_scene_runs=total_scene_runs,
        complete=next_item is None,
        next_item=next_item,
    )


def spec_from_runtime_config(
    *,
    data_dir: str,
    campaign_ids: list[str],
    character_ids: list[str],
    preset_names: list[str],
    prompt_formats: list[str],
    runtime_model_cfg: RuntimeModelConfig,
    model_names: list[str] | None = None,
    max_tokens: int = 128,
    temperature: float = 0.0,
    self_learning_enabled: bool = False,
    per_scene_retry_limit: int = 3,
    total_retry_limit: int = 20,
    initial_notes: str = "",
    output_dir: str = "",
) -> BenchmarkSpec:
    return BenchmarkSpec(
        data_dir=data_dir,
        campaign_ids=campaign_ids,
        character_ids=character_ids,
        preset_names=preset_names,
        prompt_formats=prompt_formats,
        model_names=model_names or [runtime_model_cfg.model_name],
        backend=runtime_model_cfg.backend,
        max_tokens=max_tokens,
        temperature=temperature,
        self_learning_enabled=self_learning_enabled,
        per_scene_retry_limit=per_scene_retry_limit,
        total_retry_limit=total_retry_limit,
        initial_notes=initial_notes,
        output_dir=output_dir,
    )
