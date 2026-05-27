import json
import os
from typing import Any

from src.models.catalog import DEFAULT_MODEL_CATALOG_PATH, load_model_catalog
from src.models.config import (
    DEFAULT_RUN_CONFIG_PATH,
    DEFAULT_RUNTIME_PRESET_NAME,
    load_runtime_model_config,
    load_runtime_prompt_config,
)
from src.prompts.prompt_config import PromptConfig
from src.runner.runner_utils import (
    build_run_log_payload,
    get_campaign_scene_ids,
    load_preset,
    normalize_single_scene_run,
    save_result_run_log,
    scene_status_from_verdict,
)


DEFAULT_STREAMLIT_PRESET = DEFAULT_RUNTIME_PRESET_NAME
DEFAULT_STREAMLIT_PRESET_ORDER = [
    "BLIND_ADVENTURER",
    "TOOL_MANUAL",
    "SCOUT_REPORT",
    "BATTLE_PLAN",
    "FULL_INFO",
]


def discover_catalog_models(
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> list[dict[str, str]]:
    catalog = load_model_catalog(catalog_path)
    return [
        {
            "name": entry.name,
            "display_name": entry.display_name,
            "backend": entry.backend,
            "repo_id": entry.repo_id,
            "filename": entry.filename,
            "description": entry.description,
        }
        for entry in sorted(catalog.values(), key=lambda item: item.display_name.lower())
    ]


def discover_streamlit_presets() -> list[str]:
    from src.prompts import presets  # type: ignore

    preset_names = {
        name
        for name, value in vars(presets).items()
        if name.isupper() and name != "DEFAULT_PRESET_NAME" and name != "PRESETS" and isinstance(value, PromptConfig)
    }

    ordered = [name for name in DEFAULT_STREAMLIT_PRESET_ORDER if name in preset_names]
    ordered.extend(sorted(name for name in preset_names if name not in ordered))
    return ordered


def normalize_streamlit_preset_name(preset_name: str) -> str:
    normalized = (preset_name or "").strip()
    if not normalized:
        return DEFAULT_STREAMLIT_PRESET
    return normalized


def load_streamlit_run_settings(
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    *,
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> dict[str, Any]:
    prompt_cfg = load_runtime_prompt_config(config_path)
    preset_name = normalize_streamlit_preset_name(prompt_cfg.preset_name)
    model_cfg = load_runtime_model_config(config_path, catalog_path=catalog_path)

    return {
        "preset_name": preset_name,
        "prompt_format": prompt_cfg.prompt_format,
        "preset_config": load_preset(preset_name),
        "model_name": model_cfg.model_name,
        "model_display_name": model_cfg.model_display_name,
        "repo_id": model_cfg.repo_id,
        "filename": model_cfg.filename,
        "backend": model_cfg.backend,
    }


def rewrite_run_config_for_streamlit_selection(
    *,
    model_name: str,
    preset_name: str,
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    backend: str = "llama_cpp",
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> dict[str, Any]:
    selected_model_name = (model_name or "").strip()
    if not selected_model_name:
        raise ValueError("Selected model must be a non-empty catalog name.")

    catalog = load_model_catalog(catalog_path)
    if selected_model_name not in catalog:
        raise ValueError(f"Selected model is not present in the catalog: {selected_model_name}")

    resolved_config_path = os.path.abspath(config_path)

    with open(resolved_config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    updated = dict(raw)
    updated["backend"] = backend
    updated["model"] = selected_model_name
    updated["preset"] = normalize_streamlit_preset_name(preset_name)

    with open(resolved_config_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return updated


def rewrite_run_config_for_model(
    model_name: str,
    *,
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    backend: str = "llama_cpp",
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> dict[str, Any]:
    current_prompt_cfg = load_runtime_prompt_config(config_path)
    return rewrite_run_config_for_streamlit_selection(
        model_name=model_name,
        preset_name=current_prompt_cfg.preset_name,
        config_path=config_path,
        backend=backend,
        catalog_path=catalog_path,
    )


def build_scene_result_rows(scene_runs: list[dict], gamedata: dict) -> list[dict[str, Any]]:
    rows = []

    for scene_run in scene_runs:
        scene = gamedata["scenes_by_id"][scene_run["scene_id"]]
        monster = gamedata["monsters_by_id"].get(scene["monster_id"], {})
        character = gamedata["characters_by_id"][scene_run["character_id"]]
        verdict = scene_run.get("verdict", {})
        status = scene_run.get("status") or scene_status_from_verdict(verdict)
        parsed_tool_call = scene_run.get("parsed_tool_call") or verdict.get("parsed_tool_call")

        rows.append(
            {
                "scene_id": scene_run["scene_id"],
                "scene_index": scene_run.get("scene_index"),
                "scene_title": scene.get("title", scene_run["scene_id"]),
                "scene_location": scene.get("location", ""),
                "scene_narrative": scene.get("narrative", ""),
                "scene_constraints": scene.get("constraints", {}),
                "monster_id": scene["monster_id"],
                "monster_name": monster.get("name", scene["monster_id"]),
                "monster_type": monster.get("type", ""),
                "monster_description": monster.get("description", ""),
                "monster_interactions": monster.get("interactions", {}),
                "character_id": scene_run["character_id"],
                "character_name": character.get("name", scene_run["character_id"]),
                "character_class": character.get("class", ""),
                "character_inventory": character.get("inventory", []),
                "character_traits": character.get("traits", []),
                "actor_type": scene_run.get("actor_type", "model"),
                "visible_tool_ids": scene_run.get("visible_tool_ids", []),
                "visible_tools": scene_run.get("visible_tools", []),
                "raw_model_output": scene_run.get("raw_model_output", ""),
                "messages": scene_run.get("messages", []),
                "attempts": scene_run.get("attempts", []),
                "attempt_count": scene_run.get("attempt_count"),
                "retry_count": scene_run.get("retry_count"),
                "notes_before_scene": scene_run.get("notes_before_scene", ""),
                "notes_after_scene": scene_run.get("notes_after_scene", ""),
                "parsed_tool_call": parsed_tool_call,
                "selected_tool_id": (parsed_tool_call or {}).get("tool_id"),
                "verdict": verdict,
                "validation": scene_run.get("validation", verdict),
                "model": scene_run.get("model", ""),
                "status": status,
                "status_label": status.replace("_", " "),
                "reason": scene_run.get("reason", verdict.get("reason", "")),
            }
        )

    return rows


def build_campaign_progress_rows(
    *,
    gamedata: dict,
    campaign_id: str,
    scene_results_by_id: dict[str, dict[str, Any]],
    current_scene_index: int | None = None,
    running_scene_index: int | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, scene_id in enumerate(get_campaign_scene_ids(gamedata, campaign_id)):
        scene = gamedata["scenes_by_id"][scene_id]
        scene_result = scene_results_by_id.get(scene_id)
        status = "RUNNING" if running_scene_index == index else "NOT_RUN"
        if scene_result:
            status = scene_result.get("status", status)

        rows.append(
            {
                "scene_index": index,
                "scene_id": scene_id,
                "scene_title": scene.get("title", scene_id),
                "status": status,
                "is_current": current_scene_index == index,
            }
        )
    return rows


def save_streamlit_run_log(run_mode: str, runlog: dict[str, Any]) -> str:
    model_name = load_runtime_model_config().model_name or runlog.get("model", "")
    return save_result_run_log(run_mode, runlog, model_name)
