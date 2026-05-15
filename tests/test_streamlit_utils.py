import json
import os

from src.runner.streamlit_utils import (
    build_scene_result_rows,
    build_run_log_payload,
    discover_local_models,
    discover_streamlit_presets,
    load_streamlit_run_settings,
    normalize_streamlit_preset_name,
    normalize_single_scene_run,
    rewrite_run_config_for_model,
    rewrite_run_config_for_streamlit_selection,
    save_streamlit_run_log,
)
from src.runner.runner_utils import default_run_path


def test_discover_local_models_returns_sorted_gguf_only(tmp_path):
    (tmp_path / "b-model.gguf").write_text("stub", encoding="utf-8")
    (tmp_path / "a-model.gguf").write_text("stub", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    assert discover_local_models(str(tmp_path)) == ["a-model.gguf", "b-model.gguf"]


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
    models_dir = tmp_path / "local_models"
    models_dir.mkdir()
    (models_dir / "Qwen_Qwen3-4B-Q4_K_L.gguf").write_text("stub", encoding="utf-8")

    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "../local_models/old.gguf",
                "preset": "BATTLE_PLAN",
                "extra": "keep-me",
            }
        ),
        encoding="utf-8",
    )

    updated = rewrite_run_config_for_streamlit_selection(
        model_filename="Qwen_Qwen3-4B-Q4_K_L.gguf",
        preset_name="FULL_INFO",
        config_path=str(config_path),
        models_dir=str(models_dir),
    )

    assert updated == {
        "backend": "llama_cpp",
        "model": "../local_models/Qwen_Qwen3-4B-Q4_K_L.gguf",
        "preset": "FULL_INFO",
        "extra": "keep-me",
    }

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted == updated


def test_rewrite_run_config_for_model_preserves_current_preset(tmp_path):
    models_dir = tmp_path / "local_models"
    models_dir.mkdir()
    (models_dir / "Qwen_Qwen3-4B-Q4_K_L.gguf").write_text("stub", encoding="utf-8")

    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "../local_models/old.gguf",
                "preset": "FULL_INFO",
            }
        ),
        encoding="utf-8",
    )

    updated = rewrite_run_config_for_model(
        "Qwen_Qwen3-4B-Q4_K_L.gguf",
        config_path=str(config_path),
        models_dir=str(models_dir),
    )

    assert updated["preset"] == "FULL_INFO"


def test_load_streamlit_run_settings_uses_preset_and_prompt_format_from_config(tmp_path, monkeypatch):
    model_dir = tmp_path / "local_models"
    model_dir.mkdir()
    (model_dir / "Qwen_Qwen3-4B-Q4_K_L.gguf").write_text("stub", encoding="utf-8")

    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "local_models/Qwen_Qwen3-4B-Q4_K_L.gguf",
                "preset": "FULL_INFO",
                "prompt_format": "json_only",
            }
        ),
        encoding="utf-8",
    )

    sentinel = object()
    monkeypatch.setattr("src.runner.streamlit_utils.load_preset", lambda preset_name: sentinel)

    settings = load_streamlit_run_settings(str(config_path))

    assert settings["preset_name"] == "FULL_INFO"
    assert settings["prompt_format"] == "json_only"
    assert settings["preset_config"] is sentinel
    assert settings["model_path"].endswith("Qwen_Qwen3-4B-Q4_K_L.gguf")

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


def test_save_streamlit_run_log_writes_json_file(monkeypatch, tmp_path):
    monkeypatch.setattr("src.runner.streamlit_utils.default_run_path", lambda prefix: str(tmp_path / f"{prefix}_test.json"))

    path = save_streamlit_run_log("scene", {"ok": True})

    assert path.endswith("run_one_test.json")
    assert json.loads((tmp_path / "run_one_test.json").read_text(encoding="utf-8")) == {"ok": True}


def test_default_run_path_uses_agentquest_runs_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTQUEST_RUNS_DIR", str(tmp_path))

    path = default_run_path("run_one")

    assert os.path.dirname(path) == str(tmp_path)
    assert os.path.basename(path).startswith("run_one_")
