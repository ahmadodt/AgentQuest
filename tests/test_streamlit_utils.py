import json
import os

from src.runner.streamlit_utils import (
    build_scene_result_rows,
    build_run_log_payload,
    discover_catalog_models,
    discover_streamlit_presets,
    load_streamlit_run_settings,
    normalize_streamlit_preset_name,
    normalize_single_scene_run,
    rewrite_run_config_for_model,
    rewrite_run_config_for_streamlit_selection,
    save_streamlit_run_log,
)
from src.runner.runner_utils import default_run_path


def _write_model_catalog(tmp_path):
    catalog_path = tmp_path / "model_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "name": "beta_model",
                        "display_name": "Beta Model",
                        "backend": "llama_cpp",
                        "repo_id": "org/beta",
                        "filename": "beta.gguf",
                    },
                    {
                        "name": "alpha_model",
                        "display_name": "Alpha Model",
                        "backend": "llama_cpp",
                        "repo_id": "org/alpha",
                        "filename": "alpha.gguf",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return catalog_path


def test_discover_catalog_models_returns_sorted_entries(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)

    assert discover_catalog_models(str(catalog_path)) == [
        {
            "name": "alpha_model",
            "display_name": "Alpha Model",
            "backend": "llama_cpp",
            "repo_id": "org/alpha",
            "filename": "alpha.gguf",
            "description": "",
        },
        {
            "name": "beta_model",
            "display_name": "Beta Model",
            "backend": "llama_cpp",
            "repo_id": "org/beta",
            "filename": "beta.gguf",
            "description": "",
        },
    ]


def test_discover_streamlit_presets_uses_expected_information_order_and_hides_default():
    presets = discover_streamlit_presets()

    assert presets == [
        "BLIND_ADVENTURER",
        "TOOL_MANUAL",
        "SCOUT_REPORT",
        "BATTLE_PLAN",
        "FULL_INFO",
    ]
    assert "default" not in presets
    assert "MINIMAL" not in presets


def test_normalize_streamlit_preset_name_uses_battle_plan_for_empty_only():
    assert normalize_streamlit_preset_name("") == "BATTLE_PLAN"
    assert normalize_streamlit_preset_name("FULL_INFO") == "FULL_INFO"


def test_rewrite_run_config_for_streamlit_selection_updates_model_and_preset_and_preserves_other_keys(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)

    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "beta_model",
                "preset": "BATTLE_PLAN",
                "extra": "keep-me",
            }
        ),
        encoding="utf-8",
    )

    updated = rewrite_run_config_for_streamlit_selection(
        model_name="alpha_model",
        preset_name="FULL_INFO",
        config_path=str(config_path),
        catalog_path=str(catalog_path),
    )

    assert updated == {
        "backend": "llama_cpp",
        "model": "alpha_model",
        "preset": "FULL_INFO",
        "extra": "keep-me",
    }

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted == updated


def test_rewrite_run_config_for_model_preserves_current_preset(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)

    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "beta_model",
                "preset": "FULL_INFO",
            }
        ),
        encoding="utf-8",
    )

    updated = rewrite_run_config_for_model(
        "alpha_model",
        config_path=str(config_path),
        catalog_path=str(catalog_path),
    )

    assert updated["preset"] == "FULL_INFO"
    assert updated["model"] == "alpha_model"


def test_load_streamlit_run_settings_uses_preset_and_prompt_format_from_config(tmp_path, monkeypatch):
    catalog_path = _write_model_catalog(tmp_path)

    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "alpha_model",
                "preset": "FULL_INFO",
                "prompt_format": "json_only",
            }
        ),
        encoding="utf-8",
    )

    sentinel = object()
    monkeypatch.setattr("src.runner.streamlit_utils.load_preset", lambda preset_name: sentinel)

    settings = load_streamlit_run_settings(str(config_path), catalog_path=str(catalog_path))

    assert settings["preset_name"] == "FULL_INFO"
    assert settings["prompt_format"] == "json_only"
    assert settings["preset_config"] is sentinel
    assert settings["model_name"] == "alpha_model"
    assert settings["model_display_name"] == "Alpha Model"

def test_normalize_single_scene_run_wraps_scene_and_derives_summary(make_tool_call):
    scene_run = {
        "scene_id": "scene.tutorial.001_goblin_alley",
        "character_id": "wizard.ember",
        "messages": [{"role": "system", "content": "hello"}],
        "raw_model_output": make_tool_call("common.run", {"direction": "backtrack"}),
        "verdict": {"outcome": "success", "reason": "ok"},
    }

    normalized = normalize_single_scene_run(scene_run)

    assert normalized["scene_runs"] == [scene_run]
    assert normalized["ordered_scene_results"] == [scene_run]
    assert normalized["final_outcome"] == "success"
    assert normalized["final_reason"] == "ok"
    assert normalized["stop_scene_id"] is None


def test_build_scene_result_rows_maps_scene_monster_character_and_status(make_tool_call):
    scene_runs = [
        {
            "scene_id": "scene.tutorial.001_goblin_alley",
            "scene_index": 0,
            "character_id": "wizard.ember",
            "actor_type": "human",
            "messages": [{"role": "system", "content": "sys"}],
            "raw_model_output": make_tool_call("common.run", {"direction": "backtrack"}),
            "parsed_tool_call": {"tool_id": "common.run", "args": {"direction": "backtrack"}},
            "status": "PASS",
            "validation": {"outcome": "success", "reason": "escaped safely"},
            "verdict": {"outcome": "success", "reason": "escaped safely"},
        },
        {
            "scene_id": "scene.tutorial.002_runes_on_wall",
            "scene_index": 1,
            "character_id": "wizard.ember",
            "messages": [{"role": "user", "content": "usr"}],
            "raw_model_output": make_tool_call("wizard.arcane_shield", {}),
            "parsed_tool_call": {"tool_id": "wizard.arcane_shield", "args": {}},
            "status": "FAIL",
            "validation": {"outcome": "failure", "reason": "wrong action"},
            "verdict": {"outcome": "failure", "reason": "wrong action"},
        },
    ]

    gamedata = {
        "scenes_by_id": {
            "scene.tutorial.001_goblin_alley": {
                "scene_id": "scene.tutorial.001_goblin_alley",
                "title": "Alley Ambush",
                "monster_id": "goblin.street_cutpurse",
            },
            "scene.tutorial.002_runes_on_wall": {
                "scene_id": "scene.tutorial.002_runes_on_wall",
                "title": "Runes in the Dark",
                "monster_id": "cursed.whispering_statue",
            },
        },
        "monsters_by_id": {
            "goblin.street_cutpurse": {"name": "Street Cutpurse Goblin"},
            "cursed.whispering_statue": {"name": "Whispering Statue"},
        },
        "characters_by_id": {
            "wizard.ember": {"name": "Ember"},
        },
    }

    rows = build_scene_result_rows(scene_runs, gamedata)

    assert [row["scene_id"] for row in rows] == [
        "scene.tutorial.001_goblin_alley",
        "scene.tutorial.002_runes_on_wall",
    ]
    assert rows[0]["monster_id"] == "goblin.street_cutpurse"
    assert rows[0]["monster_name"] == "Street Cutpurse Goblin"
    assert rows[0]["character_name"] == "Ember"
    assert rows[0]["actor_type"] == "human"
    assert rows[0]["status"] == "PASS"
    assert rows[0]["status_label"] == "PASS"
    assert rows[0]["messages"] == [{"role": "system", "content": "sys"}]
    assert rows[1]["status"] == "FAIL"
    assert rows[1]["reason"] == "wrong action"


def test_build_run_log_payload_matches_scene_shape():
    run_result = {
        "scene_runs": [{"scene_id": "scene.alpha"}],
        "ordered_scene_results": [{"scene_id": "scene.alpha"}],
        "final_outcome": "success",
        "final_reason": "ok",
        "stop_scene_id": None,
    }

    payload = build_run_log_payload(
        run_mode="scene",
        data_dir="data",
        preset_name="BATTLE_PLAN",
        prompt_format="json_only",
        character_id="knight.bram",
        scene_id="scene.alpha",
        run_result=run_result,
    )

    assert payload["data_dir"] == "data"
    assert payload["character_id"] == "knight.bram"
    assert payload["scene_id"] == "scene.alpha"
    assert payload["preset"] == "BATTLE_PLAN"
    assert payload["prompt_format"] == "json_only"
    assert payload["final_outcome"] == "success"


def test_build_run_log_payload_matches_campaign_shape():
    run_result = {
        "campaign_id": "campaign.alpha",
        "scene_runs": [{"scene_id": "scene.alpha"}],
        "ordered_scene_results": [{"scene_id": "scene.alpha"}],
        "final_outcome": "failure",
        "final_reason": "stop",
        "stop_scene_id": "scene.alpha",
    }

    payload = build_run_log_payload(
        run_mode="campaign",
        data_dir="data",
        preset_name="FULL_INFO",
        prompt_format="json_only",
        character_id="wizard.ember",
        campaign_id="campaign.alpha",
        run_result=run_result,
    )

    assert payload["campaign_id"] == "campaign.alpha"
    assert payload["character_id"] == "wizard.ember"
    assert payload["preset"] == "FULL_INFO"
    assert payload["stop_scene_id"] == "scene.alpha"


def test_build_run_log_payload_compacts_scene_prompt_and_tool_payloads():
    run_result = {
        "scene_id": "scene.alpha",
        "scene_index": 0,
        "scene_title": "Alpha",
        "actor_type": "human",
        "status": "FAIL",
        "reason": "wrong tool",
        "raw_model_output": '{"tool_id":"tool.alpha","arguments":{}}',
        "parsed_tool_call": {"tool_id": "tool.alpha", "arguments": {}},
        "validation": {"outcome": "failure", "reason": "wrong tool"},
        "messages": [{"role": "system", "content": "prompt"}],
        "visible_tools": [{"tool_id": "tool.alpha", "description": "Large blob"}],
        "visible_tool_ids": ["tool.alpha"],
        "metadata": {"stub": True},
    }

    payload = build_run_log_payload(
        run_mode="scene",
        data_dir="data",
        preset_name="BATTLE_PLAN",
        prompt_format="json_only",
        character_id="knight.bram",
        scene_id="scene.alpha",
        run_result=run_result,
    )

    assert payload["scene_id"] == "scene.alpha"
    assert payload["actor_type"] == "human"
    assert payload["visible_tool_ids"] == ["tool.alpha"]
    assert "messages" not in payload
    assert "visible_tools" not in payload
    assert "metadata" not in payload


def test_build_run_log_payload_compacts_campaign_attempt_payloads():
    run_result = {
        "campaign_id": "campaign.alpha",
        "scene_runs": [
            {
                "scene_id": "scene.alpha",
                "scene_index": 0,
                "actor_type": "human",
                "status": "FAIL",
                "reason": "wrong tool",
                "raw_model_output": '{"tool_id":"tool.alpha","arguments":{}}',
                "parsed_tool_call": {"tool_id": "tool.alpha", "arguments": {}},
                "validation": {"outcome": "failure", "reason": "wrong tool"},
                "messages": [{"role": "system", "content": "prompt"}],
                "visible_tools": [{"tool_id": "tool.alpha", "description": "Large blob"}],
                "visible_tool_ids": ["tool.alpha"],
                "attempt_index": 2,
                "attempt_count": 2,
                "retry_count": 1,
                "notes_before_scene": "",
                "notes_after_scene": "- Try another tool",
                "attempts": [
                    {
                        "scene_id": "scene.alpha",
                        "scene_index": 0,
                        "attempt_index": 1,
                        "status": "FAIL",
                        "reason": "wrong tool",
                        "raw_model_output": '{"tool_id":"tool.alpha","arguments":{}}',
                        "parsed_tool_call": {"tool_id": "tool.alpha", "arguments": {}},
                        "validation": {"outcome": "failure", "reason": "wrong tool"},
                        "messages": [{"role": "system", "content": "attempt prompt"}],
                        "visible_tools": [{"tool_id": "tool.alpha", "description": "Large blob"}],
                        "notes_before_attempt": "",
                        "notes_after_attempt": "- Try another tool",
                    }
                ],
            }
        ],
        "ordered_scene_results": [],
        "attempts": [
            {
                "scene_id": "scene.alpha",
                "scene_index": 0,
                "attempt_index": 1,
                "status": "FAIL",
                "reason": "wrong tool",
                "raw_model_output": '{"tool_id":"tool.alpha","arguments":{}}',
                "parsed_tool_call": {"tool_id": "tool.alpha", "arguments": {}},
                "validation": {"outcome": "failure", "reason": "wrong tool"},
                "messages": [{"role": "system", "content": "attempt prompt"}],
                "visible_tools": [{"tool_id": "tool.alpha", "description": "Large blob"}],
            }
        ],
        "final_outcome": "failure",
        "final_reason": "stop",
        "stop_scene_id": "scene.alpha",
    }

    payload = build_run_log_payload(
        run_mode="campaign",
        data_dir="data",
        preset_name="FULL_INFO",
        prompt_format="json_only",
        character_id="wizard.ember",
        campaign_id="campaign.alpha",
        run_result=run_result,
    )

    scene = payload["scene_runs"][0]
    attempt = payload["scene_runs"][0]["attempts"][0]

    assert "messages" not in scene
    assert "visible_tools" not in scene
    assert scene["actor_type"] == "human"
    assert scene["visible_tool_ids"] == ["tool.alpha"]
    assert scene["attempt_count"] == 2
    assert scene["retry_count"] == 1
    assert "attempt_index" not in scene
    assert "notes_before_scene" not in scene
    assert "notes_after_scene" not in scene
    assert "messages" not in attempt
    assert "visible_tools" not in attempt
    assert "note_update" not in attempt
    assert payload["prompt_snapshot"]["scene_id"] == "scene.alpha"
    assert payload["prompt_snapshot"]["messages"] == [{"role": "system", "content": "prompt"}]
    assert "ordered_scene_results" not in payload
    assert "attempts" not in payload


def test_save_streamlit_run_log_writes_json_file(monkeypatch, tmp_path):
    monkeypatch.setattr("src.runner.runner_utils.default_run_path", lambda prefix: str(tmp_path / f"{prefix}_test.json"))

    path = save_streamlit_run_log("scene", {"ok": True})

    assert path.endswith("run_one_test.json")
    assert json.loads((tmp_path / "run_one_test.json").read_text(encoding="utf-8")) == {"ok": True}


def test_default_run_path_uses_agentquest_runs_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTQUEST_RUNS_DIR", str(tmp_path))

    path = default_run_path("run_one")

    assert os.path.dirname(path) == str(tmp_path)
    assert os.path.basename(path).startswith("run_one_")
