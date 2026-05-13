from __future__ import annotations

from typing import Any, Dict


def _first_sentence(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return ""

    for marker in [". ", "!\n", "? ", ".\n", "!\r\n", "?\r\n"]:
        if marker in stripped:
            sentence, _rest = stripped.split(marker, 1)
            return sentence.strip() + marker[0]

    return stripped


def project_monster_for_llm(monster: Dict[str, Any]) -> Dict[str, Any]:
    interactions = monster.get("interactions") or {}
    projected_interactions = {
        "min_power_to_defeat": interactions.get("min_power_to_defeat"),
        "knowledge_tools_help": interactions.get("knowledge_tools_help"),
        "escape_allowed": interactions.get("escape_allowed"),
    }

    return {
        "monster_id": monster.get("monster_id"),
        "name": monster.get("name", ""),
        "type": monster.get("type", ""),
        "tags": list(monster.get("tags", [])),
        "weaknesses": list(monster.get("weaknesses", [])),
        "resistances": list(monster.get("resistances", [])),
        "immunities": list(monster.get("immunities", [])),
        "special_rules": list(monster.get("special_rules", [])),
        "interactions": projected_interactions,
    }


def project_tool_for_llm(tool: Dict[str, Any]) -> Dict[str, Any]:
    projected = {
        "tool_id": tool.get("tool_id"),
        "label": tool.get("label", ""),
        "description": _first_sentence(tool.get("description", "")) or tool.get("label", ""),
        "category": tool.get("category", ""),
        "args": tool.get("args", {}),
        "constraints": tool.get("constraints", {}),
        "effects": tool.get("effects", {}),
    }

    if "tool_family" in tool:
        projected["tool_family"] = tool["tool_family"]

    return projected
