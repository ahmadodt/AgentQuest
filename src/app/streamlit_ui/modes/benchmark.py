from collections.abc import Callable
from typing import Any

import streamlit as st

from src.app.streamlit_ui.constants import BENCHMARK_RESULT_KEY
from src.runner.benchmark_service import BenchmarkSpec, estimate_benchmark_scene_runs, run_benchmark
from src.runner.streamlit_utils import discover_streamlit_presets


def render_benchmark_mode(
    *,
    gamedata: dict,
    data_dir: str,
    run_settings: dict[str, Any],
    model_options: list[str],
    model_labels: dict[str, str],
    default_model_name: str,
    character_options: dict[str, str],
    campaign_options: dict[str, str],
    selected_character_id: str,
    selected_preset: str,
    handler_factory: Callable[[str], Any],
) -> None:
    id_to_character_label = {value: label for label, value in character_options.items()}
    id_to_campaign_label = {value: label for label, value in campaign_options.items()}
    campaign_ids = list(id_to_campaign_label.keys())
    character_ids = list(id_to_character_label.keys())
    default_campaign_ids = [campaign_ids[0]] if campaign_ids else []
    default_character_ids = [selected_character_id] if selected_character_id in character_ids else character_ids[:1]
    default_models = [default_model_name] if default_model_name in model_options else model_options[:1]

    st.subheader("Benchmark")
    st.caption("Benchmark mode runs repeatable sweeps and writes manifest.json, records.json, and summary.json.")
    selection_cols = st.columns(2)
    with selection_cols[0]:
        selected_models = st.multiselect(
            "Models",
            model_options,
            default=default_models,
            format_func=lambda item: model_labels.get(item, item),
        )
        selected_campaign_ids = st.multiselect(
            "Campaigns",
            campaign_ids,
            default=default_campaign_ids,
            format_func=lambda item: id_to_campaign_label.get(item, item),
        )
        selected_character_ids = st.multiselect(
            "Characters",
            character_ids,
            default=default_character_ids,
            format_func=lambda item: id_to_character_label.get(item, item),
        )
    with selection_cols[1]:
        selected_presets = st.multiselect(
            "Presets",
            discover_streamlit_presets(),
            default=[selected_preset],
        )
        selected_prompt_formats = st.multiselect(
            "Prompt formats",
            [run_settings["prompt_format"]],
            default=[run_settings["prompt_format"]],
        )
        self_learning_enabled = st.checkbox("Self-learning benchmark", value=False)

    retry_cols = st.columns(2)
    with retry_cols[0]:
        per_scene_retry_limit = st.number_input("Benchmark per-scene retry limit", min_value=0, max_value=10, value=3, step=1)
    with retry_cols[1]:
        total_retry_limit = st.number_input("Benchmark total retry limit", min_value=0, max_value=100, value=20, step=1)
    initial_notes = ""
    if self_learning_enabled:
        initial_notes = st.text_area("Benchmark initial notes", value="")
    output_dir = st.text_input(
        "Output directory override",
        value="",
        help="Leave empty to write under results/benchmarks/<dataset_id>/...",
    )

    selected_campaign_ids = list(selected_campaign_ids)
    selected_character_ids = list(selected_character_ids)
    selected_presets = list(selected_presets)
    selected_prompt_formats = list(selected_prompt_formats)
    selected_models = list(selected_models)
    run_count = 0
    if selected_campaign_ids and selected_character_ids and selected_presets and selected_prompt_formats and selected_models:
        run_count = estimate_benchmark_scene_runs(
            gamedata=gamedata,
            campaign_ids=selected_campaign_ids,
            character_ids=selected_character_ids,
            preset_names=selected_presets,
            prompt_formats=selected_prompt_formats,
            model_names=selected_models,
        )
    st.caption(f"Estimated scene runs: {run_count}")

    run_disabled = run_count == 0
    if st.button("Run benchmark", disabled=run_disabled):
        spec = BenchmarkSpec(
            data_dir=data_dir,
            campaign_ids=selected_campaign_ids,
            character_ids=selected_character_ids,
            preset_names=selected_presets,
            prompt_formats=selected_prompt_formats,
            model_names=selected_models,
            backend=run_settings["backend"],
            max_tokens=128,
            temperature=0.0,
            self_learning_enabled=self_learning_enabled,
            per_scene_retry_limit=int(per_scene_retry_limit),
            total_retry_limit=int(total_retry_limit),
            initial_notes=initial_notes,
            output_dir=output_dir.strip(),
        )
        with st.spinner("Running benchmark..."):
            st.session_state[BENCHMARK_RESULT_KEY] = run_benchmark(
                gamedata=gamedata,
                spec=spec,
                handler_factory=handler_factory,
            )

    result = st.session_state.get(BENCHMARK_RESULT_KEY)
    if not result:
        return

    summary = result["summary"]
    metric_cols = st.columns(5)
    metric_cols[0].metric("Total scenes", summary["total_scenes"])
    metric_cols[1].metric("Passed", summary["passed_scenes"])
    metric_cols[2].metric("Failed", summary["failed_scenes"])
    metric_cols[3].metric("Parse failures", summary["parse_failures"])
    metric_cols[4].metric("Success rate", f"{summary['success_rate']:.1f}%")
    st.caption(f"Output: {result['output_dir']}")
    if result.get("latest_dir"):
        st.caption(f"Latest: {result['latest_dir']}")
    st.caption(f"Dataset: {summary['dataset_id']}")
    if summary.get("failures_by_reason_code"):
        st.json(summary["failures_by_reason_code"])
    st.dataframe(result["records"], use_container_width=True)
