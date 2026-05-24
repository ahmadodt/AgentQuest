from src.engine.data_utils import resolve_monster_damage_modifiers


def build_invalid_verdict(
    reason: str,
    *,
    reason_code: str | None = None,
    hard_valid=None,
    soft_valid=None,
    outcome: str = "invalid",
    **extra_fields,
) -> dict:
    verdict = {
        "outcome": outcome,
        "reason": reason,
    }
    if reason_code is not None:
        verdict["reason_code"] = reason_code
    if hard_valid is not None:
        verdict["hard_valid"] = hard_valid
    if soft_valid is not None:
        verdict["soft_valid"] = soft_valid
    verdict.update(extra_fields)
    return verdict


def get_character_or_error(gamedata: dict, character_id: str):
    characters_by_id = gamedata["characters_by_id"]
    if character_id not in characters_by_id:
        return None, build_invalid_verdict(
            f"unknown_character: unknown character_id '{character_id}'",
            reason_code="unknown_character",
            hard_valid=False,
        )
    return characters_by_id[character_id], None


def get_tool_or_error(gamedata: dict, tool_id: str, *, layer: str):
    tools_by_id = gamedata["tools_by_id"]
    if tool_id not in tools_by_id:
        verdict_key = "hard_valid" if layer == "hard" else "soft_valid"
        return None, build_invalid_verdict(
            f"unknown_tool: unknown tool_id '{tool_id}'",
            reason_code="unknown_tool",
            **{verdict_key: False},
        )
    return tools_by_id[tool_id], None


def get_scene_or_error(gamedata: dict, scene_id: str):
    scenes_by_id = gamedata["scenes_by_id"]
    if scene_id not in scenes_by_id:
        return None, build_invalid_verdict(
            f"unknown_scene: unknown scene_id '{scene_id}'",
            reason_code="unknown_scene",
            soft_valid=False,
        )
    return scenes_by_id[scene_id], None


def get_monster_for_scene_or_error(gamedata: dict, scene: dict):
    monsters_by_id = gamedata["monsters_by_id"]
    monster_id = scene.get("monster_id")
    if monster_id not in monsters_by_id:
        return None, build_invalid_verdict(
            f"unknown_monster: scene references unknown monster_id '{monster_id}'",
            reason_code="unknown_monster",
            soft_valid=False,
        )
    return monsters_by_id[monster_id], None


def get_tool_constraints(tool: dict) -> dict:
    return tool.get("constraints", {}) or {}


def get_tool_effects(tool: dict) -> dict:
    return tool.get("effects", {}) or {}


def compute_effective_power(tool: dict, monster: dict):
    effects = get_tool_effects(tool)

    damage_type = effects.get("damage_type")
    base_power = effects.get("base_power")
    if damage_type is None or base_power is None:
        return None

    modifiers = monster.get("resolved_damage_modifiers")
    if not isinstance(modifiers, dict):
        modifiers = {}

    if damage_type not in modifiers:
        return {
            "damage_type": damage_type,
            "base_power": base_power,
            "modifier": None,
            "effective_power": None,
        }

    modifier = modifiers[damage_type]

    return {
        "damage_type": damage_type,
        "base_power": base_power,
        "modifier": modifier,
        "effective_power": base_power * modifier,
    }


def get_monster_damage_modifiers(gamedata: dict, monster: dict) -> dict[str, float]:
    return resolve_monster_damage_modifiers(gamedata, monster)
