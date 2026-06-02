from __future__ import annotations

from collections import Counter
from typing import Any


def benchmark_item_key(
    *,
    model: str,
    preset: str,
    campaign_id: str,
    character_id: str,
    prompt_format: str,
    scene_id: str,
) -> tuple[str, str, str, str, str, str]:
    return (model, preset, campaign_id, character_id, prompt_format, scene_id)


def benchmark_record_key(record: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return benchmark_item_key(
        model=str(record.get("benchmark_model") or record.get("model") or ""),
        preset=str(record.get("preset") or ""),
        campaign_id=str(record.get("campaign_id") or ""),
        character_id=str(record.get("character_id") or ""),
        prompt_format=str(record.get("prompt_format") or ""),
        scene_id=str(record.get("scene_id") or ""),
    )


def extract_effective_power(validation: dict[str, Any] | None) -> float | None:
    if not isinstance(validation, dict):
        return None
    value = validation.get("effective_power")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_benchmark_record(
    *,
    campaign_id: str,
    scene_run: dict[str, Any],
    character_id: str,
    preset: str,
    prompt_format: str,
    model: str,
    valid_tools: list[str],
    latency_seconds: float | None,
    dataset_id: str = "",
) -> dict[str, Any]:
    validation = scene_run.get("validation", {}) or {}
    parsed_tool_call = scene_run.get("parsed_tool_call") or {}
    status = scene_run.get("status")
    parse_failure = status == "PARSE_ERROR" or validation.get("ast_valid") is False

    record = {
        "dataset_id": dataset_id,
        "campaign_id": campaign_id,
        "scene_id": scene_run.get("scene_id"),
        "scene_index": scene_run.get("scene_index"),
        "character_id": character_id,
        "preset": preset,
        "prompt_format": prompt_format,
        "model": model,
        "selected_tool_id": parsed_tool_call.get("tool_id"),
        "parsed_arguments": parsed_tool_call.get("arguments"),
        "pass": status == "PASS",
        "status": status,
        "reason": validation.get("reason", scene_run.get("reason", "")),
        "reason_code": validation.get("reason_code"),
        "effective_power": extract_effective_power(validation),
        "valid_tools": list(valid_tools),
        "latency_seconds": latency_seconds,
        "parse_failure": parse_failure,
        "raw_model_output": scene_run.get("raw_model_output", ""),
    }
    if "attempt_count" in scene_run:
        record["attempt_count"] = scene_run.get("attempt_count")
    if "retry_count" in scene_run:
        record["retry_count"] = scene_run.get("retry_count")
    if "resolved_after_learning" in scene_run:
        record["resolved_after_learning"] = bool(scene_run.get("resolved_after_learning"))
    if "total_retries_used" in scene_run:
        record["total_retries_used"] = scene_run.get("total_retries_used")
    if "initial_notes" in scene_run:
        record["initial_notes"] = scene_run.get("initial_notes", "")
    if "final_notes" in scene_run:
        record["final_notes"] = scene_run.get("final_notes", "")
    if scene_run.get("attempts"):
        record["attempts"] = [
            {
                "attempt_index": attempt.get("attempt_index"),
                "status": attempt.get("status"),
                "reason": attempt.get("reason", ""),
                "parsed_tool_call": attempt.get("parsed_tool_call"),
                "validation": attempt.get("validation"),
                "raw_model_output": attempt.get("raw_model_output", ""),
            }
            for attempt in scene_run.get("attempts", [])
        ]
    return record


def aggregate_benchmark_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    total_scenes = len(records)
    passed_scenes = sum(1 for record in records if record.get("pass") is True)
    parse_failures = sum(1 for record in records if record.get("parse_failure") is True)
    failed_records = [record for record in records if record.get("pass") is not True]
    failed_scenes = len(failed_records)
    success_rate = (passed_scenes / total_scenes * 100.0) if total_scenes else 0.0

    failures_by_reason_code = Counter(
        (record.get("reason_code") or "unknown_reason")
        for record in failed_records
    )
    failures_by_preset = Counter(record.get("preset") for record in failed_records)
    failures_by_character = Counter(record.get("character_id") for record in failed_records)

    first_failed_scene = None
    if failed_records:
        first_failed = failed_records[0]
        first_failed_scene = {
            "campaign_id": first_failed.get("campaign_id"),
            "scene_id": first_failed.get("scene_id"),
            "character_id": first_failed.get("character_id"),
            "preset": first_failed.get("preset"),
            "prompt_format": first_failed.get("prompt_format"),
            "reason_code": first_failed.get("reason_code"),
        }

    return {
        "total_scenes": total_scenes,
        "passed_scenes": passed_scenes,
        "failed_scenes": failed_scenes,
        "parse_failures": parse_failures,
        "success_rate": success_rate,
        "failures_by_reason_code": dict(failures_by_reason_code),
        "failures_by_preset": dict(failures_by_preset),
        "failures_by_character": dict(failures_by_character),
        "first_failed_scene": first_failed_scene,
    }


def build_benchmark_model_summary_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        model = str(record.get("benchmark_model") or record.get("model") or "unknown")
        row = grouped.setdefault(model, _empty_summary_row(model=model))
        _add_record_to_summary_row(row, record)
    return _finalize_summary_rows(list(grouped.values()))


def build_benchmark_model_preset_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        model = str(record.get("benchmark_model") or record.get("model") or "unknown")
        preset = str(record.get("preset") or "unknown")
        key = (model, preset)
        row = grouped.setdefault(key, _empty_summary_row(model=model, preset=preset))
        _add_record_to_summary_row(row, record)
    return _finalize_summary_rows(list(grouped.values()))


def build_benchmark_failure_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        if record.get("pass") is True:
            continue
        rows.append(
            {
                "model": str(record.get("benchmark_model") or record.get("model") or "unknown"),
                "preset": record.get("preset", ""),
                "campaign_id": record.get("campaign_id", ""),
                "character_id": record.get("character_id", ""),
                "scene_id": record.get("scene_id", ""),
                "selected_tool_id": record.get("selected_tool_id", ""),
                "reason_code": record.get("reason_code") or "unknown_reason",
                "reason": record.get("reason", ""),
            }
        )
    return rows


def build_benchmark_failure_reason_rows(
    records: list[dict[str, Any]],
    *,
    include_preset: bool = False,
) -> list[dict[str, Any]]:
    grouped: Counter[tuple[str, ...]] = Counter()
    for record in records:
        if record.get("pass") is True:
            continue
        model = str(record.get("benchmark_model") or record.get("model") or "unknown")
        reason_code = str(record.get("reason_code") or "unknown_reason")
        if include_preset:
            grouped[(model, str(record.get("preset") or "unknown"), reason_code)] += 1
        else:
            grouped[(model, reason_code)] += 1

    rows: list[dict[str, Any]] = []
    for key, count in grouped.items():
        if include_preset:
            model, preset, reason_code = key
            rows.append(
                {
                    "model": model,
                    "preset": preset,
                    "reason_code": reason_code,
                    "count": count,
                }
            )
        else:
            model, reason_code = key
            rows.append(
                {
                    "model": model,
                    "reason_code": reason_code,
                    "count": count,
                }
            )

    if include_preset:
        return sorted(rows, key=lambda item: (item["model"], item["preset"], -item["count"], item["reason_code"]))
    return sorted(rows, key=lambda item: (item["model"], -item["count"], item["reason_code"]))


def _empty_summary_row(*, model: str, preset: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "model": model,
        "total_scenes": 0,
        "passed_scenes": 0,
        "failed_scenes": 0,
        "parse_failures": 0,
        "success_rate": 0.0,
        "avg_latency_seconds": None,
        "top_failure_codes": "-",
        "_latency_values": [],
        "_failure_codes": Counter(),
    }
    if preset is not None:
        row["preset"] = preset
    return row


def _add_record_to_summary_row(row: dict[str, Any], record: dict[str, Any]) -> None:
    row["total_scenes"] += 1
    if record.get("pass") is True:
        row["passed_scenes"] += 1
    else:
        row["failed_scenes"] += 1
        reason_code = str(record.get("reason_code") or "unknown_reason")
        row["_failure_codes"][reason_code] += 1
    if record.get("parse_failure") is True:
        row["parse_failures"] += 1
    latency = record.get("latency_seconds")
    if isinstance(latency, (int, float)):
        row["_latency_values"].append(float(latency))


def _finalize_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    for row in rows:
        total_scenes = row["total_scenes"]
        passed_scenes = row["passed_scenes"]
        latency_values = row.pop("_latency_values")
        failure_codes = row.pop("_failure_codes")
        row["success_rate"] = (passed_scenes / total_scenes * 100.0) if total_scenes else 0.0
        row["avg_latency_seconds"] = (
            sum(latency_values) / len(latency_values)
            if latency_values
            else None
        )
        row["top_failure_codes"] = _format_failure_codes(failure_codes)
        finalized.append(row)

    return sorted(
        finalized,
        key=lambda item: (
            -item["success_rate"],
            item["parse_failures"],
            item["avg_latency_seconds"] if item["avg_latency_seconds"] is not None else float("inf"),
            item["model"],
            item.get("preset", ""),
        ),
    )


def _format_failure_codes(failure_codes: Counter) -> str:
    if not failure_codes:
        return "-"
    return ", ".join(
        f"{reason_code} ({count})"
        for reason_code, count in failure_codes.most_common(3)
    )


def _progress_key(event: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return benchmark_item_key(
        model=str(event.get("model") or ""),
        preset=str(event.get("preset") or ""),
        campaign_id=str(event.get("campaign_id") or ""),
        character_id=str(event.get("character_id") or ""),
        prompt_format=str(event.get("prompt_format") or ""),
        scene_id=str(event.get("scene_id") or ""),
    )


def build_benchmark_progress_state(
    *,
    gamedata: dict[str, Any],
    model_names: list[str],
    preset_names: list[str],
    campaign_ids: list[str],
    character_ids: list[str],
    prompt_formats: list[str],
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "total": 0,
        "completed": 0,
        "remaining": 0,
        "passed": 0,
        "failed": 0,
        "parse_failures": 0,
        "current": None,
        "models": [],
        "index": {},
    }

    for model_name in model_names:
        model_node = {"name": model_name, "presets": []}
        state["models"].append(model_node)
        for preset_name in preset_names:
            preset_node = {"name": preset_name, "campaigns": []}
            model_node["presets"].append(preset_node)
            for campaign_id in campaign_ids:
                campaign = gamedata["campaigns_by_id"].get(campaign_id, {})
                campaign_node = {
                    "id": campaign_id,
                    "name": campaign.get("name", campaign_id),
                    "characters": [],
                }
                preset_node["campaigns"].append(campaign_node)
                scene_refs = campaign.get("scene_ids") or campaign.get("scenes", [])
                scene_ids = [
                    scene_ref["scene_id"] if isinstance(scene_ref, dict) else scene_ref
                    for scene_ref in scene_refs
                ]
                for character_id in character_ids:
                    character = gamedata["characters_by_id"].get(character_id, {})
                    character_node = {
                        "id": character_id,
                        "name": character.get("name", character_id),
                        "prompt_formats": [],
                    }
                    campaign_node["characters"].append(character_node)
                    for prompt_format in prompt_formats:
                        prompt_node = {"name": prompt_format, "scenes": []}
                        character_node["prompt_formats"].append(prompt_node)
                        for scene_index, scene_id in enumerate(scene_ids):
                            scene = gamedata["scenes_by_id"].get(scene_id, {})
                            scene_node = {
                                "scene_id": scene_id,
                                "scene_index": scene_index,
                                "scene_title": scene.get("title", scene_id),
                                "status": "NOT_RUN",
                                "reason": "",
                                "selected_tool_id": "",
                            }
                            prompt_node["scenes"].append(scene_node)
                            key = (model_name, preset_name, campaign_id, character_id, prompt_format, scene_id)
                            state["index"][key] = scene_node
                            state["total"] += 1

    state["remaining"] = state["total"]
    return state


def update_benchmark_progress_from_records(
    state: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    for record in records:
        update_benchmark_progress_state(
            state,
            {
                "event": "scene_finish",
                "model": record.get("benchmark_model") or record.get("model", ""),
                "preset": record.get("preset", ""),
                "campaign_id": record.get("campaign_id", ""),
                "character_id": record.get("character_id", ""),
                "prompt_format": record.get("prompt_format", ""),
                "scene_id": record.get("scene_id", ""),
                "scene_index": record.get("scene_index"),
                "status": record.get("status"),
                "reason": record.get("reason", ""),
                "selected_tool_id": record.get("selected_tool_id", ""),
                "parse_failure": record.get("parse_failure"),
            },
        )
    return state


def update_benchmark_progress_state(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    key = _progress_key(event)
    scene_node = state.get("index", {}).get(key)
    if scene_node is None:
        return state

    event_name = event.get("event")
    state["current"] = dict(event)

    if event_name == "scene_start":
        scene_node["status"] = "RUNNING"
        scene_node["reason"] = ""
        scene_node["selected_tool_id"] = ""
        return state

    if event_name != "scene_finish":
        return state

    previous_status = scene_node.get("status", "NOT_RUN")
    status = event.get("status") or "UNKNOWN"
    scene_node["status"] = status
    scene_node["reason"] = event.get("reason", "")
    scene_node["selected_tool_id"] = event.get("selected_tool_id", "")

    if previous_status in {"NOT_RUN", "RUNNING"}:
        state["completed"] += 1
        state["remaining"] = max(state["total"] - state["completed"], 0)
        if status == "PASS":
            state["passed"] += 1
        else:
            state["failed"] += 1
        if event.get("parse_failure") is True or status == "PARSE_ERROR":
            state["parse_failures"] += 1

    return state
