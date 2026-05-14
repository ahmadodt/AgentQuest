import json
import os
from datetime import datetime
from typing import Any

from src.engine.validator import ToolCallValidator
from src.models.registry import build_handler
from src.prompts.base_prompt import build_messages
from src.prompts.prompt_config import DEFAULT_PROMPT_CONFIG, PromptConfig
from src.prompts.presets import DEFAULT_PRESET_NAME


DEFAULT_CHARACTER_ID = "knight.bram"
DEFAULT_SCENE_ID = "scene.goblin_den.001_outer_watch"
DEFAULT_CAMPAIGN_ID = "campaign.goblin_den_v1"


def load_preset(preset_name: str) -> PromptConfig:
    try:
        from src.prompts import presets  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import src/prompts/presets.py. "
            f"Create it (or use --preset {DEFAULT_PRESET_NAME}). "
            f"Original error: {e}"
        )

    if not hasattr(presets, preset_name):
        available = sorted(
            [
                k
                for k in dir(presets)
                if k.isupper() and isinstance(getattr(presets, k), PromptConfig)
            ]
        )
        raise ValueError(f"Unknown preset '{preset_name}'. Available presets: {available}")

    cfg = getattr(presets, preset_name)
    if not isinstance(cfg, PromptConfig):
        raise TypeError(f"Preset '{preset_name}' exists but is not a PromptConfig.")
    return cfg


def ensure_dir(dirpath: str) -> None:
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def default_run_path(prefix: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return os.path.join("runs", f"{prefix}_{timestamp}.json")


def resolve_character(gamedata: dict, character_id: str) -> dict:
    try:
        return gamedata["characters_by_id"][character_id]
    except KeyError as exc:
        raise KeyError(f"Missing character id: {character_id}") from exc


def resolve_scene(gamedata: dict, scene_id: str) -> dict:
    try:
        return gamedata["scenes_by_id"][scene_id]
    except KeyError as exc:
        raise KeyError(f"Missing scene id: {scene_id}") from exc


def resolve_campaign(gamedata: dict, campaign_id: str) -> dict:
    try:
        return gamedata["campaigns_by_id"][campaign_id]
    except KeyError as exc:
        raise KeyError(f"Missing campaign id: {campaign_id}") from exc


def get_campaign_scene_ids(gamedata: dict, campaign_id: str) -> list[str]:
    campaign = resolve_campaign(gamedata, campaign_id)
    scene_ids = list(campaign.get("scene_ids") or [])
    if not scene_ids:
        raise ValueError(f"Campaign has no scenes: {campaign_id}")
    return scene_ids


def get_visible_tools(gamedata: dict, character_id: str) -> tuple[dict, list[str], list[dict]]:
    character = resolve_character(gamedata, character_id)
    visible_tool_ids = list(character["tool_ids"])
    visible_tools = [gamedata["tools_by_id"][tid] for tid in visible_tool_ids]
    return character, visible_tool_ids, visible_tools


def get_model_label(*, metadata: dict[str, Any] | None, model_path_override: str | None = None) -> str:
    if metadata and metadata.get("model_path"):
        return str(metadata["model_path"])
    if model_path_override:
        return os.path.abspath(model_path_override)
    return ""


def scene_status_from_verdict(verdict: dict[str, Any] | None) -> str:
    if not isinstance(verdict, dict):
        return "ERROR"

    outcome = verdict.get("outcome")
    if outcome == "success":
        return "PASS"
    if verdict.get("ast_valid") is False:
        return "PARSE_ERROR"
    if outcome in {"failure", "invalid"}:
        return "FAIL"
    return "ERROR"


def summarize_scene_results(
    scene_results: list[dict[str, Any]],
    *,
    campaign_id: str,
    character_id: str,
    model: str,
    total_scenes: int | None = None,
) -> dict[str, Any]:
    total_scenes = total_scenes if total_scenes is not None else len(scene_results)
    passed_scenes = sum(1 for item in scene_results if item.get("status") == "PASS")
    parse_failures = sum(1 for item in scene_results if item.get("status") == "PARSE_ERROR")
    failed_scenes = sum(1 for item in scene_results if item.get("status") in {"FAIL", "PARSE_ERROR", "ERROR"})
    success_rate = (passed_scenes / total_scenes * 100.0) if total_scenes else 0.0
    first_failed_scene_id = next(
        (item["scene_id"] for item in scene_results if item.get("status") != "PASS"),
        None,
    )

    return {
        "campaign_id": campaign_id,
        "character_id": character_id,
        "model": model,
        "total_scenes": total_scenes,
        "passed_scenes": passed_scenes,
        "failed_scenes": failed_scenes,
        "parse_failures": parse_failures,
        "success_rate": success_rate,
        "first_failed_scene_id": first_failed_scene_id,
        "ordered_scene_results": scene_results,
    }


def execute_scene_run(
    *,
    gamedata: dict,
    character_id: str,
    scene_id: str,
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    campaign_id: str | None = None,
    scene_index: int | None = None,
    model_path_override: str | None = None,
    handler=None,
) -> dict:
    cfg = cfg or DEFAULT_PROMPT_CONFIG
    character, visible_tool_ids, visible_tools = get_visible_tools(gamedata, character_id)
    scene = resolve_scene(gamedata, scene_id)

    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        prompt_format=prompt_format,
        cfg=cfg,
    )

    handler = handler or build_handler(model_key, model_path_override=model_path_override)
    gen = handler.generate(messages, max_tokens=max_tokens, temperature=temperature)
    raw = (gen.raw_text or "").strip()

    validator = ToolCallValidator(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=scene_id,
        visible_tool_ids=visible_tool_ids,
    )
    verdict = validator.validate(raw)
    status = scene_status_from_verdict(verdict)
    parsed_tool_call = verdict.get("parsed_tool_call")
    metadata = gen.metadata or {}
    model_label = get_model_label(metadata=metadata, model_path_override=model_path_override)

    return {
        "campaign_id": campaign_id,
        "scene_id": scene_id,
        "scene_index": scene_index,
        "character_id": character_id,
        "model": model_label,
        "visible_tool_ids": visible_tool_ids,
        "visible_tools": visible_tools,
        "messages": messages,
        "prompt_messages": messages,
        "raw_model_output": raw,
        "parsed_tool_call": parsed_tool_call,
        "validation": verdict,
        "status": status,
        "reason": verdict.get("reason", ""),
        "metadata": metadata,
        "verdict": verdict,
        "scene_title": scene.get("title", scene_id),
    }


def execute_campaign_run(
    *,
    gamedata: dict,
    campaign_id: str,
    character_id: str,
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    continue_on_failure: bool = False,
    model_path_override: str | None = None,
    handler=None,
) -> dict:
    campaign = resolve_campaign(gamedata, campaign_id)
    scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
    scene_runs = []
    final_outcome = "success"
    final_reason = "Campaign completed successfully"
    stop_scene_id = None

    handler = handler or build_handler(model_key, model_path_override=model_path_override)

    for scene_index, scene_id in enumerate(scene_ids):
        scene_run = execute_scene_run(
            gamedata=gamedata,
            character_id=character_id,
            scene_id=scene_id,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=model_key,
            max_tokens=max_tokens,
            temperature=temperature,
            campaign_id=campaign_id,
            scene_index=scene_index,
            model_path_override=model_path_override,
            handler=handler,
        )
        scene_runs.append(scene_run)

        verdict = scene_run["verdict"]
        if verdict.get("outcome") != "success":
            final_outcome = verdict.get("outcome", "invalid")
            final_reason = verdict.get("reason", "Campaign stopped")
            stop_scene_id = scene_id
            if not continue_on_failure:
                break

    campaign_summary = summarize_scene_results(
        scene_runs,
        campaign_id=campaign_id,
        character_id=character_id,
        model=scene_runs[-1]["model"] if scene_runs else "",
        total_scenes=len(scene_ids),
    )

    if campaign_summary["failed_scenes"] and continue_on_failure:
        final_outcome = "failure"
        final_reason = "Campaign completed with one or more failed scenes"
        stop_scene_id = None
    elif campaign_summary["failed_scenes"] == 0:
        final_outcome = "success"
        final_reason = "Campaign completed successfully"
        stop_scene_id = None

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("name", campaign_id),
        "character_id": character_id,
        "model": campaign_summary["model"],
        "scene_ids": scene_ids,
        "scene_runs": scene_runs,
        "ordered_scene_results": scene_runs,
        "continue_on_failure": continue_on_failure,
        "final_outcome": final_outcome,
        "final_reason": final_reason,
        "stop_scene_id": stop_scene_id,
        "first_failed_scene_id": campaign_summary["first_failed_scene_id"],
        "total_scenes": campaign_summary["total_scenes"],
        "passed_scenes": campaign_summary["passed_scenes"],
        "failed_scenes": campaign_summary["failed_scenes"],
        "parse_failures": campaign_summary["parse_failures"],
        "success_rate": campaign_summary["success_rate"],
    }
