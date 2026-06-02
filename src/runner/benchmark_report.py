import json
import os
from typing import Any

from src.runner.benchmark_utils import (
    build_benchmark_failure_reason_rows,
    build_benchmark_model_preset_rows,
    build_benchmark_model_summary_rows,
)


def load_benchmark_bundle(benchmark_dir: str, label: str = "") -> dict[str, Any]:
    benchmark_root = os.path.abspath(benchmark_dir)
    manifest = _read_json(os.path.join(benchmark_root, "manifest.json"))
    summary = _read_json(os.path.join(benchmark_root, "summary.json"))
    records = _read_json(os.path.join(benchmark_root, "records.json"))
    model_label = label or _default_model_label(manifest)
    return {
        "benchmark_dir": benchmark_root,
        "model_label": model_label,
        "manifest": manifest,
        "summary": summary,
        "records": records,
    }


def summarize_benchmark_bundles(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = _bundle_records_with_labels(bundles)
    rows = []
    for row in build_benchmark_model_preset_rows(records):
        adapted = dict(row)
        adapted["top_reason_codes"] = adapted.pop("top_failure_codes")
        rows.append(adapted)
    return sorted(rows, key=lambda item: (item["model"], item["preset"]))


def summarize_failure_reasons(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_benchmark_failure_reason_rows(_bundle_records_with_labels(bundles))


def build_showcase_model_summary_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_benchmark_model_summary_rows(records)


def build_showcase_model_preset_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_benchmark_model_preset_rows(records)


def build_showcase_failure_reason_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_benchmark_failure_reason_rows(records, include_preset=True)


def build_showcase_full_info_failure_rows(
    records: list[dict[str, Any]],
    *,
    preset: str = "FULL_INFO",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        if record.get("pass") is True or str(record.get("preset") or "") != preset:
            continue
        rows.append(
            {
                "model": _record_model(record),
                "scene_index": record.get("scene_index"),
                "scene_id": record.get("scene_id", ""),
                "character_id": record.get("character_id", ""),
                "selected_tool_id": record.get("selected_tool_id", ""),
                "valid_tools": ", ".join(str(tool_id) for tool_id in record.get("valid_tools") or []),
                "reason_code": record.get("reason_code") or "unknown_reason",
                "reason": record.get("reason", ""),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            item["model"],
            item["scene_index"] if isinstance(item["scene_index"], int) else -1,
            item["character_id"],
            item["reason_code"],
        ),
    )


def render_showcase_markdown(
    bundle: dict[str, Any],
    *,
    title: str = "AgentQuest Benchmark Showcase",
) -> str:
    manifest = bundle["manifest"]
    summary = bundle["summary"]
    records = bundle["records"]
    model_rows = build_showcase_model_summary_rows(records)
    preset_rows = build_showcase_model_preset_rows(records)
    reason_rows = build_showcase_failure_reason_rows(records)
    full_info_failures = build_showcase_full_info_failure_rows(records)

    lines = [
        f"# {title}",
        "",
        "## Run Snapshot",
        "",
        f"- Benchmark directory: `{bundle['benchmark_dir']}`",
        f"- Timestamp: `{manifest.get('timestamp', '')}`",
        f"- Dataset: `{manifest.get('dataset_id') or summary.get('dataset_id', '')}`",
        f"- Campaigns: {', '.join(manifest.get('campaign_ids', []))}",
        f"- Characters: {', '.join(manifest.get('character_ids', []))}",
        f"- Presets: {', '.join(manifest.get('presets', []))}",
        f"- Models: {', '.join(manifest.get('models', []))}",
        "",
        "## Model Leaderboard",
        "",
        "| Model | Success Rate | Passed | Failed | Parse Failures | Avg Latency (s) | Top Failure Codes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in model_rows:
        lines.append(
            "| {model} | {success_rate:.1f}% | {passed_scenes}/{total_scenes} | {failed_scenes} | {parse_failures} | {avg_latency} | {top_failure_codes} |".format(
                avg_latency=_format_seconds(row["avg_latency_seconds"]),
                **row,
            )
        )

    lines.extend(
        [
            "",
            "## Model By Preset",
            "",
            "| Model | Preset | Success Rate | Passed | Failed | Parse Failures | Avg Latency (s) | Top Failure Codes |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in preset_rows:
        lines.append(
            "| {model} | {preset} | {success_rate:.1f}% | {passed_scenes}/{total_scenes} | {failed_scenes} | {parse_failures} | {avg_latency} | {top_failure_codes} |".format(
                avg_latency=_format_seconds(row["avg_latency_seconds"]),
                **row,
            )
        )

    lines.extend(
        [
            "",
            "## Failure Reasons",
            "",
            "| Model | Preset | Reason Code | Count |",
            "| --- | --- | --- | ---: |",
        ]
    )
    if reason_rows:
        for row in reason_rows:
            lines.append(f"| {row['model']} | {row['preset']} | {row['reason_code']} | {row['count']} |")
    else:
        lines.append("| n/a | n/a | n/a | 0 |")

    lines.extend(
        [
            "",
            "## Full Info Failures",
            "",
            "| Model | Scene | Character | Selected Tool | Valid Tools | Reason Code | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if full_info_failures:
        for row in full_info_failures:
            lines.append(
                "| {model} | {scene_id} | {character_id} | {selected_tool_id} | {valid_tools} | {reason_code} | {reason} |".format(
                    **{key: _markdown_cell(value) for key, value in row.items()}
                )
            )
    else:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | No full-info failures. |")

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Add the main result you want readers to notice.",
            "- Separate parse failures from legal-but-ineffective tool choices.",
            "- Use the full-info failures as the first candidates for data or prompt investigation.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_markdown_report(
    bundles: list[dict[str, Any]],
    *,
    title: str = "AgentQuest Portfolio Benchmark Report",
) -> str:
    summary_rows = summarize_benchmark_bundles(bundles)
    failure_rows = summarize_failure_reasons(bundles)
    lines: list[str] = [
        f"# {title}",
        "",
        "## Snapshot",
        "",
        f"- Benchmarks compared: {len(bundles)}",
        f"- Models compared: {', '.join(bundle['model_label'] for bundle in bundles)}",
        "",
        "## Run Inputs",
        "",
        "| Model | Backend | Campaigns | Characters | Presets | Prompt Formats |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for bundle in bundles:
        manifest = bundle["manifest"]
        lines.append(
            "| {model} | {backend} | {campaigns} | {characters} | {presets} | {prompt_formats} |".format(
                model=bundle["model_label"],
                backend=manifest.get("backend", ""),
                campaigns=", ".join(manifest.get("campaign_ids", [])),
                characters=", ".join(manifest.get("character_ids", [])),
                presets=", ".join(manifest.get("presets", [])),
                prompt_formats=", ".join(manifest.get("prompt_formats", [])),
            )
        )

    lines.extend(
        [
            "",
            "## Model And Preset Comparison",
            "",
            "| Model | Preset | Success Rate | Passed | Failed | Parse Failures | Avg Latency (s) | Top Failure Codes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for row in summary_rows:
        avg_latency = "-" if row["avg_latency_seconds"] is None else f"{row['avg_latency_seconds']:.2f}"
        lines.append(
            "| {model} | {preset} | {success_rate:.1f}% | {passed_scenes}/{total_scenes} | {failed_scenes} | {parse_failures} | {avg_latency} | {top_reason_codes} |".format(
                model=row["model"],
                preset=row["preset"],
                success_rate=row["success_rate"],
                passed_scenes=row["passed_scenes"],
                total_scenes=row["total_scenes"],
                failed_scenes=row["failed_scenes"],
                parse_failures=row["parse_failures"],
                avg_latency=avg_latency,
                top_reason_codes=row["top_reason_codes"],
            )
        )

    lines.extend(
        [
            "",
            "## Failure Breakdown",
            "",
            "| Model | Reason Code | Count |",
            "| --- | --- | --- |",
        ]
    )

    if failure_rows:
        for row in failure_rows:
            lines.append(f"| {row['model']} | {row['reason_code']} | {row['count']} |")
    else:
        lines.append("| n/a | n/a | 0 |")

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Replace this section with the strongest takeaways before posting to LinkedIn.",
            "- Call out whether more visible information helped or overloaded the smaller models.",
            "- Separate parse failures from legal-but-bad scene reasoning failures when writing conclusions.",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _record_model(record: dict[str, Any]) -> str:
    return str(record.get("benchmark_model") or record.get("model") or "unknown")


def _format_seconds(value: Any) -> str:
    return "-" if value is None else f"{value:.2f}"


def _markdown_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return text


def _default_model_label(manifest: dict[str, Any]) -> str:
    model_name = str(manifest.get("model") or "").strip()
    if model_name:
        return model_name

    model_names = [str(item).strip() for item in manifest.get("models", []) if str(item).strip()]
    if len(model_names) == 1:
        return model_names[0]
    if len(model_names) > 1:
        return "model_matrix"
    return "unknown-model"


def _bundle_records_with_labels(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for bundle in bundles:
        model_label = bundle["model_label"]
        for record in bundle["records"]:
            labeled_record = dict(record)
            labeled_record["benchmark_model"] = model_label
            records.append(labeled_record)
    return records
