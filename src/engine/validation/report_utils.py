import json
from typing import Any

from src.engine.validator import ToolCallValidator


def default_value_for_schema(prop_name: str, spec: dict[str, Any]) -> object:
    if "enum" in spec and isinstance(spec["enum"], list) and spec["enum"]:
        return spec["enum"][0]

    prop_type = spec.get("type")
    if prop_type == "string":
        if prop_name == "direction":
            return "backtrack"
        if prop_name == "surface":
            return "wall"
        return "target"
    if prop_type == "integer":
        return 1
    if prop_type == "number":
        return 1.0
    if prop_type == "boolean":
        return True
    if prop_type == "array":
        return []
    if prop_type == "object":
        return {}
    return "value"


def build_tool_call_for_tool(tool: dict[str, Any]) -> str:
    args_schema = tool.get("args", {}) or {}
    properties = args_schema.get("properties", {}) or {}
    required = args_schema.get("required", []) or []
    arguments = {}
    for key in required:
        spec = properties.get(key, {}) if isinstance(properties.get(key), dict) else {}
        arguments[key] = default_value_for_schema(key, spec)
    return json.dumps({"tool_id": tool["tool_id"], "arguments": arguments}, ensure_ascii=False)


def collect_scene_character_tool_results(
    gamedata: dict[str, Any],
    *,
    scene_id: str,
    character_id: str,
) -> dict[str, list[dict[str, Any]]]:
    character = gamedata["characters_by_id"][character_id]
    tools_by_id = gamedata["tools_by_id"]
    validator = ToolCallValidator(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=scene_id,
        visible_tool_ids=character.get("tool_ids", []),
    )

    valid_tools: list[dict[str, Any]] = []
    invalid_tools: list[dict[str, Any]] = []
    for tool_id in character.get("tool_ids", []):
        tool = tools_by_id[tool_id]
        raw = build_tool_call_for_tool(tool)
        verdict = validator.validate(raw)
        result = {
            "tool_id": tool_id,
            "reason": verdict.get("reason", ""),
            "reason_code": verdict.get("reason_code"),
        }
        if verdict.get("outcome") == "success":
            valid_tools.append(result)
        else:
            invalid_tools.append(result)

    return {
        "valid_tools": valid_tools,
        "invalid_tools": invalid_tools,
    }
