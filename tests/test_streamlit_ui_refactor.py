from src.app.streamlit_ui.constants import (
    CAMPAIGN_HISTORY_KEY,
    CAMPAIGN_INDEX_KEY,
    CAMPAIGN_INITIAL_NOTES_KEY,
    CAMPAIGN_LEARNING_KEY,
    CAMPAIGN_NOTES_KEY,
    CAMPAIGN_RESULTS_KEY,
    CAMPAIGN_SIGNATURE_KEY,
    CAMPAIGN_TOTAL_RETRIES_KEY,
)
from src.app.streamlit_ui.human_tools import parse_human_arguments
from src.app.streamlit_ui.state import (
    campaign_signature,
    ensure_campaign_state,
    record_campaign_scene_result,
    record_learning_scene_result,
    reset_campaign_state,
)


def test_campaign_state_resets_when_signature_changes():
    old_signature = ("old",)
    new_signature = ("new",)
    state = {
        CAMPAIGN_SIGNATURE_KEY: old_signature,
        CAMPAIGN_RESULTS_KEY: {"scene.old": {"scene_id": "scene.old"}},
        CAMPAIGN_HISTORY_KEY: [{"scene_id": "scene.old"}],
        CAMPAIGN_INDEX_KEY: 3,
        CAMPAIGN_NOTES_KEY: "old notes",
        CAMPAIGN_TOTAL_RETRIES_KEY: 4,
        CAMPAIGN_LEARNING_KEY: True,
    }

    ensure_campaign_state(state, new_signature)

    assert state[CAMPAIGN_SIGNATURE_KEY] == new_signature
    assert state[CAMPAIGN_RESULTS_KEY] == {}
    assert state[CAMPAIGN_HISTORY_KEY] == []
    assert state[CAMPAIGN_INDEX_KEY] == 0
    assert state[CAMPAIGN_NOTES_KEY] == ""
    assert state[CAMPAIGN_TOTAL_RETRIES_KEY] == 0
    assert state[CAMPAIGN_LEARNING_KEY] is False


def test_campaign_state_records_scene_results_without_mutating_previous_containers():
    original_results = {"scene.one": {"scene_id": "scene.one"}}
    original_history = [{"scene_id": "scene.one"}]
    state = {
        CAMPAIGN_RESULTS_KEY: original_results,
        CAMPAIGN_HISTORY_KEY: original_history,
    }
    scene_result = {"scene_id": "scene.two", "status": "PASS"}

    record_campaign_scene_result(state, scene_result)

    assert state[CAMPAIGN_RESULTS_KEY] == {
        "scene.one": {"scene_id": "scene.one"},
        "scene.two": scene_result,
    }
    assert state[CAMPAIGN_HISTORY_KEY] == [
        {"scene_id": "scene.one"},
        scene_result,
    ]
    assert state[CAMPAIGN_RESULTS_KEY] is not original_results
    assert state[CAMPAIGN_HISTORY_KEY] is not original_history


def test_learning_scene_record_updates_notes_and_retry_count():
    state = {
        CAMPAIGN_RESULTS_KEY: {},
        CAMPAIGN_HISTORY_KEY: [],
        CAMPAIGN_TOTAL_RETRIES_KEY: 2,
    }

    record_learning_scene_result(
        state,
        {"scene_id": "scene.alpha", "status": "PASS"},
        updated_notes="new notes",
        retries_used_delta=3,
    )

    assert state[CAMPAIGN_NOTES_KEY] == "new notes"
    assert state[CAMPAIGN_TOTAL_RETRIES_KEY] == 5
    assert state[CAMPAIGN_RESULTS_KEY]["scene.alpha"]["status"] == "PASS"


def test_reset_campaign_state_keeps_initial_learning_notes():
    signature = campaign_signature(
        campaign_id="campaign.alpha",
        character_id="knight.bram",
        actor_selection="model.alpha",
        preset_name="BATTLE_PLAN",
        prompt_format="json_only",
        self_learning_enabled=True,
        per_scene_retry_limit=3,
        total_retry_limit=20,
        initial_notes="seed notes",
    )
    state = {}

    reset_campaign_state(
        state,
        signature,
        initial_notes="seed notes",
        self_learning_enabled=True,
    )

    assert state[CAMPAIGN_SIGNATURE_KEY] == signature
    assert state[CAMPAIGN_NOTES_KEY] == "seed notes"
    assert state[CAMPAIGN_INITIAL_NOTES_KEY] == "seed notes"
    assert state[CAMPAIGN_LEARNING_KEY] is True


def test_parse_human_arguments_parses_object_and_array_json():
    tool = {
        "args": {
            "properties": {
                "target": {"type": "string"},
                "metadata": {"type": "object"},
                "items": {"type": "array"},
            }
        }
    }

    parsed, error = parse_human_arguments(
        tool=tool,
        arguments={
            "target": "door",
            "metadata": "{\"locked\": true}",
            "items": "[\"key\"]",
        },
    )

    assert error is None
    assert parsed == {
        "target": "door",
        "metadata": {"locked": True},
        "items": ["key"],
    }


def test_parse_human_arguments_reports_invalid_json():
    tool = {"args": {"properties": {"metadata": {"type": "object"}}}}

    parsed, error = parse_human_arguments(
        tool=tool,
        arguments={"metadata": "{not json"},
    )

    assert parsed == {}
    assert error == "Argument 'metadata' must be valid JSON."
