import json
import os
from datetime import datetime

from src.engine.validator import ToolCallValidator
from src.models.registry import build_handler
from src.prompts.base_prompt import build_messages
from src.prompts.prompt_config import DEFAULT_PROMPT_CONFIG, PromptConfig


DEFAULT_CHARACTER_ID = "knight.bram"
DEFAULT_SCENE_ID = "scene.goblin_den.001_outer_watch"
DEFAULT_CAMPAIGN_ID = "campaign.goblin_den_v1"


def load_preset(preset_name: str) -> PromptConfig:
    if preset_name == "default":
        return DEFAULT_PROMPT_CONFIG

    try:
        from src.prompts import presets  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import src/prompts/presets.py. "
            "Create it (or use --preset default). "
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


def get_visible_tools(gamedata: dict, character_id: str) -> tuple[dict, list[str], list[dict]]:
    character = gamedata["characters_by_id"][character_id]
    visible_tool_ids = list(character["tool_ids"])
    visible_tools = [gamedata["tools_by_id"][tid] for tid in visible_tool_ids]
    return character, visible_tool_ids, visible_tools


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
    handler=None,
) -> dict:
    cfg = cfg or DEFAULT_PROMPT_CONFIG
    character, visible_tool_ids, visible_tools = get_visible_tools(gamedata, character_id)
    scene = gamedata["scenes_by_id"][scene_id]

    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        prompt_format=prompt_format,
        cfg=cfg,
    )

    handler = handler or build_handler(model_key)
    gen = handler.generate(messages, max_tokens=max_tokens, temperature=temperature)
    raw = (gen.raw_text or "").strip()

    validator = ToolCallValidator(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=scene_id,
        visible_tool_ids=visible_tool_ids,
    )
    verdict = validator.validate(raw)

    return {
        "scene_id": scene_id,
        "character_id": character_id,
        "visible_tool_ids": visible_tool_ids,
        "messages": messages,
        "raw_model_output": raw,
        "metadata": gen.metadata,
        "verdict": verdict,
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
    handler=None,
) -> dict:
    campaign = gamedata["campaigns_by_id"][campaign_id]
    scene_runs = []
    final_outcome = "success"
    final_reason = "Campaign completed successfully"
    stop_scene_id = None

    handler = handler or build_handler(model_key)

    for scene_id in campaign["scene_ids"]:
        scene_run = execute_scene_run(
            gamedata=gamedata,
            character_id=character_id,
            scene_id=scene_id,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=model_key,
            max_tokens=max_tokens,
            temperature=temperature,
            handler=handler,
        )
        scene_runs.append(scene_run)

        verdict = scene_run["verdict"]
        if verdict.get("outcome") != "success":
            final_outcome = verdict.get("outcome", "invalid")
            final_reason = verdict.get("reason", "Campaign stopped")
            stop_scene_id = scene_id
            break

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("name", campaign_id),
        "character_id": character_id,
        "scene_ids": list(campaign["scene_ids"]),
        "scene_runs": scene_runs,
        "final_outcome": final_outcome,
        "final_reason": final_reason,
        "stop_scene_id": stop_scene_id,
    }
