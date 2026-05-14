import os
from typing import Any

import streamlit as st

from src.engine.loader import DataValidationError, load_gamedata
from src.models.registry import build_handler
from src.runner.runner_utils import (
    execute_scene_run,
    get_campaign_scene_ids,
    get_visible_tools,
    load_preset,
    resolve_campaign,
    resolve_character,
    resolve_scene,
    summarize_scene_results,
)
from src.runner.streamlit_utils import (
    DEFAULT_LOCAL_MODELS_DIR,
    build_campaign_progress_rows,
    build_run_log_payload,
    build_scene_result_rows,
    discover_local_models,
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
SINGLE_SCENE_KEY = "aq_single_scene_result"
SINGLE_LOG_KEY = "aq_single_scene_log_path"


@st.cache_resource(show_spinner=False)
def _get_cached_handler(model_path: str):
    return build_handler(model_path_override=model_path)


def _model_path_from_filename(model_filename: str) -> str:
    model_path = os.path.abspath(os.path.join(DEFAULT_LOCAL_MODELS_DIR, model_filename))
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Selected GGUF model does not exist: {model_path}")
    return model_path


def _campaign_signature(
    *,
    campaign_id: str,
    character_id: str,
    model_filename: str,
    preset_name: str,
    prompt_format: str,
) -> tuple[str, str, str, str, str]:
    return (campaign_id, character_id, model_filename, preset_name, prompt_format)


def _ensure_campaign_state(signature: tuple[str, str, str, str, str]) -> None:
    if st.session_state.get(CAMPAIGN_SIGNATURE_KEY) == signature:
        return

    st.session_state[CAMPAIGN_SIGNATURE_KEY] = signature
    st.session_state[CAMPAIGN_RESULTS_KEY] = {}
    st.session_state[CAMPAIGN_HISTORY_KEY] = []
    st.session_state[CAMPAIGN_INDEX_KEY] = 0
    st.session_state[CAMPAIGN_LOG_KEY] = ""


def _reset_campaign_state(signature: tuple[str, str, str, str, str]) -> None:
    st.session_state[CAMPAIGN_SIGNATURE_KEY] = signature
    st.session_state[CAMPAIGN_RESULTS_KEY] = {}
    st.session_state[CAMPAIGN_HISTORY_KEY] = []
    st.session_state[CAMPAIGN_INDEX_KEY] = 0
    st.session_state[CAMPAIGN_LOG_KEY] = ""


def _record_campaign_scene_result(scene_result: dict[str, Any]) -> None:
    scene_results = dict(st.session_state.get(CAMPAIGN_RESULTS_KEY, {}))
    scene_results[scene_result["scene_id"]] = scene_result
    st.session_state[CAMPAIGN_RESULTS_KEY] = scene_results

    history = list(st.session_state.get(CAMPAIGN_HISTORY_KEY, []))
    history.append(scene_result)
    st.session_state[CAMPAIGN_HISTORY_KEY] = history


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
        data_dir="data",
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

    st.markdown("**Model Tool Call**")
    st.code((row or {}).get("raw_model_output") or "No run output for this scene yet.", language="json")

    with st.expander("Parsed Tool Call JSON", expanded=bool(row and row.get("parsed_tool_call"))):
        st.json((row or {}).get("parsed_tool_call") or {})

    with st.expander("Validation Stages / Result", expanded=bool(row)):
        st.json((row or {}).get("validation") or {})

    with st.expander("Prompt Messages"):
        prompt_messages = (row or {}).get("messages") or []
        for index, message in enumerate(prompt_messages, start=1):
            st.markdown(f"**Message {index} ({message.get('role', '?')})**")
            st.code(message.get("content", ""), language="text")


def _render_campaign_history(history_rows: list[dict[str, Any]]) -> None:
    st.subheader("Campaign History")
    if not history_rows:
        st.caption("No scene runs in this UI session yet.")
        return

    for row in history_rows:
        label = (
            f"Scene {row['scene_index'] + 1 if row.get('scene_index') is not None else '?'} | "
            f"{row['scene_id']} | {row['status']}"
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
    model_filename: str,
    character_id: str,
    campaign_id: str,
) -> None:
    scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
    signature = _campaign_signature(
        campaign_id=campaign_id,
        character_id=character_id,
        model_filename=model_filename,
        preset_name=run_settings["preset_name"],
        prompt_format=run_settings["prompt_format"],
    )
    _ensure_campaign_state(signature)

    model_path = _model_path_from_filename(model_filename)
    handler = _get_cached_handler(model_path)
    current_scene_index = min(st.session_state.get(CAMPAIGN_INDEX_KEY, 0), len(scene_ids) - 1)
    st.session_state[CAMPAIGN_INDEX_KEY] = current_scene_index

    control_cols = st.columns(6)
    run_current = control_cols[0].button("Run current scene")
    prev_scene = control_cols[1].button("Previous scene")
    next_scene = control_cols[2].button("Next scene")
    reset_campaign = control_cols[3].button("Reset campaign")
    run_remaining = control_cols[4].button("Run remaining scenes")
    run_full = control_cols[5].button("Run full campaign")
    save_results = st.button(
        "Save results",
        disabled=not st.session_state.get(CAMPAIGN_RESULTS_KEY),
        help="Save the current campaign evaluation state as a run log.",
    )

    if prev_scene:
        st.session_state[CAMPAIGN_INDEX_KEY] = max(0, current_scene_index - 1)
        st.rerun()
    if next_scene:
        st.session_state[CAMPAIGN_INDEX_KEY] = min(len(scene_ids) - 1, current_scene_index + 1)
        st.rerun()
    if reset_campaign:
        _reset_campaign_state(signature)
        st.rerun()
    if run_full:
        _reset_campaign_state(signature)
        with st.spinner("Running full campaign..."):
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
    progress_rows = build_campaign_progress_rows(
        gamedata=gamedata,
        campaign_id=campaign_id,
        scene_results_by_id=st.session_state.get(CAMPAIGN_RESULTS_KEY, {}),
        current_scene_index=current_scene_index,
    )
    _render_progress_view(progress_rows)

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
    model_filename: str,
    character_id: str,
    scene_id: str,
) -> None:
    model_path = _model_path_from_filename(model_filename)
    handler = _get_cached_handler(model_path)

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
                model_path_override=model_path,
                handler=handler,
            )
            st.session_state[SINGLE_SCENE_KEY] = scene_run
            runlog = build_run_log_payload(
                run_mode="scene",
                data_dir="data",
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


def main() -> None:
    st.title("AgentQuest Run Viewer")
    st.caption("Campaign mode is the primary flow. Single-scene runs remain available.")

    try:
        gamedata = load_gamedata("data")
    except DataValidationError as error:
        st.error(f"Data validation error: {error}")
        return
    except Exception as error:
        st.error(f"Unexpected error while loading game data: {error}")
        return

    model_options = discover_local_models()
    if not model_options:
        st.error("No GGUF models were found under local_models/.")
        return

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
        st.error("No campaigns were found in data/custom/agentquest/campaigns.json.")
        return
    if not scenes:
        st.error("No scenes were found in data/custom/agentquest/scenes.json.")
        return
    if not characters:
        st.error("No characters were found in data/custom/agentquest/characters.json.")
        return

    current_model_name = os.path.basename(run_settings.get("model_path", ""))
    model_index = model_options.index(current_model_name) if current_model_name in model_options else 0
    preset_index = preset_options.index(run_settings["preset_name"]) if run_settings["preset_name"] in preset_options else 0

    character_options = {f"{item['name']} ({item['character_id']})": item["character_id"] for item in characters}
    campaign_options = {f"{item['name']} ({item['campaign_id']})": item["campaign_id"] for item in campaigns}
    scene_options = {f"{item['title']} ({item['scene_id']})": item["scene_id"] for item in scenes}

    select_cols = st.columns(4)
    with select_cols[0]:
        selected_model = st.selectbox("Model", model_options, index=model_index)
    with select_cols[1]:
        selected_preset = st.selectbox("Preset", preset_options, index=preset_index)
    with select_cols[2]:
        selected_character_label = st.selectbox("Character", list(character_options.keys()), index=0)
        selected_character_id = character_options[selected_character_label]
    with select_cols[3]:
        run_mode = st.selectbox("Mode", ["campaign", "scene"], index=0)

    st.caption(
        f"Config model: `{current_model_name or 'unknown'}`. "
        f"Selected model override: `{selected_model}`. "
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
            selected_campaign_label = st.selectbox("Campaign", list(campaign_options.keys()), index=0)
            selected_campaign_id = campaign_options[selected_campaign_label]
            resolve_campaign(gamedata, selected_campaign_id)
            _render_campaign_mode(
                gamedata=gamedata,
                run_settings=run_settings,
                model_filename=selected_model,
                character_id=selected_character_id,
                campaign_id=selected_campaign_id,
            )
        else:
            selected_scene_label = st.selectbox("Scene", list(scene_options.keys()), index=0)
            selected_scene_id = scene_options[selected_scene_label]
            resolve_scene(gamedata, selected_scene_id)
            _render_single_scene_mode(
                gamedata=gamedata,
                run_settings=run_settings,
                model_filename=selected_model,
                character_id=selected_character_id,
                scene_id=selected_scene_id,
            )
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Run failed: {error}")


if __name__ == "__main__":
    main()
