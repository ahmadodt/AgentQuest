import os
from typing import Any

import streamlit as st

from src.models.registry import build_handler
from src.runtime_paths import get_data_dir, get_local_models_dir
from src.runner.runner_utils import (
    build_scene_prompt_context,
    execute_learning_scene,
    execute_scene_run,
    execute_scene_tool_call,
    get_campaign_scene_ids,
    resolve_campaign,
    summarize_scene_results,
)
from src.runner.streamlit_utils import (
    build_campaign_progress_rows,
    build_run_log_payload,
    build_scene_result_rows,
    save_streamlit_run_log,
)

from src.app.ui_human import render_human_tool_panel
from src.app.ui_scene import (
    render_campaign_history,
    render_campaign_summary,
    render_human_scene_briefing,
    render_progress_view,
    render_scene_detail,
)


CAMPAIGN_SIGNATURE_KEY = "aq_campaign_signature"
CAMPAIGN_RESULTS_KEY = "aq_campaign_results"
CAMPAIGN_HISTORY_KEY = "aq_campaign_history"
CAMPAIGN_INDEX_KEY = "aq_campaign_current_index"
CAMPAIGN_LOG_KEY = "aq_campaign_log_path"
CAMPAIGN_NOTES_KEY = "aq_campaign_notes"
CAMPAIGN_INITIAL_NOTES_KEY = "aq_campaign_initial_notes"
CAMPAIGN_TOTAL_RETRIES_KEY = "aq_campaign_total_retries"
CAMPAIGN_LEARNING_KEY = "aq_campaign_learning_enabled"
HUMAN_ACTOR_VALUE = "__human__"


@st.cache_resource(show_spinner=False)
def get_cached_handler(model_path: str):
    return build_handler(model_path_override=model_path)


def model_path_from_filename(model_filename: str) -> str:
    model_path = os.path.abspath(os.path.join(get_local_models_dir(), model_filename))
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Selected GGUF model does not exist: {model_path}")
    return model_path


def _count_campaign_states(scene_ids: list[str]) -> dict[str, int]:
    results = st.session_state.get(CAMPAIGN_RESULTS_KEY, {})
    counts = {"PASS": 0, "FAIL": 0, "NOT_RUN": 0}
    for scene_id in scene_ids:
        result = results.get(scene_id)
        if not result:
            counts["NOT_RUN"] += 1
            continue
        status = result.get("status", "FAIL")
        if status == "PASS":
            counts["PASS"] += 1
        else:
            counts["FAIL"] += 1
    return counts


def _campaign_signature(
    *,
    campaign_id: str,
    character_id: str,
    actor_selection: str,
    preset_name: str,
    prompt_format: str,
    self_learning_enabled: bool,
    per_scene_retry_limit: int,
    total_retry_limit: int,
    initial_notes: str,
) -> tuple[str, str, str, str, str, bool, int, int, str]:
    return (
        campaign_id,
        character_id,
        actor_selection,
        preset_name,
        prompt_format,
        self_learning_enabled,
        per_scene_retry_limit,
        total_retry_limit,
        initial_notes,
    )


def _ensure_campaign_state(signature: tuple[Any, ...]) -> None:
    if st.session_state.get(CAMPAIGN_SIGNATURE_KEY) == signature:
        return

    st.session_state[CAMPAIGN_SIGNATURE_KEY] = signature
    st.session_state[CAMPAIGN_RESULTS_KEY] = {}
    st.session_state[CAMPAIGN_HISTORY_KEY] = []
    st.session_state[CAMPAIGN_INDEX_KEY] = 0
    st.session_state[CAMPAIGN_LOG_KEY] = ""
    st.session_state[CAMPAIGN_NOTES_KEY] = ""
    st.session_state[CAMPAIGN_INITIAL_NOTES_KEY] = ""
    st.session_state[CAMPAIGN_TOTAL_RETRIES_KEY] = 0
    st.session_state[CAMPAIGN_LEARNING_KEY] = False


def _reset_campaign_state(
    signature: tuple[Any, ...],
    *,
    initial_notes: str = "",
    self_learning_enabled: bool = False,
) -> None:
    st.session_state[CAMPAIGN_SIGNATURE_KEY] = signature
    st.session_state[CAMPAIGN_RESULTS_KEY] = {}
    st.session_state[CAMPAIGN_HISTORY_KEY] = []
    st.session_state[CAMPAIGN_INDEX_KEY] = 0
    st.session_state[CAMPAIGN_LOG_KEY] = ""
    st.session_state[CAMPAIGN_NOTES_KEY] = initial_notes
    st.session_state[CAMPAIGN_INITIAL_NOTES_KEY] = initial_notes
    st.session_state[CAMPAIGN_TOTAL_RETRIES_KEY] = 0
    st.session_state[CAMPAIGN_LEARNING_KEY] = self_learning_enabled


def _record_campaign_scene_result(scene_result: dict[str, Any]) -> None:
    scene_results = dict(st.session_state.get(CAMPAIGN_RESULTS_KEY, {}))
    scene_results[scene_result["scene_id"]] = scene_result
    st.session_state[CAMPAIGN_RESULTS_KEY] = scene_results

    history = list(st.session_state.get(CAMPAIGN_HISTORY_KEY, []))
    history.append(scene_result)
    st.session_state[CAMPAIGN_HISTORY_KEY] = history


def _record_learning_scene_result(
    scene_result: dict[str, Any],
    *,
    updated_notes: str,
    retries_used_delta: int,
) -> None:
    _record_campaign_scene_result(scene_result)
    st.session_state[CAMPAIGN_NOTES_KEY] = updated_notes
    st.session_state[CAMPAIGN_TOTAL_RETRIES_KEY] = st.session_state.get(CAMPAIGN_TOTAL_RETRIES_KEY, 0) + retries_used_delta


def _save_campaign_log(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    character_id: str,
    campaign_id: str,
    scene_ids: list[str],
) -> None:
    scene_results_by_id = st.session_state.get(CAMPAIGN_RESULTS_KEY, {})
    ordered_scene_runs = [
        scene_results_by_id[scene_id]
        for scene_id in scene_ids
        if scene_id in scene_results_by_id
    ]
    scenes_completed = len(ordered_scene_runs)
    campaign_completed = scenes_completed == len(scene_ids)
    run_result = summarize_scene_results(
        ordered_scene_runs,
        campaign_id=campaign_id,
        character_id=character_id,
        model=ordered_scene_runs[-1]["model"] if ordered_scene_runs else "",
        total_scenes=len(scene_ids),
    )
    run_result.update(
        {
            "campaign_name": resolve_campaign(gamedata, campaign_id).get("name", campaign_id),
            "scene_ids": scene_ids,
            "scene_runs": ordered_scene_runs,
            "ordered_scene_results": ordered_scene_runs,
            "scenes_completed": scenes_completed,
            "campaign_completed": campaign_completed,
            "continue_on_failure": True,
            "self_learning_enabled": st.session_state.get(CAMPAIGN_LEARNING_KEY, False),
            "initial_notes": st.session_state.get(CAMPAIGN_INITIAL_NOTES_KEY, ""),
            "final_notes": st.session_state.get(CAMPAIGN_NOTES_KEY, ""),
            "total_retries_used": st.session_state.get(CAMPAIGN_TOTAL_RETRIES_KEY, 0),
            "attempts": [
                attempt
                for scene_run in ordered_scene_runs
                for attempt in scene_run.get("attempts", [])
            ],
            "final_outcome": (
                "success"
                if campaign_completed and run_result["failed_scenes"] == 0
                else "failure"
                if campaign_completed
                else "in_progress"
            ),
            "final_reason": (
                "Campaign completed successfully"
                if campaign_completed and run_result["failed_scenes"] == 0
                else "Campaign completed with one or more failed scenes"
                if campaign_completed
                else "Partial campaign evaluation snapshot saved"
            ),
            "stop_scene_id": None,
        }
    )
    runlog = build_run_log_payload(
        run_mode="campaign",
        data_dir=get_data_dir(),
        preset_name=run_settings["preset_name"],
        prompt_format=run_settings["prompt_format"],
        character_id=character_id,
        campaign_id=campaign_id,
        run_result=run_result,
    )
    st.session_state[CAMPAIGN_LOG_KEY] = save_streamlit_run_log("campaign", runlog)


def _run_campaign_scene(
    *,
    gamedata: dict,
    handler,
    campaign_id: str,
    character_id: str,
    scene_id: str,
    scene_index: int,
    run_settings: dict[str, Any],
    model_path: str,
) -> dict[str, Any]:
    return execute_scene_run(
        gamedata=gamedata,
        campaign_id=campaign_id,
        character_id=character_id,
        scene_id=scene_id,
        scene_index=scene_index,
        prompt_format=run_settings["prompt_format"],
        cfg=run_settings["preset_config"],
        model_key="",
        max_tokens=128,
        temperature=0.0,
        model_path_override=model_path,
        handler=handler,
    )


def _run_campaign_range(
    *,
    gamedata: dict,
    handler,
    campaign_id: str,
    character_id: str,
    scene_ids: list[str],
    start_index: int,
    run_settings: dict[str, Any],
    model_path: str,
) -> None:
    progress = st.progress(0.0, text="Running campaign scenes...")
    total = len(scene_ids) - start_index
    for offset, scene_index in enumerate(range(start_index, len(scene_ids)), start=1):
        scene_result = _run_campaign_scene(
            gamedata=gamedata,
            handler=handler,
            campaign_id=campaign_id,
            character_id=character_id,
            scene_id=scene_ids[scene_index],
            scene_index=scene_index,
            run_settings=run_settings,
            model_path=model_path,
        )
        _record_campaign_scene_result(scene_result)
        st.session_state[CAMPAIGN_INDEX_KEY] = scene_index
        progress.progress(offset / total, text=f"Running {scene_ids[scene_index]}")

    progress.empty()


def _run_learning_campaign_range(
    *,
    gamedata: dict,
    handler,
    campaign_id: str,
    character_id: str,
    scene_ids: list[str],
    start_index: int,
    run_settings: dict[str, Any],
    model_path: str,
    per_scene_retry_limit: int,
    total_retry_limit: int,
) -> None:
    progress = st.progress(0.0, text="Running self-learning campaign scenes...")
    total = len(scene_ids) - start_index
    for offset, scene_index in enumerate(range(start_index, len(scene_ids)), start=1):
        learning_scene = execute_learning_scene(
            gamedata=gamedata,
            campaign_id=campaign_id,
            character_id=character_id,
            scene_id=scene_ids[scene_index],
            scene_index=scene_index,
            prompt_format=run_settings["prompt_format"],
            cfg=run_settings["preset_config"],
            model_key="",
            max_tokens=128,
            temperature=0.0,
            current_notes=st.session_state.get(CAMPAIGN_NOTES_KEY, ""),
            per_scene_retry_limit=per_scene_retry_limit,
            total_retry_limit_remaining=max(
                total_retry_limit - st.session_state.get(CAMPAIGN_TOTAL_RETRIES_KEY, 0),
                0,
            ),
            model_path_override=model_path,
            handler=handler,
        )
        _record_learning_scene_result(
            learning_scene["scene_result"],
            updated_notes=learning_scene["updated_notes"],
            retries_used_delta=learning_scene["retries_used"],
        )
        st.session_state[CAMPAIGN_INDEX_KEY] = scene_index
        progress.progress(offset / total, text=f"Learning on {scene_ids[scene_index]}")

    progress.empty()


def render_campaign_mode(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    actor_selection: str,
    character_id: str,
    campaign_id: str,
    self_learning_enabled: bool,
    per_scene_retry_limit: int,
    total_retry_limit: int,
    initial_notes: str,
) -> None:
    scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
    is_human_actor = actor_selection == HUMAN_ACTOR_VALUE
    signature = _campaign_signature(
        campaign_id=campaign_id,
        character_id=character_id,
        actor_selection=actor_selection,
        preset_name=run_settings["preset_name"],
        prompt_format=run_settings["prompt_format"],
        self_learning_enabled=self_learning_enabled,
        per_scene_retry_limit=per_scene_retry_limit,
        total_retry_limit=total_retry_limit,
        initial_notes=initial_notes,
    )
    _ensure_campaign_state(signature)
    if st.session_state.get(CAMPAIGN_SIGNATURE_KEY) != signature:
        _reset_campaign_state(
            signature,
            initial_notes=initial_notes,
            self_learning_enabled=self_learning_enabled,
        )
    if st.session_state.get(CAMPAIGN_INITIAL_NOTES_KEY, "") == "" and initial_notes:
        st.session_state[CAMPAIGN_INITIAL_NOTES_KEY] = initial_notes
        st.session_state[CAMPAIGN_NOTES_KEY] = initial_notes
    st.session_state[CAMPAIGN_LEARNING_KEY] = self_learning_enabled

    model_path = ""
    handler = None
    if not is_human_actor:
        model_path = model_path_from_filename(actor_selection)
        handler = get_cached_handler(model_path)
    current_scene_index = min(st.session_state.get(CAMPAIGN_INDEX_KEY, 0), len(scene_ids) - 1)
    st.session_state[CAMPAIGN_INDEX_KEY] = current_scene_index

    counts = _count_campaign_states(scene_ids)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Scenes", len(scene_ids))
    metric_cols[1].metric("Passed", counts["PASS"])
    metric_cols[2].metric("Failed", counts["FAIL"])
    metric_cols[3].metric("Unplayed", counts["NOT_RUN"])

    control_cols = st.columns(6)
    run_current = control_cols[0].button("Run current scene", disabled=is_human_actor)
    prev_scene = control_cols[1].button("Previous scene")
    next_scene = control_cols[2].button("Next scene")
    reset_campaign = control_cols[3].button("Reset campaign")
    run_remaining = control_cols[4].button("Run remaining scenes", disabled=is_human_actor)
    run_full = control_cols[5].button("Run full campaign", disabled=is_human_actor)
    save_results = st.button(
        "Save results",
        disabled=not st.session_state.get(CAMPAIGN_RESULTS_KEY),
        help="Save the current campaign evaluation state as a run log.",
    )

    if is_human_actor:
        st.caption("Human mode is step-driven. Submit one tool choice at a time for the current scene.")

    if self_learning_enabled:
        st.markdown("### Learning Notes")
        st.caption(
            f"Total retries used: {st.session_state.get(CAMPAIGN_TOTAL_RETRIES_KEY, 0)} / {total_retry_limit}"
        )
        st.code(st.session_state.get(CAMPAIGN_NOTES_KEY, ""), language="text")

    if prev_scene:
        st.session_state[CAMPAIGN_INDEX_KEY] = max(0, current_scene_index - 1)
        st.rerun()
    if next_scene:
        st.session_state[CAMPAIGN_INDEX_KEY] = min(len(scene_ids) - 1, current_scene_index + 1)
        st.rerun()
    if reset_campaign:
        _reset_campaign_state(
            signature,
            initial_notes=initial_notes if self_learning_enabled else "",
            self_learning_enabled=self_learning_enabled,
        )
        st.rerun()
    if run_full:
        _reset_campaign_state(
            signature,
            initial_notes=initial_notes if self_learning_enabled else "",
            self_learning_enabled=self_learning_enabled,
        )
        with st.spinner("Running full campaign..."):
            if self_learning_enabled:
                _run_learning_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=0,
                    run_settings=run_settings,
                    model_path=model_path,
                    per_scene_retry_limit=per_scene_retry_limit,
                    total_retry_limit=total_retry_limit,
                )
            else:
                _run_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=0,
                    run_settings=run_settings,
                    model_path=model_path,
                )
        st.rerun()
    elif run_remaining:
        with st.spinner("Running remaining campaign scenes..."):
            if self_learning_enabled:
                _run_learning_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=st.session_state[CAMPAIGN_INDEX_KEY],
                    run_settings=run_settings,
                    model_path=model_path,
                    per_scene_retry_limit=per_scene_retry_limit,
                    total_retry_limit=total_retry_limit,
                )
            else:
                _run_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=st.session_state[CAMPAIGN_INDEX_KEY],
                    run_settings=run_settings,
                    model_path=model_path,
                )
        st.rerun()
    elif run_current:
        with st.spinner("Running current scene..."):
            scene_index = st.session_state[CAMPAIGN_INDEX_KEY]
            if self_learning_enabled:
                learning_scene = execute_learning_scene(
                    gamedata=gamedata,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_id=scene_ids[scene_index],
                    scene_index=scene_index,
                    prompt_format=run_settings["prompt_format"],
                    cfg=run_settings["preset_config"],
                    model_key="",
                    max_tokens=128,
                    temperature=0.0,
                    current_notes=st.session_state.get(CAMPAIGN_NOTES_KEY, ""),
                    per_scene_retry_limit=per_scene_retry_limit,
                    total_retry_limit_remaining=max(
                        total_retry_limit - st.session_state.get(CAMPAIGN_TOTAL_RETRIES_KEY, 0),
                        0,
                    ),
                    model_path_override=model_path,
                    handler=handler,
                )
                _record_learning_scene_result(
                    learning_scene["scene_result"],
                    updated_notes=learning_scene["updated_notes"],
                    retries_used_delta=learning_scene["retries_used"],
                )
            else:
                scene_result = _run_campaign_scene(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_id=scene_ids[scene_index],
                    scene_index=scene_index,
                    run_settings=run_settings,
                    model_path=model_path,
                )
                _record_campaign_scene_result(scene_result)
        st.rerun()
    elif save_results:
        with st.spinner("Saving campaign evaluation run..."):
            _save_campaign_log(
                gamedata=gamedata,
                run_settings=run_settings,
                character_id=character_id,
                campaign_id=campaign_id,
                scene_ids=scene_ids,
            )

    current_scene_index = st.session_state.get(CAMPAIGN_INDEX_KEY, 0)
    current_scene_id = scene_ids[current_scene_index]
    scene_context = build_scene_prompt_context(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=current_scene_id,
        prompt_format=run_settings["prompt_format"],
        cfg=run_settings["preset_config"],
        learning_notes=st.session_state.get(CAMPAIGN_NOTES_KEY, "") if self_learning_enabled else "",
    )
    scene_results_by_id = st.session_state.get(CAMPAIGN_RESULTS_KEY, {})
    progress_rows = build_campaign_progress_rows(
        gamedata=gamedata,
        campaign_id=campaign_id,
        scene_results_by_id=scene_results_by_id,
        current_scene_index=current_scene_index,
    )
    progress_col, detail_col = st.columns([1, 1.5])
    with progress_col:
        render_progress_view(progress_rows)

    with detail_col:
        if is_human_actor:
            current_scene_result = scene_results_by_id.get(current_scene_id)
            render_human_scene_briefing(
                gamedata=gamedata,
                scene_id=current_scene_id,
                character_id=character_id,
                scene_result=current_scene_result,
                scene_index=current_scene_index,
            )
            human_tool_call = render_human_tool_panel(
                gamedata=gamedata,
                run_settings=run_settings,
                scene_context=scene_context,
                submit_label="Submit tool choice",
                form_key=f"campaign_{campaign_id}_{current_scene_id}_{run_settings['preset_name']}",
            )
            if human_tool_call:
                scene_result = execute_scene_tool_call(
                    gamedata=gamedata,
                    character_id=character_id,
                    scene_id=current_scene_id,
                    prompt_format=run_settings["prompt_format"],
                    cfg=run_settings["preset_config"],
                    raw_tool_call=human_tool_call,
                    campaign_id=campaign_id,
                    scene_index=current_scene_index,
                    messages=scene_context["messages"],
                    visible_tool_ids=scene_context["visible_tool_ids"],
                    visible_tools=scene_context["visible_tools"],
                    scene_title=scene_context["scene"].get("title", current_scene_id),
                    actor_type="human",
                )
                _record_campaign_scene_result(scene_result)
                st.rerun()
        else:
            current_scene_result = scene_results_by_id.get(current_scene_id)
            render_scene_detail(
                gamedata=gamedata,
                scene_id=current_scene_id,
                character_id=character_id,
                scene_result=current_scene_result,
                scene_index=current_scene_index,
            )

    history_rows = build_scene_result_rows(st.session_state.get(CAMPAIGN_HISTORY_KEY, []), gamedata)
    render_campaign_history(history_rows)
    render_campaign_summary(
        gamedata=gamedata,
        campaign_id=campaign_id,
        character_id=character_id,
        scene_ids=scene_ids,
        scene_results_by_id=scene_results_by_id,
    )

    saved_log_path = st.session_state.get(CAMPAIGN_LOG_KEY)
    if saved_log_path:
        st.caption(f"Saved evaluation run: {saved_log_path}")
