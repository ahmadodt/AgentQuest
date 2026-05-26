from typing import Any

import streamlit as st

from src.runtime_paths import get_data_dir
from src.runner.runner_utils import (
    build_scene_prompt_context,
    execute_scene_run,
    execute_scene_tool_call,
    get_visible_tools,
    resolve_scene,
    summarize_scene_results,
)
from src.runner.streamlit_utils import (
    build_run_log_payload,
    build_scene_result_rows,
    normalize_single_scene_run,
    save_streamlit_run_log,
)

from src.app.ui_chrome import format_status_label, render_info_panel, status_css_class
from src.app.ui_human import render_human_tool_panel


SINGLE_SCENE_KEY = "aq_single_scene_result"
SINGLE_LOG_KEY = "aq_single_scene_log_path"


def render_status_banner(status: str, reason: str) -> None:
    label = status.replace("_", " ")
    if status == "PASS":
        st.success(f"PASS: {reason or 'Scene succeeded'}")
    elif status == "NOT_RUN":
        st.info("NOT RUN")
    elif status == "RUNNING":
        st.warning("RUNNING")
    else:
        st.error(f"{label}: {reason or 'Scene failed'}")


def render_progress_view(progress_rows: list[dict[str, Any]]) -> None:
    st.markdown("### Campaign Progress")
    st.markdown("<div class='aq-progress-grid'>", unsafe_allow_html=True)
    for row in progress_rows:
        marker = "Current Scene" if row["is_current"] else "Queued"
        status_class = status_css_class(row["status"])
        st.markdown(
            (
                f"<section class='aq-scene-card{' current' if row['is_current'] else ''}'>"
                f"<div class='aq-scene-title'>Scene {row['scene_index'] + 1}: {row['scene_title']}</div>"
                f"<div class='aq-scene-meta'>{row['scene_id']} | {marker}</div>"
                f"<div class='aq-status-pill {status_class}'>{format_status_label(row['status'])}</div>"
                "</section>"
            ),
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_prompt_messages(messages: list[dict[str, str]]) -> None:
    st.markdown("### Prompt Messages")
    for index, message in enumerate(messages, start=1):
        role = message.get("role", "?").upper()
        with st.container(border=True):
            st.caption(f"Message {index} | {role}")
            st.code(message.get("content", ""), language="text")


def render_scene_detail(
    *,
    gamedata: dict,
    scene_id: str,
    character_id: str,
    scene_result: dict[str, Any] | None,
    scene_index: int,
) -> None:
    scene = resolve_scene(gamedata, scene_id)
    character, _, visible_tools = get_visible_tools(gamedata, character_id)
    monster = gamedata["monsters_by_id"].get(scene["monster_id"], {})
    rows = build_scene_result_rows([scene_result], gamedata) if scene_result else []
    row = rows[0] if rows else None

    left_col, right_col = st.columns(2)
    with left_col:
        render_info_panel(
            f"Scene {scene_index + 1}: {scene.get('title', scene_id)}",
            [
                ("Scene ID", scene_id),
                ("Location", scene.get("location", "Unknown")),
                ("Monster", monster.get("name", scene["monster_id"])),
            ],
        )

    with right_col:
        render_info_panel(
            character.get("name", character_id),
            [
                ("Character ID", character_id),
                ("Class", character.get("class", "Unknown")),
                ("Inventory", ", ".join(character.get("inventory", [])) or "None"),
                ("Traits", ", ".join(character.get("traits", [])) or "None"),
            ],
        )

    status = row["status"] if row else "NOT_RUN"
    reason = row["reason"] if row else ""
    render_status_banner(status, reason)
    overview_tab, tool_tab, validation_tab, prompt_tab, attempts_tab = st.tabs(
        ["Briefing", "Tool Call", "Validation", "Prompt", "Attempts"]
    )
    with overview_tab:
        st.markdown("### Scene Context")
        st.write(scene.get("narrative", ""))
        if scene.get("constraints"):
            st.caption(f"Constraints: {scene['constraints']}")
        if monster:
            st.markdown("### Monster Notes")
            st.write(monster.get("description", ""))
            st.json(monster.get("interactions", {}))
        with st.expander("Visible Tools", expanded=False):
            for tool in visible_tools:
                with st.container(border=True):
                    st.markdown(f"**{tool['tool_id']}**")
                    st.write(tool.get("description", ""))
                    st.json(tool.get("args", {}))
    with tool_tab:
        st.markdown("### Submitted Tool Call")
        st.code((row or {}).get("raw_model_output") or "No run output for this scene yet.", language="json")
        st.markdown("### Parsed Tool Call")
        st.json((row or {}).get("parsed_tool_call") or {})
    with validation_tab:
        st.markdown("### Validation Stages / Result")
        st.json((row or {}).get("validation") or {})
    with prompt_tab:
        render_prompt_messages((row or {}).get("messages") or [])
    with attempts_tab:
        if row and row.get("attempts"):
            for attempt in row["attempts"]:
                with st.container(border=True):
                    st.markdown(
                        f"**Attempt {attempt.get('attempt_index', '?')}** "
                        f"| `{attempt.get('status', 'UNKNOWN')}`"
                    )
                    st.code(attempt.get("raw_model_output") or "", language="json")
                    if attempt.get("reason"):
                        st.caption(attempt["reason"])
                    if attempt.get("note_update"):
                        st.markdown("**Updated Notes**")
                        st.code(attempt["note_update"].get("updated_notes", ""), language="text")
        else:
            st.caption("No learning attempts recorded for this scene.")


def render_human_scene_briefing(
    *,
    gamedata: dict,
    scene_id: str,
    character_id: str,
    scene_result: dict[str, Any] | None,
    scene_index: int,
) -> None:
    st.markdown("### Briefing")
    st.caption("Review the encounter first. The tool choice comes after the scenario context.")
    render_scene_detail(
        gamedata=gamedata,
        scene_id=scene_id,
        character_id=character_id,
        scene_result=scene_result,
        scene_index=scene_index,
    )


def render_campaign_history(history_rows: list[dict[str, Any]]) -> None:
    st.markdown("### Campaign History")
    if not history_rows:
        st.caption("No scene runs in this UI session yet.")
        return

    for row in history_rows:
        label = (
            f"Scene {row['scene_index'] + 1 if row.get('scene_index') is not None else '?'} | "
            f"{row['scene_id']} | {row.get('actor_type', 'model')} | {row['status']}"
        )
        if row.get("selected_tool_id"):
            label += f" | {row['selected_tool_id']}"
        with st.expander(label):
            if row.get("reason"):
                st.caption(row["reason"])
            st.code(row.get("raw_model_output") or "", language="json")
            st.json(row.get("parsed_tool_call") or {})
            st.json(row.get("validation") or {})


def render_campaign_summary(
    *,
    gamedata: dict,
    campaign_id: str,
    character_id: str,
    scene_ids: list[str],
    scene_results_by_id: dict[str, Any],
) -> None:
    if len(scene_results_by_id) != len(scene_ids):
        return

    ordered_scene_runs = [scene_results_by_id[scene_id] for scene_id in scene_ids]
    summary = summarize_scene_results(
        ordered_scene_runs,
        campaign_id=campaign_id,
        character_id=character_id,
        model=ordered_scene_runs[-1]["model"] if ordered_scene_runs else "",
        total_scenes=len(scene_ids),
    )

    st.markdown("### Campaign Completed")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Scenes", summary["total_scenes"])
    metric_cols[1].metric("Passed", summary["passed_scenes"])
    metric_cols[2].metric("Failed", summary["failed_scenes"])
    metric_cols[3].metric("Success Rate", f"{summary['success_rate']:.1f}%")

    before_col, after_col = st.columns(2)
    with before_col:
        st.markdown("**Before Running**")
        for index, scene_id in enumerate(scene_ids, start=1):
            st.markdown(f"Scene {index}: `NOT_RUN` {scene_id}")
    with after_col:
        st.markdown("**After Running**")
        for index, scene_result in enumerate(ordered_scene_runs, start=1):
            st.markdown(f"Scene {index}: `{scene_result['status']}` {scene_result['scene_id']}")


def render_single_scene_mode(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    actor_selection: str,
    character_id: str,
    scene_id: str,
    human_actor_value: str,
    get_cached_handler,
    model_path_from_filename,
) -> None:
    is_human_actor = actor_selection == human_actor_value
    scene_context = build_scene_prompt_context(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=scene_id,
        prompt_format=run_settings["prompt_format"],
        cfg=run_settings["preset_config"],
    )

    if is_human_actor:
        st.markdown("### Human Trial")
        render_human_scene_briefing(
            gamedata=gamedata,
            scene_id=scene_id,
            character_id=character_id,
            scene_result=st.session_state.get(SINGLE_SCENE_KEY),
            scene_index=0,
        )
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
        model_path = model_path_from_filename(actor_selection)
        handler = get_cached_handler(model_path)

        if st.button("Run scene", type="primary"):
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
                    model_path_override=model_path,
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
