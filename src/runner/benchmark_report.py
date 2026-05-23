import json
import os
from collections import Counter
from typing import Any


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
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for bundle in bundles:
        model_label = bundle["model_label"]
        for record in bundle["records"]:
            preset = str(record.get("preset") or "unknown")
            key = (model_label, preset)
            if key not in grouped:
                grouped[key] = {
                    "model": model_label,
                    "preset": preset,
                    "total_scenes": 0,
                    "passed_scenes": 0,
                    "parse_failures": 0,
                    "latency_values": [],
                    "reason_codes": Counter(),
                }

            row = grouped[key]
            row["total_scenes"] += 1
            if record.get("pass") is True:
                row["passed_scenes"] += 1
            if record.get("parse_failure") is True:
                row["parse_failures"] += 1
            latency = record.get("latency_seconds")
            if isinstance(latency, (int, float)):
                row["latency_values"].append(float(latency))
            if record.get("pass") is not True:
                reason_code = str(record.get("reason_code") or "unknown_reason")
                row["reason_codes"][reason_code] += 1

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        row = grouped[key]
        total_scenes = row["total_scenes"]
        passed_scenes = row["passed_scenes"]
        failed_scenes = total_scenes - passed_scenes
        avg_latency = None
        if row["latency_values"]:
            avg_latency = sum(row["latency_values"]) / len(row["latency_values"])
        summary_rows.append(
            {
                "model": row["model"],
                "preset": row["preset"],
                "total_scenes": total_scenes,
                "passed_scenes": passed_scenes,
                "failed_scenes": failed_scenes,
                "parse_failures": row["parse_failures"],
                "success_rate": (passed_scenes / total_scenes * 100.0) if total_scenes else 0.0,
                "avg_latency_seconds": avg_latency,
                "top_reason_codes": _format_top_reason_codes(row["reason_codes"]),
            }
        )
    return summary_rows


def summarize_failure_reasons(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        failures = Counter()
        for record in bundle["records"]:
            if record.get("pass") is True:
                continue
            reason_code = str(record.get("reason_code") or "unknown_reason")
            failures[reason_code] += 1
        for reason_code, count in failures.most_common():
            rows.append(
                {
                    "model": bundle["model_label"],
                    "reason_code": reason_code,
                    "count": count,
                }
            )
    return rows


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


def _default_model_label(manifest: dict[str, Any]) -> str:
    model_path = str(manifest.get("model") or "").strip()
    if not model_path:
        return "unknown-model"
    return os.path.splitext(os.path.basename(model_path))[0]


def _format_top_reason_codes(reason_codes: Counter) -> str:
    if not reason_codes:
        return "-"
    parts: list[str] = []
    for reason_code, count in reason_codes.most_common(3):
        parts.append(f"{reason_code} ({count})")
    return ", ".join(parts)
