from typing import Any, Dict, List

from src.prompts.formats.json_only import build_json_only_messages


def build_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
    prompt_format: str = "json_only",
) -> List[Dict[str, str]]:
    if prompt_format == "json_only":
        return build_json_only_messages(scene=scene, character=character, visible_tools=visible_tools)

    raise ValueError(f"Unknown prompt_format: {prompt_format}")