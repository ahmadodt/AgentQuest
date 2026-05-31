import os

import streamlit as st

from src.app.streamlit_ui.constants import HUMAN_ACTOR_VALUE
from src.app.streamlit_ui.modes.benchmark import render_benchmark_mode
from src.app.streamlit_ui.modes.campaign import render_campaign_mode
from src.app.streamlit_ui.modes.scene import render_single_scene_mode
from src.engine.loader import DataValidationError, load_gamedata
from src.models.registry import build_handler
from src.runtime_paths import get_data_dir
from src.runner.runner_utils import load_preset, resolve_campaign, resolve_character, resolve_scene
from src.runner.streamlit_utils import (
    discover_catalog_models,
    discover_streamlit_presets,
    load_streamlit_run_settings,
)


st.set_page_config(page_title="AgentQuest Run Viewer", layout="wide")


def _close_handler(handler) -> None:
    close_handler = getattr(handler, "close", None)
    if callable(close_handler):
        close_handler()


def get_session_handler(model_name: str):
    active_model_name = st.session_state.get("active_handler_model_name")
    active_handler = st.session_state.get("active_handler")

    if active_model_name == model_name and active_handler is not None:
        return active_handler

    if active_handler is not None:
        _close_handler(active_handler)

    handler = build_handler(model_name_override=model_name)
    st.session_state["active_handler_model_name"] = model_name
    st.session_state["active_handler"] = handler
    return handler


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
            render_campaign_mode(
                gamedata=gamedata,
                run_settings=run_settings,
                actor_selection=selected_actor,
                character_id=selected_character_id,
                campaign_id=selected_campaign_id,
                self_learning_enabled=self_learning_enabled,
                per_scene_retry_limit=int(per_scene_retry_limit),
                total_retry_limit=int(total_retry_limit),
                initial_notes=initial_notes,
                handler_factory=get_session_handler,
            )
        elif run_mode == "scene":
            selected_scene_label = st.selectbox("Scene", list(scene_options.keys()), index=0)
            selected_scene_id = scene_options[selected_scene_label]
            resolve_scene(gamedata, selected_scene_id)
            render_single_scene_mode(
                gamedata=gamedata,
                run_settings=run_settings,
                actor_selection=selected_actor,
                character_id=selected_character_id,
                scene_id=selected_scene_id,
                handler_factory=get_session_handler,
            )
        else:
            render_benchmark_mode(
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
                handler_factory=get_session_handler,
            )
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Run failed: {error}")
