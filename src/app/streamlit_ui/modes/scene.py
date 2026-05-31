from collections.abc import Callable
from typing import Any

import streamlit as st

from src.app.streamlit_ui.common import render_prompt_messages, render_scene_detail
from src.app.streamlit_ui.constants import HUMAN_ACTOR_VALUE, SINGLE_LOG_KEY, SINGLE_SCENE_KEY
from src.app.streamlit_ui.human_tools import render_human_tool_panel
from src.runtime_paths import get_data_dir
from src.runner.runner_utils import build_scene_prompt_context, execute_scene_run, execute_scene_tool_call
from src.runner.streamlit_utils import build_run_log_payload, normalize_single_scene_run, save_streamlit_run_log


def render_single_scene_mode(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    actor_selection: str,
    character_id: str,
    scene_id: str,
    handler_factory: Callable[[str], Any],
) -> None:
    is_human_actor = actor_selection == HUMAN_ACTOR_VALUE
    scene_context = build_scene_prompt_context(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=scene_id,
        prompt_format=run_settings["prompt_format"],
        cfg=run_settings["preset_config"],
    )

    if is_human_actor:
        with st.expander("Prompt Messages", expanded=False):
            render_prompt_messages(scene_context["messages"])
        human_tool_call = render_human_tool_panel(
            gamedata=gamedata,
            run_settings=run_settings,
            scene_context=scene_context,
            submit_label="Submit tool choice",
            form_key=f"scene_{scene_id}_{run_settings['preset_name']}",
        )
        if human_tool_call:
            scene_run = execute_scene_tool_call(
                gamedata=gamedata,
                character_id=character_id,
                scene_id=scene_id,
                prompt_format=run_settings["prompt_format"],
                cfg=run_settings["preset_config"],
                raw_tool_call=human_tool_call,
                messages=scene_context["messages"],
                visible_tool_ids=scene_context["visible_tool_ids"],
                visible_tools=scene_context["visible_tools"],
                scene_title=scene_context["scene"].get("title", scene_id),
                actor_type="human",
            )
            st.session_state[SINGLE_SCENE_KEY] = scene_run
            runlog = build_run_log_payload(
                run_mode="scene",
                data_dir=get_data_dir(),
                preset_name=run_settings["preset_name"],
                prompt_format=run_settings["prompt_format"],
                character_id=character_id,
                scene_id=scene_id,
                run_result=normalize_single_scene_run(scene_run),
            )
            st.session_state[SINGLE_LOG_KEY] = save_streamlit_run_log("scene", runlog)
    else:
        model_name = actor_selection
        handler = handler_factory(model_name)

        if st.button("Run scene"):
            with st.spinner("Running scene..."):
                scene_run = execute_scene_run(
                    gamedata=gamedata,
                    character_id=character_id,
                    scene_id=scene_id,
                    prompt_format=run_settings["prompt_format"],
                    cfg=run_settings["preset_config"],
                    model_key="",
                    max_tokens=128,
                    temperature=0.0,
                    model_name_override=model_name,
                    handler=handler,
                )
                st.session_state[SINGLE_SCENE_KEY] = scene_run
                runlog = build_run_log_payload(
                    run_mode="scene",
                    data_dir=get_data_dir(),
                    preset_name=run_settings["preset_name"],
                    prompt_format=run_settings["prompt_format"],
                    character_id=character_id,
                    scene_id=scene_id,
                    run_result=normalize_single_scene_run(scene_run),
                )
                st.session_state[SINGLE_LOG_KEY] = save_streamlit_run_log("scene", runlog)

    render_scene_detail(
        gamedata=gamedata,
        scene_id=scene_id,
        character_id=character_id,
        scene_result=st.session_state.get(SINGLE_SCENE_KEY),
        scene_index=0,
    )
    if st.session_state.get(SINGLE_LOG_KEY):
        st.caption(f"Saved run log: {st.session_state[SINGLE_LOG_KEY]}")
