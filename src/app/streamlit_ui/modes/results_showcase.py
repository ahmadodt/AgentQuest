from typing import Any

import streamlit as st

from src.runner.benchmark_history import discover_benchmark_bundles
from src.runner.benchmark_utils import (
    build_benchmark_failure_reason_rows,
    build_benchmark_failure_rows,
    build_benchmark_model_preset_rows,
    build_benchmark_model_summary_rows,
)


def _run_label(bundle: dict[str, Any]) -> str:
    manifest = bundle["manifest"]
    showcase = bundle.get("showcase") or {}
    title = showcase.get("title") or ", ".join(manifest.get("models") or []) or "Benchmark run"
    timestamp = str(manifest.get("timestamp") or "unknown date")[:10]
    return f"{title} | {timestamp} | {bundle['source']}"


def _format_latency(value: Any) -> str:
    return "-" if not isinstance(value, (int, float)) else f"{value:.2f}s"


def _render_run(bundle: dict[str, Any]) -> None:
    manifest = bundle["manifest"]
    summary = bundle["summary"]
    records = bundle["records"]
    showcase = bundle.get("showcase") or {}
    compatibility = bundle["compatibility"]

    st.subheader(showcase.get("title") or "Benchmark run")
    if showcase.get("description"):
        st.write(showcase["description"])

    if compatibility["status"] == "exact":
        st.success("This run uses the exact current dataset fingerprint.")
    elif compatibility["status"] == "mismatch":
        detail = "; ".join(compatibility["differences"]) or "File content changed without a version change."
        st.warning(f"This historical run uses a different dataset. {detail}")
    else:
        st.warning("This legacy run has no dataset fingerprint, so compatibility cannot be verified.")

    completed = summary.get("completed_scene_runs", summary.get("total_scenes", len(records)))
    expected = summary.get("expected_scene_runs", summary.get("total_scenes", len(records)))
    metric_cols = st.columns(5)
    metric_cols[0].metric("Completed", f"{completed}/{expected}")
    metric_cols[1].metric("Success rate", f"{float(summary.get('success_rate') or 0):.1f}%")
    metric_cols[2].metric("Passed", summary.get("passed_scenes", 0))
    metric_cols[3].metric("Failed", summary.get("failed_scenes", 0))
    metric_cols[4].metric("Parse failures", summary.get("parse_failures", 0))

    st.caption(
        f"Source: `{bundle['source']}` | Dataset: `{manifest.get('dataset_id', 'unknown')}` | "
        f"Run time: `{manifest.get('timestamp', 'unknown')}`"
    )
    st.caption(
        f"Campaigns: {', '.join(manifest.get('campaign_ids') or [])} | "
        f"Characters: {len(manifest.get('character_ids') or [])} | "
        f"Presets: {', '.join(manifest.get('presets') or [])}"
    )

    model_rows = build_benchmark_model_summary_rows(records)
    for row in model_rows:
        row["avg_latency"] = _format_latency(row.pop("avg_latency_seconds"))
    st.markdown("**Model leaderboard**")
    st.dataframe(model_rows, use_container_width=True, hide_index=True)

    preset_rows = build_benchmark_model_preset_rows(records)
    for row in preset_rows:
        row["avg_latency"] = _format_latency(row.pop("avg_latency_seconds"))
    with st.expander("Model by prompt preset", expanded=True):
        st.dataframe(preset_rows, use_container_width=True, hide_index=True)

    reason_rows = build_benchmark_failure_reason_rows(records, include_preset=True)
    with st.expander(f"Failure reasons ({sum(row['count'] for row in reason_rows)})", expanded=False):
        if reason_rows:
            st.dataframe(reason_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No failed scenes.")

    failure_rows = build_benchmark_failure_rows(records)
    with st.expander(f"Failed scenes ({len(failure_rows)})", expanded=False):
        if failure_rows:
            st.dataframe(failure_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No failed scenes.")

    with st.expander("Run conditions and raw records", expanded=False):
        st.json(manifest)
        st.dataframe(records, use_container_width=True)


def render_results_showcase(*, data_dir: str) -> None:
    st.subheader("Results Showcase")
    st.caption(
        "Explore committed portfolio benchmarks and local run history without loading an inference model. "
        "Dataset fingerprints keep comparisons honest when game data changes."
    )
    bundles = discover_benchmark_bundles(data_dir=data_dir)
    if not bundles:
        st.info("No benchmark bundles were found in showcase/benchmarks or results/benchmarks.")
        return

    exact_count = sum(bundle["compatibility"]["matches"] for bundle in bundles)
    source_cols = st.columns(3)
    source_cols[0].metric("Available runs", len(bundles))
    source_cols[1].metric("Exact dataset matches", exact_count)
    source_cols[2].metric("Curated showcases", sum(bundle["source"] == "curated" for bundle in bundles))

    include_mismatches = st.checkbox(
        "Include dataset mismatches in the run selector",
        value=True,
        help="Mismatched runs remain clearly labeled and are not treated as directly comparable.",
    )
    visible = bundles if include_mismatches else [bundle for bundle in bundles if bundle["compatibility"]["matches"]]
    if not visible:
        st.info("No exact-match benchmark runs are available for the current dataset.")
        return
    selected_index = st.selectbox(
        "Benchmark run",
        range(len(visible)),
        format_func=lambda index: _run_label(visible[index]),
    )
    _render_run(visible[selected_index])
