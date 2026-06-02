# Scripts

These scripts are developer-facing entrypoints. Reusable benchmark logic should live under `src/runner/`; scripts should stay thin wrappers or local analysis helpers.

Run commands from the repository root.

## `run_benchmark.py`

Runs a benchmark from the command line and writes `manifest.json`, `records.json`, and `summary.json` under `results/benchmarks/...` unless `--output-dir` is provided.

```powershell
python scripts/run_benchmark.py --campaign-id campaign.tutorial_v1 --character-id wizard.ember
```

Useful options:

```powershell
python scripts/run_benchmark.py --all-campaigns --all-characters --preset BATTLE_PLAN --model qwen3_4b_q4_k_m
python scripts/run_benchmark.py --campaign-id campaign.tutorial_v1 --character-id wizard.ember --self-learning
python scripts/run_benchmark.py --campaign-id campaign.tutorial_v1 --character-id wizard.ember --output-dir results/benchmarks/manual_run
```

## `render_benchmark_report.py`

Reads one or more benchmark output directories and renders a markdown comparison report. It does not run a benchmark.

```powershell
python scripts/render_benchmark_report.py --benchmark-dir results/benchmarks/custom_id/campaign.tutorial_v1/model/latest
```

With output files:

```powershell
python scripts/render_benchmark_report.py --benchmark-dir results/benchmarks/custom_id/campaign.tutorial_v1/model/latest --label "Model A" --output docs/portfolio_assets/benchmark_report.md --summary-json results/benchmark_report_summary.json
```

For multiple benchmark dirs, repeat `--benchmark-dir`; if labels are used, pass one `--label` per directory.

## `render_benchmark_showcase.py`

Local showcase exporter for a currently hardcoded benchmark directory. It writes markdown and CSV files beside that benchmark's `records.json`.

```powershell
python scripts/render_benchmark_showcase.py
```

Before reuse, update `BENCHMARK_DIR` and `REPORT_TITLE` in the script.

## `extract_benchmark_failures.py`

Local debugging helper for a currently hardcoded `records.json`. It filters failed benchmark records and writes failure-focused JSON and markdown outputs.

```powershell
python scripts/extract_benchmark_failures.py
```

Before reuse, update `RECORDS_PATH`, `MODEL_FILTER`, and `PRESET_FILTER` in the script.

## `generate_validation_report.py`

Runs deterministic scene/character solvability checks using the validation pipeline. This does not call a model and does not run a benchmark.

```powershell
python scripts/generate_validation_report.py --data-dir data
```

