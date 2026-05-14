from typing import Any, Dict, List, Optional

from src.prompts.formats.json_only import (
    build_json_only_messages,
    build_json_only_note_update_messages,
)
from src.prompts.prompt_config import PromptConfig, DEFAULT_PROMPT_CONFIG


def build_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
    gamedata: Optional[Dict[str, Any]] = None,
    prompt_format: str = "json_only",
    cfg: Optional[PromptConfig] = None,
    learning_notes: str = "",
) -> List[Dict[str, str]]:
    cfg = cfg or DEFAULT_PROMPT_CONFIG

    if prompt_format == "json_only":
        return build_json_only_messages(
            scene=scene,
            character=character,
            visible_tools=visible_tools,
            gamedata=gamedata,
            cfg=cfg,
            learning_notes=learning_notes,
        )

    raise ValueError(f"Unknown prompt_format: {prompt_format}")


def build_note_update_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
    scene_run: Dict[str, Any],
    existing_notes: str,
    gamedata: Optional[Dict[str, Any]] = None,
    prompt_format: str = "json_only",
    cfg: Optional[PromptConfig] = None,
) -> List[Dict[str, str]]:
    cfg = cfg or DEFAULT_PROMPT_CONFIG

    if prompt_format == "json_only":
        return build_json_only_note_update_messages(
            scene=scene,
            character=character,
            visible_tools=visible_tools,
            scene_run=scene_run,
            existing_notes=existing_notes,
            gamedata=gamedata,
            cfg=cfg,
        )

    raise ValueError(f"Unknown prompt_format: {prompt_format}")
