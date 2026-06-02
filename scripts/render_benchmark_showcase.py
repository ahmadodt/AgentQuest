import csv
import os
import sys
from typing import Any

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.runner.benchmark_report import (
    build_showcase_failure_reason_rows,
    build_showcase_full_info_failure_rows,
    build_showcase_model_preset_rows,
    build_showcase_model_summary_rows,
    load_benchmark_bundle,
    render_showcase_markdown,
)


BENCHMARK_DIR = (
    r"results\benchmarks\custom_t1_4_chars1_2_m1_4_s1_2_camps1_1_dmg1_0\campaign.benchmark_core_v1\model_matrix\20260602_075144"
)
REPORT_TITLE = "AgentQuest Benchmark Showcase"


def main() -> int:
    benchmark_dir = os.path.abspath(BENCHMARK_DIR)
    bundle = load_benchmark_bundle(benchmark_dir)
    records = list(bundle.get("records") or [])

    outputs = {
        "markdown": os.path.join(benchmark_dir, "showcase_report.md"),
        "model_summary": os.path.join(benchmark_dir, "showcase_model_summary.csv"),
        "model_preset_summary": os.path.join(benchmark_dir, "showcase_model_preset_summary.csv"),
        "failure_reasons": os.path.join(benchmark_dir, "showcase_failure_reasons.csv"),
        "full_info_failures": os.path.join(benchmark_dir, "showcase_full_info_failures.csv"),
    }

    _write_text_file(outputs["markdown"], render_showcase_markdown(bundle, title=REPORT_TITLE))
    _write_csv_file(outputs["model_summary"], build_showcase_model_summary_rows(records))
    _write_csv_file(outputs["model_preset_summary"], build_showcase_model_preset_rows(records))
    _write_csv_file(outputs["failure_reasons"], build_showcase_failure_reason_rows(records))
    _write_csv_file(outputs["full_info_failures"], build_showcase_full_info_failure_rows(records))

    print(f"Read records: {len(records)}")
    for label, path in outputs.items():
        print(f"Saved {label}: {path}")
    return 0


def _write_csv_file(path: str, rows: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = _fieldnames(rows)
    with open(path, "w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["empty"]
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _write_text_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_obj:
        file_obj.write(content)


if __name__ == "__main__":
    raise SystemExit(main())
