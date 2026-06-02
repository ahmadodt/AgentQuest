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
    resolved_damage_modifiers = monster.get("resolved_damage_modifiers")
    if isinstance(resolved_damage_modifiers, dict) and resolved_damage_modifiers:
        lines.append(f"- resolved_damage_modifiers: {json.dumps(resolved_damage_modifiers)}")

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

    if cfg.include_scene_constraints:
        constraints = scene.get("constraints")
        if isinstance(constraints, dict):
            lines.append(f"- constraints: {json.dumps(constraints)}")

    if cfg.include_validation_rules:
        validation_rules = scene.get("validation_rules")
        if isinstance(validation_rules, dict):
            lines.append(f"- validation_rules: {json.dumps(validation_rules)}")

    return "\n".join(lines).strip()


def _build_visible_tool_block(
    visible_tools: List[Dict[str, Any]],
    gamedata: Optional[Dict[str, Any]],
    cfg: PromptConfig,
) -> tuple[list[str], str]:
    llm_tools_by_id = (gamedata or {}).get("llm_tools_by_id", {}) if gamedata else {}
    llm_visible_tools = [
        llm_tools_by_id.get(tool.get("tool_id"), tool) for tool in visible_tools
    ]
    allowed_tool_ids = [t.get("tool_id", "") for t in visible_tools if t.get("tool_id")]
    return allowed_tool_ids, render_tools_compact(llm_visible_tools, cfg)


def _build_character_block(character: Dict[str, Any], cfg: PromptConfig) -> str:
    char_lines = [
        f"- name: {character.get('name', character.get('character_id', 'character'))}",
        f"- class: {character.get('class', character.get('char_class', 'Unknown'))}",
    ]
    if cfg.include_inventory:
        char_lines.append(f"- inventory: {json.dumps(character.get('inventory', []))}")
    if cfg.include_traits:
        char_lines.append(f"- traits: {json.dumps(character.get('traits', []))}")
    return "\n".join(char_lines)


def _build_monster_block(
    scene: Dict[str, Any],
    gamedata: Optional[Dict[str, Any]],
    cfg: PromptConfig,
) -> str:
    if not gamedata or cfg.monster_detail_level == "none":
        return ""

    mid = scene.get("monster_id")
    llm_monsters_by_id = gamedata.get("llm_monsters_by_id", {})
    if mid and mid in llm_monsters_by_id:
        return _render_monster(llm_monsters_by_id[mid], cfg.monster_detail_level)
    if mid and mid in gamedata.get("monsters_by_id", {}):
        return _render_monster(gamedata["monsters_by_id"][mid], cfg.monster_detail_level)
    return ""


def build_json_only_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
    gamedata: Optional[Dict[str, Any]] = None,
    cfg: Optional[PromptConfig] = None,
    learning_notes: str = "",
) -> List[Dict[str, str]]:
    cfg = cfg or PromptConfig()
    allowed_tool_ids, tool_block = _build_visible_tool_block(visible_tools, gamedata, cfg)
    char_block = _build_character_block(character, cfg)
    scene_block = _render_scene(scene, cfg)
    monster_block = _build_monster_block(scene, gamedata, cfg)

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
    user_parts.append("CHARACTER:\n" + char_block)
    user_parts.append("SCENE:\n" + scene_block)

    if monster_block:
        user_parts.append("MONSTER INFO:\n" + monster_block)

    if learning_notes.strip():
        user_parts.append(
            "CAMPAIGN NOTES:\n"
            "These are notes from earlier failed attempts in this campaign. "
            "Treat them as optional hypotheses, not facts. "
            "Use them only when they fit the visible context in this scene, and ignore them when they do not.\n"
            + learning_notes.strip()
        )

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


def build_json_only_note_update_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
    scene_run: Dict[str, Any],
    existing_notes: str,
    gamedata: Optional[Dict[str, Any]] = None,
    cfg: Optional[PromptConfig] = None,
) -> List[Dict[str, str]]:
    cfg = cfg or PromptConfig()
    allowed_tool_ids, tool_block = _build_visible_tool_block(visible_tools, gamedata, cfg)
    char_block = _build_character_block(character, cfg)
    scene_block = _render_scene(scene, cfg)
    monster_block = _build_monster_block(scene, gamedata, cfg)
    parsed_tool_call = scene_run.get("parsed_tool_call") or {}

    system = (
        "You maintain compact campaign notes for a learning agent.\n"
        "Return ONLY a valid JSON object with exactly one key: notes.\n"
        'Example: {"notes":"- note one\\n- note two"}\n'
        "Keep only actionable lessons that are grounded in the provided prompt-visible information or the validator result.\n"
        "Do not repeat the same lesson in different words.\n"
        "Do not invent or change tool mechanics, damage, power, cooldowns, requirements, hidden stats, or monster rules.\n"
        "Do not introduce numeric thresholds unless they appear explicitly in the provided prompt-visible information.\n"
        "Because these notes carry into later scenes, prefer transferable lessons over enemy-specific instructions whenever possible.\n"
        "Prefer qualitative guidance instead of copying raw validator mechanics or hidden comparisons.\n"
        "Prefer notes about failed tool choice, visible tool constraints or effects, visible monster traits, and scene-specific constraints.\n"
        "If the failure only shows that one tool was wrong, note what to try or avoid next without guessing extra mechanics.\n"
        "Treat the validator reason as evidence, then rewrite it into natural guidance rather than copying it literally.\n"
    )

    user_parts: List[str] = []
    user_parts.append("CHARACTER:\n" + char_block)
    user_parts.append("SCENE:\n" + scene_block)
    if monster_block:
        user_parts.append("MONSTER INFO:\n" + monster_block)
    user_parts.append("OLD NOTES:\n" + (existing_notes or "(empty)"))
    user_parts.append(
        "FAILED ATTEMPT:\n"
        f"- selected_tool_id: {parsed_tool_call.get('tool_id', '')}\n"
        f"- selected_arguments: {json.dumps(parsed_tool_call.get('arguments') or {})}\n"
        f"- raw_model_output: {scene_run.get('raw_model_output', '')}\n"
        f"- status: {scene_run.get('status', 'FAIL')}\n"
        f"- reason: {scene_run.get('reason', '')}"
    )
    user_parts.append("ALLOWED tool_id values (JSON array):\n" + json.dumps(allowed_tool_ids))
    user_parts.append("VISIBLE TOOLS (schemas):\n" + tool_block)
    user_parts.append(
        "TASK:\n"
        "Revise the notes for the next attempt. Keep them short, non-redundant, grounded in the information shown above, and phrased so they can still help in later scenes without pretending to be universal facts."
    )

    user = "\n\n".join(user_parts) + "\n"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
