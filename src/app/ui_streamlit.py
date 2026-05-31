import json
import os
from typing import Any

import streamlit as st

from src.engine.loader import DataValidationError, load_gamedata
from src.models.registry import build_handler
from src.prompts.tool_renderers.compact_tools import render_tools_compact
from src.runtime_paths import get_data_dir
from src.runner.benchmark_service import (
    BenchmarkSpec,
    estimate_benchmark_scene_runs,
    run_benchmark,
)
from src.runner.runner_utils import (
    build_scene_prompt_context,
    execute_scene_run,
    execute_scene_tool_call,
    execute_learning_campaign,
    execute_learning_scene,
    get_campaign_scene_ids,
    get_visible_tools,
    load_preset,
    resolve_campaign,
    resolve_character,
    resolve_scene,
    summarize_scene_results,
)
from src.runner.streamlit_utils import (
    build_campaign_progress_rows,
    build_run_log_payload,
    build_scene_result_rows,
    discover_catalog_models,
    discover_streamlit_presets,
    load_streamlit_run_settings,
    normalize_single_scene_run,
    save_streamlit_run_log,
)


st.set_page_config(page_title="AgentQuest Run Viewer", layout="wide")

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
SINGLE_SCENE_KEY = "aq_single_scene_result"
SINGLE_LOG_KEY = "aq_single_scene_log_path"
BENCHMARK_RESULT_KEY = "aq_benchmark_result"


@st.cache_resource(show_spinner=False)
def _get_cached_handler(model_name: str):
    return build_handler(model_name_override=model_name)


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


def _run_campaign_range(
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
        scene_result = _run_campaign_scene(
            gamedata=gamedata,
            handler=handler,
            campaign_id=campaign_id,
            character_id=character_id,
            scene_id=scene_ids[scene_index],
            scene_index=scene_index,
            run_settings=run_settings,
            model_name=model_name,
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
        _record_learning_scene_result(
            learning_scene["scene_result"],
            updated_notes=learning_scene["updated_notes"],
            retries_used_delta=learning_scene["retries_used"],
        )
        st.session_state[CAMPAIGN_INDEX_KEY] = scene_index
        progress.progress(offset / total, text=f"Learning on {scene_ids[scene_index]}")

    progress.empty()


def _render_status_banner(status: str, reason: str) -> None:
    label = status.replace("_", " ")
    if status == "PASS":
        st.success(f"PASS: {reason or 'Scene succeeded'}")
    elif status == "NOT_RUN":
        st.info("NOT RUN")
    elif status == "RUNNING":
        st.warning("RUNNING")
    else:
        st.error(f"{label}: {reason or 'Scene failed'}")


def _render_progress_view(progress_rows: list[dict[str, Any]]) -> None:
    st.subheader("Campaign Progress")
    for row in progress_rows:
        marker = "->" if row["is_current"] else "  "
        st.markdown(
            f"`{marker}` Scene {row['scene_index'] + 1}: "
            f"`{row['status']}`  "
            f"{row['scene_id']}  "
            f"({row['scene_title']})"
        )


def _render_prompt_messages(messages: list[dict[str, str]]) -> None:
    st.markdown("**Prompt Messages**")
    for index, message in enumerate(messages, start=1):
        st.markdown(f"**Message {index} ({message.get('role', '?')})**")
        st.code(message.get("content", ""), language="text")


def _resolve_tool_for_display(gamedata: dict, tool: dict[str, Any]) -> dict[str, Any]:
    llm_tools_by_id = gamedata.get("llm_tools_by_id", {})
    return llm_tools_by_id.get(tool.get("tool_id"), tool)


def _build_human_tool_call(
    *,
    form_key: str,
    tool: dict[str, Any],
) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    args_schema = tool.get("args", {}) or {}
    properties = args_schema.get("properties", {}) or {}
    required = set(args_schema.get("required", []) or [])

    for arg_name, schema in properties.items():
        field_key = f"{form_key}_{tool.get('tool_id')}_{arg_name}"
        arg_type = schema.get("type", "string")
        value: Any

        if isinstance(schema.get("enum"), list) and schema["enum"]:
            value = st.selectbox(
                f"{arg_name}{' *' if arg_name in required else ''}",
                schema["enum"],
                key=field_key,
            )
        elif arg_type == "boolean":
            value = st.checkbox(arg_name, key=field_key)
        elif arg_type == "integer":
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            default_value = minimum if isinstance(minimum, int) else 0
            input_label = f"{arg_name}{' *' if arg_name in required else ''}"
            if isinstance(minimum, int) and isinstance(maximum, int):
                value = st.number_input(input_label, min_value=minimum, max_value=maximum, value=default_value, step=1, key=field_key)
            elif isinstance(minimum, int):
                value = st.number_input(input_label, min_value=minimum, value=default_value, step=1, key=field_key)
            elif isinstance(maximum, int):
                value = st.number_input(input_label, max_value=maximum, value=min(default_value, maximum), step=1, key=field_key)
            else:
                value = st.number_input(input_label, value=default_value, step=1, key=field_key)
        elif arg_type == "number":
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            default_value = float(minimum) if isinstance(minimum, (int, float)) else 0.0
            input_label = f"{arg_name}{' *' if arg_name in required else ''}"
            if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
                value = st.number_input(input_label, min_value=float(minimum), max_value=float(maximum), value=default_value, key=field_key)
            elif isinstance(minimum, (int, float)):
                value = st.number_input(input_label, min_value=float(minimum), value=default_value, key=field_key)
            elif isinstance(maximum, (int, float)):
                value = st.number_input(input_label, max_value=float(maximum), value=min(default_value, float(maximum)), key=field_key)
            else:
                value = st.number_input(input_label, value=default_value, key=field_key)
        elif arg_type in {"object", "array"}:
            raw_json = st.text_area(
                f"{arg_name}{' *' if arg_name in required else ''} (JSON)",
                value="{}" if arg_type == "object" else "[]",
                key=field_key,
            )
            if raw_json.strip():
                value = raw_json
            else:
                value = None
        else:
            value = st.text_input(
                f"{arg_name}{' *' if arg_name in required else ''}",
                key=field_key,
            )

        if arg_type in {"object", "array"}:
            if value is None or (isinstance(value, str) and not value.strip()):
                if arg_name in required:
                    arguments[arg_name] = value
                continue
            arguments[arg_name] = value
            continue

        if arg_name in required or value not in ("", None):
            arguments[arg_name] = value

    return arguments


def _parse_human_arguments(
    *,
    tool: dict[str, Any],
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    parsed_arguments: dict[str, Any] = {}
    properties = ((tool.get("args", {}) or {}).get("properties", {}) or {})
    for arg_name, value in arguments.items():
        schema = properties.get(arg_name, {})
        arg_type = schema.get("type")
        if arg_type in {"object", "array"} and isinstance(value, str):
            try:
                parsed_arguments[arg_name] = json.loads(value)
            except Exception:
                return {}, f"Argument '{arg_name}' must be valid JSON."
        else:
            parsed_arguments[arg_name] = value
    return parsed_arguments, None


def _render_human_tool_panel(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    scene_context: dict[str, Any],
    submit_label: str,
    form_key: str,
) -> str | None:
    cfg = run_settings["preset_config"]
    visible_tools = scene_context["visible_tools"]
    tool_labels = {
        tool["tool_id"]: f"{tool.get('label') or tool['tool_id']} ({tool['tool_id']})"
        for tool in visible_tools
    }
    selected_tool_key = f"{form_key}_selected_tool"
    selected_tool_id = st.session_state.get(selected_tool_key) or next(iter(tool_labels))

    st.subheader("Choose a Tool")
    tool_cols = st.columns(min(3, len(visible_tools)) or 1)
    for index, visible_tool in enumerate(visible_tools):
        display_tool = _resolve_tool_for_display(gamedata, visible_tool)
        with tool_cols[index % len(tool_cols)]:
            with st.container(border=True):
                st.markdown(f"**{visible_tool.get('label') or visible_tool['tool_id']}**")
                st.caption(visible_tool["tool_id"])
                with st.expander("Tool details", expanded=visible_tool["tool_id"] == selected_tool_id):
                    st.code(render_tools_compact([display_tool], cfg), language="text")

    selected_tool_id = st.selectbox(
        "Selected tool",
        list(tool_labels.keys()),
        format_func=lambda item: tool_labels[item],
        key=selected_tool_key,
    )
    selected_tool = next(tool for tool in visible_tools if tool["tool_id"] == selected_tool_id)
    with st.form(key=f"{form_key}_tool_form"):
        st.caption("Required fields are marked with *.")
        raw_arguments = _build_human_tool_call(form_key=form_key, tool=selected_tool)
        submitted = st.form_submit_button(submit_label)

    if not submitted:
        return None

    parsed_arguments, argument_error = _parse_human_arguments(tool=selected_tool, arguments=raw_arguments)
    if argument_error:
        st.error(argument_error)
        return None

    return json.dumps(
        {
            "tool_id": selected_tool_id,
            "arguments": parsed_arguments,
        },
        ensure_ascii=False,
    )


def _render_scene_detail(
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
    _render_status_banner(status, reason)

    st.markdown("**Submitted Tool Call**")
    st.code((row or {}).get("raw_model_output") or "No run output for this scene yet.", language="json")

    with st.expander("Parsed Tool Call JSON", expanded=bool(row and row.get("parsed_tool_call"))):
        st.json((row or {}).get("parsed_tool_call") or {})

    with st.expander("Validation Stages / Result", expanded=bool(row)):
        st.json((row or {}).get("validation") or {})

    with st.expander("Prompt Messages"):
        _render_prompt_messages((row or {}).get("messages") or [])

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


def _render_campaign_history(history_rows: list[dict[str, Any]]) -> None:
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


def _render_campaign_summary(
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


def _render_campaign_mode(
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

    model_name = ""
    handler = None
    if not is_human_actor:
        model_name = actor_selection
        handler = _get_cached_handler(model_name)
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
                    model_name=model_name,
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
                    model_name=model_name,
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
                    model_name=model_name,
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
                    model_name=model_name,
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
    progress_rows = build_campaign_progress_rows(
        gamedata=gamedata,
        campaign_id=campaign_id,
        scene_results_by_id=st.session_state.get(CAMPAIGN_RESULTS_KEY, {}),
        current_scene_index=current_scene_index,
    )
    _render_progress_view(progress_rows)

    if is_human_actor:
        with st.expander("Prompt Messages", expanded=False):
            _render_prompt_messages(scene_context["messages"])
        human_tool_call = _render_human_tool_panel(
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

    current_scene_result = st.session_state.get(CAMPAIGN_RESULTS_KEY, {}).get(current_scene_id)
    _render_scene_detail(
        gamedata=gamedata,
        scene_id=current_scene_id,
        character_id=character_id,
        scene_result=current_scene_result,
        scene_index=current_scene_index,
    )

    history_rows = build_scene_result_rows(st.session_state.get(CAMPAIGN_HISTORY_KEY, []), gamedata)
    _render_campaign_history(history_rows)
    _render_campaign_summary(
        gamedata=gamedata,
        campaign_id=campaign_id,
        character_id=character_id,
        scene_ids=scene_ids,
    )

    saved_log_path = st.session_state.get(CAMPAIGN_LOG_KEY)
    if saved_log_path:
        st.caption(f"Saved evaluation run: {saved_log_path}")


def _render_single_scene_mode(
    *,
    gamedata: dict,
    run_settings: dict[str, Any],
    actor_selection: str,
    character_id: str,
    scene_id: str,
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
            _render_prompt_messages(scene_context["messages"])
        human_tool_call = _render_human_tool_panel(
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
        handler = _get_cached_handler(model_name)

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

    _render_scene_detail(
        gamedata=gamedata,
        scene_id=scene_id,
        character_id=character_id,
        scene_result=st.session_state.get(SINGLE_SCENE_KEY),
        scene_index=0,
    )
    if st.session_state.get(SINGLE_LOG_KEY):
        st.caption(f"Saved run log: {st.session_state[SINGLE_LOG_KEY]}")


def _render_benchmark_mode(
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
                handler_factory=lambda model_name: _get_cached_handler(model_name),
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


def main() -> None:
    st.title("AgentQuest Run Viewer")
    st.caption("Campaign mode is the primary flow. Single-scene runs remain available.")
    data_dir = get_data_dir()
    try:
        gamedata = load_gamedata(data_dir)
    except DataValidationError as error:
        st.error(f"Data validation error: {error}")
        return
    except Exception as error:
        st.error(f"Unexpected error while loading game data: {error}")
        return

    catalog_models = discover_catalog_models()
    model_options = [item["name"] for item in catalog_models]
    model_labels = {
        item["name"]: f"Model: {item['display_name']}"
        for item in catalog_models
    }

    try:
        run_settings = load_streamlit_run_settings()
    except FileNotFoundError as error:
        st.error(f"Missing configs/run_config.json or model file: {error}")
        return
    except Exception as error:
        st.error(f"Unable to load run settings: {error}")
        return

    preset_options = discover_streamlit_presets()
    characters = gamedata["raw"]["characters"]
    campaigns = gamedata["raw"]["campaigns"]
    scenes = gamedata["raw"]["scenes"]

    if not campaigns:
        st.error(f"No campaigns were found in {os.path.join(data_dir, 'custom', 'agentquest', 'campaigns.json')}.")
        return
    if not scenes:
        st.error(f"No scenes were found in {os.path.join(data_dir, 'custom', 'agentquest', 'scenes.json')}.")
        return
    if not characters:
        st.error(f"No characters were found in {os.path.join(data_dir, 'custom', 'agentquest', 'characters.json')}.")
        return

    current_model_name = run_settings.get("model_name", "")
    actor_options = [HUMAN_ACTOR_VALUE] + model_options
    actor_labels = {
        HUMAN_ACTOR_VALUE: "Human Player",
        **model_labels,
    }
    actor_index = actor_options.index(current_model_name) if current_model_name in actor_options else 0
    preset_index = preset_options.index(run_settings["preset_name"]) if run_settings["preset_name"] in preset_options else 0

    character_options = {f"{item['name']} ({item['character_id']})": item["character_id"] for item in characters}
    campaign_options = {f"{item['name']} ({item['campaign_id']})": item["campaign_id"] for item in campaigns}
    scene_options = {f"{item['title']} ({item['scene_id']})": item["scene_id"] for item in scenes}
    character_labels = list(character_options.keys())
    campaign_labels = list(campaign_options.keys())
    default_character_id = "knight.bram"
    default_campaign_id = "campaign.goblin_den_v1"
    default_character_index = next(
        (
            index
            for index, label in enumerate(character_labels)
            if character_options[label] == default_character_id
        ),
        0,
    )
    default_campaign_index = next(
        (
            index
            for index, label in enumerate(campaign_labels)
            if campaign_options[label] == default_campaign_id
        ),
        0,
    )

    select_cols = st.columns(4)
    with select_cols[0]:
        selected_actor = st.selectbox(
            "Actor",
            actor_options,
            index=actor_index,
            format_func=lambda item: actor_labels[item],
        )
    with select_cols[1]:
        selected_preset = st.selectbox("Preset", preset_options, index=preset_index)
    with select_cols[2]:
        selected_character_label = st.selectbox("Character", character_labels, index=default_character_index)
        selected_character_id = character_options[selected_character_label]
    with select_cols[3]:
        run_mode = st.selectbox("Mode", ["campaign", "scene", "benchmark"], index=0)

    st.caption(
        f"Config model: `{run_settings.get('model_display_name') or current_model_name or 'unknown'}`. "
        f"Selected actor: `{actor_labels[selected_actor]}`. "
        f"Preset: `{selected_preset}`."
    )

    run_settings = dict(run_settings)
    run_settings["preset_name"] = selected_preset
    run_settings["preset_config"] = load_preset(selected_preset)

    try:
        resolve_character(gamedata, selected_character_id)
    except KeyError as error:
        st.error(str(error))
        return

    try:
        if run_mode == "campaign":
            selected_campaign_label = st.selectbox("Campaign", campaign_labels, index=default_campaign_index)
            selected_campaign_id = campaign_options[selected_campaign_label]
            self_learning_enabled = st.checkbox("Self-learning agent", value=False)
            if selected_actor == HUMAN_ACTOR_VALUE and self_learning_enabled:
                st.warning("Self-learning is unavailable in Human Player mode for now.")
                self_learning_enabled = False
            learning_cols = st.columns(2)
            with learning_cols[0]:
                per_scene_retry_limit = st.number_input("Per-scene retry limit", min_value=0, max_value=10, value=3, step=1)
            with learning_cols[1]:
                total_retry_limit = st.number_input("Total retry limit", min_value=0, max_value=100, value=20, step=1)
            initial_notes = ""
            if self_learning_enabled:
                initial_notes = st.text_area(
                    "Initial notes",
                    value="",
                    help="Optional seed notes for this learning run.",
                )
            resolve_campaign(gamedata, selected_campaign_id)
            _render_campaign_mode(
                gamedata=gamedata,
                run_settings=run_settings,
                actor_selection=selected_actor,
                character_id=selected_character_id,
                campaign_id=selected_campaign_id,
                self_learning_enabled=self_learning_enabled,
                per_scene_retry_limit=int(per_scene_retry_limit),
                total_retry_limit=int(total_retry_limit),
                initial_notes=initial_notes,
            )
        elif run_mode == "scene":
            selected_scene_label = st.selectbox("Scene", list(scene_options.keys()), index=0)
            selected_scene_id = scene_options[selected_scene_label]
            resolve_scene(gamedata, selected_scene_id)
            _render_single_scene_mode(
                gamedata=gamedata,
                run_settings=run_settings,
                actor_selection=selected_actor,
                character_id=selected_character_id,
                scene_id=selected_scene_id,
            )
        else:
            _render_benchmark_mode(
                gamedata=gamedata,
                data_dir=data_dir,
                run_settings=run_settings,
                model_options=model_options,
                model_labels=model_labels,
                default_model_name=current_model_name if current_model_name in model_options else selected_actor,
                character_options=character_options,
                campaign_options=campaign_options,
                selected_character_id=selected_character_id,
                selected_preset=selected_preset,
            )
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Run failed: {error}")


if __name__ == "__main__":
    main()
