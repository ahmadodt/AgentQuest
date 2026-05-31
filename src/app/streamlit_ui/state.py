from collections.abc import MutableMapping
from typing import Any

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
)


def campaign_signature(
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


def ensure_campaign_state(state: MutableMapping[str, Any], signature: tuple[Any, ...]) -> None:
    if state.get(CAMPAIGN_SIGNATURE_KEY) == signature:
        return

    state[CAMPAIGN_SIGNATURE_KEY] = signature
    state[CAMPAIGN_RESULTS_KEY] = {}
    state[CAMPAIGN_HISTORY_KEY] = []
    state[CAMPAIGN_INDEX_KEY] = 0
    state[CAMPAIGN_LOG_KEY] = ""
    state[CAMPAIGN_NOTES_KEY] = ""
    state[CAMPAIGN_INITIAL_NOTES_KEY] = ""
    state[CAMPAIGN_TOTAL_RETRIES_KEY] = 0
    state[CAMPAIGN_LEARNING_KEY] = False


def reset_campaign_state(
    state: MutableMapping[str, Any],
    signature: tuple[Any, ...],
    *,
    initial_notes: str = "",
    self_learning_enabled: bool = False,
) -> None:
    state[CAMPAIGN_SIGNATURE_KEY] = signature
    state[CAMPAIGN_RESULTS_KEY] = {}
    state[CAMPAIGN_HISTORY_KEY] = []
    state[CAMPAIGN_INDEX_KEY] = 0
    state[CAMPAIGN_LOG_KEY] = ""
    state[CAMPAIGN_NOTES_KEY] = initial_notes
    state[CAMPAIGN_INITIAL_NOTES_KEY] = initial_notes
    state[CAMPAIGN_TOTAL_RETRIES_KEY] = 0
    state[CAMPAIGN_LEARNING_KEY] = self_learning_enabled


def record_campaign_scene_result(
    state: MutableMapping[str, Any],
    scene_result: dict[str, Any],
) -> None:
    scene_results = dict(state.get(CAMPAIGN_RESULTS_KEY, {}))
    scene_results[scene_result["scene_id"]] = scene_result
    state[CAMPAIGN_RESULTS_KEY] = scene_results

    history = list(state.get(CAMPAIGN_HISTORY_KEY, []))
    history.append(scene_result)
    state[CAMPAIGN_HISTORY_KEY] = history


def record_learning_scene_result(
    state: MutableMapping[str, Any],
    scene_result: dict[str, Any],
    *,
    updated_notes: str,
    retries_used_delta: int,
) -> None:
    record_campaign_scene_result(state, scene_result)
    state[CAMPAIGN_NOTES_KEY] = updated_notes
    state[CAMPAIGN_TOTAL_RETRIES_KEY] = state.get(CAMPAIGN_TOTAL_RETRIES_KEY, 0) + retries_used_delta
