from typing import Any, Dict, List

from src.prompts.tool_renderers.compact_tools import render_tools_compact


def _render_scene_summary(scene: Dict[str, Any]) -> str:
    scene_id = scene.get("scene_id", "")
    title = scene.get("title", "")
    location = scene.get("location", "")
    narrative = scene.get("narrative", scene.get("description", ""))

    monster_id = scene.get("monster_id", "")
    knowledge_level = scene.get("knowledge_level", "")

    lines: List[str] = []
    if scene_id:
        lines.append(f"- id: {scene_id}")
    if title:
        lines.append(f"- title: {title}")
    if location:
        lines.append(f"- location: {location}")
    if monster_id:
        lines.append(f"- monster_id: {monster_id}")
    if knowledge_level:
        lines.append(f"- knowledge_level: {knowledge_level}")
    if narrative:
        lines.append(f"- narrative: {narrative}")

    constraints = scene.get("constraints")
    if isinstance(constraints, dict) and constraints:
        items = ", ".join([f"{k}={v}" for k, v in constraints.items()])
        lines.append(f"- constraints: {items}")

    success = scene.get("success_condition")
    if isinstance(success, dict) and success:
        stype = success.get("type")
        if stype:
            lines.append(f"- success_condition: {stype}")
        prefs = success.get("preferred_effects")
        if isinstance(prefs, list) and prefs:
            lines.append(f"- preferred_effects: {prefs}")

    return "\n".join(lines).strip()


def build_json_only_messages(
    scene: Dict[str, Any],
    character: Dict[str, Any],
    visible_tools: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    tool_block = render_tools_compact(visible_tools)
    allowed_tool_ids = [t.get("tool_id", "") for t in visible_tools if t.get("tool_id")]

    char_name = character.get("name", character.get("character_id", "character"))
    char_class = character.get("class", character.get("char_class", "Unknown"))
    inventory = character.get("inventory", [])
    traits = character.get("traits", [])

    scene_summary = _render_scene_summary(scene)

    system = (
        "You are an assistant that must choose exactly ONE tool call.\n"
        "You MUST output ONLY a valid JSON object, with NO extra text, NO markdown.\n"
        "The JSON object must have exactly two keys: tool_id and arguments.\n"
        "tool_id MUST be one of the allowed tool_ids.\n"
        "arguments MUST be an object. Do not include keys not in the tool schema.\n"
        "If a tool has no args, use arguments: {}.\n"
        "IMPORTANT: Any output that is not EXACTLY the JSON object will be rejected.\n"
    )

    user = (
        "CHARACTER:\n"
        f"- name: {char_name}\n"
        f"- class: {char_class}\n"
        f"- inventory: {inventory}\n"
        f"- traits: {traits}\n\n"
        "SCENE:\n"
        f"{scene_summary}\n\n"
        f"ALLOWED tool_id values:\n{allowed_tool_ids}\n\n"
        "VISIBLE TOOLS (schemas):\n"
        f"{tool_block}\n\n"
        "OUTPUT FORMAT (EXACTLY THIS SHAPE):\n"
        '{"tool_id":"<one of the allowed tool_ids>","arguments":{...}}\n'
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]