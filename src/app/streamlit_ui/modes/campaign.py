from collections.abc import Callable
from typing import Any

import streamlit as st

from src.app.streamlit_ui.common import (
    render_campaign_history,
    render_campaign_summary,
    render_progress_view,
    render_prompt_messages,
    render_scene_detail,
)
from src.app.streamlit_ui.constants import (
    CAMPAIGN_HISTORY_KEY,
    CAMPAIGN_INDEX_KEY,
    CAMPAIGN_INITIAL_NOTES_KEY,
    CAMPAIGN_LEARNING_KEY,
    CAMPAIGN_LOG_KEY,
    CAMPAIGN_NOTES_KEY,
    CAMPAIGN_RESULTS_KEY,
    CAMPAIGN_SIGNATURE_KEY,
    CAMPAIGN_TOTAL_RETRIES_KEY,
    HUMAN_ACTOR_VALUE,
)
from src.app.streamlit_ui.human_tools import render_human_tool_panel
from src.app.streamlit_ui.state import (
    campaign_signature,
    ensure_campaign_state,
    record_campaign_scene_result,
    record_learning_scene_result,
    reset_campaign_state,
)
from src.runtime_paths import get_data_dir
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


def save_campaign_log(
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


def run_campaign_scene(
    *,
    gamedata: dict,
    handler,
    campaign_id: str,
    character_id: str,
    scene_id: str,
    scene_index: int,
    run_settings: dict[str, Any],
    model_name: str,
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
        model_name_override=model_name,
        handler=handler,
    )


def run_campaign_range(
    *,
    gamedata: dict,
    handler,
    campaign_id: str,
    character_id: str,
    scene_ids: list[str],
    start_index: int,
    run_settings: dict[str, Any],
    model_name: str,
) -> None:
    progress = st.progress(0.0, text="Running campaign scenes...")
    total = len(scene_ids) - start_index
    for offset, scene_index in enumerate(range(start_index, len(scene_ids)), start=1):
        scene_result = run_campaign_scene(
            gamedata=gamedata,
            handler=handler,
            campaign_id=campaign_id,
            character_id=character_id,
            scene_id=scene_ids[scene_index],
            scene_index=scene_index,
            run_settings=run_settings,
            model_name=model_name,
        )
        record_campaign_scene_result(st.session_state, scene_result)
        st.session_state[CAMPAIGN_INDEX_KEY] = scene_index
        progress.progress(offset / total, text=f"Running {scene_ids[scene_index]}")

    progress.empty()


def run_learning_campaign_range(
    *,
    gamedata: dict,
    handler,
    campaign_id: str,
    character_id: str,
    scene_ids: list[str],
    start_index: int,
    run_settings: dict[str, Any],
    model_name: str,
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
            model_name_override=model_name,
            handler=handler,
        )
        record_learning_scene_result(
            st.session_state,
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
    handler_factory: Callable[[str], Any],
) -> None:
    scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
    is_human_actor = actor_selection == HUMAN_ACTOR_VALUE
    signature = campaign_signature(
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
    ensure_campaign_state(st.session_state, signature)
    if st.session_state.get(CAMPAIGN_SIGNATURE_KEY) != signature:
        reset_campaign_state(
            st.session_state,
            signature,
            initial_notes=initial_notes,
            self_learning_enabled=self_learning_enabled,
        )
    if st.session_state.get(CAMPAIGN_INITIAL_NOTES_KEY, "") == "" and initial_notes:
        st.session_state[CAMPAIGN_INITIAL_NOTES_KEY] = initial_notes
        st.session_state[CAMPAIGN_NOTES_KEY] = initial_notes
    st.session_state[CAMPAIGN_LEARNING_KEY] = self_learning_enabled

    model_name = ""
    handler = None
    if not is_human_actor:
        model_name = actor_selection
        handler = handler_factory(model_name)
    current_scene_index = min(st.session_state.get(CAMPAIGN_INDEX_KEY, 0), len(scene_ids) - 1)
    st.session_state[CAMPAIGN_INDEX_KEY] = current_scene_index

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
        st.subheader("Learning Notes")
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
        reset_campaign_state(
            st.session_state,
            signature,
            initial_notes=initial_notes if self_learning_enabled else "",
            self_learning_enabled=self_learning_enabled,
        )
        st.rerun()
    if run_full:
        reset_campaign_state(
            st.session_state,
            signature,
            initial_notes=initial_notes if self_learning_enabled else "",
            self_learning_enabled=self_learning_enabled,
        )
        with st.spinner("Running full campaign..."):
            if self_learning_enabled:
                run_learning_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=0,
                    run_settings=run_settings,
                    model_name=model_name,
                    per_scene_retry_limit=per_scene_retry_limit,
                    total_retry_limit=total_retry_limit,
                )
            else:
                run_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=0,
                    run_settings=run_settings,
                    model_name=model_name,
                )
        st.rerun()
    elif run_remaining:
        with st.spinner("Running remaining campaign scenes..."):
            if self_learning_enabled:
                run_learning_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=st.session_state[CAMPAIGN_INDEX_KEY],
                    run_settings=run_settings,
                    model_name=model_name,
                    per_scene_retry_limit=per_scene_retry_limit,
                    total_retry_limit=total_retry_limit,
                )
            else:
                run_campaign_range(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_ids=scene_ids,
                    start_index=st.session_state[CAMPAIGN_INDEX_KEY],
                    run_settings=run_settings,
                    model_name=model_name,
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
                    model_name_override=model_name,
                    handler=handler,
                )
                record_learning_scene_result(
                    st.session_state,
                    learning_scene["scene_result"],
                    updated_notes=learning_scene["updated_notes"],
                    retries_used_delta=learning_scene["retries_used"],
                )
            else:
                scene_result = run_campaign_scene(
                    gamedata=gamedata,
                    handler=handler,
                    campaign_id=campaign_id,
                    character_id=character_id,
                    scene_id=scene_ids[scene_index],
                    scene_index=scene_index,
                    run_settings=run_settings,
                    model_name=model_name,
                )
                record_campaign_scene_result(st.session_state, scene_result)
        st.rerun()
    elif save_results:
        with st.spinner("Saving campaign evaluation run..."):
            save_campaign_log(
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
    progress_rows = build_campaign_progress_rows(
        gamedata=gamedata,
        campaign_id=campaign_id,
        scene_results_by_id=st.session_state.get(CAMPAIGN_RESULTS_KEY, {}),
        current_scene_index=current_scene_index,
    )
    render_progress_view(progress_rows)

    if is_human_actor:
        with st.expander("Prompt Messages", expanded=False):
            render_prompt_messages(scene_context["messages"])
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
            record_campaign_scene_result(st.session_state, scene_result)
            st.rerun()

    current_scene_result = st.session_state.get(CAMPAIGN_RESULTS_KEY, {}).get(current_scene_id)
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
    )

    saved_log_path = st.session_state.get(CAMPAIGN_LOG_KEY)
    if saved_log_path:
        st.caption(f"Saved evaluation run: {saved_log_path}")
