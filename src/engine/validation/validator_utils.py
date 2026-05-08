def build_invalid_verdict(
    reason: str,
    *,
    hard_valid=None,
    soft_valid=None,
    outcome: str = "invalid",
) -> dict:
    verdict = {
        "outcome": outcome,
        "reason": reason,
    }
    if hard_valid is not None:
        verdict["hard_valid"] = hard_valid
    if soft_valid is not None:
        verdict["soft_valid"] = soft_valid
    return verdict


def get_character_or_error(gamedata: dict, character_id: str):
    characters_by_id = gamedata["characters_by_id"]
    if character_id not in characters_by_id:
        return None, build_invalid_verdict(
            f"Unknown character_id '{character_id}'",
            hard_valid=False,
        )
    return characters_by_id[character_id], None


def get_tool_or_error(gamedata: dict, tool_id: str, *, layer: str):
    tools_by_id = gamedata["tools_by_id"]
    if tool_id not in tools_by_id:
        verdict_key = "hard_valid" if layer == "hard" else "soft_valid"
        return None, build_invalid_verdict(
            f"Unknown tool_id '{tool_id}'",
            **{verdict_key: False},
        )
    return tools_by_id[tool_id], None


def get_scene_or_error(gamedata: dict, scene_id: str):
    scenes_by_id = gamedata["scenes_by_id"]
    if scene_id not in scenes_by_id:
        return None, build_invalid_verdict(
            f"Unknown scene_id '{scene_id}'",
            soft_valid=False,
        )
    return scenes_by_id[scene_id], None


def get_monster_for_scene_or_error(gamedata: dict, scene: dict):
    monsters_by_id = gamedata["monsters_by_id"]
    monster_id = scene.get("monster_id")
    if monster_id not in monsters_by_id:
        return None, build_invalid_verdict(
            f"Scene references unknown monster_id '{monster_id}'",
            soft_valid=False,
        )
    return monsters_by_id[monster_id], None


def get_tool_constraints(tool: dict) -> dict:
    return tool.get("constraints", {}) or {}


def get_tool_effects(tool: dict) -> dict:
    return tool.get("effects", {}) or {}


def compute_effective_power(tool: dict, monster: dict):
    effects = get_tool_effects(tool)
    interactions = monster.get("interactions", {}) or {}

    damage_type = effects.get("damage_type")
    base_power = effects.get("base_power")
    if damage_type is None or base_power is None:
        return None

    modifiers = interactions.get("damage_type_modifiers", {}) or {}
    modifier = modifiers.get(damage_type, 1.0)

    return {
        "damage_type": damage_type,
        "base_power": base_power,
        "modifier": modifier,
        "effective_power": base_power * modifier,
    }
