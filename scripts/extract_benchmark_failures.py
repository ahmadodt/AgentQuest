import json
import os
import sys
from collections import Counter
from typing import Any

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.runner.runner_utils import write_json_file


RECORDS_PATH = (
    r"results\benchmarks\custom_t1_4_chars1_2_m1_4_s1_2_camps1_1_dmg1_0_edaf7450"
    r"\campaign.benchmark_core_v1\model_matrix\20260601_213227\records.json"
)
MODEL_FILTER = "qwen3_4b_q4_k_m"
PRESET_FILTER = "FULL_INFO"


def main() -> int:
    records_path = os.path.abspath(RECORDS_PATH)
    output_dir = os.path.dirname(records_path)
    records = _read_records(records_path)
    failures = extract_failures(
        records,
        model_filter=MODEL_FILTER,
        preset_filter=PRESET_FILTER,
    )
    summary = summarize_failures(failures)

    failures_json_path = os.path.join(output_dir, "failures.json")
    summary_json_path = os.path.join(output_dir, "failure_summary.json")
    failures_md_path = os.path.join(output_dir, "failures.md")

    write_json_file(failures_json_path, failures)
    write_json_file(summary_json_path, summary)
    _write_text_file(failures_md_path, render_failures_markdown(failures, summary))

    print(f"Read records: {len(records)}")
    print(f"Extracted failures: {len(failures)}")
    print(f"Saved failures JSON: {failures_json_path}")
    print(f"Saved summary JSON: {summary_json_path}")
    print(f"Saved markdown report: {failures_md_path}")
    return 0


def extract_failures(
    records: list[dict[str, Any]],
    *,
    model_filter: str = "",
    preset_filter: str = "",
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for record in records:
        if record.get("pass") is True:
            continue
        model = str(record.get("benchmark_model") or record.get("model") or "")
        preset = str(record.get("preset") or "")
        if model_filter and model != model_filter:
            continue
        if preset_filter and preset != preset_filter:
            continue
        failures.append(_failure_detail(record, model=model, preset=preset))
    return failures


def summarize_failures(failures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_failures": len(failures),
        "filters": {
            "model": MODEL_FILTER,
            "preset": PRESET_FILTER,
        },
        "by_model": _counter_dict(failures, "model"),
        "by_preset": _counter_dict(failures, "preset"),
        "by_character": _counter_dict(failures, "character_id"),
        "by_scene": _counter_dict(failures, "scene_id"),
        "by_selected_tool": _counter_dict(failures, "selected_tool_id"),
        "by_reason_code": _counter_dict(failures, "reason_code"),
        "parse_failures": sum(1 for failure in failures if failure.get("parse_failure") is True),
    }


def render_failures_markdown(failures: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Failures",
        "",
        f"- Records path: `{RECORDS_PATH}`",
        f"- Model filter: `{MODEL_FILTER or 'all'}`",
        f"- Preset filter: `{PRESET_FILTER or 'all'}`",
        f"- Total failures: {summary['total_failures']}",
        f"- Parse failures: {summary['parse_failures']}",
        "",
        "## Failure Codes",
        "",
    ]
    reason_counts = summary.get("by_reason_code") or {}
    if reason_counts:
        for reason_code, count in reason_counts.items():
            lines.append(f"- `{reason_code}`: {count}")
    else:
        lines.append("- None")

    current_group: tuple[str, str, str] | None = None
    sorted_failures = sorted(
        failures,
        key=lambda item: (
            item.get("model", ""),
            item.get("preset", ""),
            item.get("reason_code", ""),
            item.get("scene_index", -1),
            item.get("character_id", ""),
        ),
    )
    for failure in sorted_failures:
        group = (
            str(failure.get("model", "")),
            str(failure.get("preset", "")),
            str(failure.get("reason_code", "")),
        )
        if group != current_group:
            current_group = group
            lines.extend(
                [
                    "",
                    f"## {group[0]} / {group[1]} / {group[2]}",
                    "",
                ]
            )
        lines.extend(_failure_markdown_lines(failure))

    return "\n".join(lines) + "\n"


def _failure_detail(record: dict[str, Any], *, model: str, preset: str) -> dict[str, Any]:
    return {
        "model": model,
        "preset": preset,
        "campaign_id": record.get("campaign_id", ""),
        "scene_index": record.get("scene_index"),
        "scene_id": record.get("scene_id", ""),
        "character_id": record.get("character_id", ""),
        "prompt_format": record.get("prompt_format", ""),
        "status": record.get("status", ""),
        "parse_failure": bool(record.get("parse_failure")),
        "reason_code": record.get("reason_code") or "unknown_reason",
        "reason": record.get("reason", ""),
        "selected_tool_id": record.get("selected_tool_id", ""),
        "valid_tools": list(record.get("valid_tools") or []),
        "effective_power": record.get("effective_power"),
        "parsed_arguments": record.get("parsed_arguments"),
        "raw_model_output": record.get("raw_model_output", ""),
    }


def _failure_markdown_lines(failure: dict[str, Any]) -> list[str]:
    valid_tools = failure.get("valid_tools") or []
    parsed_arguments = json.dumps(failure.get("parsed_arguments"), indent=2, sort_keys=True)
    raw_model_output = str(failure.get("raw_model_output") or "")
    return [
        f"### Scene {failure.get('scene_index')}: `{failure.get('scene_id')}`",
        "",
        f"- Character: `{failure.get('character_id')}`",
        f"- Selected tool: `{failure.get('selected_tool_id') or '-'}`",
        f"- Valid tools: `{', '.join(valid_tools) if valid_tools else '-'}`",
        f"- Status: `{failure.get('status')}`",
        f"- Reason: {failure.get('reason')}",
        f"- Effective power: `{failure.get('effective_power')}`",
        "- Parsed arguments:",
        "",
        "```json",
        parsed_arguments,
        "```",
        "",
        "- Raw model output:",
        "",
        "```text",
        raw_model_output,
        "```",
        "",
    ]


def _counter_dict(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter = Counter(str(item.get(key) or "unknown") for item in items)
    return dict(counter.most_common())


def _read_records(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as file_obj:
        raw = json.load(file_obj)
    if not isinstance(raw, list):
        raise ValueError(f"Expected benchmark records list: {path}")
    return [item for item in raw if isinstance(item, dict)]


def _write_text_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_obj:
        file_obj.write(content)


if __name__ == "__main__":
    raise SystemExit(main())
