import json

from src.runner.streamlit_utils import (
    build_scene_result_rows,
    discover_local_models,
    load_streamlit_run_settings,
    normalize_single_scene_run,
    rewrite_run_config_for_model,
)


def test_discover_local_models_returns_sorted_gguf_only(tmp_path):
    (tmp_path / "b-model.gguf").write_text("stub", encoding="utf-8")
    (tmp_path / "a-model.gguf").write_text("stub", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    assert discover_local_models(str(tmp_path)) == ["a-model.gguf", "b-model.gguf"]


def test_rewrite_run_config_for_model_updates_relative_path_and_preserves_other_keys(tmp_path):
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
                "extra": "keep-me",
            }
        ),
        encoding="utf-8",
    )

    updated = rewrite_run_config_for_model(
        "Qwen_Qwen3-4B-Q4_K_L.gguf",
        config_path=str(config_path),
        models_dir=str(models_dir),
    )

    assert updated == {
        "backend": "llama_cpp",
        "model": "../local_models/Qwen_Qwen3-4B-Q4_K_L.gguf",
        "extra": "keep-me",
    }

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted == updated


def test_load_streamlit_run_settings_uses_preset_and_prompt_format_from_config(tmp_path, monkeypatch):
    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "../local_models/Qwen_Qwen3-4B-Q4_K_L.gguf",
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


def test_normalize_single_scene_run_wraps_scene_and_derives_summary(make_tool_call):
    scene_run = {
        "scene_id": "scene.tutorial.001_goblin_alley",
        "character_id": "wizard.ember",
        "raw_model_output": make_tool_call("common.run", {"direction": "backtrack"}),
        "verdict": {"outcome": "success", "reason": "ok"},
    }

    normalized = normalize_single_scene_run(scene_run)

    assert normalized["scene_runs"] == [scene_run]
    assert normalized["final_outcome"] == "success"
    assert normalized["final_reason"] == "ok"
    assert normalized["stop_scene_id"] is None


def test_build_scene_result_rows_maps_scene_monster_character_and_status(make_tool_call):
    scene_runs = [
        {
            "scene_id": "scene.tutorial.001_goblin_alley",
            "character_id": "wizard.ember",
            "raw_model_output": make_tool_call("common.run", {"direction": "backtrack"}),
            "verdict": {"outcome": "success", "reason": "escaped safely"},
        },
        {
            "scene_id": "scene.tutorial.002_runes_on_wall",
            "character_id": "wizard.ember",
            "raw_model_output": make_tool_call("wizard.arcane_shield", {}),
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
    assert rows[0]["status"] == "success"
    assert rows[0]["status_label"] == "Success"
    assert rows[1]["status"] == "failure"
    assert rows[1]["reason"] == "wrong action"
