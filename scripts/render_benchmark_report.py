import argparse
import os
import sys

from src.runner.benchmark_report import load_benchmark_bundle, render_markdown_report
from src.runner.runner_utils import write_json_file


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark-dir",
        action="append",
        required=True,
        help="Benchmark output directory containing manifest.json, summary.json, and records.json. Repeat for multiple models.",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        help="Optional display label for a benchmark directory. If provided, the number of labels must match the number of benchmark dirs.",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="AgentQuest Portfolio Benchmark Report",
        help="Markdown report title.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional markdown output path. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--summary-json",
        type=str,
        default="",
        help="Optional path to save the combined bundle metadata as JSON.",
    )
    return parser.parse_args()


def _resolve_labels(benchmark_dirs: list[str], labels: list[str]) -> list[str]:
    if labels and len(labels) != len(benchmark_dirs):
        raise ValueError("If --label is provided, pass one label per --benchmark-dir.")
    if labels:
        return labels
    return [""] * len(benchmark_dirs)


def main() -> int:
    args = _parse_args()
    try:
        labels = _resolve_labels(args.benchmark_dir, args.label)
        bundles = [
            load_benchmark_bundle(benchmark_dir, label=label)
            for benchmark_dir, label in zip(args.benchmark_dir, labels)
        ]
        markdown = render_markdown_report(bundles, title=args.title)

        if args.output:
            output_path = os.path.abspath(args.output)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as file_obj:
                file_obj.write(markdown)
            print(f"Saved markdown report to: {output_path}")
        else:
            print(markdown)

        if args.summary_json:
            summary_path = os.path.abspath(args.summary_json)
            os.makedirs(os.path.dirname(summary_path), exist_ok=True)
            write_json_file(
                summary_path,
                {
                    "title": args.title,
                    "bundles": [
                        {
                            "benchmark_dir": bundle["benchmark_dir"],
                            "model_label": bundle["model_label"],
                            "manifest": bundle["manifest"],
                            "summary": bundle["summary"],
                        }
                        for bundle in bundles
                    ],
                },
            )
            print(f"Saved report metadata to: {summary_path}")

        return 0
    except Exception as error:
        print("Unexpected error:")
        print(error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
