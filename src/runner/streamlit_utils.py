import json
import os
from typing import Any

from src.models.config import DEFAULT_RUN_CONFIG_PATH


DEFAULT_LOCAL_MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "local_models")
)


def discover_local_models(models_dir: str = DEFAULT_LOCAL_MODELS_DIR) -> list[str]:
    if not os.path.isdir(models_dir):
        return []

    model_names = [
        entry.name
        for entry in os.scandir(models_dir)
        if entry.is_file() and entry.name.lower().endswith(".gguf")
    ]
    return sorted(model_names)


def rewrite_run_config_for_model(
    model_filename: str,
    *,
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    models_dir: str = DEFAULT_LOCAL_MODELS_DIR,
    backend: str = "llama_cpp",
) -> dict[str, Any]:
    if not model_filename or not model_filename.lower().endswith(".gguf"):
        raise ValueError("Selected model must be a non-empty .gguf filename.")

    resolved_config_path = os.path.abspath(config_path)
    resolved_models_dir = os.path.abspath(models_dir)
    model_path = os.path.abspath(os.path.join(resolved_models_dir, model_filename))

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Selected GGUF model does not exist: {model_path}")

    with open(resolved_config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    config_dir = os.path.dirname(resolved_config_path)
    relative_model_path = os.path.relpath(model_path, config_dir).replace("\\", "/")

    updated = dict(raw)
    updated["backend"] = backend
    updated["model"] = relative_model_path

    with open(resolved_config_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return updated


def normalize_single_scene_run(scene_run: dict) -> dict[str, Any]:
    verdict = scene_run["verdict"]
    return {
        "scene_runs": [scene_run],
        "final_outcome": verdict.get("outcome", "invalid"),
        "final_reason": verdict.get("reason", ""),
        "stop_scene_id": scene_run["scene_id"]
        if verdict.get("outcome") != "success"
        else None,
    }


def build_scene_result_rows(scene_runs: list[dict], gamedata: dict) -> list[dict[str, Any]]:
    rows = []

    for scene_run in scene_runs:
        scene = gamedata["scenes_by_id"][scene_run["scene_id"]]
        monster = gamedata["monsters_by_id"][scene["monster_id"]]
        character = gamedata["characters_by_id"][scene_run["character_id"]]
        verdict = scene_run["verdict"]
        outcome = verdict.get("outcome", "invalid")

        rows.append(
            {
                "scene_id": scene_run["scene_id"],
                "scene_title": scene.get("title", scene_run["scene_id"]),
                "monster_id": scene["monster_id"],
                "monster_name": monster.get("name", scene["monster_id"]),
                "character_id": scene_run["character_id"],
                "character_name": character.get("name", scene_run["character_id"]),
                "raw_model_output": scene_run.get("raw_model_output", ""),
                "verdict": verdict,
                "status": "success" if outcome == "success" else "failure",
                "status_label": "Success" if outcome == "success" else "Failure",
                "reason": verdict.get("reason", ""),
            }
        )

    return rows
