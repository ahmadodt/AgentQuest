from typing import Any

import streamlit as st

from src.app.streamlit_ui.constants import CAMPAIGN_RESULTS_KEY
from src.runner.runner_utils import get_visible_tools, resolve_scene, summarize_scene_results
from src.runner.streamlit_utils import build_scene_result_rows


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
    st.subheader("Campaign Progress")
    for row in progress_rows:
        marker = "->" if row["is_current"] else "  "
        st.markdown(
            f"`{marker}` Scene {row['scene_index'] + 1}: "
            f"`{row['status']}`  "
            f"{row['scene_id']}  "
            f"({row['scene_title']})"
        )


def render_prompt_messages(messages: list[dict[str, str]]) -> None:
    st.markdown("**Prompt Messages**")
    for index, message in enumerate(messages, start=1):
        st.markdown(f"**Message {index} ({message.get('role', '?')})**")
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
    character, visible_tool_ids, visible_tools = get_visible_tools(gamedata, character_id)
    monster = gamedata["monsters_by_id"].get(scene["monster_id"], {})
    rows = build_scene_result_rows([scene_result], gamedata) if scene_result else []
    row = rows[0] if rows else None

    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(f"### Scene {scene_index + 1}: {scene_id}")
        st.caption(scene.get("title", scene_id))
        st.markdown(f"**Location:** {scene.get('location', '')}")
        st.markdown(f"**Monster:** {monster.get('name', scene['monster_id'])}")
        st.code(scene["monster_id"])
        if monster:
            st.caption(monster.get("description", ""))
            st.json(monster.get("interactions", {}))

    with right_col:
        st.markdown(f"### {character.get('name', character_id)}")
        st.code(character_id)
        st.markdown(f"**Class:** {character.get('class', '')}")
        st.markdown(f"**Inventory:** {', '.join(character.get('inventory', [])) or 'None'}")
        st.markdown(f"**Traits:** {', '.join(character.get('traits', [])) or 'None'}")

    st.markdown("**Scene Context**")
    st.write(scene.get("narrative", ""))
    if scene.get("constraints"):
        st.caption(f"Constraints: {scene['constraints']}")

    with st.expander("Visible Tools"):
        for tool in visible_tools:
            st.markdown(f"**{tool['tool_id']}**")
            st.write(tool.get("description", ""))
            st.json(tool.get("args", {}))

    status = row["status"] if row else "NOT_RUN"
    reason = row["reason"] if row else ""
    render_status_banner(status, reason)

    st.markdown("**Submitted Tool Call**")
    st.code((row or {}).get("raw_model_output") or "No run output for this scene yet.", language="json")

    with st.expander("Parsed Tool Call JSON", expanded=bool(row and row.get("parsed_tool_call"))):
        st.json((row or {}).get("parsed_tool_call") or {})

    with st.expander("Validation Stages / Result", expanded=bool(row)):
        st.json((row or {}).get("validation") or {})

    with st.expander("Prompt Messages"):
        render_prompt_messages((row or {}).get("messages") or [])

    if row and row.get("attempts"):
        with st.expander("Learning Attempts"):
            for attempt in row["attempts"]:
                st.markdown(
                    f"**Attempt {attempt.get('attempt_index', '?')}** "
                    f"- `{attempt.get('status', 'UNKNOWN')}`"
                )
                st.code(attempt.get("raw_model_output") or "", language="json")
                if attempt.get("reason"):
                    st.caption(attempt["reason"])
                if attempt.get("note_update"):
                    st.markdown("**Updated Notes**")
                    st.code(attempt["note_update"].get("updated_notes", ""), language="text")


def render_campaign_history(history_rows: list[dict[str, Any]]) -> None:
    st.subheader("Campaign History")
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
) -> None:
    scene_results_by_id = st.session_state.get(CAMPAIGN_RESULTS_KEY, {})
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

    st.subheader("Campaign Completed")
    st.markdown(
        f"Total scenes: {summary['total_scenes']}  \n"
        f"Passed: {summary['passed_scenes']}  \n"
        f"Failed: {summary['failed_scenes']}  \n"
        f"Success rate: {summary['success_rate']:.1f}%"
    )

    before_col, after_col = st.columns(2)
    with before_col:
        st.markdown("**Before Running**")
        for index, scene_id in enumerate(scene_ids, start=1):
            st.markdown(f"Scene {index}: `NOT_RUN` {scene_id}")
    with after_col:
        st.markdown("**After Running**")
        for index, scene_result in enumerate(ordered_scene_runs, start=1):
            st.markdown(f"Scene {index}: `{scene_result['status']}` {scene_result['scene_id']}")
