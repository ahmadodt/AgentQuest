from src.models.base import GenerationResult
from src.runner.runner_utils import (
    execute_campaign_run,
    execute_learning_campaign,
    execute_learning_scene,
    execute_scene_run,
    execute_scene_tool_call,
)


class StubHandler:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, messages, *, max_tokens=256, temperature=0.0):
        self.calls.append(
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        raw_text = self.responses.pop(0)
        return GenerationResult(raw_text=raw_text, metadata={"stub": True})


def test_execute_scene_run_uses_character_tool_ids_and_returns_scene_record(gamedata, make_tool_call):
    handler = StubHandler([make_tool_call("wizard.arcane_bolt", {"target": "goblin"})])

    scene_run = execute_scene_run(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.tutorial.001_goblin_alley",
        prompt_format="json_only",
        cfg=None,
        model_key="",
        max_tokens=64,
        temperature=0.0,
        handler=handler,
    )

    assert scene_run["scene_id"] == "scene.tutorial.001_goblin_alley"
    assert scene_run["character_id"] == "wizard.ember"
    assert scene_run["visible_tool_ids"] == gamedata["characters_by_id"]["wizard.ember"]["tool_ids"]
    assert scene_run["verdict"]["outcome"] == "success"
    assert scene_run["status"] == "PASS"
    assert scene_run["parsed_tool_call"]["tool_id"] == "wizard.arcane_bolt"
    assert scene_run["metadata"] == {"stub": True}
    assert scene_run["actor_type"] == "model"
    assert "prompt_messages" not in scene_run


def test_execute_scene_tool_call_validates_human_submission_and_returns_scene_record(gamedata, make_tool_call):
    scene_run = execute_scene_tool_call(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.tutorial.001_goblin_alley",
        prompt_format="json_only",
        cfg=None,
        raw_tool_call=make_tool_call("wizard.arcane_bolt", {"target": "goblin"}),
    )

    assert scene_run["scene_id"] == "scene.tutorial.001_goblin_alley"
    assert scene_run["character_id"] == "wizard.ember"
    assert scene_run["status"] == "PASS"
    assert scene_run["actor_type"] == "human"
    assert scene_run["parsed_tool_call"]["tool_id"] == "wizard.arcane_bolt"
    assert len(scene_run["messages"]) == 2


def test_execute_scene_tool_call_reuses_provided_scene_context(gamedata, make_tool_call):
    raw_tool_call = make_tool_call("wizard.arcane_bolt", {"target": "goblin"})
    scene_run = execute_scene_tool_call(
        gamedata=gamedata,
        character_id="wizard.ember",
        scene_id="scene.tutorial.001_goblin_alley",
        prompt_format="json_only",
        cfg=None,
        raw_tool_call=raw_tool_call,
        messages=[{"role": "system", "content": "cached"}],
        visible_tool_ids=gamedata["characters_by_id"]["wizard.ember"]["tool_ids"],
        visible_tools=[gamedata["tools_by_id"][tid] for tid in gamedata["characters_by_id"]["wizard.ember"]["tool_ids"]],
        scene_title="Cached Title",
        actor_type="human",
    )

    assert scene_run["messages"] == [{"role": "system", "content": "cached"}]
    assert scene_run["scene_title"] == "Cached Title"
    assert scene_run["raw_model_output"] == raw_tool_call


def test_execute_campaign_run_stops_on_first_non_success(gamedata, make_tool_call):
    handler = StubHandler(
        [
            make_tool_call("wizard.arcane_bolt", {"target": "goblin"}),
            make_tool_call("wizard.arcane_shield", {}),
        ]
    )

    campaign_run = execute_campaign_run(
        gamedata=gamedata,
        campaign_id="campaign.tutorial_v1",
        character_id="wizard.ember",
        prompt_format="json_only",
        cfg=None,
        model_key="",
        max_tokens=64,
        temperature=0.0,
        handler=handler,
    )

    assert [item["scene_id"] for item in campaign_run["scene_runs"]] == [
        "scene.tutorial.001_goblin_alley",
        "scene.tutorial.002_runes_on_wall",
    ]
    assert campaign_run["final_outcome"] == "failure"
    assert campaign_run["stop_scene_id"] == "scene.tutorial.002_runes_on_wall"
    assert campaign_run["passed_scenes"] == 1
    assert campaign_run["failed_scenes"] == 1


def test_execute_campaign_run_can_continue_after_failure(gamedata, make_tool_call):
    handler = StubHandler(
        [
            make_tool_call("wizard.arcane_bolt", {"target": "goblin"}),
            make_tool_call("wizard.arcane_shield", {}),
            make_tool_call("wizard.cast_water_ball", {"target": "flame sentinel"}),
        ]
    )

    campaign_run = execute_campaign_run(
        gamedata=gamedata,
        campaign_id="campaign.tutorial_v1",
        character_id="wizard.ember",
        prompt_format="json_only",
        cfg=None,
        model_key="",
        max_tokens=64,
        temperature=0.0,
        continue_on_failure=True,
        handler=handler,
    )

    assert [item["scene_id"] for item in campaign_run["scene_runs"]] == [
        "scene.tutorial.001_goblin_alley",
        "scene.tutorial.002_runes_on_wall",
        "scene.tutorial.003_flame_gate",
    ]
    assert campaign_run["continue_on_failure"] is True
    assert campaign_run["stop_scene_id"] is None
    assert campaign_run["first_failed_scene_id"] == "scene.tutorial.002_runes_on_wall"
    assert campaign_run["passed_scenes"] == 2
    assert campaign_run["failed_scenes"] == 1
    assert campaign_run["success_rate"] == 2 / 3 * 100.0


def test_execute_campaign_run_succeeds_when_all_scenes_succeed(gamedata, make_tool_call):
    handler = StubHandler(
        [
            make_tool_call("wizard.arcane_bolt", {"target": "goblin"}),
            make_tool_call("wizard.read_runes", {"surface": "wall"}),
            make_tool_call("wizard.cast_water_ball", {"target": "flame sentinel"}),
        ]
    )

    campaign_run = execute_campaign_run(
        gamedata=gamedata,
        campaign_id="campaign.tutorial_v1",
        character_id="wizard.ember",
        prompt_format="json_only",
        cfg=None,
        model_key="",
        max_tokens=64,
        temperature=0.0,
        handler=handler,
    )

    assert len(campaign_run["scene_runs"]) == 3
    assert campaign_run["final_outcome"] == "success"
    assert campaign_run["stop_scene_id"] is None
    assert campaign_run["passed_scenes"] == 3
    assert campaign_run["failed_scenes"] == 0


def test_execute_learning_scene_retries_after_failure_and_updates_notes(gamedata, make_tool_call):
    handler = StubHandler(
        [
            make_tool_call("wizard.arcane_shield", {}),
            '{"notes":"- The runes scene needs a knowledge-oriented tool.\\n- Arcane Shield is not enough here."}',
            make_tool_call("wizard.read_runes", {"surface": "wall"}),
        ]
    )

    learning_scene = execute_learning_scene(
        gamedata=gamedata,
        campaign_id="campaign.tutorial_v1",
        character_id="wizard.ember",
        scene_id="scene.tutorial.002_runes_on_wall",
        scene_index=1,
        prompt_format="json_only",
        cfg=None,
        model_key="",
        max_tokens=64,
        temperature=0.0,
        current_notes="",
        per_scene_retry_limit=3,
        total_retry_limit_remaining=5,
        handler=handler,
    )

    scene_result = learning_scene["scene_result"]
    assert scene_result["status"] == "PASS"
    assert scene_result["attempt_count"] == 2
    assert scene_result["retry_count"] == 1
    assert learning_scene["retries_used"] == 1
    assert "knowledge-oriented tool" in learning_scene["updated_notes"]
    assert scene_result["attempts"][0]["note_update"]["updated_notes"] == learning_scene["updated_notes"]
    assert scene_result["attempts"][1]["learning_notes"] == learning_scene["updated_notes"]


def test_execute_learning_campaign_carries_notes_across_scenes(gamedata, make_tool_call):
    handler = StubHandler(
        [
            make_tool_call("wizard.arcane_bolt", {"target": "goblin"}),
            make_tool_call("wizard.arcane_shield", {}),
            '{"notes":"- Use rune-reading on glowing walls or statues."}',
            make_tool_call("wizard.read_runes", {"surface": "wall"}),
            make_tool_call("wizard.cast_water_ball", {"target": "flame sentinel"}),
        ]
    )

    campaign_run = execute_learning_campaign(
        gamedata=gamedata,
        campaign_id="campaign.tutorial_v1",
        character_id="wizard.ember",
        prompt_format="json_only",
        cfg=None,
        model_key="",
        max_tokens=64,
        temperature=0.0,
        per_scene_retry_limit=2,
        total_retry_limit=5,
        initial_notes="",
        handler=handler,
    )

    assert campaign_run["self_learning_enabled"] is True
    assert campaign_run["passed_scenes"] == 3
    assert campaign_run["failed_scenes"] == 0
    assert campaign_run["total_retries_used"] == 1
    assert "Use rune-reading" in campaign_run["final_notes"]
    assert len(campaign_run["attempts"]) == 4
    assert campaign_run["scene_runs"][1]["resolved_after_learning"] is True
