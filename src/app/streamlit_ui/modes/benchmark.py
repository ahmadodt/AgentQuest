from collections.abc import Callable
from typing import Any

import streamlit as st

from src.app.streamlit_ui.constants import (
    BENCHMARK_ERROR_KEY,
    BENCHMARK_RESULT_KEY,
    BENCHMARK_SESSION_KEY,
    DEFAULT_LEARNING_PER_SCENE_RETRY_LIMIT,
    DEFAULT_LEARNING_TOTAL_RETRY_LIMIT,
    DISABLED_LEARNING_RETRY_LIMIT,
)
from src.runner.benchmark_service import (
    BenchmarkRunError,
    BenchmarkSpec,
    estimate_benchmark_scene_runs,
    run_benchmark_batch,
)
from src.runner.benchmark_utils import (
    build_benchmark_difficulty_rows,
    build_benchmark_failure_rows,
    build_benchmark_scene_type_rows,
    build_benchmark_skill_rows,
    build_benchmark_model_preset_rows,
    build_benchmark_model_summary_rows,
    build_benchmark_progress_state,
    update_benchmark_progress_from_records,
    update_benchmark_progress_state,
)
from src.runner.streamlit_utils import discover_streamlit_presets


DEFAULT_BENCHMARK_CAMPAIGN_ID = "campaign.benchmark_core_v1"


def _status_marker(status: str) -> str:
    if status == "PASS":
        return "[x]"
    if status == "RUNNING":
        return "[~]"
    if status == "NOT_RUN":
        return "[ ]"
    return "[!]"


def _scene_counts(scenes: list[dict[str, Any]]) -> str:
    completed = sum(1 for scene in scenes if scene["status"] not in {"NOT_RUN", "RUNNING"})
    passed = sum(1 for scene in scenes if scene["status"] == "PASS")
    failed = completed - passed
    return f"{completed}/{len(scenes)} done, {passed} pass, {failed} fail"


def _format_current_path(event: dict[str, Any] | None) -> str:
    if not event:
        return "Current: waiting to start"
    return (
        "Current: "
        f"{event.get('model', '')} / "
        f"{event.get('preset', '')} / "
        f"{event.get('campaign_id', '')} / "
        f"{event.get('character_id', '')} / "
        f"{event.get('prompt_format', '')} / "
        f"{event.get('scene_id', '')}"
    )


def _benchmark_tree_lines(state: dict[str, Any], model_labels: dict[str, str], *, max_lines: int = 260) -> list[str]:
    lines: list[str] = []
    for model_node in state["models"]:
        model_label = model_labels.get(model_node["name"], model_node["name"])
        lines.append(f"{model_label}")
        for preset_node in model_node["presets"]:
            lines.append(f"  {preset_node['name']}")
            for campaign_node in preset_node["campaigns"]:
                lines.append(f"    {campaign_node['name']} ({campaign_node['id']})")
                for character_node in campaign_node["characters"]:
                    lines.append(f"      {character_node['name']} ({character_node['id']})")
                    for prompt_node in character_node["prompt_formats"]:
                        lines.append(f"        {prompt_node['name']} - {_scene_counts(prompt_node['scenes'])}")
                        for scene_node in prompt_node["scenes"]:
                            label = (
                                f"          {_status_marker(scene_node['status'])} "
                                f"Scene {scene_node['scene_index'] + 1}: "
                                f"{scene_node['scene_title']} ({scene_node['scene_id']}) - "
                                f"{scene_node['status']}"
                            )
                            if scene_node.get("selected_tool_id"):
                                label += f" - {scene_node['selected_tool_id']}"
                            if scene_node.get("reason") and scene_node["status"] != "PASS":
                                label += f" - {scene_node['reason']}"
                            lines.append(label)
                            if len(lines) >= max_lines:
                                lines.append("          ... tree truncated for display")
                                return lines
    return lines


def _render_benchmark_progress(
    state: dict[str, Any],
    *,
    model_labels: dict[str, str],
    container,
) -> None:
    total = state["total"]
    completed = state["completed"]
    remaining = state["remaining"]
    progress_value = (completed / total) if total else 0.0
    with container.container():
        st.progress(
            progress_value,
            text=f"{completed} / {total} done, {remaining} remaining",
        )
        metric_cols = st.columns(4)
        metric_cols[0].metric("Passed", state["passed"])
        metric_cols[1].metric("Failed", state["failed"])
        metric_cols[2].metric("Parse failures", state["parse_failures"])
        metric_cols[3].metric("Remaining", remaining)
        st.caption(_format_current_path(state.get("current")))
        st.code("\n".join(_benchmark_tree_lines(state, model_labels)), language="text")


def _benchmark_signature(
    *,
    selected_campaign_ids: list[str],
    selected_character_ids: list[str],
    selected_presets: list[str],
    selected_prompt_formats: list[str],
    selected_models: list[str],
    self_learning_enabled: bool,
    per_scene_retry_limit: int,
    total_retry_limit: int,
    initial_notes: str,
    output_dir: str,
) -> tuple[Any, ...]:
    return (
        tuple(selected_campaign_ids),
        tuple(selected_character_ids),
        tuple(selected_presets),
        tuple(selected_prompt_formats),
        tuple(selected_models),
        self_learning_enabled,
        per_scene_retry_limit,
        total_retry_limit,
        initial_notes,
        output_dir,
    )


def _session_spec(session: dict[str, Any]) -> BenchmarkSpec:
    return BenchmarkSpec(**session["spec"])


def _result_progress_state(
    *,
    gamedata: dict,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    manifest = result.get("manifest") or {}
    if not manifest:
        return None
    state = build_benchmark_progress_state(
        gamedata=gamedata,
        model_names=list(manifest.get("models") or []),
        preset_names=list(manifest.get("presets") or []),
        campaign_ids=list(manifest.get("campaign_ids") or []),
        character_ids=list(manifest.get("character_ids") or []),
        prompt_formats=list(manifest.get("prompt_formats") or []),
    )
    update_benchmark_progress_from_records(state, list(result.get("records") or []))
    return state


def _run_benchmark_step(
    *,
    gamedata: dict,
    handler_factory: Callable[[str], Any],
    progress_container,
    model_labels: dict[str, str],
) -> None:
    session = st.session_state.get(BENCHMARK_SESSION_KEY)
    if not session or session.get("paused") or session.get("complete"):
        return

    spec = _session_spec(session)
    progress_state = build_benchmark_progress_state(
        gamedata=gamedata,
        model_names=spec.model_names,
        preset_names=spec.preset_names,
        campaign_ids=spec.campaign_ids,
        character_ids=spec.character_ids,
        prompt_formats=spec.prompt_formats,
    )
    existing_result = st.session_state.get(BENCHMARK_RESULT_KEY)
    if existing_result:
        update_benchmark_progress_from_records(progress_state, list(existing_result.get("records") or []))

    def on_progress(event: dict[str, Any]) -> None:
        update_benchmark_progress_state(progress_state, event)
        _render_benchmark_progress(progress_state, model_labels=model_labels, container=progress_container)

    try:
        result = run_benchmark_batch(
            gamedata=gamedata,
            spec=spec,
            handler_factory=handler_factory,
            progress_callback=on_progress,
            max_scene_runs=1,
            resume=bool(session.get("resume", True)),
        )
    except BenchmarkRunError as error:
        st.session_state[BENCHMARK_RESULT_KEY] = error.result
        session["spec"]["output_dir"] = error.result["output_dir"]
        session["resume"] = True
        session["paused"] = True
        session["error"] = str(error)
        st.session_state[BENCHMARK_ERROR_KEY] = str(error)
        st.session_state[BENCHMARK_SESSION_KEY] = session
        return

    st.session_state[BENCHMARK_RESULT_KEY] = result
    st.session_state[BENCHMARK_ERROR_KEY] = ""
    session["spec"]["output_dir"] = result["output_dir"]
    session["resume"] = True
    session["complete"] = bool(result.get("complete"))
    st.session_state[BENCHMARK_SESSION_KEY] = session
    if not session["complete"] and not session.get("paused"):
        st.rerun()


def _format_latency(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}s"
    return "-"


def _render_benchmark_results(result: dict[str, Any]) -> None:
    summary = result["summary"]
    records = list(result.get("records") or [])
    completed = summary.get("completed_scene_runs", summary.get("total_scenes", len(records)))
    expected = summary.get("expected_scene_runs", summary.get("total_scenes", len(records)))
    remaining = summary.get("remaining_scene_runs", max(expected - completed, 0))

    st.subheader("Results")
    metric_cols = st.columns(5)
    metric_cols[0].metric("Completed", f"{completed}/{expected}")
    metric_cols[1].metric("Success rate", f"{summary['success_rate']:.1f}%")
    metric_cols[2].metric("Failed", summary["failed_scenes"])
    metric_cols[3].metric("Parse failures", summary["parse_failures"])
    metric_cols[4].metric("Remaining", remaining)

    st.caption(f"Output: {result['output_dir']}")
    if result.get("latest_dir"):
        st.caption(f"Latest: {result['latest_dir']}")
    st.caption(f"Dataset: {summary['dataset_id']}")

    model_rows = build_benchmark_model_summary_rows(records)
    for row in model_rows:
        row["avg_latency"] = _format_latency(row.pop("avg_latency_seconds"))
    st.markdown("**Model comparison**")
    st.dataframe(model_rows, use_container_width=True, hide_index=True)

    failure_rows = build_benchmark_failure_rows(records)
    reason_rows = [
        {"reason_code": reason_code, "count": count}
        for reason_code, count in sorted(
            (summary.get("failures_by_reason_code") or {}).items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    if reason_rows:
        st.markdown("**Failure reasons**")
        st.dataframe(reason_rows, use_container_width=True, hide_index=True)

    with st.expander("Model and preset comparison", expanded=False):
        preset_rows = build_benchmark_model_preset_rows(records)
        for row in preset_rows:
            row["avg_latency"] = _format_latency(row.pop("avg_latency_seconds"))
        st.dataframe(preset_rows, use_container_width=True, hide_index=True)

    with st.expander("Benchmark tag breakdowns", expanded=False):
        st.markdown("**By scene type**")
        st.dataframe(build_benchmark_scene_type_rows(records), use_container_width=True, hide_index=True)
        st.markdown("**By difficulty**")
        st.dataframe(build_benchmark_difficulty_rows(records), use_container_width=True, hide_index=True)
        st.markdown("**By skill tested**")
        st.dataframe(build_benchmark_skill_rows(records), use_container_width=True, hide_index=True)

    with st.expander(f"Failed scenes ({len(failure_rows)})", expanded=False):
        if failure_rows:
            st.dataframe(failure_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No failed scenes.")

    with st.expander("Raw records", expanded=False):
        st.dataframe(records, use_container_width=True)


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
    default_campaign_ids = (
        [DEFAULT_BENCHMARK_CAMPAIGN_ID]
        if DEFAULT_BENCHMARK_CAMPAIGN_ID in campaign_ids
        else campaign_ids[:1]
    )
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

    retry_inputs_disabled = not self_learning_enabled
    default_per_scene_retry_limit = (
        DEFAULT_LEARNING_PER_SCENE_RETRY_LIMIT
        if self_learning_enabled
        else DISABLED_LEARNING_RETRY_LIMIT
    )
    default_total_retry_limit = (
        DEFAULT_LEARNING_TOTAL_RETRY_LIMIT
        if self_learning_enabled
        else DISABLED_LEARNING_RETRY_LIMIT
    )
    retry_cols = st.columns(2)
    with retry_cols[0]:
        per_scene_retry_limit = st.number_input(
            "Benchmark per-scene retry limit",
            min_value=0,
            max_value=10,
            value=default_per_scene_retry_limit,
            step=1,
            disabled=retry_inputs_disabled,
        )
    with retry_cols[1]:
        total_retry_limit = st.number_input(
            "Benchmark total retry limit",
            min_value=0,
            max_value=100,
            value=default_total_retry_limit,
            step=1,
            disabled=retry_inputs_disabled,
        )
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
    progress_state = build_benchmark_progress_state(
        gamedata=gamedata,
        model_names=selected_models,
        preset_names=selected_presets,
        campaign_ids=selected_campaign_ids,
        character_ids=selected_character_ids,
        prompt_formats=selected_prompt_formats,
    )
    progress_container = st.empty()
    existing_result = st.session_state.get(BENCHMARK_RESULT_KEY)
    existing_progress_state = _result_progress_state(gamedata=gamedata, result=existing_result) if existing_result else None
    if existing_progress_state:
        _render_benchmark_progress(existing_progress_state, model_labels=model_labels, container=progress_container)
    elif run_count:
        _render_benchmark_progress(progress_state, model_labels=model_labels, container=progress_container)

    run_disabled = run_count == 0
    session = st.session_state.get(BENCHMARK_SESSION_KEY) or {}
    current_signature = _benchmark_signature(
        selected_campaign_ids=selected_campaign_ids,
        selected_character_ids=selected_character_ids,
        selected_presets=selected_presets,
        selected_prompt_formats=selected_prompt_formats,
        selected_models=selected_models,
        self_learning_enabled=self_learning_enabled,
        per_scene_retry_limit=int(per_scene_retry_limit),
        total_retry_limit=int(total_retry_limit),
        initial_notes=initial_notes,
        output_dir=output_dir.strip(),
    )
    session_matches_selection = session.get("signature") == current_signature
    active_session = bool(session) and not session.get("complete") and session_matches_selection
    control_cols = st.columns(3)
    run_clicked = control_cols[0].button("Run benchmark", disabled=run_disabled)
    pause_clicked = control_cols[1].button("Pause benchmark", disabled=not active_session or session.get("paused", False))
    continue_clicked = control_cols[2].button("Continue benchmark", disabled=run_disabled or not active_session)

    if pause_clicked:
        session["paused"] = True
        st.session_state[BENCHMARK_SESSION_KEY] = session
        st.rerun()

    if continue_clicked and active_session:
        session["paused"] = False
        session["error"] = ""
        st.session_state[BENCHMARK_ERROR_KEY] = ""
        st.session_state[BENCHMARK_SESSION_KEY] = session
        st.rerun()

    if run_clicked:
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
        st.session_state[BENCHMARK_RESULT_KEY] = None
        st.session_state[BENCHMARK_ERROR_KEY] = ""
        st.session_state[BENCHMARK_SESSION_KEY] = {
            "signature": _benchmark_signature(
                selected_campaign_ids=selected_campaign_ids,
                selected_character_ids=selected_character_ids,
                selected_presets=selected_presets,
                selected_prompt_formats=selected_prompt_formats,
                selected_models=selected_models,
                self_learning_enabled=self_learning_enabled,
                per_scene_retry_limit=int(per_scene_retry_limit),
                total_retry_limit=int(total_retry_limit),
                initial_notes=initial_notes,
                output_dir=output_dir.strip(),
            ),
            "spec": spec.__dict__.copy(),
            "resume": False,
            "paused": False,
            "complete": False,
            "error": "",
        }
        st.rerun()

    session = st.session_state.get(BENCHMARK_SESSION_KEY) or {}
    if session and not session.get("paused") and not session.get("complete") and session.get("signature") == current_signature:
        with st.spinner("Running benchmark..."):
            _run_benchmark_step(
                gamedata=gamedata,
                handler_factory=handler_factory,
                progress_container=progress_container,
                model_labels=model_labels,
            )
    elif session and not session.get("complete") and not session_matches_selection:
        st.caption("Benchmark controls are showing a previous run. Restore its selections or start a new benchmark.")

    benchmark_error = st.session_state.get(BENCHMARK_ERROR_KEY)
    if benchmark_error:
        st.error(benchmark_error)
        failed_item = (st.session_state.get(BENCHMARK_RESULT_KEY) or {}).get("next_item")
        if failed_item:
            st.caption(
                "Next continue attempt will rerun: "
                f"{failed_item.get('model')} / {failed_item.get('preset')} / "
                f"{failed_item.get('campaign_id')} / {failed_item.get('character_id')} / "
                f"{failed_item.get('prompt_format')} / {failed_item.get('scene_id')}"
            )

    result = st.session_state.get(BENCHMARK_RESULT_KEY)
    if not result:
        return

    _render_benchmark_results(result)
