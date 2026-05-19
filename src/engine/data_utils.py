from typing import Any


def resolve_monster_damage_modifiers(gamedata: dict[str, Any], monster: dict[str, Any]) -> dict[str, float]:
    damage_profile = monster.get("damage_profile")
    profiles_by_id = gamedata.get("damage_profiles_by_id", {})
    base_modifiers = profiles_by_id.get(damage_profile, {})
    overrides = monster.get("damage_modifier_overrides", {}) or {}

    resolved = dict(base_modifiers)
    resolved.update(overrides)
    return resolved
