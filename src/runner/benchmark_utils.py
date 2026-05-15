from __future__ import annotations

from collections import Counter
from typing import Any


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
) -> dict[str, Any]:
    validation = scene_run.get("validation", {}) or {}
    parsed_tool_call = scene_run.get("parsed_tool_call") or {}
    status = scene_run.get("status")
    parse_failure = status == "PARSE_ERROR" or validation.get("ast_valid") is False

    return {
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
