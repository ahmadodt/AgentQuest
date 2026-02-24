import json
from typing import Any, Dict, List, Optional

from src.prompts.prompt_config import PromptConfig
from src.prompts.tool_renderers.compact_tools import render_tools_compact


def _render_monster(monster: Dict[str, Any], level: str) -> str:
    if level == "none" or not monster:
        return ""

    lines: List[str] = []
    name = monster.get("name", "")
    mtype = monster.get("type", "")
    desc = monster.get("description", "")

    # basic
    if name:
        lines.append(f"- name: {name}")
    if mtype:
        lines.append(f"- type: {mtype}")
    if desc:
        lines.append(f"- description: {desc}")

    if level == "basic":
        return "\n".join(lines).strip()

    # stats (+tags, weaknesses, resistances, immunities, special_rules, escape_allowed)
    tags = monster.get("tags", [])
    weaknesses = monster.get("weaknesses", [])
    resistances = monster.get("resistances", [])
    immunities = monster.get("immunities", [])
    special_rules = monster.get("special_rules", [])

    if tags:
        lines.append(f"- tags: {json.dumps(tags)}")
    if weaknesses:
        lines.append(f"- weaknesses: {json.dumps(weaknesses)}")
    if resistances:
        lines.append(f"- resistances: {json.dumps(resistances)}")
    if immunities:
        lines.append(f"- immunities: {json.dumps(immunities)}")
    if special_rules:
        lines.append(f"- special_rules: {json.dumps(special_rules)}")

    interactions = monster.get("interactions") or {}
    if isinstance(interactions, dict):
        if "escape_allowed" in interactions:
            lines.append(f"- escape_allowed: {json.dumps(interactions.get('escape_allowed'))}")

    if level == "stats":
        return "\n".join(lines).strip()

    # full (everything else in interactions, but still no UI)
    if isinstance(interactions, dict) and interactions:
        # Keep it compact but JSON-shaped
        full_interactions = {k: v for k, v in interactions.items() if k != "escape_allowed"}
        if full_interactions:
            lines.append(f"- interactions: {json.dumps(full_interactions)}")

    return "\n".join(lines).strip()


def _render_scene(scene: Dict[str, Any], cfg: PromptConfig) -> str:
    lines: List[str] = []

    if cfg.include_scene_id and scene.get("scene_id"):
        lines.append(f"- id: {scene['scene_id']}")
    if cfg.include_title and scene.get("title"):
        lines.append(f"- title: {scene['title']}")
    if cfg.include_location and scene.get("location"):
        lines.append(f"- location: {scene['location']}")

    if cfg.include_monster_id and scene.get("monster_id"):
        lines.append(f"- monster_id: {scene['monster_id']}")

    if cfg.include_knowledge_level and scene.get("knowledge_level"):
        lines.append(f"- knowledge_level: {scene['knowledge_level']}")

    if cfg.include_narrative and scene.get("narrative"):
        lines.append(f"- narrative: {scene['narrative']}")

    if cfg.include_success_condition:
        sc = scene.get("success_condition")
        if isinstance(sc, dict) and sc.get("type"):
            lines.append(f"- success_condition: {sc['type']}")
            prefs = sc.get("preferred_effects")
            if isinstance(prefs, list) and prefs:
                lines.append(f"- preferred_effects: {json.dumps(prefs)}")

    if cfg.include_failure_condition:
        fc = scene.get("failure_condition")
        if isinstance(fc, dict) and fc.get("type"):
            lines.append(f"- failure_condition: {fc['type']}")

    # NOTE: scene["constraints"] intentionally NOT rendered (per your decision)
    return "\n".join(lines).strip()


def build_json_only_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
    gamedata: Optional[Dict[str, Any]] = None,
    cfg: Optional[PromptConfig] = None,
) -> List[Dict[str, str]]:
    cfg = cfg or PromptConfig()

    allowed_tool_ids = [t.get("tool_id", "") for t in visible_tools if t.get("tool_id")]
    tool_block = render_tools_compact(visible_tools, cfg)

    # Character
    char_lines = [
        f"- name: {character.get('name', character.get('character_id', 'character'))}",
        f"- class: {character.get('class', character.get('char_class', 'Unknown'))}",
    ]
    if cfg.include_inventory:
        char_lines.append(f"- inventory: {json.dumps(character.get('inventory', []))}")
    if cfg.include_traits:
        char_lines.append(f"- traits: {json.dumps(character.get('traits', []))}")

    # Scene
    scene_block = _render_scene(scene, cfg)

    # Monster block (optional)
    monster_block = ""
    if gamedata and cfg.monster_detail_level != "none":
        mid = scene.get("monster_id")
        if mid and mid in gamedata.get("monsters_by_id", {}):
            monster = gamedata["monsters_by_id"][mid]
            monster_block = _render_monster(monster, cfg.monster_detail_level)

    system = (
        "You are an assistant that must choose exactly ONE tool call.\n"
        "You MUST output ONLY a valid JSON object, with NO extra text, NO markdown.\n"
        "Use double quotes in JSON strings.\n"
        "The JSON object must have exactly two keys: tool_id and arguments.\n"
        "tool_id MUST be one of the allowed tool_ids.\n"
        "arguments MUST be an object. Do not include keys not in the tool schema.\n"
        "If a tool has no args, use arguments: {}.\n"
        "IMPORTANT: Any output that is not EXACTLY the JSON object will be rejected.\n"
    )

    user_parts: List[str] = []
    user_parts.append("CHARACTER:\n" + "\n".join(char_lines))
    user_parts.append("SCENE:\n" + scene_block)

    if monster_block:
        user_parts.append("MONSTER INFO:\n" + monster_block)

    user_parts.append("ALLOWED tool_id values (JSON array):\n" + json.dumps(allowed_tool_ids))
    user_parts.append("VISIBLE TOOLS (schemas):\n" + tool_block)
    user_parts.append(
        "OUTPUT FORMAT (EXACTLY THIS SHAPE):\n"
        '{"tool_id":"<one of the allowed tool_ids>","arguments":{...}}\n'
    )

    user = "\n\n".join(user_parts) + "\n"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]